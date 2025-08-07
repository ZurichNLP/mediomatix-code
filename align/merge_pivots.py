import argparse
from ast import literal_eval
from functools import reduce
import os
import re

import pandas as pd

IDIOMS = ["sursilv", "sutsilv", "puter", "vallader", "surmiran"]

PAIRS = [
    "puter-vallader",
    "surmiran-vallader",
    "sursilv-surmiran",
    "sursilv-vallader",
    "sutsilv-surmiran",
    "surmiran-puter",
    "sursilv-puter",
    "sursilv-sutsilv",
    "sutsilv-puter",
    "sutsilv-vallader",
]


def get_args():
    parser = argparse.ArgumentParser(
        "Script to infer alignments through a pivot idiom."
    )

    parser.add_argument("--model", type=str, default="cohere-v4")

    parser.add_argument("--input", type=str, default="text")

    parser.add_argument("--chapter", type=str, required=False)

    parser.add_argument("--val_set_only", action="store_true")

    parser.add_argument(
        "--store_pairwise",
        action="store_true",
        help="By default, the script stores the consensus alignment and the multiparallel for each pivot. If this arg is passed, the inferred pairwise alignments will be isolated from the multiparallel alignment and saved separately.",
    )

    parser.add_argument("--book", type=str, required=False)

    return parser.parse_args()


def parse_indices(s):
    """convert regex matches to lists of indices"""
    s = s.strip()
    if not s:
        return None
    items = [i.strip() for i in s.split(",") if i.strip()]
    return [int(i) for i in items] if items else None


def get_piv_alignment(base_path, chap, label, pivot):
    # get the source-pivot alignment
    out_list = []
    file_path = f"{base_path}/{chap}/{pivot}/{label}_align.txt"
    with open(file_path, "r") as f:
        # We want pivot sent in position 0
        if pivot == label.split("-")[0]:
            correct_order = True
        else:
            correct_order = False

        for line in f:
            # [0]:[]:score
            try:
                match = re.match(r"\[(.*?)\]:\[(.*?)\]:(\d\.\d+)", line)
                left_col, right_col, score = match.groups()
            except:
                match = re.match(r"\[(.*?)\]:\[(.*?)\]", line)
                left_col, right_col = match.groups()
                score=None

            left_idxs = parse_indices(left_col)
            right_idxs = parse_indices(right_col)

            if correct_order:
                # left col corresponds to pivot already
                out_list.append((left_idxs, right_idxs))
            else:
                # put the pivot idiom in the left column
                out_list.append((right_idxs, left_idxs))

        return out_list


def get_df(pivot_alignments, pivot, other):
    rows = []
    for pivots, values in pivot_alignments:
        # Convert nones to empty lists
        pivots = pivots if pivots is not None else [None]
        for p in pivots:
            rows.append({pivot: p, other: values})  # values can be None too
    return pd.DataFrame(rows)


def format_merged(merged, pivot):

    matched = merged[merged[pivot].notna()]
    unmatched = merged[merged[pivot].isna()]

    # one row per idiom only if the idiom's value is not NaN
    columns = merged.columns.drop(pivot)
    individual_rows = []

    for col in columns:
        temp = unmatched[[pivot, col]].copy()
        temp = temp[temp[col].notna()]  # only keep rows where this idiom has a value
        for _, row in temp.iterrows():
            new_row = {c: None for c in merged.columns}
            new_row[pivot] = None
            new_row[col] = row[col]
            individual_rows.append(new_row)

    # Create DataFrame from disaggregated rows
    cleaned_unmatched = pd.DataFrame(individual_rows)

    # Final concat and sort
    final = pd.concat([matched, cleaned_unmatched], ignore_index=True)
    final = final.sort_values(by=pivot, na_position="last").reset_index(drop=True)

    final[pivot] = final[pivot].apply(lambda x: [int(x)] if pd.notna(x) else None)

    # Replace all remaining NaN with None across the whole DataFrame
    final = final.where(pd.notna(final), None)

    # reorder the rows alphabetically so the order is retained across pivots.
    final = final[sorted(final.columns)]

    return final


def merge_two_col_dfs(dfs, pivot):
    from collections import defaultdict

    aligned = defaultdict(dict)
    columns = set([pivot])

    for df in dfs:
        col = [c for c in df.columns if c != pivot][0]
        columns.add(col)
        for _, row in df.iterrows():
            aligned[row[pivot]][col] = row[col]

    # Build a new DataFrame from the aligned dictionary
    rows = []
    for piv_val, idioms in aligned.items():
        row = {pivot: piv_val}
        row.update(idioms)
        rows.append(row)
    final = pd.DataFrame(rows, columns=sorted(columns))

    return final


def main(args):
    # load the alignments with each pivot lang:
    if args.val_set_only:

        base_path = f"/projects/text/romansh/textbooks/val_test/align_02/{args.input}/{args.model}"
        alignments = {}

        for pivot in IDIOMS:
            temp = []
            for hyp in os.listdir(f"{base_path}/{args.chapter}/{pivot}"):
                if pivot in hyp:
                    # get the alignments with the pivot idiom
                    idiom1 = hyp.split("_")[0].split("-")[0]
                    idiom2 = hyp.split("_")[0].split("-")[1]
                    hyp_align = get_piv_alignment(
                        base_path, args.chapter, hyp.split("_")[0], pivot
                    )

                    other = idiom1 if idiom1 != pivot else idiom2
                    # turn into a df
                    hyp_align = get_df(hyp_align, pivot, other)

                    temp.append(hyp_align)

            # merge all the alignments with the pivot using the pivot as a key
            merged_hyp = merge_two_col_dfs(temp, pivot)
            # Wrap the 'pivot' column in a list, and convert NaN to None afterward
            merged_hyp = format_merged(merged_hyp, pivot)

            # Get rid of any duplicates in the multiparallel alignment by making it a set of strings
            out_hyp = set()
            for i in range(len(merged_hyp)):
                out_hyp.add(str(list(merged_hyp.iloc[i])))

            # Add the set of set of strings to the dictionary with this pivot idiom as the key
            alignments[pivot] = out_hyp

            # Save the multiparallel dataset:
            os.makedirs(f"{base_path}/{args.chapter}/{pivot}", exist_ok=True)
            with open(f"{base_path}/{args.chapter}/{pivot}/merged.txt", "w") as f:
                for line in out_hyp:
                    parsed = literal_eval(line)
                    output = ":".join(
                        str(item) if item is not None else "[]" for item in parsed
                    )
                    f.write(output + "\n")

            # Save the pairwise versions if arg passed
            if args.store_pairwise:
                for pair in PAIRS:
                    idiom1 = pair.split("-")[0]
                    idiom2 = pair.split("-")[1]
                    # Select the pair from the multiparallel dataset
                    pair_align = merged_hyp[[idiom1, idiom2]]
                    out = set()
                    for i in range(len(pair_align)):
                        out.add(str(list(pair_align.iloc[i])))
                    with open(
                        f"{base_path}/{args.chapter}/{pivot}/{pair}_align.txt", "w"
                    ) as f:
                        for line in out:
                            parsed = literal_eval(line)
                            output = ":".join(
                                str(item) if item is not None else "[]"
                                for item in parsed
                            )
                            f.write(output + "\n")

        # Consensus:
        intersection = reduce(set.intersection, alignments.values())

        os.makedirs(f"{base_path}/{args.chapter}/consensus", exist_ok=True)
        # save consensus alignment
        with open(f"{base_path}/{args.chapter}/consensus/merged.txt", "w") as f:
            for line in intersection:
                parsed = literal_eval(line)
                output = ":".join(
                    str(item) if item is not None else "[]" for item in parsed
                )
                f.write(output + "\n")
        # Save the pairwise consensus if the arg is passed:
        if args.store_pairwise:
            col = sorted(IDIOMS)
            for pair in PAIRS:
                idiom1 = pair.split("-")[0]
                idiom2 = pair.split("-")[1]
                with open(
                    f"{base_path}/{args.chapter}/consensus/{pair}_align.txt", "w"
                ) as f:
                    for line in intersection:
                        parsed = literal_eval(line)
                        output = ":".join(
                            str(item) if item is not None else "[]"
                            for item in [
                                parsed[col.index(idiom1)],
                                parsed[col.index(idiom2)],
                            ]
                        )
                        f.write(output + "\n")

    else:
        base_path = f"/projects/text/romansh/textbooks/final/TEST"

        for chap in os.listdir(f"{base_path}/{args.book}"):

            print(f"Processing {args.book}/{chap}")
            alignments = {}
            chap_idioms = []
            for idiom in IDIOMS:
                # if the pivot doesn't exist, skip it
                if os.path.isdir(f"{base_path}/{args.book}/{chap}/{idiom}/"):
                    chap_idioms.append(idiom)
            if len(chap_idioms) < 2:
                print(f"Skipping {args.book}/{chap} as not enough idioms found")
                continue
            for pivot in chap_idioms:
                temp = []
                for hyp in os.listdir(f"{base_path}/{args.book}/{chap}/{pivot}"):
                    if pivot in hyp:
                        idiom1 = hyp.split("_")[0].split("-")[0]
                        idiom2 = hyp.split("_")[0].split("-")[1]
                        hyp_align = get_piv_alignment(
                            base_path + f"/{args.book}", chap, hyp.split("_")[0], pivot
                        )

                        other = idiom1 if idiom1 != pivot else idiom2
                        hyp_align = get_df(hyp_align, pivot, other)

                        temp.append(hyp_align)
                # merge everything
                merged_hyp = merge_two_col_dfs(temp, pivot)

                # Wrap the 'pivot' column in a list, and convert NaN to None afterward
                merged_hyp = format_merged(merged_hyp, pivot)

                out_hyp = set()
                for i in range(len(merged_hyp)):
                    out_hyp.add(str(list(merged_hyp.iloc[i])))

                # Save the merged pivot alignments
                with open(
                    f"{base_path}/{args.book}/{chap}/{pivot}/merged.txt", "w"
                ) as f:
                    for line in out_hyp:
                        parsed = literal_eval(line)
                        output = ":".join(
                            str(item) if item is not None else "[]" for item in parsed
                        )
                        f.write(output + "\n")
                # Save the pairwise version of the multiparallel corpus if requested
                if args.store_pairwise:
                    for pair in PAIRS:
                        idiom1 = pair.split("-")[0]
                        idiom2 = pair.split("-")[1]
                        if idiom1 in chap_idioms and idiom2 in chap_idioms:
                            # Select the pair from the multiparallel dataset
                            pair_align = merged_hyp[[idiom1, idiom2]]
                            out = set()
                            for i in range(len(pair_align)):
                                out.add(str(list(pair_align.iloc[i])))
                            with open(
                                f"{base_path}/{args.book}/{chap}/{pivot}/{pair}_align.txt", "w"
                            ) as f:
                                for line in out:
                                    parsed = literal_eval(line)
                                    output = ":".join(
                                        str(item) if item is not None else "[]"
                                        for item in parsed
                                    )
                                    f.write(output + "\n")

                # Add the set of row strings to the dictionary with this pivot idiom as the key
                alignments[pivot] = out_hyp

            intersection = reduce(set.intersection, alignments.values())
            # Save consensus
            os.makedirs(f"{base_path}/{args.book}/{chap}/consensus/", exist_ok=True)
            with open(f"{base_path}/{args.book}/{chap}/consensus/merged.txt", "w") as f:
                for line in intersection:
                    parsed = literal_eval(line)
                    output = ":".join(
                        str(item) if item is not None else "[]" for item in parsed
                    )
                    f.write(output + "\n")
            # Save pairwise consensus
            if args.store_pairwise:
                col = sorted(chap_idioms)
                for pair in PAIRS:
                    idiom1 = pair.split("-")[0]
                    idiom2 = pair.split("-")[1]
                    if idiom1 in chap_idioms and idiom2 in chap_idioms:
                        with open(
                            f"{base_path}/{args.book}/{chap}/consensus/{pair}_align.txt",
                            "w",
                        ) as f:
                            for line in intersection:
                                parsed = literal_eval(line)
                                output = ":".join(
                                    str(item) if item is not None else "[]"
                                    for item in [
                                        parsed[col.index(idiom1)],
                                        parsed[col.index(idiom2)],
                                    ]
                                )
                                f.write(output + "\n")


if __name__ == "__main__":
    args = get_args()
    # If the val set is false, we need a book
    if args.val_set_only:
        assert args.chapter, "You must add a chapter if working with the validation set"
    else:
        assert (
            args.book
        ), "You must add a book title if not working with the validation set"

    main(args)

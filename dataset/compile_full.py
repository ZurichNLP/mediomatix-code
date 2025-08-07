"""Compile all the chapters' alignments into the final jsonl dataset.
The pivot arg controls which of the multiparalllel corpora is compiled (i.e., the multiparallel corpus formed with a certain pivot idiom or all of the pivots' consensus).
Filters segments in beads that are too long or too short relative to the rest of the segments in the bead.
If the "--clean" arg is passed, will do post-processing happens (removal of remaining markup, beads that contain URLs, etc).
"""

import argparse
from ast import literal_eval
import json
import os
import re

from tqdm import tqdm


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--pivot",
        type=str,
        default="consensus",
        choices=["consensus", "puter", "surmiran", "sursilv", "sutsilv", "vallader"],
    )
    parser.add_argument("--clean", action="store_true")

    parser.add_argument(
        "--out_dir",
        type=str,
        required=True,
        help="Dir in which the compiled dataset should be stored",
    )

    parser.add_argument(
        "--text_dir",
        type=str,
        required=True,
        help="Path to the text files for each chapter made by get_text.py",
    )

    parser.add_argument(
        "--align_dir",
        type=str,
        required=True,
        help="directory containing subdirs with each books' pivot alignments.",
    )

    return parser.parse_args()


def get_bead(bead):
    list_bead = literal_eval(bead)
    return list_bead[0] if len(list_bead) > 0 else None


def main(args):
    base = args.out_dir
    text_path = args.text_dir
    align_path = args.align_dir

    # list of dictionary, fields for each idiom, book, and chapter
    out_data = []

    # Loop through all the books
    for book in tqdm(os.listdir(align_path), desc="Processing books"):
        print(f"Processing book: {book}")
        # loop through all the chapters in the book:
        for chap in os.listdir(f"{align_path}/{book}"):
            print(f"Processing chapter: {chap}")
            # Get the idioms for which this chapter exists
            if not os.path.isfile(
                f"{align_path}/{book}/{chap}/{args.pivot}/merged.txt"
            ):
                continue

            columns = []
            for i in ["puter", "surmiran", "sursilv", "sutsilv", "vallader"]:
                if os.path.isfile(f"{text_path}/{book}/{chap}/rm-{i}_text.txt"):
                    columns.append(i)
            columns = sorted(columns)

            with open(
                f"{align_path}/{book}/{chap}/{args.pivot}/merged.txt", "r"
            ) as f_hyp:
                texts = {}
                for col in columns:
                    with open(
                        f"{text_path}/{book}/{chap}/rm-{col}_text.txt",
                        "r",
                        encoding="utf-8",
                    ) as f_text:
                        texts[f"rm-{col}"] = [line.strip() for line in f_text]

                # loop through alignmnet lines:
                for bead in f_hyp:
                    temp = {}
                    split_bead = bead.strip().split(":")
                    assert len(split_bead) == len(columns)

                    idiom_keys = ["sursilv", "sutsilv", "surmiran", "puter", "vallader"]
                    none_count = 0

                    for idiom in idiom_keys:
                        key = f"rm-{idiom}"
                        if texts.get(key):
                            seg = get_bead(split_bead[columns.index(idiom)])
                            if seg:
                                temp[key] = texts[key][seg]
                            else:
                                temp[key] = None
                                none_count += 1
                        else:
                            temp[key] = None
                            none_count += 1
                    if args.clean:
                        # Collect all idiom data (non-None values) from temp
                        idiom_texts = [
                            temp.get(f"rm-{idiom}")
                            for idiom in [
                                "puter",
                                "surmiran",
                                "sursilv",
                                "sutsilv",
                                "vallader",
                            ]
                            if temp.get(f"rm-{idiom}") is not None
                        ]

                        html_tag_pattern = re.compile(r"</?strong>", re.IGNORECASE)
                        punc_pattern = re.compile(r"[:()]", re.IGNORECASE)
                        url_pattern = re.compile(r"https?://\S+")

                        # Get rid of URLs
                        if any(url_pattern.search(text) for text in idiom_texts):
                            continue

                        # Strip HTML from each idiom text before checking its length so we don't get "<strong>A</strong>"
                        cleaned_idiom_texts = [
                            html_tag_pattern.sub("", text) for text in idiom_texts
                        ]
                        cleaned_idiom_texts = [
                            punc_pattern.sub("", text) for text in cleaned_idiom_texts
                        ]

                        # If all cleaned idiom texts are only one character long, skip:
                        if cleaned_idiom_texts and all(
                            len(text) == 1 for text in cleaned_idiom_texts
                        ):
                            continue

                        # If none of the idiom texts contain any word character, skip:
                        if cleaned_idiom_texts and not any(
                            re.search(r"[a-zA-ZÀ-ÖØ-öø-ÿ]", text)
                            for text in cleaned_idiom_texts
                        ):
                            continue

                        # If any idiom data point contains a word with more than one underscore, skip this bead. (might represent an exercise where letter's are filled in a word)
                        found_invalid = False
                        for text in idiom_texts:
                            # Remove any <strong> or </strong> tags before checking
                            clean_text = re.sub(r"</?strong>", "", text)
                            for word in clean_text.split():
                                if word.count("_") > 1:
                                    found_invalid = True
                                    break
                            if found_invalid:
                                break
                        if found_invalid:
                            continue

                        # skip if the whole cleaned idiom text is just 2+ enum fragments (e.g. 'd) 1.', '11. 12.')
                        enum_frag = re.compile(r"(?:[a-zA-Z]\)|\d+\.)")
                        for text in cleaned_idiom_texts:
                            matches = enum_frag.findall(text.strip())
                            if (
                                len(matches) >= 2
                                and enum_frag.sub("", text.strip()).strip() == ""
                            ):
                                continue  # skip if all content is enum-like fragments

                        # Replace nonbreaking spaces with regular spaces
                        for key in temp:
                            if temp[key] is not None:
                                temp[key] = temp[key].replace("\xa0", " ")

                        # Clean <strong> tags so they just include <strong>
                        for key in temp:
                            if temp[key] is not None:
                                temp[key] = re.sub(
                                    r"<strong\b[^>]*>", "<strong>", temp[key]
                                )

                    # Apply length-based filter
                    if none_count < 4:
                        non_none_values = [
                            temp[key] for key in temp if temp[key] is not None
                        ]
                        avg_length = sum(
                            len(temp[key]) for key in temp if temp[key] is not None
                        ) / len(non_none_values)
                        for key in temp:
                            if temp[key] is not None and (
                                len(temp[key]) > avg_length * 1.5
                                or len(temp[key]) < avg_length * 0.67
                            ):
                                temp[key] = None
                        # update none_count in case we removed any values.
                        none_count = sum(1 for key in temp if temp[key] is None)

                    # Don't add data point to parallel dataset if there are no parallel data points (bc only one idiom has data)
                    if none_count < 4:
                        temp["book"] = book
                        temp["chapter"] = chap
                        # temp['isbn'] = BOOKS[]
                        out_data.append(temp)

    # Write the output to a jsonl file
    if args.clean:
        out_file = f"{base}/full_dataset/{args.pivot}/mediomatix_filtered.jsonl"
    else:
        out_file = f"{base}/full_dataset/{args.pivot}/mediomatix.jsonl"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f_out:
        for item in out_data:
            f_out.write(json.dumps(item, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    args = get_args()
    main(args)

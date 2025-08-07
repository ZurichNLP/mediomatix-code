"""Prints Table X for the validation set's descriptive statistics."""

from collections import Counter

import pandas as pd

from load_val_set import load_val_set

val_set = load_val_set()

if __name__ == "__main__":
    # Initialize data; list for where each chapter is an {idiom:count} dict
    seg_count = []
    tok_count = []
    single_count = []
    del_count = []
    many_count = []

    for chap in val_set:
        seg_temp = Counter()
        tok_temp = Counter()
        single_temp = Counter()
        del_temp = Counter()
        many_temp = Counter()
        data = val_set[chap]

        # Iterate over each row in the chapter
        for row in data:
            for idiom in [
                "rm-sursilv",
                "rm-sutsilv",
                "rm-surmiran",
                "rm-puter",
                "rm-vallader",
            ]:
                if len(row[idiom]) == 1 and row[idiom][0] == None:
                    del_temp[idiom] += 1
                else:
                    # Count Segments
                    seg_temp[idiom] += len(row[idiom])
                    # Count Tokens divided on whitespace
                    for seg in row[idiom]:
                        tok_temp[idiom] += len(seg.split())
                    if len(row[idiom]) == 1:
                        single_temp[idiom] += 1
                    else:
                        # more than one seg in the bead
                        many_temp[idiom] += 1
        seg_count.append(seg_temp)
        tok_count.append(tok_temp)
        single_count.append(single_temp)
        many_count.append(many_temp)
        del_count.append(del_temp)

    final = {}
    # Sum all the counts across the chap in the val set
    seg_total = Counter()
    for c in seg_count:
        seg_total += c

    tok_total = Counter()
    for c in tok_count:
        tok_total += c

    single_total = Counter()
    for c in single_count:
        single_total += c

    del_total = Counter()
    for c in del_count:
        del_total += c

    many_total = Counter()
    for c in many_count:
        many_total += c

    final["seg_count"] = seg_total
    final["tok_count"] = tok_total
    final["single_count"] = single_total
    final["del_count"] = del_total
    final["many_count"] = many_total

    # Print table
    df = pd.DataFrame(
        {
            "Segments": pd.Series(final["seg_count"]),
            "Tokens": pd.Series(final["tok_count"]),
            "Single": pd.Series(final["single_count"]),
            "Deletions": pd.Series(final["del_count"]),
            "Many": pd.Series(final["many_count"]),
        }
    )

    desired_order = [
        "rm-sursilv",
        "rm-sutsilv",
        "rm-surmiran",
        "rm-puter",
        "rm-vallader",
    ]
    df = df.loc[desired_order]

    df = df.rename(
        index={
            "rm-sursilv": "Sursilvan",
            "rm-sutsilv": "Sutsilvan",
            "rm-surmiran": "Surmiran",
            "rm-puter": "Puter",
            "rm-vallader": "Vallader",
        }
    )

    # Print LaTeX table
    latex_table = df.to_latex(
        column_format="lrrrrr",
        index=True,
        header=True,
        bold_rows=False,
        caption="Counts by idiom",
        label="tab:idiom_counts",
        escape=False,
    )

    print(latex_table)

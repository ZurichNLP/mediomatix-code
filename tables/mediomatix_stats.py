"""Collect stats for final dataset and print out latex formatted Table"""

import argparse
from collections import Counter, defaultdict
import json

from tqdm import tqdm

from load_textbooks import load_textbooks

base_dir = "/projects/text/romansh/textbooks/final/full_dataset/consensus"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect stats for final dataset")
    parser.add_argument("--file_name", type=str, default="mediomatix_filtered.jsonl")
    parser.add_argument(
        "--splits",
        action="store_true",
        help="If passed, the counts in the table will be divided according to their dataset split",
    )
    args = parser.parse_args()
    stats = {
        "train": Counter(),
        "val": Counter(),
        "test": Counter(),
        "no_surm": Counter(),
    }

    books = {
        "train": defaultdict(set),
        "val": defaultdict(set),
        "test": defaultdict(set),
        "no_surm": defaultdict(set),
    }

    with open(f"{base_dir}/{args.file_name}", "r", encoding="utf-8") as f:
        for line in tqdm(f, desc="Processing lines"):
            data = json.loads(line)

            if data["book"].startswith("2") or data["book"].startswith("3"):
                split = "train"
            elif data["book"].startswith("4"):
                split = "val"
            elif data["book"].startswith("5"):
                split = "test"
            elif data["book"][0] in ["6", "7", "8", "9"]:
                split = "no_surm"
            else:
                raise ValueError(f"Unexpected book number: {data['book']}")

            for key, value in data.items():
                if key not in ["book", "chapter"]:

                    if value:
                        stats[split][f"{key}_seg"] += 1
                        stats[split][f"{key}_tok"] += len(value.split())
                        books[split][f"{key}"].add(data["book"])

    stats["total"] = stats["train"] + stats["val"] + stats["test"] + stats["no_surm"]
    idiom_keys = ["rm-sursilv", "rm-sutsilv", "rm-surmiran", "rm-puter", "rm-vallader"]
    books_total = {}
    for idiom in idiom_keys:
        books_total[idiom] = (
            books["train"].get(idiom, set())
            | books["val"].get(idiom, set())
            | books["test"].get(idiom, set())
            | books["no_surm"].get(idiom, set())
        )
    books["total"] = books_total

    textbooks = load_textbooks()

    overall_stats = {
        "train": Counter(),
        "val": Counter(),
        "test": Counter(),
        "no_surm": Counter(),
    }

    for tb in tqdm(textbooks, desc="Processing textbooks"):
        title = f"{textbooks[tb].grade_volume}_{'wb' if textbooks[tb].book_type=='workbook' else 'tc'}"
        idiom = textbooks[tb].idiom

        if title.startswith("2") or title.startswith("3"):
            split = "train"
        elif title.startswith("4"):
            split = "val"
        elif title.startswith("5"):
            split = "test"
        elif title[0] in ["6", "7", "8", "9"]:
            split = "no_surm"
        else:
            raise ValueError(f"Unexpected book number: {data['book']}")

        if title in books[split][idiom]:
            for line in textbooks[tb].hf_dataset:
                overall_stats[split][f"{idiom}_seg"] += 1
                overall_stats[split][f"{idiom}_tok"] += len(
                    line["sentenceExtractedText"].split()
                )

    overall_stats["total"] = (
        overall_stats["train"]
        + overall_stats["val"]
        + overall_stats["test"]
        + overall_stats["no_surm"]
    )

    correspondance = {
        "rm-sursilv": "Sursilvan",
        "rm-sutsilv": "Sutsilvan",
        "rm-surmiran": "Surmiran",
        "rm-puter": "Puter",
        "rm-vallader": "Vallader",
    }
    # Get Totals

    total_books = (
        len(books["total"]["rm-sursilv"])
        + len(books["total"]["rm-sutsilv"])
        + len(books["total"]["rm-surmiran"])
        + len(books["total"]["rm-puter"])
        + len(books["total"]["rm-vallader"])
    )
    total_overall_seg = (
        overall_stats["total"]["rm-puter_seg"]
        + overall_stats["total"]["rm-surmiran_seg"]
        + overall_stats["total"]["rm-sursilv_seg"]
        + overall_stats["total"]["rm-sutsilv_seg"]
        + overall_stats["total"]["rm-vallader_seg"]
    )
    total_aligned_seg = (
        stats["total"]["rm-puter_seg"]
        + stats["total"]["rm-surmiran_seg"]
        + stats["total"]["rm-sursilv_seg"]
        + stats["total"]["rm-sutsilv_seg"]
        + stats["total"]["rm-vallader_seg"]
    )
    total_overall_tok = (
        overall_stats["total"]["rm-puter_tok"]
        + overall_stats["total"]["rm-surmiran_tok"]
        + overall_stats["total"]["rm-sursilv_tok"]
        + overall_stats["total"]["rm-sutsilv_tok"]
        + overall_stats["total"]["rm-vallader_tok"]
    )
    total_aligned_tok = (
        stats["total"]["rm-puter_tok"]
        + stats["total"]["rm-surmiran_tok"]
        + stats["total"]["rm-sursilv_tok"]
        + stats["total"]["rm-sutsilv_tok"]
        + stats["total"]["rm-vallader_tok"]
    )

    if args.splits:
        print(
            "\\textbf{Idiom} & \\textbf{Book Volumes} & \\textbf{Aligned Segments} & \\textbf{Aligned Tokens} \\\\ \\midrule"
        )
        for idiom in correspondance.keys():
            # Book volumes per split
            books_split = [
                len(books["train"][idiom]),
                len(books["val"][idiom]),
                len(books["test"][idiom]),
                len(books["no_surm"][idiom]),
            ]
            books_str = f"{books_split[0]} / {books_split[1]} / {books_split[2]} / {books_split[3]}"

            # Segments per split
            seg_split = [
                stats["train"][f"{idiom}_seg"],
                stats["val"][f"{idiom}_seg"],
                stats["test"][f"{idiom}_seg"],
                stats["no_surm"][f"{idiom}_seg"],
            ]
            seg_str = f"{seg_split[0]:,} / {seg_split[1]:,} / {seg_split[2]:,} / {seg_split[3]:,}"

            # Tokens per split
            tok_split = [
                stats["train"][f"{idiom}_tok"],
                stats["val"][f"{idiom}_tok"],
                stats["test"][f"{idiom}_tok"],
                stats["no_surm"][f"{idiom}_tok"],
            ]
            tok_str = f"{tok_split[0]:,} / {tok_split[1]:,} / {tok_split[2]:,} / {tok_split[3]:,}"

            print(f"{correspondance[idiom]} & {books_str} & {seg_str} & {tok_str} \\\\")
        print("\\bottomrule")
    else:
        # Overall, no splits
        print(
            "\\textbf{Idiom} & \\textbf{Book volumes} & \\multicolumn{2}{c}{\\textbf{Segments}} & \\multicolumn{2}{c}{\\textbf{Tokens}} \\\\"
        )
        print(
            "& (workbook + commentary) & Overall & Aligned      & Overall & Aligned \\\\ \\midrule"
        )
        for idiom in list(correspondance.keys()):
            print(
                f"{correspondance[idiom]} & {len(books['total'][idiom])} & {overall_stats['total'][f'{idiom}_seg']:,} & {stats['total'][f'{idiom}_seg']:,} & {overall_stats['total'][f'{idiom}_tok']:,} & {stats['total'][f'{idiom}_tok']:,} \\\\"
            )
        print("\\midrule")
        print(
            f"\\textbf{{Total}} & \\textbf{{{total_books}}} & \\textbf{{{total_overall_seg:,}}} & \\textbf{{{total_aligned_seg:,}}} & \\textbf{{{total_overall_tok:,}}} & \\textbf{{{total_aligned_tok:,}}} \\\\ \\bottomrule"
        )

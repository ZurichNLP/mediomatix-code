"""A script to randomly select sample of the complete dataset for manual evaluation.
Expects a jsonl dataset with the fields 'rm-puter','rm-surmiran','rm-sursilv','rm-sutsilv','rm-valalder','book','chapter'

Will output a csv with a column for each idiom.
"""

import argparse
import csv
import json
import random


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data_path",
        type=str,
        default="/projects/text/romansh/textbooks/final/full_dataset/consensus/mediomatix_filtered.jsonl",
    )

    parser.add_argument("--sample_size", type=int, default=100)

    parser.add_argument(
        "--eval_split",
        help="grade level to take as eval sample",
        type=str,
        choices=["2", "3", "4", "5", "6", "7", "8", "9"],
        default="5",
    )

    return parser.parse_args()


def main(args):
    with open(args.data_path, "r", encoding="utf-8") as f:
        data = [json.loads(line) for line in f]

    if args.sample_size > len(data):
        raise ValueError("Sample size cannot be larger than the dataset size.")

    eval = [row for row in data if args.eval_split == row.get("book").split(".")[0]]

    sampled_data = random.sample(eval, args.sample_size)

    output_data = []
    for item in sampled_data:
        output_row = {
            "rm-sursilv": item.get("rm-sursilv", ""),
            "rm-sutsilv": item.get("rm-sutsilv", ""),
            "rm-surmiran": item.get("rm-surmiran", ""),
            "rm-puter": item.get("rm-puter", ""),
            "rm-vallader": item.get("rm-vallader", ""),
            "book": item.get("book", ""),
            "chapter": item.get("chapter", ""),
        }
        output_data.append(output_row)

    with open("eval_samp.csv", "w", newline="") as csvfile:
        fieldnames = output_data[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_data)


if __name__ == "__main__":
    args = get_args()
    main(args)

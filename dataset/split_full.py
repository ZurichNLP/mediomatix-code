"""Split full aligned mediomatix dataset"""

import argparse
import json
import os

from tqdm import tqdm

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data_path",
        type=str,
        default="/projects/text/romansh/textbooks/final/full_dataset/consensus/mediomatix_filtered.jsonl",
    )

    args = parser.parse_args()

    test = []

    valid = []

    train = []

    no_surm = []

    with open(args.data_path, "r", encoding="utf-8") as f:
        data = [json.loads(line) for line in f]

        for line in tqdm(data, desc="Divvying up lines between splits"):
            if line["book"].startswith("2") or line["book"].startswith("3"):
                train.append(line)
            elif line["book"].startswith("4"):
                valid.append(line)
            elif line["book"].startswith("5"):
                test.append(line)
            elif line["book"][0] in ["6", "7", "8", "9"]:
                # Keep the surm line for consistency
                # del line['rm-surmiran']
                no_surm.append(line)
            else:
                raise ValueError(f"Unexpected book number: {line['book']}")

    base_out = "/projects/text/romansh/textbooks/final/full_dataset/consensus/"
    os.makedirs(f"{base_out}/split_filtered", exist_ok=True)
    with open(
        f"{base_out}/split_filtered/train.jsonl", "w", encoding="utf-8"
    ) as f_train:
        for item in train:
            f_train.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(
        f"{base_out}/split_filtered/valid.jsonl", "w", encoding="utf-8"
    ) as f_valid:
        for item in valid:
            f_valid.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(f"{base_out}/split_filtered/test.jsonl", "w", encoding="utf-8") as f_test:
        for item in test:
            f_test.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(
        f"{base_out}/split_filtered/no_surm.jsonl", "w", encoding="utf-8"
    ) as f_no_surm:
        for item in no_surm:
            f_no_surm.write(json.dumps(item, ensure_ascii=False) + "\n")

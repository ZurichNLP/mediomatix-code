import csv
from pathlib import Path

from datasets import load_dataset

mediomatix = load_dataset('ZurichNLP/mediomatix')
val_set = mediomatix['validation']

idioms = ["rm-sursilv", "rm-sutsilv", "rm-surmiran", "rm-puter", "rm-vallader"]

seed = 123
val_set = val_set.shuffle(seed=seed)

# Filter out rows with missing translations
val_set = val_set.filter(lambda x: all(x[idiom] for idiom in idioms))

# Filter out rows outside of the length range 50–100 characters for each idiom
val_set = val_set.filter(lambda x: all(len(x[idiom]) >= 50 and len(x[idiom]) <= 100 for idiom in idioms))

num_few_shots = 3

out_dir = Path("few_shots")
assert out_dir.exists(), f"Output directory {out_dir} does not exist."

out_path = out_dir / "romansh_few_shots.tsv"

few_shots = val_set.select(range(num_few_shots))

with open(out_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=idioms, delimiter="\t")
    writer.writeheader()
    for row in few_shots:
        writer.writerow({idiom: row[idiom] for idiom in idioms})
print(f"Few-shot examples saved to {out_path}")

from pathlib import Path

from datasets import load_dataset

mediomatix = load_dataset('ZurichNLP/mediomatix')
test_set = mediomatix['test']

idioms = ["rm_sursilv", "rm_sutsilv", "rm_surmiran", "rm_puter", "rm_vallader"]

seed = 123
test_set = test_set.shuffle(seed=seed)

# Filter out rows with missing translations
test_set = test_set.filter(lambda x: all(x[idiom.replace("_", "-")] is not None for idiom in idioms))

max_test = 500
test_set = test_set.select(range(min(max_test, len(test_set))))

out_dir = Path("testset_mediomatix")
assert out_dir.exists(), f"Output directory {out_dir} does not exist."

for src_idiom in idioms:
    for tgt_idiom in idioms:
        if src_idiom == tgt_idiom:
            continue

        out_path = out_dir / f"wmttest2024.src.{src_idiom}-{tgt_idiom}.xml.no-testsuites.{src_idiom}"
        with open(out_path, "w", encoding="utf-8") as f:
            for row in test_set:
                src_text = row[src_idiom.replace("_", "-")]
                f.write(src_text.replace("\n", " ") + "\n")

import subprocess

result = subprocess.run(
    "wc -l *",
    cwd=out_dir,
    capture_output=True,
    text=True,
    shell=True
)
print(result.stdout)

from pathlib import Path
import random

from datasets import load_dataset
import jsonlines

from mt_experiment.tools import prompts


mediomatix = load_dataset('ZurichNLP/mediomatix')
train_set = mediomatix['train']
val_set = mediomatix['validation']

idioms = ["rm_sursilv", "rm_sutsilv", "rm_surmiran", "rm_puter", "rm_vallader"]

seed = 123

# Filter out rows with missing translations
train_set = train_set.filter(lambda x: all(x[idiom.replace("_", "-")] is not None for idiom in idioms))
val_set = val_set.filter(lambda x: all(x[idiom.replace("_", "-")] is not None for idiom in idioms))

max_train = 250  # per direction
max_val = 25  # per direction

out_dir = Path("finetuning_data")
assert out_dir.exists(), f"Output directory {out_dir} does not exist."

train_lines = []
valid_lines = []

for i, src_idiom in enumerate(idioms):
    for j, tgt_idiom in enumerate(idioms):
        if src_idiom == tgt_idiom:
            continue

        train_set = train_set.shuffle(seed=int(str(seed) + str(i) + str(j)))
        val_set = val_set.shuffle(seed=int(str(seed) + str(i) + str(j)))

        train_samples = train_set.select(range(min(max_train, len(train_set))))
        val_samples = val_set.select(range(min(max_val, len(val_set))))

        for row in train_samples:
            src_text = row[src_idiom.replace("_", "-")]
            tgt_text = row[tgt_idiom.replace("_", "-")]
            prompt = prompts.get_prompt(src_text, src_idiom, tgt_idiom, "conversation")
            prompt.append({"role": "assistant", "content": f"```{tgt_text}```"})
            train_lines.append({"messages": prompt})
        for row in val_samples:
            src_text = row[src_idiom.replace("_", "-")]
            tgt_text = row[tgt_idiom.replace("_", "-")]
            prompt = prompts.get_prompt(src_text, src_idiom, tgt_idiom, "conversation")
            prompt.append({"role": "assistant", "content": f"```{tgt_text}```"})
            valid_lines.append({"messages": prompt})

random.shuffle(train_lines)
random.shuffle(valid_lines)

with jsonlines.open(out_dir / "train.jsonl", mode='w') as writer:
    for line in train_lines:
        writer.write(line)

with jsonlines.open(out_dir / "valid.jsonl", mode='w') as writer:
    for line in valid_lines:
        writer.write(line)
print(f"Exported {len(train_lines)} training samples and {len(valid_lines)} validation samples to {out_dir}.")

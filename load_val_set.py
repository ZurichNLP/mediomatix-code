"""Load HF DatasetDict where each dataset is a manually aligned chapter in all 5 Romansh idioms."""
import os
import json

from datasets import Dataset, DatasetDict

def load_val_set(path = './val_set'):
    out = {}
    files = [os.path.join(path,file) for file in os.listdir(path) if "jsonl" in file]
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f]
        key = os.path.splitext(os.path.basename(path))[0]  # Use file name without extension as key
        out[key] = Dataset.from_list(data)

    return DatasetDict(out)
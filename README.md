# _Mediomatix_

This is the code for the paper "The Mediomatix Corpus: Parallel Data for Romansh Idioms via Comparable Schoolbooks". 

- The automatically aligned dataset can be found [here](https://huggingface.co/datasets/ZurichNLP/mediomatix). 
- The unaligned raw text is found [here](https://huggingface.co/datasets/ZurichNLP/mediomatix-raw).

In this repository, we publish the code to re-build the dataset from scratch and reproduce the experiments in the paper.

---

## Installing dependencies
In order to install the required packages, run in your created virtual environment
```
pip install -r requirements.txt
```

## Setup
Before running the code, make sure to put your API KEY into the appropriate variable ```API_KEY``` inside ```constant.py``` file.

If running the `embed_overlaps.py` script, you'll also need to fill in the appropriate variables in `./embed/embed_api_keys.py`

Vecalign (Copyright 2019 Brian Thompson, released under Apache License, Version 2.0) is used throughout the experiments: https://github.com/thompsonb/vecalign 

## Fetching the unaligned dataset
In order to fetch the dataset from the API and save it as a JSONL file, run the following command:
```
python fetch_api_dataset.py
```

## Locally recreating the unaligned HF dataset
In order to locally recreate the HF dataset for the unaligned _Mediomatix_ textbooks, make sure you have first fetched the dataset. Then, call the following function:
```
from load_textbooks import load_textbooks
textbooks = load_textbooks()
```
By default, the segments are sorted in the order they were retrieved from API. In order to have them sorted like in sample two PDFs, run the following command instead:
```
from load_textbooks import load_textbooks
textbooks = load_textbooks(sort_like_sample_textbooks=True)
```
By default, the segments text is also stored in big chunks, one per segment. In order to have segments split into smaller, sentence-like chunks, run the following command:
```
from load_textbooks import load_textbooks
textbooks = load_textbooks(split_segments_into_sentences=True)
```

## Running tests
In order to run the unit tests to confirm that all pipeline components work without errors, run:
```
pytest tests/
```

## Running HF Datasets Statistics
In order to run statistics for the HF datasets, run:
```
python stats.py
```

# Reproducing Alignment Experiments

## Dataset Preparation

### `./dataset/compile_full.py`  
Compiles aligned segments into a full dataset.
- Filters out segments that are <0.67× or >1.5× the average bead length.
- With `--clean`, performs post-processing (removes URLs, non-breaking spaces).
- Outputs a `.jsonl` file with aligned sentences.

### `./dataset/split_full.py`  
Splits the compiled dataset into:
- **Train**: Grades 2–3  
- **Validation**: Grade 4  
- **Test**: Grade 5  
- **no-tm-urmiran**: Grades 6–9

---

## Alignment Procedures

### `./embed/get_text.py`  
Extracts plain text or HTML segments from textbook objects.

### `./embed/embed_overlaps.py`  
Embeds overlapping segments (i.e., plain text or HTML) produced by `vecalign`.
- Supports both full dataset and validation set (`--val_set_only`).
- Requires grade level for full dataset embedding.

### `./embed/concat_embs.py`  
Concatenates HTML and plain text embeddings for the validation set.

### `./align/merge_pivots.py`  
Merges pairwise alignments using each idiom as pivot.
- Outputs multi-parallel alignments and consensus alignment (intersection).
- With `--store_pairwise`, saves pairwise alignments derived from the multi-parallel set.

### `./val_exp/greedy_align.py`  
Performs the validation set greedy, 1-1 alignment experiment using cosine similarity.
- Aligns each source segment to the most similar target.
- Reports average proportion of correct alignments.

---

## Evaluation and Table Generation

### `./dataset/random_eval.py`  
Randomly selects 100 validation set segments for manual evaluation.

### `./tables/create_mt_results_table.py`  
Evaluates machine translation (MT) outputs from three systems:
- GPT-4o  
- GPT-4o-mini  
- Fine-tuned GPT-4o-mini  
Outputs BLEU score tables for inter-idiom MT performance.

### `./tables/p_r_tab.py`  
Outputs precision and recall table for validation alignments:
- Includes all pivot idioms and the consensus alignment.

### `./tables/model_val_tab.py`  
Summarises greedy alignment performance:
- Compares across embedding models and input types (text, HTML, concatenated).

### `./tables/mediomatix_stats.py`  
Reports corpus statistics:
- Number of books, segments, and tokens.  
- With `--splits`, shows stats for train/val/test/no-rm-surmiran splits.

### `./tables/val_desc_tab.py`  
Descriptive statistics for the validation set:
- Segments per idiom  
- Deletions per idiom  
- Many-to-many alignments per idiom

---

## Shell Scripts

### `./align/all2all_full.sh [GRADE]`  
Runs `vecalign` for all idiom pairs in the specified grade.

### `./align/prep_pivot.sh [GRADE]`  
Moves alignment files for a pivot idiom into a directory for merging.

### `./align/full_merge.sh [GRADE]`  
Executes `merge_pivots.py` for each chapter in the grade to produce:
- Multi-parallel alignments
- Consensus alignment

### `./val_exp/run_greedy_alignment.sh`  
Runs greedy alignment for all idiom pairs in the validation set.

### `./align/eval_pivot.sh [text/html/embconcat]` 
Evaluates pivot alignments on validation set:
- Outputs precision, recall, and F1 scores.
- Should specify whether the alignments made from text embeddings, html embeddings, or their concatenation ('embconcat') are to be evaluated

### `./align/eval_consensus.sh`  
Evaluates consensus alignments on validation set:
- Outputs precision, recall, and F1 scores.

---

## Ground Truths & Outputs

- `./val_set/` — Manually aligned validation set (`.jsonl` per chapter)  
- `./chapter_mappings/` — Manually aligned chapter title mappings  
- `./align/ground_truth/` — Ground-truth alignments for validation set  
- `./align/eval/consensus_eval_new.csv` — Consensus alignment scores  
- `./align/eval/pivot_2_text.csv` — Pivot scores using plain text embeddings  
- `./align/eval/pivot_2_html.csv` — Pivot scores using HTML embeddings  
- `./align/eval/pivot_2_embconcat.csv` — Pivot scores using concatenated embeddings  

---

## MT Experiment (Section 5)
- `./mt_experiment/export_few_shot.py` – Samples few-shot examples from the validation set.
- `./mt_experiment/export_finetuning_data.py` – Samples and formats training data for fine-tuning GPT-4o-mini.
- `./mt_experiment/export_test_sample.py` – Samples test data for MT evaluation.
- `./mt_experiment/run_translate.py` – Calls the OpenAI API to translate the test segments (example call is in `./mt_experiment/run_gpt-4o.sh`)

## Citation
```bibtex
@misc{hopton-et-al-2025-mediomatix,
      title={The Mediomatix Corpus: Parallel Data for Romansh Idioms via Comparable Schoolbooks},
      author={Zachary Hopton and Jannis Vamvas and Andrin Büchler and Anna Rutkiewicz and Rico Cathomas and Rico Sennrich},
      year={2025},
      eprint={2508.16371},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2508.16371},
}
```

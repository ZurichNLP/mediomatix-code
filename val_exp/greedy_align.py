"""Implement "Greedy decoding" to choose model and input type for embedding Mediomatix.
Compares all embeddings for all segments in the source idiom's validation set to those in the target idiom's corpus and aligns each src segment
to the highest scoring target segment. Prints the average proportion of correct 1-1 beads.
"""

import argparse
from collections import Counter
import os
import unicodedata

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from load_val_set import load_val_set


VAL_SET = load_val_set()

MODELS = [
    "gemini-embedding",
    "cohere-v4",
    "voyage-v3",
    "sentence-swissbert",
    "qwen3-Embedding-0.6B",
    "openai-v3",
]

IDIOMS = ["puter", "sursilv", "sutsilv", "vallader", "surmiran"]


def get_args():
    parser = argparse.ArgumentParser(description="Use cosine sim to align embeddings")

    parser.add_argument("--model", type=str, required=True, choices=MODELS)

    parser.add_argument("--src", type=str, required=True, choices=IDIOMS)

    parser.add_argument("--tgt", type=str, required=True, choices=IDIOMS)

    parser.add_argument(
        "--input", type=str, required=True, choices=["text", "html", "embconcat"]
    )

    return parser.parse_args()


def get_emb(model, idiom, chapter, input):
    """Function to read in embeddings and reshape them to fit the overlap file; code adapted from vecalign https://github.com/thompsonb/vecalign/blob/master/dp_utils.py"""
    line_embeddings = np.fromfile(
        f"/projects/text/romansh/textbooks/val_embeddings/align_02/{model}/{chapter}/rm-{idiom}_{input}_overlaps.emb",
        dtype=np.float32,
        count=-1,
    )

    sent2line = {}
    with open(
        f"/projects/text/romansh/textbooks/val_overlaps/align_02/{chapter}/rm-{idiom}_{input}_overlaps.txt",
        "r",
        encoding="utf-8",
    ) as f:
        for ii, line in enumerate(f):

            sent2line[line.strip()] = ii

    embedding_size = line_embeddings.size // len(sent2line)

    line_embeddings.resize(line_embeddings.shape[0] // embedding_size, embedding_size)

    output = {}
    text_file = "text" if input in ["text", "embconcat"] else "html"
    with open(
        f"/projects/text/romansh/textbooks/val_embeddings/texts/{chapter}/rm-{idiom}_{text_file}.txt",
        "r",
        encoding="utf-8",
    ) as f:
        for line in f:
            output[line.strip()] = line_embeddings[sent2line[line.strip()]].reshape(
                1, -1
            )

    # {sent:emb,...}
    return output


def get_mapping(idiom, chapter):
    """function to build an html:text mapping for convenience during scoring"""
    mapping = {}
    with (
        open(
            f"/projects/text/romansh/textbooks/val_embeddings/texts/{chapter}/rm-{idiom}_html.txt",
            "r",
            encoding="utf-8",
        ) as f_html,
        open(
            f"/projects/text/romansh/textbooks/val_embeddings/texts/{chapter}/rm-{idiom}_text.txt",
            "r",
            encoding="utf-8",
        ) as f_text,
    ):

        return {
            unicodedata.normalize("NFKC", l_h.strip()): unicodedata.normalize(
                "NFKC", l_t.strip()
            )
            for l_h, l_t in zip(f_html, f_text)
        }


def greedy_align(src_emb, tgt_emb, src_mapping=None, tgt_mapping=None):
    alignment = {}

    if src_mapping and tgt_mapping:
        for sent, se in src_emb.items():
            # initialize an array with a spot for every tgt sent
            temp = np.zeros(len(tgt_emb.keys()))
            for i, te in enumerate(tgt_emb.values()):
                # compare src emb to every tgt emb, add to the relevant position in the array
                temp[i] = cosine_similarity(se, te).item()
            # get the index of the highest sim and then select that sent from tgt emb; append to the output alignment
            alignment[src_mapping[unicodedata.normalize("NFKC", sent)]] = tgt_mapping[
                unicodedata.normalize("NFKC", list(tgt_emb.keys())[np.argmax(temp)])
            ]
        return alignment
    else:
        for sent, se in src_emb.items():
            # initialize an array with a spot for every tgt sent
            temp = np.zeros(len(tgt_emb.keys()))
            for i, te in enumerate(tgt_emb.values()):
                # compare src emb to every tgt emb, add to the relevant position in the array
                temp[i] = cosine_similarity(se, te).item()
            # get the index of the highest sim and then select that sent from tgt emb; append to the output alignment
            alignment[unicodedata.normalize("NFKC", sent)] = unicodedata.normalize(
                "NFKC", list(tgt_emb.keys())[np.argmax(temp)]
            )
        return alignment


def score_alignment(alignment, src, tgt, chapter):
    # go through elements in groundtruth
    val_set = VAL_SET[chapter]

    scores = Counter()

    for row in val_set:
        if len(row[f"rm-{src}"]) > 1 or len(row[f"rm-{tgt}"]) > 1:
            # we don't want to credit or penalize many-to-many beads since this method doesn't account for them
            continue
        elif None in row[f"rm-{src}"] or None in row[f"rm-{tgt}"]:
            # we don't want to credit or penalize null alignments since this method doesn't account for them
            continue
        else:
            # if the previous checks worked, then the length should not be longer than 1
            assert len(row[f"rm-{src}"]) == 1 and len(row[f"rm-{tgt}"]) == 1
            # we consider this data point
            scores["total"] += 1
            # Check if the relevant data point is correct:
            src_sent = unicodedata.normalize("NFKC", row[f"rm-{src}"][0])
            tgt_sent = unicodedata.normalize("NFKC", row[f"rm-{tgt}"][0])

            if alignment[src_sent] == tgt_sent:
                scores["correct"] += 1

    return scores["correct"] / scores["total"]


def main(args):
    chap_scores = np.zeros(len(os.listdir("../align/ground_truth")))
    for num, chap in enumerate(os.listdir("../align/ground_truth")):
        # get the relevant src embeddings
        src_emb = get_emb(args.model, args.src, chap, args.input)
        # get the relevant tgt embeddings
        tgt_emb = get_emb(args.model, args.tgt, chap, args.input)

        if args.input == "html":
            src_mapping = get_mapping(args.src, chap)
            tgt_mapping = get_mapping(args.tgt, chap)
            # For each sentence in the src, what is the most similar tgt emb?
            alignment = greedy_align(src_emb, tgt_emb, src_mapping, tgt_mapping)
        else:
            alignment = greedy_align(src_emb, tgt_emb)

        # Score: proportion correct
        chap_scores[num] = score_alignment(alignment, args.src, args.tgt, chap)

    # print the avg across chapters in the val set
    print(f"{args.model},{args.src}-{args.tgt},{args.input},{chap_scores.mean():.3f}")


if __name__ == "__main__":
    args = get_args()
    main(args)

"""A script to concatenate the embeddings of the HTML and plain text of the val set for a given idiom. Since we work with the vecalign overlaps, much of the code is adapted from:
https://github.com/thompsonb/vecalign/blob/master/dp_utils.py
"""

import argparse
import os

import numpy as np


def get_args():
    parser = argparse.ArgumentParser(
        description="Concatenate HTML and Text vecalign overlaps"
    )

    parser.add_argument(
        "--num_overlaps",
        type=int,
        default=2,
        help="Number of overlaps made when generating the overlap files for vecalign",
    )

    parser.add_argument(
        "--idiom",
        required=True,
        choices=["sursilv", "sutsilv", "surmiran", "puter", "vallader"],
    )

    parser.add_argument(
        "--text_path",
        type=str,
        help="Path to a directory containing subdir for the val_set chapters. In each subdir should be the txt files with the html and text of each idiom",
    )

    parser.add_argument(
        "--overlap_path",
        type=str,
        help="Path to a directory containing subdir for the val_set chapters. In each subdir should be the overlaps for the html and text of each idiom",
    )

    parser.add_argument(
        "--embedding_path",
        type=str,
        help="Path to a directory containing subdir for the val_set chapters. In each subdir should be the embedded overlaps for the html and text of each idiom. This will also be the output dir for the concatenated html and text embeddings.",
    )

    return parser.parse_args()


def get_sent2line(in_path, idiom, chapter, input):
    sent2line = {}
    with open(
        f"{in_path}/{chapter}/rm-{idiom}_{input}_overlaps.txt",
        "r",
        encoding="utf-8",
    ) as f:
        for ii, line in enumerate(f):

            sent2line[line.strip()] = ii
    return sent2line


def get_emb(in_path, idiom, chapter, sent2line, input):
    line_embeddings = np.fromfile(
        f"{in_path}/{chapter}/rm-{idiom}_{input}_overlaps.emb",
        dtype=np.float32,
        count=-1,
    )

    embedding_size = line_embeddings.size // len(sent2line)

    line_embeddings.resize(line_embeddings.shape[0] // embedding_size, embedding_size)

    # return [len(overlaps),d] array
    return line_embeddings


def reorder_emb(text_path, emb, idiom, chapter, sent2line, input, num_overlaps):
    """Yield the embeddings in the same order for both the HTML and plain text so we can concatenate them. Mostly based on the make_doc_embedding function at https://github.com/thompsonb/vecalign/blob/master/dp_utils.py"""
    # open the normal (non overlap) lines, read and preprocess
    with open(
        f"{text_path}/{chapter}/rm-{idiom}_{input}.txt",
        "r",
        encoding="utf-8",
    ) as f:
        lines = [preprocess_line(line) for line in f]

    vecsize = emb.shape[1]

    # Get the set of overaps
    seen = set()
    unique_overlaps = []
    for overlap in range(1, num_overlaps + 1):
        for out_line in layer(lines, overlap):
            if out_line not in seen:
                unique_overlaps.append(out_line)
                seen.add(out_line)

    # Prepare output embedding array
    vecs0 = np.empty((len(unique_overlaps), vecsize), dtype=np.float32)
    out_text = []

    # Fill embeddings and text in the same order
    for idx, out_line in enumerate(unique_overlaps):
        try:
            line_id = sent2line[out_line]
        except KeyError:
            print('Failed to find line "%s". Will use random vector.', out_line)
            line_id = None

        if line_id is not None:
            vec = emb[line_id]
        else:
            vec = np.random.random(vecsize) - 0.5
            vec = vec / np.linalg.norm(vec)

        vecs0[idx, :] = vec

        out_text.append(out_line)

    return vecs0, out_text


def preprocess_line(line):
    """Utility function from https://github.com/thompsonb/vecalign/blob/master/dp_utils.py"""
    line = line.strip()
    if len(line) == 0:
        line = "BLANK_LINE"
    return line


def layer(lines, num_overlaps, comb=" "):
    """
    make front-padded overlapping sentences; Utility function from https://github.com/thompsonb/vecalign/blob/master/dp_utils.py
    """
    if num_overlaps < 1:
        raise Exception("num_overlaps must be >= 1")
    out = [
        "PAD",
    ] * min(num_overlaps - 1, len(lines))
    for ii in range(len(lines) - num_overlaps + 1):
        out.append(comb.join(lines[ii : ii + num_overlaps]))
    return out


def main(args):

    for chap in os.listdir(args.overlap_path):
        print(f"---{chap}---")
        # get the sent2line dict since overlaps rearrange the sentences in the text
        text_sent2line = get_sent2line(args.overlap_path, args.idiom, chap, "text")
        html_sent2line = get_sent2line(args.overlap_path, args.idiom, chap, "html")
        # get the overlap embeddings
        text_emb = get_emb(
            args.embedding_path,
            args.idiom,
            chap,
            text_sent2line,
            "text",
        )
        html_emb = get_emb(
            args.embedding_path,
            args.idiom,
            chap,
            html_sent2line,
            "html",
        )
        # # reorder the arrays so that they correspond to the original doc order.
        text_emb, overlap_text = reorder_emb(
            args.text_path,
            text_emb,
            args.idiom,
            chap,
            text_sent2line,
            "text",
            args.num_overlaps,
        )
        html_emb, _ = reorder_emb(
            args.text_path,
            html_emb,
            args.idiom,
            chap,
            html_sent2line,
            "html",
            args.num_overlaps,
        )
        # # Concatenate the embeddings for each line along the last axis, i.e., the embedding dim
        emb_concat = np.concatenate((text_emb, html_emb), axis=-1)

        # save overlaps
        with open(
            f"{args.overlap_path}/{chap}/rm-{args.idiom}_embconcat_overlaps.txt",
            "w",
            encoding="utf-8",
        ) as f:
            # It doesn't matter if we save the text or html, just the order is important
            for line in overlap_text:
                f.write(line + "\n")

        # Save concatenated embeddings;
        with open(
            f"{args.embedding_path}/{chap}/rm-{args.idiom}_embconcat_overlaps.emb",
            "wb",
        ) as wb:
            emb_concat.astype(np.float32).tofile(wb)


if __name__ == "__main__":
    args = get_args()
    main(args)

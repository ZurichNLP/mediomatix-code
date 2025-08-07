import argparse
import json
import os
import time
import random
import re
import requests
import socket

import cohere
from cohere.core.api_error import ApiError
from google import genai
import numpy as np
from openai import OpenAI
from ratelimit import limits, sleep_and_retry
from tqdm import tqdm
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
import voyageai

from embed_api_keys import (
    COHERE_API_KEY,
    OPENAI_API_KEY,
    VOYAGE_API_KEY,
    GOOGLE_API_KEY,
)
from load_textbooks import load_textbooks

MODELS = {
    "qwen3-Embedding-0.6B": "Qwen/Qwen3-Embedding-0.6B",
    "sentence-swissbert": "jgrosjean-mathesis/sentence-swissbert",
    "openai-v3": "text-embedding-3-large",
    "gemini-embedding": "gemini-embedding-exp-03-07",
    "voyage-v3": "voyage-3-large",
    "cohere-v4": "embed-v4.0",
}

client_cohere = cohere.ClientV2(api_key=COHERE_API_KEY)
client_openai = OpenAI(api_key=OPENAI_API_KEY)
client_gemini = genai.Client(api_key=GOOGLE_API_KEY)
client_voyage = voyageai.Client(api_key=VOYAGE_API_KEY)


def get_args():
    parser = argparse.ArgumentParser(description="Embed textbooks")

    parser.add_argument(
        "--model_name",
        type=str,
        choices=[
            "qwen3-Embedding-0.6B",
            "sentence-swissbert",
            "openai-v3",
            "gemini-embedding",
            "voyage-v3",
            "cohere-v4",
        ],
        help="Model name for embeddings",
    )

    parser.add_argument(
        "--in_path",
        type=str,
        default="/projects/text/romansh/textbooks/val_overlaps",
        help="Path to the chapter-wise overlap files.",
    )

    parser.add_argument(
        "--text_type",
        type=str,
        default="text",
        choices=["text", "html"],
        help="Embed the extracted text of each segment or the html",
    )

    parser.add_argument("--val_set_only", action="store_true")

    parser.add_argument(
        "--grade",
        type=int,
        default=4,
        choices=[2, 3, 4, 5, 6, 7, 8, 9],
        help="Grade level to embed. If --val_set_only, this argument is not relevant",
    )

    parser.add_argument("--out_dir", type=str, help="Directory for output embeddings")

    return parser.parse_args()


def get_hf_model(model_name):
    if model_name == "sentence-swissbert":
        model = AutoModel.from_pretrained(MODELS[model_name])
        # romansh adapter
        model.set_default_language("rm_CH")
        tokenizer = AutoTokenizer.from_pretrained(MODELS[model_name])

        return model, tokenizer

    elif model_name == "qwen3-Embedding-0.6B":
        model = AutoModel.from_pretrained(MODELS[model_name])
        tokenizer = AutoTokenizer.from_pretrained(MODELS[model_name])

        return model, tokenizer


def get_hf_chapter(parsed_line, tb):
    chapter_name = parsed_line[tb.idiom]
    if chapter_name:
        return tb.hf_dataset.filter(lambda row: chapter_name in row["chapterPath"])
    # in case this chapter doesn't exist for an idiom
    else:
        return None


def embed_qwen(text, model, tokenizer):
    # from QWEN3 Documentation: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
    inputs = tokenizer(
        text, padding=True, truncation=True, return_tensors="pt", max_length=512
    )
    with torch.no_grad():
        outputs = model(**inputs)

    # Extract the last hidden state and apply last token pooling (as in QWEN3 documentation)
    last_hidden_states = outputs.last_hidden_state
    attention_mask = inputs["attention_mask"]
    left_padding = attention_mask[:, -1].sum() == attention_mask.shape[0]
    if left_padding:
        embedding = last_hidden_states[:, -1]
    else:
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        embedding = last_hidden_states[
            torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths
        ]

    return embedding.squeeze().tolist()


def embed_swissbert(text, model, tokenizer):
    # From sentence-SwissBERT documentation: https://huggingface.co/jgrosjean-mathesis/sentence-swissbert
    inputs = tokenizer(
        text, padding=True, truncation=True, return_tensors="pt", max_length=512
    )
    with torch.no_grad():
        outputs = model(**inputs)

    # Extract sentence embeddings via mean pooling
    token_embeddings = outputs.last_hidden_state
    attention_mask = (
        inputs["attention_mask"].unsqueeze(-1).expand(token_embeddings.size()).float()
    )
    sum_embeddings = torch.sum(token_embeddings * attention_mask, 1)
    sum_mask = torch.clamp(attention_mask.sum(1), min=1e-9)
    embedding = sum_embeddings / sum_mask

    return embedding.squeeze().tolist()


def embed_openai(text, model_name):
    # OpenAI API call for text embedding
    response_text = client_openai.embeddings.create(
        input=text, model=MODELS[model_name]
    )
    return response_text.data[0].embedding


@sleep_and_retry
@limits(calls=10, period=60)
def embed_gemini(text, model_name):
    # Gemini embedding API call, with sleep wrapper for low RPM
    response = client_gemini.models.embed_content(
        contents=text, model=MODELS[model_name]
    )
    return response.embeddings[0].values


def embed_voyage(text, model_name):
    # Voyage AI embedding API call
    response = client_voyage.embed(text, model=MODELS[model_name])
    return response.embeddings[0]


def embed_cohere(text, model_name, max_retries=5):
    # Cohere embedding API call, with exception handling to continue after timeouts and API errors
    for attempt in range(max_retries):
        try:
            response = client_cohere.embed(
                texts=[text],
                model=MODELS[model_name],
                embedding_types=["float"],
                input_type="clustering",
            )
            return response.embeddings.float[0]
        except (
            ApiError,
            json.decoder.JSONDecodeError,
            requests.exceptions.RequestException,
            socket.timeout,
            TimeoutError,
            ConnectionError,
        ) as e:

            wait_time = 30 + random.uniform(0, 5) * (attempt + 1)
            print(f"[Attempt {attempt+1}/{max_retries}] Error: {e}")

            print(f"Waiting {wait_time:.1f}s before retrying...")
            time.sleep(wait_time)

    raise RuntimeError(f"Failed to embed text after {max_retries} retries")


def embed_overlap(
    text_type, in_path, out_path, idiom, model_name=None, model=None, tokenizer=None
):
    """Write .emb files with the binary embeddings of the text in the overlap files."""

    with (
        open(
            f"{in_path}/rm-{idiom}_{text_type}_overlaps.txt", "r", encoding="utf-8"
        ) as f,
        open(f"{out_path}/rm-{idiom}_{text_type}_overlaps.emb", "wb") as wb,
    ):
        # loop through each segment in the book
        for line in tqdm(f, desc=f"Embedding with {model_name}"):
            if model_name == "qwen3-Embedding-0.6B":
                # Write text embedding
                emb = np.array(embed_qwen(line, model, tokenizer), dtype=np.float32)
                emb.tofile(wb)
            elif model_name == "sentence-swissbert":
                emb = np.array(
                    embed_swissbert(line, model, tokenizer), dtype=np.float32
                )
                emb.tofile(wb)
            elif model_name == "openai-v3":
                emb = np.array(embed_openai(line, model_name), dtype=np.float32)
                emb.tofile(wb)
            elif model_name == "gemini-embedding":
                emb = np.array(embed_gemini(line, model_name), dtype=np.float32)
                emb.tofile(wb)
            elif model_name == "voyage-v3":
                emb = np.array(embed_voyage(line, model_name), dtype=np.float32)
                emb.tofile(wb)
            elif model_name == "cohere-v4":
                emb = np.array(embed_cohere(line, model_name), dtype=np.float32)
                emb.tofile(wb)
            else:
                raise ValueError(
                    f"Model {model_name} is not supported. Choose from {list(MODELS.keys())}."
                )


def embed_overlaps_full(in_path, book, chapter, idiom):
    with (
        open(
            f"{in_path}/{book}/{chapter}/rm-{idiom}_text_overlaps.txt",
            "r",
            encoding="utf-8",
        ) as f,
        open(
            f"/projects/text/romansh/textbooks/final/embeddings/{book}/{chapter}/rm-{idiom}_text_overlaps.emb",
            "wb",
        ) as wb,
    ):
        # loop through each segment in the book
        for line in tqdm(f, desc=f"Embedding with Cohere-v4"):
            emb = np.array(embed_cohere(line, "cohere-v4"), dtype=np.float32)
            emb.tofile(wb)


def get_grade_number(name):
    match = re.match(r"^(\d)", name)
    return int(match.group(1)) if match else None


def main(model_name, in_path, text_type, val_set_only, grade, out):
    if val_set_only:

        if model_name in ["qwen3-Embedding-0.6B", "sentence-swissbert"]:
            model, tokenizer = get_hf_model(model_name)
        else:
            model, tokenizer = None, None

        for chap in os.listdir(in_path):
            print(f"Now embedding {chap}")
            extended_in = os.path.join(in_path, chap)
            out_dir = f"{out}/{model_name}"
            out_path = os.path.join(out_dir, chap)

            os.makedirs(out_dir, exist_ok=True)
            os.makedirs(out_path, exist_ok=True)

            for idiom in ["puter", "sursilv", "sutsilv", "surmiran", "vallader"]:
                embed_overlap(
                    text_type,
                    extended_in,
                    out_path,
                    idiom,
                    model_name,
                    model,
                    tokenizer,
                )
    else:
        assert model_name == "cohere-v4"
        assert text_type == "text"

        for book in os.listdir(in_path):
            book_grade = get_grade_number(book)
            if book_grade != grade:
                continue

            print(f"---{book}---")
            book_path = os.path.join(in_path, book)
            emb_book_path = f"{out}/{book}"
            os.makedirs(emb_book_path, exist_ok=True)

            for chapter in os.listdir(book_path):
                print(f"---{chapter}---")
                chapter_path = os.path.join(book_path, chapter)
                emb_chap_path = os.path.join(emb_book_path, chapter)
                os.makedirs(emb_chap_path, exist_ok=True)

                for idiom in ["puter", "sursilv", "sutsilv", "surmiran", "vallader"]:
                    text_path = f"{chapter_path}/rm-{idiom}_text_overlaps.txt"
                    emb_path = f"{emb_chap_path}/rm-{idiom}_text_overlaps.emb"

                    if os.path.isfile(text_path):
                        if not os.path.isfile(emb_path):
                            embed_overlaps_full(in_path, book, chapter, idiom)
                        else:
                            print(f"Already embedded {idiom} {chapter} in {book}")


if __name__ == "__main__":
    args = get_args()
    main(
        args.model_name,
        args.in_path,
        args.text_type,
        args.val_set_only,
        args.grade,
        args.out_dir,
    )

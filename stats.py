import re
from collections import defaultdict

from load_textbooks import load_textbooks

README_PATH = "README.md"


def calculate_statistics():
    # Load textbooks and handle potential errors
    try:
        textbooks = load_textbooks()
    except FileNotFoundError as e:
        raise RuntimeError(f"Error loading textbooks: {e}")
    except ImportError as e:
        raise RuntimeError(f"Required module missing: {e}")

    if not textbooks:
        raise RuntimeError("No textbooks were loaded.")

    # Initialize counters
    books_per_idiom = defaultdict(int)
    segments_per_idiom = defaultdict(int)
    tokens_per_idiom = defaultdict(int)


    all_idioms = sorted({tb.idiom for tb in textbooks.values()})

    # Aggregate statistics
    for idiom in all_idioms:
        idiom_books = [tb for tb in textbooks.values() if tb.idiom == idiom]
        books_per_idiom[idiom] = len(idiom_books)
        for tb in idiom_books:
            ds = getattr(tb, 'hf_dataset', None)
            if not ds:
                continue
            # count segments
            segments_per_idiom[idiom] += len(ds)
            # pick the right text column
            if 'segmentExtractedText' in ds.column_names:
                text_column = 'segmentExtractedText'
            elif 'sentenceExtractedText' in ds.column_names:
                text_column = 'sentenceExtractedText'
            else:
                continue  # skip if no text column found
            # count tokens by whitespace
            for text in ds[text_column]:
                tokens_per_idiom[idiom] += len(text.split())

    table_md = build_markdown_table(
        books_per_idiom,
        segments_per_idiom,
        tokens_per_idiom,
        all_idioms
    )
    print("Updating README.md with dataset statistics...")
    update_readme_statistics(README_PATH, table_md)


def build_markdown_table(books_per_idiom, segments_per_idiom, tokens_per_idiom, all_idioms):
    lines = [
        "| Idiom | Books | Segments | Tokens (Whitespace) |",
        "| --- | --- | --- | --- |"
    ]
    total_books = total_segments = total_tokens = 0

    for idiom in all_idioms:
        b = books_per_idiom[idiom]
        s = segments_per_idiom[idiom]
        t = tokens_per_idiom[idiom]
        lines.append(f"| {idiom} | {b} | {s:,} | {t:,} |")
        total_books += b
        total_segments += s
        total_tokens += t

    # Grand total row
    lines.append(f"| **Total** | {total_books} | {total_segments:,} | {total_tokens:,} |")
    return "\n".join(lines)


def update_readme_statistics(path, table_md):
    """
    Replace everything under the '## Dataset Statistics' heading
    with our freshly generated table.
    """
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex: capture the heading, then everything until the next '## ' or EOF
    new_content = re.sub(
        r"(## Dataset Statistics\n)(.*?)(?=\n## |\Z)",
        lambda m: m.group(1) + table_md + "\n",
        content,
        flags=re.DOTALL
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)


if __name__ == "__main__":
    calculate_statistics()

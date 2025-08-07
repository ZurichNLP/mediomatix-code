import argparse
import json
import os

from load_textbooks import load_textbooks

textbooks = load_textbooks()

IDIOMS = {
    "rm-surmiran": "surmiran",
    "rm-puter": "puter",
    "rm-vallader": "vallader",
    "rm-sursilv": "sursilvan",
    "rm-sutsilv": "sutsilvan",
}

VAL_CHAP = [
    "1-regurdientschas-da-stad",
    "2-viadi-datun",
    "3-ir-a-scola-ei-schi-bi",
    "4-advent-advent",
    "7-inegliada-anavos-sigl-onn-da-scola",
    "8-scriver-ei-buc-adina-sempel",
]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--val_set_only", action="store_true")
    parser.add_argument(
        "--out_dir",
        type=str,
        help="Will make sub directories for each chapter (if --val_set_only) or for each book if extracting full dataset text.",
    )
    parser.add_argument(
        "--text_type",
        type=str,
        choices=["text", "html"],
        default="text",
        help="Determines whether the plain text or the HTML for each segment is written to the output",
    )
    args = parser.parse_args()

    if args.val_set_only:
        # Get for workbook 4.1
        klasse = 4
        book_num = 1
        with open(f"./chapter_mappings/final_jsonl/4.1_wb.jsonl", "r") as f:
            # loop through chapters until one of the val_chap is found
            for chap in f:
                chapter_map = json.loads(chap)
                name = chapter_map["rm-sursilv"]
                if name in VAL_CHAP:
                    print(f"---{name}---")
                    for idiom in list(chapter_map.keys()):
                        if chapter_map.get(idiom, None):
                            data = textbooks[
                                f"/{IDIOMS[idiom]}/klasse-{klasse}/arbeitsbuch-{book_num}/workbook"
                            ]
                            filtered = data.hf_dataset.filter(
                                lambda row: chapter_map[idiom] in row["chapterPath"]
                            )

                            os.makedirs(f"{args.out_dir}/{name}", exist_ok=True)
                            with open(
                                f"{args.out_dir}/{name}/{idiom}_{args.text_type}.txt",
                                "w",
                                encoding="utf-8",
                            ) as f_out:
                                for segment in filtered:
                                    if args.text_type == "text":
                                        f_out.write(
                                            f"{segment['sentenceExtractedText']}\n"
                                        )
                                    else:
                                        f_out.write(f"{segment['sentenceHTML']}\n")
                else:
                    continue
    else:
        for book in os.listdir("./chapter_mappings/final_jsonl"):
            print(f"---{book}---")
            klasse = book.split("_")[0].split(".")[0]
            book_num = book.split("_")[0].split(".")[1]
            with open(f"./chapter_mappings/final_jsonl/{book}", "r") as f:
                for chap in f:
                    chapter_map = json.loads(chap)
                    name = chapter_map["rm-sursilv"]
                    print(f"---{name}---")
                    for idiom in list(chapter_map.keys()):
                        if chapter_map.get(idiom, None):
                            data = textbooks[
                                f"/{IDIOMS[idiom]}/klasse-{klasse}/arbeitsbuch-{book_num}/{'workbook' if 'wb' in book else 'teachers_commentary'}"
                            ]
                            filtered = data.hf_dataset.filter(
                                lambda row: chapter_map[idiom] in row["chapterPath"]
                            )

                            os.makedirs(
                                f"{args.out_dir}/{book.strip('.jsonl')}/", exist_ok=True
                            )
                            os.makedirs(
                                f"{args.out_dir}/{book.strip('.jsonl')}/{name}",
                                exist_ok=True,
                            )
                            with open(
                                f"{args.out_dir}/{book.strip('.jsonl')}/{name}/{idiom}_{args.text_type}.txt",
                                "w",
                                encoding="utf-8",
                            ) as f_out:
                                for segment in filtered:
                                    if args.text_type == "text":
                                        f_out.write(
                                            f"{segment['sentenceExtractedText']}\n"
                                        )
                                    else:
                                        f_out.write(f"{segment['sentenceHTML']}\n")

import csv
import json
import os

romansh_column_to_code = {
    "Sursilvan": "rm_sursilv",
    "Vallader": "rm_vallader",
    "Puter": "rm_puter",
    "Surmiran": "rm_surmiran",
    "Sutsilvan": "rm_sutsilv",
}

# Path to the TSV file
tsv_path = os.path.join(os.path.dirname(__file__), "romansh_few_shots.tsv")

# Read the TSV file
with open(tsv_path, encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    rows = list(reader)

# For each idiom pair, create JSON files in both directions
for column1, code1 in romansh_column_to_code.items():
    for column2, code2 in romansh_column_to_code.items():
        if column1 == column2:
            continue
        # Idiom1 to Idiom2
        data_idiom1_to_idiom2 = []
        # Idiom2 to Idiom1
        data_idiom2_to_idiom1 = []
        for row in rows:
            source_idiom1 = row[code1.replace("_", "-")].strip()
            target_idiom2 = row[code2.replace("_", "-")].strip()
            if source_idiom1 and target_idiom2:
                data_idiom1_to_idiom2.append({"source": source_idiom1, "target": target_idiom2})
                data_idiom2_to_idiom1.append({"source": target_idiom2, "target": source_idiom1})

        # Write Idiom1 to Idiom2
        json_filename_idiom1_to_idiom2 = f"shots.{code1}-{code2}.json"
        json_path_idiom1_to_idiom2 = os.path.join(os.path.dirname(__file__), json_filename_idiom1_to_idiom2)
        with open(json_path_idiom1_to_idiom2, "w", encoding="utf-8") as jf:
            json.dump(data_idiom1_to_idiom2, jf, ensure_ascii=False, indent=2)

        # Write Idiom2 to Idiom1
        json_filename_idiom2_to_idiom1 = f"shots.{code2}-{code1}.json"
        json_path_idiom2_to_idiom1 = os.path.join(os.path.dirname(__file__), json_filename_idiom2_to_idiom1)
        with open(json_path_idiom2_to_idiom1, "w", encoding="utf-8") as jf:
            json.dump(data_idiom2_to_idiom1, jf, ensure_ascii=False, indent=2)

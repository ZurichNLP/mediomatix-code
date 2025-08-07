from pathlib import Path

from sacrebleu import BLEU

src_sentences_dir = Path("../mt_experiment/testset_mediomatix")
assert src_sentences_dir.exists(), f"Source sentences directory {src_sentences_dir} does not exist."

system_output_dir = Path("../mt_experiment/system_output_mediomatix")
assert system_output_dir.exists(), f"System output directory {system_output_dir} does not exist."

systems = [
    "GPT-4o",
    "GPT-4o-mini",
    "GPT-4o-mini-finetuned",
]

idioms = ["rm_sursilv", "rm_sutsilv", "rm_surmiran", "rm_puter", "rm_vallader"]

src_sentences = {}
ref_sentences = {}
sys_sentences = {system: dict() for system in systems}
bleu_scores = {system: dict() for system in systems}

for src_idiom in idioms:
    for tgt_idiom in idioms:
        if src_idiom == tgt_idiom:
            continue

        src_file = src_sentences_dir / f"wmttest2024.src.{src_idiom}-{tgt_idiom}.xml.no-testsuites.{src_idiom}"
        assert src_file.exists(), f"Source file {src_file} does not exist."
        with open(src_file, "r", encoding="utf-8") as f:
            src_sentences[(src_idiom, tgt_idiom)] = [line.strip() for line in f]

        ref_file = src_sentences_dir / f"wmttest2024.src.{tgt_idiom}-{src_idiom}.xml.no-testsuites.{tgt_idiom}"
        assert ref_file.exists(), f"Reference file {ref_file} does not exist."
        with open(ref_file, "r", encoding="utf-8") as f:
            ref_sentences[(src_idiom, tgt_idiom)] = [line.strip() for line in f]

        for system in systems:
            sys_file = system_output_dir / system / f"wmttest2024.src.{src_idiom}-{tgt_idiom}.xml.no-testsuites.{src_idiom}"
            if not sys_file.exists():
                print(f"System output file {sys_file} does not exist. Skipping system {system}.")
                sys_sentences[system][(src_idiom, tgt_idiom)] = []
                continue
            with open(sys_file, "r", encoding="utf-8") as f:
                sys_sentences[system][(src_idiom, tgt_idiom)] = [line.strip() for line in f]

            assert len(src_sentences[(src_idiom, tgt_idiom)]) == len(ref_sentences[(src_idiom, tgt_idiom)]) == len(sys_sentences[system][(src_idiom, tgt_idiom)]), \
                f"Mismatch in number of sentences for {src_idiom}-{tgt_idiom} in system {system}. " \
                f"Source: {len(src_sentences[(src_idiom, tgt_idiom)])}, " \
                f"Reference: {len(ref_sentences[(src_idiom, tgt_idiom)])}, " \
                f"System: {len(sys_sentences[system][(src_idiom, tgt_idiom)])}"

bleu = BLEU()
for system in systems:
    for (src_idiom, tgt_idiom), sys_lines in sys_sentences[system].items():
        if not sys_lines:
            continue
        ref_lines = ref_sentences[(src_idiom, tgt_idiom)]
        bleu_score = bleu.corpus_score(sys_lines, [ref_lines]).score
        bleu_scores[system][(src_idiom, tgt_idiom)] = bleu_score

print(bleu.get_signature().format(short=True))

import pprint
pprint.pprint(bleu_scores)

TABLE_TEMPLATE = r"""
\begin{tabularx}{\textwidth}{@{}l*{5}{>{\centering\arraybackslash}X}*{5}{>{\centering\arraybackslash}X}>{\centering\arraybackslash}X}
\toprule
\textbf{System} & \multicolumn{2}{c}{\textbf{Sursilvan}} & \multicolumn{2}{c}{\textbf{Sutsilvan}} & \multicolumn{2}{c}{\textbf{Surmiran}} & \multicolumn{2}{c}{\textbf{Puter}} & \multicolumn{2}{c}{\textbf{Vallader}} & \textbf{Avg.} \\
                & from & into & from & into & from & into & from & into & from & into &  \\
\midrule
GPT-4o & {gpt4o_sursilvan_from} & {gpt4o_sursilvan_into} & {gpt4o_sutsilvan_from} & {gpt4o_sutsilvan_into} & {gpt4o_surmiran_from} & {gpt4o_surmiran_into} & {gpt4o_puter_from} & {gpt4o_puter_into} & {gpt4o_vallader_from} & {gpt4o_vallader_into} & {gpt4o_avg} \\
GPT-4o-mini & {gpt4omini_sursilvan_from} & {gpt4omini_sursilvan_into} & {gpt4omini_sutsilvan_from} & {gpt4omini_sutsilvan_into} & {gpt4omini_surmiran_from} & {gpt4omini_surmiran_into} & {gpt4omini_puter_from} & {gpt4omini_puter_into} & {gpt4omini_vallader_from} & {gpt4omini_vallader_into} & {gpt4omini_avg} \\
~– fine-tuned & {gpt4omini_finetuned_sursilvan_from} & {gpt4omini_finetuned_sursilvan_into} & {gpt4omini_finetuned_sutsilvan_from} & {gpt4omini_finetuned_sutsilvan_into} & {gpt4omini_finetuned_surmiran_from} & {gpt4omini_finetuned_surmiran_into} & {gpt4omini_finetuned_puter_from} & {gpt4omini_finetuned_puter_into} & {gpt4omini_finetuned_vallader_from} & {gpt4omini_finetuned_vallader_into} & {gpt4omini_finetuned_avg} \\
\bottomrule
\end{tabularx}
"""

idioms = ["sursilvan", "sutsilvan", "surmiran", "puter", "vallader"]
idiom_codes = {
    "sursilvan": "rm_sursilv",
    "sutsilvan": "rm_sutsilv",
    "surmiran": "rm_surmiran",
    "puter": "rm_puter",
    "vallader": "rm_vallader",
}

# Helper to get BLEU for a system, idiom, direction
def get_bleu(system, idiom, direction):
    # direction: "from" or "into"
    if direction == "from":
        # idiom as source, all others as target
        scores = []
        for tgt in idioms:
            if tgt == idiom:
                continue
            key = (idiom_codes[idiom], idiom_codes[tgt])
            score = bleu_scores.get(system, {}).get(key)
            if score is not None:
                scores.append(score)
        if scores:
            return sum(scores) / len(scores)
        else:
            return None
    elif direction == "into":
        # idiom as target, all others as source
        scores = []
        for src in idioms:
            if src == idiom:
                continue
            key = (idiom_codes[src], idiom_codes[idiom])
            score = bleu_scores.get(system, {}).get(key)
            if score is not None:
                scores.append(score)
        if scores:
            return sum(scores) / len(scores)
        else:
            return None

def format_bleu(score):
    if score is None:
        return "--"
    return f"{score:.1f}"

# Build the table values
table_values = {}
for system in systems:
    sys_key = system.lower().replace("-finetuned", "_finetuned").replace("-", "").replace(" ", "")
    for idiom in idioms:
        bleu_from = get_bleu(system, idiom, "from")
        bleu_into = get_bleu(system, idiom, "into")
        table_values[f"{sys_key}_{idiom}_from"] = format_bleu(bleu_from)
        table_values[f"{sys_key}_{idiom}_into"] = format_bleu(bleu_into)
    # Compute average over all directions (10 directions)
    all_scores = []
    for src in idioms:
        for tgt in idioms:
            if src == tgt:
                continue
            key = (idiom_codes[src], idiom_codes[tgt])
            score = bleu_scores.get(system, {}).get(key)
            if score is not None:
                all_scores.append(score)
    if all_scores:
        avg = sum(all_scores) / len(all_scores)
    else:
        avg = None
    table_values[f"{sys_key}_avg"] = format_bleu(avg)

# Fill in the template using replace to avoid issues with other {}
table_str = TABLE_TEMPLATE

idioms_list = ["sursilvan", "sutsilvan", "surmiran", "puter", "vallader"]
directions = ["from", "into"]

# Compute min and max BLEU values for color scaling
bleu_numeric_values = []
for v in table_values.values():
    try:
        # Only consider numeric values (not "--" or None)
        if v is not None and v != "--":
            bleu_numeric_values.append(float(v))
    except Exception:
        continue

if bleu_numeric_values:
    min_bleu = min(bleu_numeric_values)
    max_bleu = max(bleu_numeric_values)
else:
    min_bleu = 0.19
    max_bleu = 1.0  # avoid div by zero

def bleu_to_color(score):
    """
    Map BLEU score to color intensity for LaTeX cellcolor.
    0.0 -> 0 (white), max_bleu -> 100 (full color)
    """
    if score is None or score == "--":
        return ""
    try:
        score = float(score)
    except Exception:
        return ""
    if max_bleu == min_bleu:
        intensity = 38  # fallback
    else:
        norm = (score - min_bleu) / (max_bleu - min_bleu)
        intensity = int(norm * 30)
    return f"\\cellcolor{{uzhblue!{intensity}}}"

for sys_key in ["gpt4o", "gpt4omini", "gpt4omini_finetuned"]:
    for idiom in idioms_list:
        for direction in directions:
            key = f"{sys_key}_{idiom}_{direction}"
            table_key = f"{sys_key}_{idiom}_{direction}"
            value = table_values.get(table_key)
            # For color, try to extract the numeric value
            if value is not None and value != "--" and value != "tba":
                try:
                    numeric = float(value)
                except Exception:
                    numeric = None
            else:
                numeric = None
            color = bleu_to_color(value)
            if value is None:
                value_str = "tba"
            else:
                value_str = value
            if color:
                latex_value = f"{color} {value_str}"
            else:
                latex_value = value_str
            table_str = table_str.replace("{" + key + "}", latex_value)
    # avg
    avg_key = f"{sys_key}_avg"
    avg_table_key = f"{sys_key}_avg"
    value = table_values.get(avg_table_key)
    if value is not None and value != "--" and value != "tba":
        try:
            numeric = float(value)
        except Exception:
            numeric = None
    else:
        numeric = None
    color = bleu_to_color(value)
    if value is None:
        value_str = "tba"
    else:
        value_str = value
    if color:
        latex_value = f"{color} {value_str}"
    else:
        latex_value = value_str
    table_str = table_str.replace("{" + avg_key + "}", latex_value)

print(table_str)

# Print a BLEU matrix table for each system, with color highlighting
for system in systems:
    sys_key = system.lower().replace("-", "").replace(" ", "")
    print(f"\nSystem: {system}\n")
    print(r"\begin{tabularx}{\textwidth}{@{}Xrrrrr}")
    print(r"\toprule")
    print(r"\textbf{Source} $\rightarrow$ \textbf{Target} & \textbf{Sursilvan} & \textbf{Sutsilvan} & \textbf{Surmiran} & \textbf{Puter} & \textbf{Vallader} \\")
    print(r"\midrule")
    for src in idioms_list:
        row = []
        row.append(f"\\textbf{{{src.capitalize()}}}")
        for tgt in idioms_list:
            if src == tgt:
                cell = "--"
            else:
                key = (idiom_codes[src], idiom_codes[tgt])
                score = bleu_scores.get(system, {}).get(key)
                if score is not None:
                    formatted = format_bleu(score)
                    color = bleu_to_color(formatted)
                    if color:
                        cell = f"{color} {formatted}"
                    else:
                        cell = formatted
                else:
                    cell = "tba"
            row.append(cell)
        print("   & ".join(row) + r" \\")
    print(r"\bottomrule")
    print(r"\end{tabularx}")
    print()

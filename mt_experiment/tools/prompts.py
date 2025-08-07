from pathlib import Path

import ipdb
import json

language_mapping = {
    "rm_sursilv": "Sursilvan",
    "rm_vallader": "Vallader",
    "rm_puter": "Puter",
    "rm_surmiran": "Surmiran",
    "rm_sutsilv": "Sutsilvan"
}


def get_prompt(segment, source_language, target_language, prompt_style):
    # use English name of language
    source_lang_name = language_mapping[source_language]
    target_lang_name= language_mapping[target_language]

    template = 'Translate the following segment surrounded in triple backticks into {target_language}. The {source_language} segment: \n```{source_segment}```\n'

    few_shots = load_shots(source_language, target_language)
    
    if prompt_style == "conversation":
        prompt = []
        for shot in few_shots:
            content = template.format(target_language=target_lang_name, source_language=source_lang_name, source_segment=shot["source"])
            prompt.append({
                "role": "user",
                "content": content
            })
            answer = f"```{shot['target']}```"

            prompt.append({
                "role": "assistant",
                "content": answer
            })

        prompt.append({
                "role": "user",
                "content": template.format(target_language=target_lang_name, source_language=source_lang_name, source_segment=segment)
            })
    
    if prompt_style == "textual":
        prompt = ""
        for shot in few_shots:
            prompt += template.format(target_language=target_lang_name, source_language=source_lang_name, source_segment=shot["source"])            
            prompt += f"Translated {target_lang_name} segment: ```{shot['target']}```\n\n"

        prompt += template.format(target_language=target_lang_name, source_language=source_lang_name, source_segment=segment)
        prompt += f"Translated {target_lang_name} segment: "
        
    return prompt

def load_shots(source_language, target_language):
    # load few-shot examples from file
    few_shots_dir = Path(__file__).parent.parent / "few_shots"
    with open(few_shots_dir / f"shots.{source_language}-{target_language}.json") as f:
        few_shots = json.load(f)
    return few_shots

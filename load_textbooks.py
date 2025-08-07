from pathlib import Path
from bs4 import BeautifulSoup
from tqdm import tqdm

from models.textbook import Textbook
from datasets import Dataset, Features, Value, load_from_disk
import json
# from textbooks.constants import CONTENT_TYPES_INCLUDED, IDIOMS_MAPPING, CACHE_DIR
from constants import CONTENT_TYPES_INCLUDED, IDIOMS_MAPPING, CACHE_DIR
import re
from extract_natural_language import extract_text, extract_text_workbook_teacher, strip_html_tags
from sorting_utils import sort_teacher_commentary_segments, sort_workbook_segments
from sentence_utils import postprocess_merge_sentences
from collections import defaultdict
import os
import zipfile
import string


def load_and_filter_jsonl(filepath):
    data = []
    textbooks = []
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            parsed_line = json.loads(line)
            data.append(parsed_line)
            if parsed_line["contentType"] == "book":
                textbooks.append(parsed_line)
    return data, textbooks


def init_textbooks_list(textbooks):
    textbooks_dict = {}
    for txtbook in textbooks:
        common_args = {
            'idiom': txtbook['properties']['idiom'],
            'subject': 'language',
            'grade_volume': f"{txtbook['properties']['klass']}.{txtbook['properties']['workBook']}",
            'ISBN': str(txtbook['properties'].get('isbn', ''))
        }
        base_path = str(txtbook['route']['path'])
        wb_path = f"{base_path}/workbook"
        tc_path = f"{base_path}/teachers_commentary"
        textbooks_dict[wb_path] = Textbook(**common_args, book_type='workbook', textbook_path=f"{base_path}/workbook")
        textbooks_dict[tc_path] = Textbook(**common_args, book_type='teacher\'s commentary', textbook_path=f"{base_path}/teachers_commentary")
    return textbooks_dict


def define_textbook_type(content_type, path):
    if content_type in ['explanation', 'solution', 'chapter']:
        return 'teachers_commentary'
    if re.search(r"lernkontrolle-\d+", path):
        return 'teachers_commentary'
    pattern = r"kopiervorlage[^/]*\/."
    if bool(re.search(pattern, path)):
        return 'teachers_commentary'
    return 'workbook'


def build_stripped_to_html_map(soup):
    """
    Returns a dict mapping stripped_text -> best-matching element HTML.
    Chooses <p> first, then other block tags, then shortest match.
    """
    stripped_map = {}
    # Consider only block-level tags (far fewer than “all”)
    block_tags = ['p','div','li','td','th','h1','h2','h3','h4','h5','h6','caption','dt','dd']
    for el in soup.find_all(block_tags):
        html = str(el)
        text = strip_html_tags(html).strip()
        if not text:
            continue
        # if not seen yet, or this html is a tighter match, record it
        prev = stripped_map.get(text)
        if prev is None or len(html) < len(prev):
            stripped_map[text] = html
    return stripped_map



def save_segments_to_textbooks(json_list, textbooks_dict, split_segments_into_sentences=False):
    if split_segments_into_sentences:
        dataset_features = Features({
            "segmentId": Value("string"),
            "sentenceId": Value("string"),
            "sentenceExtractedText": Value("string"),
            "sentenceHTML": Value("string"),
            "segmentPath": Value("string"),
            "contentType": Value("string"),
            "chapterPath": Value("string")
        })
    else:
        dataset_features = Features({
            "segmentId": Value("string"), 
            "segmentPath": Value("string"),
            "segmentExtractedText": Value("string"),
            "contentType": Value("string"),
            "chapterPath": Value("string")
        })
    rows_per_book = defaultdict(list)

    total_segments = len(json_list)
    for idx, json_line in tqdm(enumerate(json_list), total=total_segments, desc="Processing segments"):
        content_type = json_line.get("contentType")
        if content_type in CONTENT_TYPES_INCLUDED:
            segment_path = json_line["route"]["path"]
            match_base = re.match(r"^(/[^/]+/[^/]+/[^/]+)", segment_path)
            path_base = match_base.group(1) if match_base else None

            if content_type == "topicsPage": # special case  
                if path_base:
                    parts = path_base.split('/')
                    # parts will be ['', 'idiom', 'klasse-X', 'vorwort-Y']
                    if len(parts) == 4 and 'vorwort' in parts[3]:
                        # Extract the number from 'vorwort-Y'
                        num_match = re.search(r'-(\d+)$', parts[3])
                        if num_match:
                            number = num_match.group(1)
                            parts[3] = f'arbeitsbuch-{number}'
                            path_base = '/'.join(parts)

                extracted_text_workbook, extracted_text_teacher, wb, tc, wb_htmls, tc_htmls = extract_text_workbook_teacher(json_line)
                if extracted_text_workbook != "" and extracted_text_teacher != "":
                    for role, extracted in [('workbook', extracted_text_workbook), ('teachers_commentary', extracted_text_teacher)]:
                        full_path = f"{path_base}/{role}"
                        #teacher_path = f"{path_base}/teachers_commentary"
                        if full_path in textbooks_dict:
                            if split_segments_into_sentences:
                                text_chunks_for_role = wb if role == 'workbook' else tc
                                html_chunks_for_role = wb_htmls if role == 'workbook' else tc_htmls
                                for text_chunk_idx, text_chunk_content in enumerate(text_chunks_for_role):
                                    html_chunk_content = html_chunks_for_role[text_chunk_idx] if text_chunk_idx < len(html_chunks_for_role) else ""
                                    if not text_chunk_content.strip(): # Skip if the text chunk itself is empty
                                        continue
                                    soup_for_chunk = BeautifulSoup(html_chunk_content, 'html.parser')
                                    mapping = build_stripped_to_html_map(soup_for_chunk)
                                    count = 0
                                    for line in text_chunk_content.splitlines():
                                        text = line.strip()
                                        inner = re.sub(r'<[^>]+>', '', text)
                                        if not inner.strip() or all(ch in string.punctuation or ch.isspace() for ch in inner): # skip empty or punctuation-only lines
                                            continue
                                        specific_sentence_html = mapping.get(text, html_chunk_content)
                                        rows_per_book[full_path].append({
                                            "segmentId": str(json_line["id"]),
                                            "sentenceId": f"{json_line['id']}.{count}",
                                            "sentenceExtractedText": text,
                                            "sentenceHTML": specific_sentence_html,
                                            "segmentPath": full_path,
                                            "contentType": content_type,
                                            "chapterPath": segment_path if segment_path else "",
                                        })
                                        count += 1
                            else:
                                rows_per_book[full_path].append({
                                    "segmentId": str(json_line["id"]),
                                    "segmentPath": full_path,
                                    "segmentExtractedText": extracted,
                                    "contentType": content_type,
                                    "chapterPath": segment_path if segment_path else ""
                                })
            else:
                target_booktype = define_textbook_type(content_type, segment_path)
                full_path = f"{path_base}/{target_booktype}"
                if full_path in textbooks_dict:
                    extracted_primary_string, unique_text_chunks, html_for_unique_chunks = extract_text(json_line)
                    extracted = extracted_primary_string or ""
                    if extracted:
                        if split_segments_into_sentences:
                            count = 0
                            for chunk_idx, chunk_content in enumerate(unique_text_chunks):
                                html_for_this_chunk = html_for_unique_chunks[chunk_idx] if chunk_idx < len(html_for_unique_chunks) else ""
                                if not chunk_content.strip():
                                    continue
                                soup_for_chunk = BeautifulSoup(html_for_this_chunk, 'html.parser')
                                mapping = build_stripped_to_html_map(soup_for_chunk)
                                for line in chunk_content.splitlines():
                                    text = line.strip()
                                    inner = re.sub(r'<[^>]+>', '', text)
                                    if not inner.strip() or all(ch in string.punctuation or ch.isspace() for ch in inner):
                                        continue
                                    specific_sentence_html = mapping.get(text, html_for_this_chunk)
                                    rows_per_book[full_path].append({
                                        "segmentId": str(json_line["id"]),
                                        "sentenceId": f"{json_line['id']}.{count}",
                                        "sentenceExtractedText": text,
                                        "sentenceHTML": specific_sentence_html,
                                        "segmentPath": full_path,
                                        "contentType": content_type,
                                        "chapterPath": segment_path if segment_path else "",
                                    })
                                    count += 1
                        else:
                            rows_per_book[full_path].append({
                                "segmentId": str(json_line["id"]),
                                "segmentPath": segment_path,
                                "segmentExtractedText": extracted,
                                "contentType": content_type,
                                "chapterPath": segment_path if segment_path else ""
                            })       
    return rows_per_book, dataset_features


def load_textbooks(sort_like_sample_textbooks=False, data_path=None, split_segments_into_sentences=False):
    if data_path is None:
        data_path = Path(__file__).parent / 'raw_data'
    zip_path     = data_path / 'umbraco-export.v1.zip'
    extract_dir  = data_path
    jsonl_name   = 'umbraco-export.v1.jsonl'
    jsonl_path   = os.path.join(extract_dir, 'umbraco-export.v1', jsonl_name)
    
    if not os.path.exists(jsonl_path):
        print(f"Extracting {zip_path} → {extract_dir} …")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

    print(f"Loading metadata from {jsonl_path} …")
    json_list, textbooks_meta = load_and_filter_jsonl(jsonl_path)
    textbooks_dict = init_textbooks_list(textbooks_meta)

    # Prepare segment data
    rows_per_book, features = save_segments_to_textbooks(json_list, textbooks_dict, split_segments_into_sentences)
    if split_segments_into_sentences:
        print("Post-processing sentences for merging...")
        rows_per_book = postprocess_merge_sentences(rows_per_book)
        print("Sentence merging complete.")
    os.makedirs(CACHE_DIR, exist_ok=True)

    loaded, built = 0, 0
    for _, tb in enumerate(textbooks_dict.values()):
        # Determine safe cache folder name
        mapped_idiom = IDIOMS_MAPPING.get(tb.idiom, tb.idiom)
        safe_name = f"{mapped_idiom.lower()}_{tb.grade_volume.replace('.', '_')}_{tb.book_type.replace(' ', '_')}"
        cache_folder = os.path.join(CACHE_DIR, safe_name)

        if os.path.isdir(cache_folder):
            # Load existing dataset
            try:
                tb.hf_dataset = load_from_disk(cache_folder)
                tb.idiom = mapped_idiom
                print(f"Loaded from cache: {mapped_idiom} {tb.grade_volume} {tb.book_type}")
                loaded += 1
                continue
            except Exception as e:
                print(f"Failed to load cache for {mapped_idiom} at {cache_folder}: {e}")
                # fall through to rebuild

        tb.idiom = mapped_idiom
        # Build dataset if no cache or load failed
        rows = rows_per_book.get(tb.textbook_path, [])
        if not rows:
            print(f"No segments for {mapped_idiom} {tb.grade_volume} {tb.book_type}, skipping.")
            continue

        if sort_like_sample_textbooks:
            # Sort segments for teacher's commentary
            if tb.book_type == "teacher's commentary":
                rows = sort_teacher_commentary_segments(rows, tb.textbook_path)
            elif tb.book_type == "workbook":
                rows = sort_workbook_segments(rows, tb.textbook_path)

        data = { key: [r[key] for r in rows] for key in rows[0].keys() }
        ds = Dataset.from_dict(data, features=features)
        tb.hf_dataset = ds

        # Save to cache
        os.makedirs(cache_folder, exist_ok=True)
        try:
            ds.save_to_disk(cache_folder)
            print(f"Built and cached: {mapped_idiom} {tb.grade_volume} {tb.book_type}")
            built += 1
        except Exception as e:
            print(f"Failed to save cache for {mapped_idiom}: {e}")

    ret_txtbook_dict = {
        path: tb
        for path, tb in textbooks_dict.items()
        if hasattr(tb, 'hf_dataset') and len(tb.hf_dataset) > 0
    }
    print(f"Finished. Loaded {loaded}, Built {built}, Total textbooks: {len(ret_txtbook_dict.values())}.")
    # Return only textbooks with datasets
    return ret_txtbook_dict

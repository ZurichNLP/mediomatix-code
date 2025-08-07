import re
from html import unescape

def strip_html_tags(text):
    """Remove HTML tags, unescape HTML entities, and convert <b> to <strong>."""
    text = unescape(text)
    # Convert <b> and </b> to <strong> and </strong>
    text = re.sub(r'<b\b[^>]*>', '<strong>', text, flags=re.IGNORECASE)
    text = re.sub(r'</b\s*>', '</strong>', text, flags=re.IGNORECASE)
    # Remove all other HTML tags, except for <strong> and </strong>
    text = re.sub(r'<(?!\/?strong\b)[^>]+>', '', text)
    return text.strip()

def collect_texts(obj, texts, html_pieces):
    """
    Walk through dicts/lists and append any
    matching text pieces into `texts` list.
    """
    if isinstance(obj, dict):
        # skip pure image entries
        if obj.get('mediaType') == 'Image':
            return

        for key, val in obj.items():
            if key == 'url':
                continue

            if key in ('memoTitle') and isinstance(val, str):
                texts.append(val)
                html_pieces.append(val)

            if key == 'properties' and isinstance(val, dict):
                title = val.get('title')
                if title and obj["contentType"] != "chapter":
                    texts.append(title)
                    html_pieces.append(title)

            if key == 'markup' and isinstance(val, str):
                stripped = strip_html_tags(val)
                if stripped:
                    texts.append(stripped)
                    html_pieces.append(val)

            # recurse
            collect_texts(val, texts, html_pieces)

    elif isinstance(obj, list):
        for item in obj:
            collect_texts(item, texts, html_pieces)

def collect_texts_workbook_commentary(obj, workbook_texts, teacher_texts, workbook_htmls, teacher_htmls, current_obj_is_main_content_context, parent_content_type=None):
    """
    Recursive helper to collect texts into workbook and teacher lists.
    - current_obj_is_main_content_context: True if 'obj' is the content of a 'mainContent' field.
      This helps decide where generic 'markup' fields go.
    - parent_content_type: The 'contentType' of the object that contained the current 'obj'
      if 'obj' is, for example, a 'properties' dictionary.
    """
    if isinstance(obj, dict):
        if obj.get('mediaType') == 'Image':
            return

        for key, val in obj.items():
            if key == 'url':
                continue

            if key == 'mainContent' and isinstance(val, dict):
                markup = val.get('markup')
                if markup and isinstance(markup, str):
                    stripped = strip_html_tags(markup)
                    if stripped:
                        teacher_texts.append(stripped)
                        teacher_htmls.append(markup)
                collect_texts_workbook_commentary(val, workbook_texts, teacher_texts, workbook_htmls, teacher_htmls, True, obj.get("contentType"))
            
            elif key == 'mainContent2' and isinstance(val, dict):
                markup = val.get('markup')
                if markup and isinstance(markup, str):
                    stripped = strip_html_tags(markup)
                    if stripped:
                        workbook_texts.append(stripped) # mainContent2.markup to workbook
                        workbook_htmls.append(markup)
                collect_texts_workbook_commentary(val, workbook_texts, teacher_texts, workbook_htmls, teacher_htmls, False, obj.get("contentType"))

            elif key == 'memoTitle' and isinstance(val, str):
                workbook_texts.append(val)
                workbook_htmls.append(val)
            
            elif key == 'properties' and isinstance(val, dict):
                # 'title' within 'properties' depends on the contentType of 'obj' (the holder of 'properties')
                title = val.get('title')
                if title and isinstance(title,str) and obj.get("contentType") != "chapter":
                    workbook_texts.append(strip_html_tags(title))
                    workbook_htmls.append(title)
                collect_texts_workbook_commentary(val, workbook_texts, teacher_texts, workbook_htmls, teacher_htmls, False, obj.get("contentType"))
            
            elif key == 'markup' and isinstance(val, str):
                if not current_obj_is_main_content_context: # we want to collect all non-mainContent markup into workbook_texts
                    stripped = strip_html_tags(val)
                    if stripped:
                        workbook_texts.append(stripped)
                        workbook_htmls.append(val)
            
            elif isinstance(val, (dict, list)) and key not in ('mainContent', 'mainContent2', 'properties'):
                 collect_texts_workbook_commentary(val, workbook_texts, teacher_texts, workbook_htmls, teacher_htmls, False, obj.get("contentType"))

    elif isinstance(obj, list):
        for item in obj:
            # Propagate context and parent_content_type. parent_content_type might be less relevant for list items directly.
            collect_texts_workbook_commentary(item, workbook_texts, teacher_texts, workbook_htmls, teacher_htmls, current_obj_is_main_content_context, parent_content_type)

def extract_text(obj):
    """
    Return all text from the dict.
    """
    bits = []
    html_bits = []
    collect_texts(obj, bits, html_bits)

    unique_texts_intermediate = []
    corresponding_htmls_intermediate = []
    seen_texts = set()

    for i, text_item in enumerate(bits):
        # Deduplicate based on the stripped text_item
        if text_item not in seen_texts:
            unique_texts_intermediate.append(text_item)
            if i < len(html_bits): # Ensure index is valid for HTML list
                corresponding_htmls_intermediate.append(html_bits[i])
            else:
                # This case should ideally not be reached if collect_texts is correct
                corresponding_htmls_intermediate.append("") # Fallback
            seen_texts.add(text_item)
    return "\n".join(bits), unique_texts_intermediate, corresponding_htmls_intermediate # Return both

def extract_text_workbook_teacher(obj):
    """
    Extracts texts into workbook and teacher commentary.
    Workbook: general texts + mainContent2.markup
    Teacher Commentary: mainContent.markup
    """
    workbook_bits = []
    teacher_bits = []
    workbook_htmls = []
    teacher_htmls = []

    collect_texts_workbook_commentary(obj, workbook_bits, teacher_bits, workbook_htmls, teacher_htmls, False, obj.get("contentType"))
    
    # Remove duplicates while preserving order (Python 3.7+)
    # This is a safeguard; ideally, the logic prevents duplicate additions of the same text item.
    unique_workbook_bits = list(dict.fromkeys(workbook_bits))
    unique_teacher_bits = list(dict.fromkeys(teacher_bits))

    workbook_string = "\n".join(unique_workbook_bits)
    teacher_commentary_string = "\n".join(unique_teacher_bits)

    unique_workbook_texts_intermediate = []
    corresponding_workbook_htmls = []
    seen_wb_texts = set()
    for i, text in enumerate(workbook_bits):
        if text not in seen_wb_texts:
            unique_workbook_texts_intermediate.append(text)
            if i < len(workbook_htmls): # Ensure index is valid for HTML list
                corresponding_workbook_htmls.append(workbook_htmls[i])
            seen_wb_texts.add(text)
    
    unique_teacher_texts_intermediate = []
    corresponding_teacher_htmls = []
    seen_tc_texts = set()
    for i, text in enumerate(teacher_bits):
        if text not in seen_tc_texts:
            unique_teacher_texts_intermediate.append(text)
            if i < len(teacher_htmls): # Ensure index is valid for HTML list
                corresponding_teacher_htmls.append(teacher_htmls[i])
            seen_tc_texts.add(text)
    
    return workbook_string, teacher_commentary_string, unique_workbook_texts_intermediate, unique_teacher_texts_intermediate, corresponding_workbook_htmls, corresponding_teacher_htmls

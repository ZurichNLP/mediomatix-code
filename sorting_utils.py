import re

def _alphanum_key(s):
    """
    Turn a string into a list of string and number chunks.
    "z23a" -> ["z", 23, "a"]
    Needed for natural sorting.
    """
    def tryint(s_chunk):
        try:
            return int(s_chunk)
        except ValueError:
            return s_chunk
    return [tryint(c) for c in re.split('([0-9]+)', s)]

def _transform_path_for_natural_sort(path_string):
    """
    Transforms a path string into a list of naturally sorted components.
    Example: "/a/b/10-item" -> [["a"], ["b"], ["", 10, "-item"]]
    """
    if not path_string:
        return [] 
    segments = [segment for segment in path_string.lstrip('/').split('/') if segment]
    if not segments: 
        return []
    return [_alphanum_key(s) for s in segments]

def sort_teacher_commentary_segments(segments, base_tc_path):
    """
    Sorts segments for a teacher's commentary book with detailed multi-level logic,
    including natural sorting for numbered chapter/section names.
    """
    book_level_priority_rows = []
    other_rows = []
    for row_data in segments:
        if row_data.get("segmentPath", "") == base_tc_path:
            book_level_priority_rows.append(row_data)
        else:
            other_rows.append(row_data)

    if not other_rows:
        return book_level_priority_rows

    book_base_path_parts = base_tc_path.split('/')[:-1] 

    def get_sort_key(item):
        path = item["segmentPath"]
        content_type = item["contentType"]
        path_parts = path.split('/')

        major_collection_path_val = ""
        if len(path_parts) > len(book_base_path_parts):
            if len(path_parts) >= len(book_base_path_parts) + 1:
                 major_collection_path_val = "/".join(path_parts[:len(book_base_path_parts) + 1])
            else:
                major_collection_path_val = path 
        else:
            major_collection_path_val = path

        is_major_overview_page_val = 1 
        if path == major_collection_path_val and content_type == 'chapter':
            is_major_overview_page_val = 0 

        content_group_priority_val = 5 # Default for CGP_OTHER
        grouping_key_for_content_group_val_orig = path 
        type_priority_within_grouping_key_val = 0 # Default

        if is_major_overview_page_val == 0:
            content_group_priority_val = -1 # Sorts before all content groups
            grouping_key_for_content_group_val_orig = "" 
        else:
            is_lk_item = "/lernkontrolle-" in path
            is_kv_item = "/kopiervorlage-" in path

            if content_type == 'explanation': # General Explanations
                content_group_priority_val = 0  # CGP_ES_GENERAL
                grouping_key_for_content_group_val_orig = "/".join(path_parts[:-1]) 
                type_priority_within_grouping_key_val = 0  
            
            elif content_type == 'solution' and not is_lk_item: # General Solutions
                content_group_priority_val = 0  # CGP_ES_GENERAL
                grouping_key_for_content_group_val_orig = "/".join(path_parts[:-1]) 
                type_priority_within_grouping_key_val = 1  
            
            elif is_kv_item: # Kopiervorlagen
                content_group_priority_val = 1  # CGP_KV_CONTENT
                kv_parent_match = re.match(r"(.+)/kopiervorlage-\d+/", path)
                if kv_parent_match:
                    grouping_key_for_content_group_val_orig = kv_parent_match.group(1)
                else: 
                    grouping_key_for_content_group_val_orig = "/".join(path_parts[:-1]) if content_type != 'chapter' else path
                # type_priority_within_grouping_key_val remains 0 for KV items
            
            elif is_lk_item: # Lernkontrolle items
                lk_auftrag_match = re.match(r"(.*/lernkontrolle-\d+/lernkontrolle-auftrag-\d+)", path)
                if lk_auftrag_match:
                    grouping_key_for_content_group_val_orig = lk_auftrag_match.group(1)
                else: 
                    grouping_key_for_content_group_val_orig = "/".join(path_parts[:-1]) if content_type != 'chapter' else path

                if content_type == 'solution': # Lernkontrolle Solutions
                    content_group_priority_val = 3  # CGP_LK_SOL
                else: # Lernkontrolle Content (e.g., bild-und-text)
                    content_group_priority_val = 2  # CGP_LK_CONTENT
                # type_priority_within_grouping_key_val remains 0 for LK items as CGP differentiates them
            
            elif content_type == 'chapter': # Other chapter pages
                content_group_priority_val = 4  # CGP_CHAPTER_OTHER
                grouping_key_for_content_group_val_orig = path
                # type_priority_within_grouping_key_val remains 0
            
            # Else, it remains CGP_OTHER (5)

        sortable_grouping_key = _transform_path_for_natural_sort(grouping_key_for_content_group_val_orig)
        sortable_full_path_key = _transform_path_for_natural_sort(path)

        return (major_collection_path_val,
                is_major_overview_page_val,
                content_group_priority_val,
                sortable_grouping_key, 
                type_priority_within_grouping_key_val,
                sortable_full_path_key)

    other_rows.sort(key=get_sort_key)
    return book_level_priority_rows + other_rows

def sort_workbook_segments(segments, base_workbook_path=None):
    """
    Sorts segments for a workbook.
    1. The segment matching base_workbook_path (if provided).
    2. Other segments with contentType 'chapter', sorted by path.
    3. All other segments, sorted by path.
    Natural sort is used for paths.
    """
    def get_workbook_sort_key(item):
        path = item.get("segmentPath", "")
        content_type = item.get("contentType", "")

        is_base_path_val = 1 # Default: not base path
        if base_workbook_path and path == base_workbook_path:
            is_base_path_val = 0 # Highest priority if it's the base workbook path
        
        is_chapter_val = 1 # Default: not a chapter
        if content_type == "chapter":
            is_chapter_val = 0 # Prioritize chapters over non-chapters

        sortable_path_key = _transform_path_for_natural_sort(path)

        return (is_base_path_val, is_chapter_val, sortable_path_key)

    # Create a new list or sort in place if segments can be modified
    sorted_segments = sorted(segments, key=get_workbook_sort_key)
    return sorted_segments

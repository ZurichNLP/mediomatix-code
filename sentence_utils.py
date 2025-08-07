import re
from collections import defaultdict

def postprocess_merge_sentences(rows_per_book_input):
    """
    Post-processes rows to merge sentences based on specific patterns.
    - Merges "a)" or "1." type prefixes with the subsequent sentence.
    - Handles '•' character:
        - If '•' is followed by another '•', the first '•' is removed.
        - If '•' is followed by a different sentence, they are merged.
    - Updates sentenceHTML by concatenation.
    - Re-indexes sentenceId within segments if merges or removals occur.
    """
    processed_rows_per_book = defaultdict(list)
    bullet_char = '•' # U+2022 BULLET
    for book_path, book_rows in rows_per_book_input.items():
        if not book_rows:
            processed_rows_per_book[book_path] = []
            continue
        # Group rows by segmentId for processing
        segments_in_book = defaultdict(list)
        for row in book_rows:
            segments_in_book[row['segmentId']].append(row)
        newly_processed_book_rows = []
        for segment_id, segment_sentences in segments_in_book.items():
            if not segment_sentences:
                continue
            merged_segment_sentences = []
            i = 0
            merges_happened_in_segment = False
            while i < len(segment_sentences):
                current_row = segment_sentences[i]
                current_text_stripped = current_row['sentenceExtractedText'].strip()
                action_taken_this_iteration = False
                # Rule 1: Handle '•' character
                if current_text_stripped == bullet_char:
                    merges_happened_in_segment = True
                    action_taken_this_iteration = True
                    if i + 1 < len(segment_sentences): # If there's a next sentence
                        next_row = segment_sentences[i+1]
                        next_text_stripped = next_row['sentenceExtractedText'].strip()

                        if next_text_stripped == bullet_char:
                            # Current '•' is followed by another '•'. Remove current '•'.
                            i += 1 # Advance to the next sentence (which is the second '•')
                        else:
                            # Current '•' is followed by a non-'•' sentence. Merge them.
                            merged_text = current_row['sentenceExtractedText'] + " " + next_row['sentenceExtractedText']
                            merged_html = current_row['sentenceHTML'] + next_row['sentenceHTML']
                            new_merged_row = {
                                "segmentId": current_row['segmentId'],
                                "sentenceId": "", # Will be re-indexed later
                                "sentenceExtractedText": merged_text,
                                "sentenceHTML": merged_html,
                                "segmentPath": current_row['segmentPath'],
                                "contentType": current_row['contentType'],
                                "chapterPath": current_row["chapterPath"]
                            }
                            merged_segment_sentences.append(new_merged_row)
                            i += 2 # Move past the two merged sentences
                    else:
                        i += 1
                    # If '•' is the last sentence, it will be handled by the default case later
                # Rule 2: Handle "a)" or "1." prefixes (if no action taken for '•')
                if not action_taken_this_iteration and i + 1 < len(segment_sentences):
                    # Check for pattern 1: "a)", "b)", etc.
                    is_letter_paren = re.fullmatch(r"^[a-zA-Z]\)$", current_text_stripped)
                    # Check for pattern 2: "1.", "2.", etc.
                    is_number_dot = re.fullmatch(r"^\d+\.$", current_text_stripped)
                    if is_letter_paren or is_number_dot:
                        next_row = segment_sentences[i+1]
                        # Merge text
                        merged_text = current_row['sentenceExtractedText'] + " " + next_row['sentenceExtractedText']
                        # Merge HTML
                        merged_html = current_row['sentenceHTML'] + next_row['sentenceHTML']
                        new_merged_row = {
                            "segmentId": current_row['segmentId'],
                            "sentenceId": "", # Will be re-indexed later
                            "sentenceExtractedText": merged_text,
                            "sentenceHTML": merged_html,
                            "segmentPath": current_row['segmentPath'],
                            "contentType": current_row['contentType'],
                            "chapterPath": current_row["chapterPath"]
                        }
                        merged_segment_sentences.append(new_merged_row)
                        merges_happened_in_segment = True
                        i += 2 # Move past the two merged sentences
                        action_taken_this_iteration = True
                if not action_taken_this_iteration:
                    merged_segment_sentences.append(current_row)
                    i += 1
            # Re-index sentence IDs if merges occurred in this segment
            if merges_happened_in_segment:
                for new_idx, row_to_reindex in enumerate(merged_segment_sentences):
                    row_to_reindex['sentenceId'] = f"{segment_id}.{new_idx}"
            newly_processed_book_rows.extend(merged_segment_sentences)
        processed_rows_per_book[book_path] = newly_processed_book_rows        
    return processed_rows_per_book
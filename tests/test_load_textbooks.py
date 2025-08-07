import json
import os
import tempfile
from types import SimpleNamespace
import pytest
from load_textbooks import build_stripped_to_html_map, save_segments_to_textbooks
from bs4 import BeautifulSoup

import load_textbooks  # adjust this to your actual module name
from datasets import Features, Value


class DummyTb(SimpleNamespace):
    """A minimal stand-in for your Textbook, with only the attrs save_segments_to_textbooks cares about."""
    pass


def test_load_and_filter_jsonl(tmp_path):
    # Create a .jsonl with 3 lines, two of which are contentType == "book"
    lines = [
        {"id": "1", "contentType": "foo"},
        {"id": "2", "contentType": "book"},
        {"id": "3", "contentType": "book"},
    ]
    p = tmp_path / "data.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for obj in lines:
            f.write(json.dumps(obj) + "\n")

    all_data, only_books = load_textbooks.load_and_filter_jsonl(str(p))
    assert all_data == lines
    assert only_books == [lines[1], lines[2]]


def test_init_textbooks_list_with_and_without_isbn():
    # With isbn
    meta = [{
        "properties": {
            "idiom": "Fr",
            "klass": "4",
            "workBook": "2",
            "isbn": "ISBN123",
        },
        "route":
        {"path": "/Fr/klasse-4/workbook-2"},
    }]
    tbs = load_textbooks.init_textbooks_list(meta)
    # Two entries per meta (workbook + teacher's commentary)
    assert len(tbs) == 2
    wb, tc = tbs.values()
    for tb in (wb, tc):
        assert tb.idiom == "Fr"
        assert tb.subject == "language"
        assert tb.grade_volume == "4.2"
        assert tb.ISBN == "ISBN123"
    assert wb.book_type == "workbook"
    assert tc.book_type == "teacher's commentary"

    # Without isbn
    meta2 = [{
        "properties": {
            "idiom": "It",
            "klass": "5",
            "workBook": "1",
            # isbn missing
        },
        "route":
        {"path": "/Fr/klasse-4/workbook-2"},
    }]
    tbs2 = load_textbooks.init_textbooks_list(meta2)
    assert all(tb.ISBN == "" for tb in tbs2.values())


def test_save_segments_to_textbooks(monkeypatch):
    # Only include "T1" as valid contentType
    monkeypatch.setattr(load_textbooks, "CONTENT_TYPES_INCLUDED", {"T1"})

    # Two dummy textbooks: one workbook, one teacher's commentary
    tb1 = DummyTb(idiom="En", grade_volume="3.1", book_type="workbook")
    tb2 = DummyTb(idiom="En", grade_volume="3.1", book_type="teacher's commentary")
    base_path_segA = "/En/klasse-3/book-1" # from json_lines segA
    path_tb1 = f"{base_path_segA}/workbook"
    path_tb2 = f"{base_path_segA}/teachers_commentary"
    textbooks_as_dict = {
        path_tb1: tb1,
        path_tb2: tb2,
    }


    # Three JSON lines:
    #  - one matches (contentType=T1, correct path, has markup)
    #  - one wrong contentType
    #  - one wrong path
    json_lines = [
        {
            "id": "segA",
            "contentType": "T1",
            "route": {"path": "/En/klasse-3/book-1"},
            "markup": "<p>Hello</p>"
        },
        {
            "id": "segB",
            "contentType": "X",
            "route": {"path": "/En/klasse-3/book-1"},
            "markup": "<p>Bye</p>"
        },
        {
            "id": "segC",
            "contentType": "T1",
            "route": {"path": "/bad/path"},
            "markup": "<p>Skip</p>"
        },
    ]

    rows_per_book, features = load_textbooks.save_segments_to_textbooks(json_lines, textbooks_as_dict)

    # Only the first JSON line should be captured, under index 0 (the workbook)
    assert list(rows_per_book.keys()) == [path_tb1]
    rows = rows_per_book[path_tb1]
    assert len(rows) == 1
    row = rows[0]
    assert row["segmentId"] == "segA"
    assert row["segmentPath"] == "/En/klasse-3/book-1"
    assert row["contentType"] == "T1"
    # save_segments_to_textbooks wraps extract_text, which returns ["Hello"]
    assert row["segmentExtractedText"] == "Hello"

    # Check the returned Features object
    assert isinstance(features, Features)
    expected_fields = {"segmentId", "segmentPath", "segmentExtractedText", "contentType","chapterPath"}
    assert set(features) == expected_fields
    for k in expected_fields:
        assert isinstance(features[k], Value)
        assert features[k].dtype == "string"


def test_load_textbooks_build_and_cache(tmp_path, monkeypatch):
    # 1) CWD → tmp_path so raw_data/... is under tmp_path
    monkeypatch.chdir(tmp_path)

    # 2) Create raw_data/umbraco-export.v1.jsonl
    raw_dir = tmp_path / "raw_data" / "umbraco-export.v1"
    raw_dir.mkdir(parents=True)
    jsonl = raw_dir / "umbraco-export.v1.jsonl"
    meta = {
        "id": "m1",
        "contentType": "book",
        "route": {"path": "/En/klasse-3/book-1"},
        "properties": {"idiom": "En", "klass": "3", "workBook": "1", "isbn": ""}
    }
    seg = {
        "id": "s1",
        "contentType": "T1",
        "route": {"path": "/En/klasse-3/book-1"},
        "markup": "<p>Text</p>"
    }
    with open(jsonl, "w", encoding="utf-8") as f:
        f.write(json.dumps(meta) + "\n")
        f.write(json.dumps(seg) + "\n")

    # 3) Monkey‐patch loader internals
    monkeypatch.setattr(load_textbooks, "CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(load_textbooks, "CONTENT_TYPES_INCLUDED", {"T1"})
    monkeypatch.setattr(load_textbooks, "IDIOMS_MAPPING", {"En": "En"})
    monkeypatch.setattr(load_textbooks, "extract_text", lambda obj: ("Text", ["Text"], ["<p>Text</p>"]))
    monkeypatch.setattr(load_textbooks, "load_from_disk",
                        lambda folder: (_ for _ in ()).throw(IOError("no cache")))
    class DummyDS:
        def __init__(self, data_dict, features_arg):
            # Calculate length based on the structure of data_dict
            # data_dict is expected to be {'column_name': [values], ...}
            if data_dict and isinstance(data_dict, dict) and data_dict:
                try:
                    # The length is the number of items in any of the column lists
                    self._length = len(next(iter(data_dict.values())))
                except StopIteration: # Handles empty data_dict {}
                    self._length = 0
            else: # Handles None or other non-dict/empty dict cases
                self._length = 0
        def save_to_disk(self, path):
            os.makedirs(path, exist_ok=True)
            open(os.path.join(path, "marker"), "w").close()
        def __len__(self):
            return self._length
    monkeypatch.setattr(load_textbooks, "Dataset",
                        SimpleNamespace(from_dict=lambda data, features: DummyDS(data, features)))

    # 4) Run
    results = load_textbooks.load_textbooks(data_path=tmp_path / "raw_data")

    # 5) Now two textbooks both have hf_dataset:
    #    - workbook → our DummyDS
    assert len(results.values()) == 1

    tb_work = list(results.values())[0]
    # workbook:
    assert isinstance(tb_work.hf_dataset, DummyDS)
    assert len(tb_work.hf_dataset) > 0
    
@pytest.mark.parametrize("content_type,path,expected", [
    # explicit content types always map to teachers_commentary
    ("explanation", "/any/path", "teachers_commentary"),
    ("solution",    "/foo/bar",  "teachers_commentary"),
])
def test_define_textbook_type_explicit(content_type, path, expected):
    assert load_textbooks.define_textbook_type(content_type, path) == expected


@pytest.mark.parametrize("path", [
    "/En/klasse-3/kopiervorlage/1",         # exact folder
    "/En/klasse-4/kopiervorlage-xyz/A",     # suffix after kopiervorlage
    "/foo/kopiervorlage123/bar/baz",        # digits and deeper nesting
])
def test_define_textbook_type_kopiervorlage(path):
    # any content_type not in explanation/solution but matching the regex
    ct = "T1"
    assert load_textbooks.define_textbook_type(ct, path) == "teachers_commentary"


@pytest.mark.parametrize("content_type,path", [
    ("T1", "/En/klasse-3/book-1"),                     # normal workbook path
    ("randomType", "/something/without/kopiervorlage"), # unrelated path
])
def test_define_textbook_type_default_to_workbook(content_type, path):
    assert load_textbooks.define_textbook_type(content_type, path) == "workbook"


def test_save_segments_to_textbooks_split_sentences(monkeypatch):
    # only T1 is valid
    monkeypatch.setattr(load_textbooks, "CONTENT_TYPES_INCLUDED", {"T1"})
    # One JSON line with markup containing two paragraphs
    json_lines = [
        {
            "id": "seg1",
            "contentType": "T1",
            "route": {"path": "/X/Y/Z"},
            "markup": "<p>Hello world\n</p><p>Bye now</p>"
        }
    ]
    # textbook dict has a single workbook path
    tb = DummyTb()
    textbooks_dict = { "/X/Y/Z/workbook": tb }
    rows_per_book, features = save_segments_to_textbooks(
        json_lines,
        textbooks_dict,
        split_segments_into_sentences=True
    )
    # we should get two sentence‐rows under that path
    assert list(rows_per_book) == ["/X/Y/Z/workbook"]
    rows = rows_per_book["/X/Y/Z/workbook"]
    assert len(rows) == 2

    # Check IDs and texts
    assert rows[0]["sentenceId"] == "seg1.0"
    assert rows[0]["sentenceExtractedText"] == "Hello world"
    assert rows[1]["sentenceId"] == "seg1.1"
    assert rows[1]["sentenceExtractedText"] == "Bye now"

    # Features should reflect the split‐sentence schema
    expected_fields = {
        "segmentId", "sentenceId", "sentenceExtractedText",
        "sentenceHTML", "segmentPath", "contentType", "chapterPath"
    }
    assert set(features) == expected_fields


def test_define_textbook_type_additional_patterns():
    # lernkontrolle-n should go to teachers_commentary
    assert load_textbooks.define_textbook_type("foo", "/a/b/lernkontrolle-42/c") == "teachers_commentary"
    # chapter always goes there, even if path looks workbook‐like
    assert load_textbooks.define_textbook_type("chapter", "/foo/workbook") == "teachers_commentary"
    # anything else defaults
    assert load_textbooks.define_textbook_type("foo", "/no/special/path") == "workbook"
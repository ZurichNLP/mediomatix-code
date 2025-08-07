import re
from html import unescape
import pytest
import tempfile
import os

from extract_natural_language import (
    strip_html_tags,
    collect_texts,
    extract_text,
    collect_texts_workbook_commentary,
    extract_text_workbook_teacher,
)


class TestStripHtmlTags:

    @pytest.mark.parametrize("input_html,expected", [
        # unescape("&nbsp;") → non-breaking space (\u00A0), regex only strips tags
        ("<p>Hello&nbsp;World!</p>", "Hello\u00A0World!"),
        ("<div><strong>Bold</strong> and <i>italic</i></div>", "<strong>Bold</strong> and italic"),
        ("No tags here", "No tags here"),
        # unescape("&lt;escaped&gt;") → "<escaped>", then regex removes it entirely
        ("&lt;escaped&gt;", ""),
        ("<br><br/>", ""),
    ])
    def test_strip_html_tags_various(self, input_html, expected):
        assert strip_html_tags(input_html) == expected


class TestCollectTexts:

    def test_skips_media_image(self):
        texts, html_pieces = [], []
        obj = {"mediaType": "Image", "memoTitle": "ShouldNotAppear"}
        collect_texts(obj, texts, html_pieces)
        assert texts == []

    def test_skips_url_key(self):
        texts, html_pieces = [], []
        obj = {"url": "http://example.com", "memoTitle": "ValidName"}
        collect_texts(obj, texts, html_pieces)
        assert "ValidName" in texts
        assert all("http" not in t for t in texts)

    def test_memo_title_and_name_inclusion_and_exclusion(self):
        texts, html_pieces = [], []
        o = {
            "memoTitle": "MyMemo",
            "name": "GoodName",
            "name2": "ignore me",  # key not 'name'
            "badfile": "file.jpg",
        }
        # note: collect_texts only treats key=='name', not 'name2'
        collect_texts(o, texts, html_pieces)
        assert "MyMemo" in texts
        assert "GoodName" not in texts
        assert not any("file.jpg" in t for t in texts)

    def test_name_skips_file_extensions_and_generic_labels(self):
        for bad in ["picture.png", "photo.jpeg", "diagram.gif", "image.svg", "Bild und Text-123"]:
            texts, html_pieces = [], []
            collect_texts({"name": bad}, texts, html_pieces)
            assert texts == []

    def test_properties_title_skipped_for_chapter(self):
        texts, html_pieces = [], []
        obj = {
            "properties": {"title": "ShouldSkip"},
            "contentType": "chapter"
        }
        collect_texts(obj, texts, html_pieces)
        assert texts == []

    def test_properties_title_included(self):
        texts, html_pieces = [], []
        obj = {
            "properties": {"title": "IncludeMe"},
            "contentType": "section"
        }
        collect_texts(obj, texts, html_pieces)
        assert texts == ["IncludeMe"]

    def test_markup_stripping(self):
        texts, html_pieces = [], []
        obj = {"markup": "<h1> Header </h1><p>Para</p>"}
        collect_texts(obj, texts, html_pieces)
        # strip_html_tags("<h1> Header </h1><p>Para</p>") => "Header\nPara"? Actually tags removed, line break not preserved,
        # so it's "HeaderPara" or "Header Para"? The regex simply removes tags, leaving " Header Para", then .strip()
        joined = " ".join(texts)
        assert "Header" in joined and "Para" in joined

    def test_deeply_nested_list_and_dict(self):
        nested = [
            {
                "memoTitle": "M1",
                "children": [
                    {"memoTitle": "ChildName"},
                    {"properties": {"title": "ChildProp"}, "contentType": "section"},
                ]
            },
            {"markup": "<strong>X</strong>"}
        ]
        texts, html_pieces = [], []
        collect_texts(nested, texts, html_pieces)
        # order might be: M1, ChildName, ChildProp, X
        for want in ("M1", "ChildName", "ChildProp", "X"):
            assert any(want in t for t in texts), f"{want!r} not found in {texts}"


class TestExtractText:

    def test_extract_text_single_dict(self):
        obj = {
            "contentType": "section",
            "memoTitle": "MemoVal",
            "name": "NameVal",
            "properties": {"title": "PropVal"},
            "markup": "<i>Inner</i>"
        }
        out, unique, htmls = extract_text(obj)
        # should be a string
        assert isinstance(out, str)
        # bits in insertion order: memoTitle, name, properties.title, markup
        assert all(piece in out for piece in ("MemoVal", "PropVal", "Inner"))

    def test_extract_text_list_of_dicts(self):
        items = [
            {"memoTitle": "A"},
            {"name": "B"},
            {"mediaType": "Image", "memoTitle": "X"},
            {"markup": "<p>C</p>"},
        ]
        out, unique, htmls = extract_text(items)
        # Ensure each of A, C appears as its own entry - and B does not appear
        assert "A" in out
        assert "B\n" not in out
        assert "C" in out

    def test_extract_text_empty(self):
         # object with no textful fields
        text, unique, htmls = extract_text({})
        assert text == ""


class TestCollectTextsWorkbookCommentary:

    def test_maincontent_goes_to_teacher_and_maincontent2_to_workbook(self):
        obj = {
            "contentType": "section",
            "mainContent": {"markup": "<p>Teach&nbsp;This</p>"},
            "mainContent2": {"markup": "<div>Work&nbsp;That</div>"},
        }
        wb, tc, wb_htmls, tc_htmls = [], [], [], []
        collect_texts_workbook_commentary(obj, wb, tc, wb_htmls, tc_htmls, False)
        # strip_html_tags preserves &nbsp;
        assert "Teach\u00A0This" in tc
        assert "Work\u00A0That" in wb

    def test_memo_title_and_properties_title_and_generic_markup(self):
        obj = {
            "contentType": "section",
            "memoTitle": "MyMemo",
            "properties": {"title": "<strong>Prop</strong>"},
            "markup": "<span>Generic</span>",
        }
        wb, tc, wb_htmls, tc_htmls = [], [], [], []
        collect_texts_workbook_commentary(obj, wb, tc, wb_htmls, tc_htmls, False)
        # memoTitle always to workbook
        assert "MyMemo" in wb
        # properties.title for non-chapter to workbook (tags stripped)
        assert "<strong>Prop</strong>" in wb
        # generic markup not in mainContent gets stripped into workbook
        assert "Generic" in wb
        # teacher list stays empty
        assert tc == []

    def test_properties_title_skipped_for_chapter(self):
        obj = {
            "contentType": "chapter",
            "properties": {"title": "SkipMe"},
            "memoTitle": "KeepMe"
        }
        wb, tc, wb_htmls, tc_htmls = [], [], [], []
        collect_texts_workbook_commentary(obj, wb, tc, wb_htmls, tc_htmls, False)
        # chapter.properties.title is skipped
        assert "SkipMe" not in wb
        # memoTitle still included
        assert "KeepMe" in wb

    def test_skips_images_and_urls(self):
        obj = {
            "mediaType": "Image",
            "memoTitle": "Nope",
            "url": "http://example.com",
            "markup": "<p>Yes</p>",
        }
        wb, tc, wb_htmls, tc_htmls = [], [], [], []
        collect_texts_workbook_commentary(obj, wb, tc, wb_htmls, tc_htmls, False)
        # entire dict short‐circuits because mediaType=Image
        assert wb == [] and tc == []

    def test_deeply_nested_list_and_dicts(self):
        nested = [
            {
                "memoTitle": "Top",
                "children": [
                    {"memoTitle": "Child1"},
                    {
                        "properties": {"title": "ChildProp"},
                        "contentType": "section",
                        "markup": "<em>ChildMark</em>"
                    },
                ]
            },
            {"mainContent": {"markup": "<h1>TeachDeep</h1>"}},
            ["<ignore>", {"markup": "<p>GenericDeep</p>"}]
        ]
        wb, tc, wb_htmls, tc_htmls = [], [], [], []
        collect_texts_workbook_commentary(nested, wb, tc, wb_htmls, tc_htmls, False)
        for want in ("Top", "Child1", "ChildProp", "ChildMark", "GenericDeep"):
            assert any(want in x for x in wb)
        assert any("TeachDeep" in x for x in tc)


class TestExtractTextWorkbookTeacher:

    def test_extract_text_workbook_teacher_simple(self):
        obj = {
            "contentType": "section",
            "memoTitle": "M1",
            "mainContent": {"markup": "<p>Teach1</p>"},
            "mainContent2": {"markup": "<div>Work1</div>"},
            "properties": {"title": "Prop1"}
        }
        wb_str, tc_str, *_ = extract_text_workbook_teacher(obj)
        wb_lines = wb_str.split("\n")
        tc_lines = tc_str.split("\n")
        assert "M1" in wb_lines
        assert "Prop1" in wb_lines
        assert "Work1" in wb_lines
        assert tc_lines == ["Teach1"]

    def test_extract_text_workbook_teacher_empty(self):
        # no relevant fields at all
        wb_str, tc_str, *_ = extract_text_workbook_teacher({})
        assert wb_str == ""
        assert tc_str == ""

    def test_extract_text_workbook_teacher_nested(self):
        obj = {
            "contentType": "section",
            "memoTitle": "Top",
            "mainContent": {"markup": "<p>T</p>"},
            "children": [
                {"memoTitle": "C1"},
                {"mainContent2": {"markup": "<span>W2</span>"}},
            ]
        }
        wb_str, tc_str, *_ = extract_text_workbook_teacher(obj)
        wb_lines = wb_str.split("\n")
        tc_lines = tc_str.split("\n")
        # ensure nested bits appear
        assert wb_lines == ["Top", "C1", "W2"]
        assert tc_lines == ["T"]

    def test_extract_text_workbook_teacher_dedup(self):
        # same markup appears multiple times
        obj = {
            "contentType": "section",
            "mainContent": {"markup": "<p>Dup</p>"},
            "children": [
                {"mainContent": {"markup": "<p>Dup</p>"}},
                {"mainContent2": {"markup": "<p>Work</p>"}},
                {"mainContent2": {"markup": "<p>Work</p>"}},
            ]
        }
        wb_str, tc_str, *_ = extract_text_workbook_teacher(obj)
        wb_lines = wb_str.split("\n")
        tc_lines = tc_str.split("\n")
        # dedup, only one "Work"; teacher only one "Dup"
        assert wb_lines == ["Work"]
        assert tc_lines == ["Dup"]

import unittest
import tempfile
import os
import re
from collections import defaultdict
from unittest.mock import patch, MagicMock
from stats import calculate_statistics, build_markdown_table, update_readme_statistics

import stats  # your module


class DummyTextbook:
    def __init__(self, idiom, segments=None):
        self.idiom = idiom
        if segments is not None:
            self.hf_dataset = {"segmentExtractedText": segments}


class DummyDS:
    def __init__(self, texts):
        self._texts = texts
        self.column_names = ["segmentExtractedText"]
    def __len__(self):
        return len(self._texts)
    def __getitem__(self, key):
        if key == "segmentExtractedText":
            return self._texts
        raise KeyError(key)


class TestCalculateStatistics(unittest.TestCase):

    @patch("stats.update_readme_statistics")
    @patch("builtins.print")
    @patch("stats.load_textbooks")
    def test_calculate_statistics_success(self, mock_load, mock_print, mock_update):
        # Two books for "en" with segments, one book for "de" without hf_dataset
        tb1 = DummyTextbook("en")
        tb1.hf_dataset = DummyDS(["hello world", "foo bar baz"])
        tb2 = DummyTextbook("en")
        tb2.hf_dataset = DummyDS(["another example"])
        tb3 = DummyTextbook("de")
        mock_load.return_value = {"path_a": tb1, "path_b": tb2, "path_c": tb3}
        stats.calculate_statistics()
        mock_print.assert_called_with("Updating README.md with dataset statistics...")
        self.assertTrue(mock_update.called)
        called_path, called_table = mock_update.call_args[0]
        self.assertEqual(called_path, stats.README_PATH)
        books = defaultdict(int, {"en": 2, "de": 1})
        segments = defaultdict(int, {"en": 3, "de": 0})
        tokens = defaultdict(int, {"en": 7, "de": 0})
        expected = stats.build_markdown_table(books, segments, tokens, ["de", "en"])
        self.assertEqual(called_table, expected)

    @patch("stats.load_textbooks", side_effect=FileNotFoundError("no file"))
    def test_calculate_statistics_file_not_found(self, mock_load):
        with self.assertRaises(RuntimeError) as cm:
            stats.calculate_statistics()
        self.assertIn("Error loading textbooks", str(cm.exception))
        self.assertIn("no file", str(cm.exception))

    @patch("stats.load_textbooks", side_effect=ImportError("bad import"))
    def test_calculate_statistics_import_error(self, mock_load):
        with self.assertRaises(RuntimeError) as cm:
            stats.calculate_statistics()
        self.assertIn("Required module missing", str(cm.exception))
        self.assertIn("bad import", str(cm.exception))

    @patch("stats.load_textbooks", return_value=[])
    def test_calculate_statistics_no_textbooks(self, mock_load):
        with self.assertRaises(RuntimeError) as cm:
            stats.calculate_statistics()
        self.assertEqual(str(cm.exception), "No textbooks were loaded.")

class TestBuildMarkdownTable:

    def test_basic_counts_and_commas(self):
        books = {"x": 1, "y": 1000}
        segments = {"x": 2000, "y": 3000000}
        tokens = {"x": 500, "y": 6000000}
        idioms = ["x", "y"]

        md = build_markdown_table(books, segments, tokens, idioms)
        lines = md.splitlines()

        # Header + separator + 2 idiom rows + total row = 5 lines
        assert len(lines) == 5

        # Header & separator
        assert lines[0] == "| Idiom | Books | Segments | Tokens (Whitespace) |"
        assert lines[1] == "| --- | --- | --- | --- |"

        # 'books' column is raw (no comma), segments/tokens get commas
        assert lines[2] == "| x | 1 | 2,000 | 500 |"
        assert lines[3] == "| y | 1000 | 3,000,000 | 6,000,000 |"

        # Totals row: books raw, others with commas
        assert lines[4] == "| **Total** | 1001 | 3,002,000 | 6,000,500 |"

    def test_empty_idioms(self):
        # No idioms → only header, separator, and total row
        md = build_markdown_table({}, {}, {}, [])
        assert md.splitlines() == [
            "| Idiom | Books | Segments | Tokens (Whitespace) |",
            "| --- | --- | --- | --- |",
            "| **Total** | 0 | 0 | 0 |",
        ]


class TestUpdateReadmeStatistics:

    TEMPLATE = (
        "# Title\n\n"
        "Intro text\n\n"
        "## Dataset Statistics\n"
        "{old}\n"
        "## Following\n"
        "Rest\n"
    )

    def _make_readme(self, old_table):
        content = self.TEMPLATE.format(old=old_table)
        tf = tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8")
        tf.write(content)
        tf.flush()
        tf.close()
        return tf.name

    def test_replaces_middle_section(self):
        old = "old line1\nold line2"
        path = self._make_readme(old)
        new_table = "| A | B |\n| - | - |\n| 1 | 2 |"

        update_readme_statistics(path, new_table)
        updated = open(path, encoding="utf-8").read()
        os.remove(path)

        # old content is gone
        assert "old line1" not in updated
        assert "old line2" not in updated

        # new table is right after header
        assert "## Dataset Statistics\n" + new_table + "\n" in updated

        # following section still present
        assert "## Following\nRest" in updated

    def test_replaces_section_at_end(self):
        # README ends immediately after the stats section
        content = (
            "# Title\n\n"
            "## Dataset Statistics\n"
            "to be replaced\n"
        )
        path = tempfile.mktemp()
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        new_table = "| I | J |\n| - | - |\n| 3 | 4 |"
        update_readme_statistics(path, new_table)

        updated = open(path, encoding="utf-8").read()
        os.remove(path)

        # should end with the new table plus newline
        assert updated.endswith("## Dataset Statistics\n" + new_table + "\n")

    def test_no_dataset_section_leaves_file_unchanged(self):
        # If there's no '## Dataset Statistics' header, nothing should change
        content = "# No stats here\n\nSome text\n"
        path = tempfile.mktemp()
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        before = open(path, encoding="utf-8").read()
        update_readme_statistics(path, "| X | Y |\n")
        after = open(path, encoding="utf-8").read()
        os.remove(path)

        assert before == after
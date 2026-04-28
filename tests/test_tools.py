"""Unit tests for tools.py — list_files, read_file, search_docs, TOOL_DEFINITIONS."""

import base64
import json
import unittest
from unittest.mock import patch, MagicMock

import tools
from tools import set_repo, list_files, read_file, search_docs, TOOL_DEFINITIONS, TOOL_MAP


class TestSetRepo(unittest.TestCase):
    def test_sets_global_owner_and_repo(self):
        set_repo("myowner", "myrepo")
        self.assertEqual(tools._owner, "myowner")
        self.assertEqual(tools._repo, "myrepo")

    def tearDown(self):
        set_repo("", "")


class TestListFiles(unittest.TestCase):
    def setUp(self):
        set_repo("testowner", "testrepo")

    def tearDown(self):
        set_repo("", "")

    @patch("tools.gh_get")
    def test_returns_sorted_dirs_first(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [
                {"type": "file", "name": "app.py", "path": "app.py"},
                {"type": "dir", "name": "src", "path": "src"},
                {"type": "file", "name": "README.md", "path": "README.md"},
            ],
        )
        result = list_files("")
        lines = result.splitlines()
        # Directories should appear before files
        self.assertTrue(lines[0].startswith("📁"))
        self.assertTrue(lines[1].startswith("📄"))

    @patch("tools.gh_get")
    def test_uses_correct_api_url(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
        list_files("src/utils")
        call_url = mock_get.call_args[0][0]
        self.assertIn("testowner", call_url)
        self.assertIn("testrepo", call_url)
        self.assertIn("src/utils", call_url)

    @patch("tools.gh_get")
    def test_returns_error_on_non_200(self, mock_get):
        mock_get.return_value = MagicMock(status_code=404)
        result = list_files("nonexistent")
        self.assertIn("Error", result)
        self.assertIn("404", result)

    @patch("tools.gh_get")
    def test_non_list_response_detected(self, mock_get):
        # When path points to a file, GitHub returns a dict
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"type": "file", "name": "app.py"},
        )
        result = list_files("app.py")
        self.assertIn("is a file", result)

    @patch("tools.gh_get")
    def test_empty_directory(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
        result = list_files("")
        self.assertEqual(result, "(empty directory)")

    @patch("tools.gh_get")
    def test_icons_in_output(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [
                {"type": "file", "name": "main.py", "path": "main.py"},
                {"type": "dir", "name": "tests", "path": "tests"},
            ],
        )
        result = list_files("")
        self.assertIn("📁 tests", result)
        self.assertIn("📄 main.py", result)


class TestReadFile(unittest.TestCase):
    def setUp(self):
        set_repo("testowner", "testrepo")

    def tearDown(self):
        set_repo("", "")

    def _make_b64_response(self, content: str) -> MagicMock:
        encoded = base64.b64encode(content.encode()).decode()
        return MagicMock(
            status_code=200,
            json=lambda: {"type": "file", "content": encoded + "\n", "name": "test.py"},
        )

    @patch("tools.gh_get")
    def test_decodes_base64_content(self, mock_get):
        mock_get.return_value = self._make_b64_response("print('hello')")
        result = read_file("main.py")
        self.assertEqual(result.strip(), "print('hello')")

    @patch("tools.gh_get")
    def test_truncates_large_files(self, mock_get):
        large_content = "x" * 10000
        mock_get.return_value = self._make_b64_response(large_content)
        result = read_file("large.py")
        self.assertLessEqual(len(result), 8100)  # 8000 + "(truncated)" message
        self.assertIn("truncated", result)

    @patch("tools.gh_get")
    def test_does_not_truncate_small_files(self, mock_get):
        content = "small content"
        mock_get.return_value = self._make_b64_response(content)
        result = read_file("small.py")
        self.assertEqual(result, content)

    @patch("tools.gh_get")
    def test_returns_error_on_non_200(self, mock_get):
        mock_get.return_value = MagicMock(status_code=404)
        result = read_file("missing.py")
        self.assertIn("Error", result)
        self.assertIn("404", result)

    @patch("tools.gh_get")
    def test_returns_error_for_non_file_type(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"type": "dir", "name": "src"},
        )
        result = read_file("src")
        self.assertIn("not a file", result)

    @patch("tools.gh_get")
    def test_uses_correct_api_url(self, mock_get):
        mock_get.return_value = self._make_b64_response("content")
        read_file("path/to/file.py")
        call_url = mock_get.call_args[0][0]
        self.assertIn("testowner", call_url)
        self.assertIn("testrepo", call_url)
        self.assertIn("path/to/file.py", call_url)


class TestSearchDocs(unittest.TestCase):
    def setUp(self):
        set_repo("testowner", "testrepo")

    def tearDown(self):
        set_repo("", "")

    @patch("tools.gh_get")
    def test_returns_matching_files(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "items": [
                    {
                        "path": "src/app.py",
                        "text_matches": [{"fragment": "import streamlit as st"}],
                    }
                ]
            },
        )
        result = search_docs("streamlit")
        self.assertIn("src/app.py", result)
        self.assertIn("import streamlit as st", result)

    @patch("tools.gh_get")
    def test_empty_results(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"items": []},
        )
        result = search_docs("nonexistent_symbol")
        self.assertIn("No results", result)

    @patch("tools.gh_get")
    def test_returns_error_on_non_200(self, mock_get):
        mock_get.return_value = MagicMock(status_code=403)
        result = search_docs("query")
        self.assertIn("Search error", result)
        self.assertIn("403", result)

    @patch("tools.gh_get")
    def test_handles_missing_text_matches(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "items": [{"path": "config.py", "text_matches": []}]
            },
        )
        result = search_docs("config")
        self.assertIn("config.py", result)

    @patch("tools.gh_get")
    def test_query_includes_repo_scope(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"items": []},
        )
        search_docs("database")
        call_kwargs = mock_get.call_args[1]
        params = call_kwargs.get("params", {})
        self.assertIn("testowner/testrepo", params.get("q", ""))


class TestToolDefinitions(unittest.TestCase):
    def test_three_tools_defined(self):
        self.assertEqual(len(TOOL_DEFINITIONS), 3)

    def test_each_tool_has_required_fields(self):
        for tool_def in TOOL_DEFINITIONS:
            self.assertEqual(tool_def["type"], "function")
            func = tool_def["function"]
            self.assertIn("name", func)
            self.assertIn("description", func)
            self.assertIn("parameters", func)

    def test_tool_names(self):
        names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
        self.assertEqual(names, {"list_files", "read_file", "search_docs"})

    def test_tool_map_contains_callables(self):
        self.assertIn("list_files", TOOL_MAP)
        self.assertIn("read_file", TOOL_MAP)
        self.assertIn("search_docs", TOOL_MAP)
        self.assertTrue(callable(TOOL_MAP["list_files"]))
        self.assertTrue(callable(TOOL_MAP["read_file"]))
        self.assertTrue(callable(TOOL_MAP["search_docs"]))

    def test_list_files_parameter_is_path(self):
        lf = next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "list_files")
        self.assertIn("path", lf["function"]["parameters"]["properties"])

    def test_read_file_parameter_is_path(self):
        rf = next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "read_file")
        self.assertIn("path", rf["function"]["parameters"]["properties"])

    def test_search_docs_parameter_is_query(self):
        sd = next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "search_docs")
        self.assertIn("query", sd["function"]["parameters"]["properties"])


if __name__ == "__main__":
    unittest.main()

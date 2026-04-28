"""Unit tests for retriever.py — chunking, file selection, RepoRetriever."""

import base64
import os
import unittest
from unittest.mock import MagicMock, patch

from retriever import (
    _chunk_text,
    _select_files_to_index,
    RepoRetriever,
)


class TestChunkText(unittest.TestCase):
    def test_empty_string_returns_empty_list(self):
        self.assertEqual(_chunk_text(""), [])

    def test_short_text_returns_single_chunk(self):
        text = "Hello world"
        chunks = _chunk_text(text)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_long_text_produces_multiple_chunks(self):
        # 1600 chars with chunk_size=800, overlap=200 → more than 1 chunk
        text = "a" * 1600
        chunks = _chunk_text(text, chunk_size=800, overlap=200)
        self.assertGreater(len(chunks), 1)

    def test_overlap_causes_shared_content(self):
        text = "a" * 100 + "b" * 100 + "c" * 100
        chunks = _chunk_text(text, chunk_size=150, overlap=50)
        # Should produce more than one chunk
        self.assertGreater(len(chunks), 1)

    def test_chunks_stripped(self):
        text = "   hello world   "
        chunks = _chunk_text(text)
        self.assertEqual(chunks[0], "hello world")

    def test_whitespace_only_chunks_excluded(self):
        text = "abc"
        chunks = _chunk_text(text, chunk_size=3, overlap=2)
        for chunk in chunks:
            self.assertGreater(len(chunk.strip()), 0)

    def test_default_parameters(self):
        text = "x" * 2000
        chunks = _chunk_text(text)
        self.assertGreater(len(chunks), 2)


class TestSelectFilesToIndex(unittest.TestCase):
    def _blob(self, path):
        return {"type": "blob", "path": path}

    def test_readme_always_indexed(self):
        tree = [self._blob("README.md")]
        selected = _select_files_to_index(tree)
        self.assertIn("README.md", selected)

    def test_readme_variants_indexed(self):
        for name in ["readme.txt", "README.rst", "README"]:
            tree = [self._blob(name)]
            selected = _select_files_to_index(tree)
            self.assertIn(name, selected, f"{name} should be indexed")

    def test_config_files_indexed(self):
        for config in ["requirements.txt", "package.json", "Dockerfile", "pyproject.toml"]:
            tree = [self._blob(config)]
            selected = _select_files_to_index(tree)
            self.assertIn(config, selected, f"{config} should be indexed")

    def test_doc_files_in_docs_folder_indexed(self):
        tree = [self._blob("docs/getting_started.md")]
        selected = _select_files_to_index(tree)
        self.assertIn("docs/getting_started.md", selected)

    def test_top_level_md_indexed(self):
        tree = [self._blob("CONTRIBUTING.md")]
        selected = _select_files_to_index(tree)
        self.assertIn("CONTRIBUTING.md", selected)

    def test_source_entry_point_indexed(self):
        tree = [self._blob("app.py")]
        selected = _select_files_to_index(tree)
        self.assertIn("app.py", selected)

    def test_tree_type_entries_skipped(self):
        tree = [{"type": "tree", "path": "src"}]
        selected = _select_files_to_index(tree)
        self.assertEqual(selected, [])

    def test_doc_count_capped_at_10(self):
        tree = [self._blob(f"docs/doc_{i}.md") for i in range(20)]
        selected = _select_files_to_index(tree)
        doc_files = [f for f in selected if f.startswith("docs/")]
        self.assertLessEqual(len(doc_files), 10)

    def test_nested_non_entry_source_not_indexed(self):
        # Non-entry-point source files in subdirs should not be indexed
        tree = [self._blob(f"src/module_{i}.py") for i in range(5)]
        selected = _select_files_to_index(tree)
        self.assertEqual(len(selected), 0)

    def test_nested_non_doc_md_not_double_counted(self):
        tree = [self._blob("docs/api.md")]
        selected = _select_files_to_index(tree)
        self.assertEqual(selected.count("docs/api.md"), 1)


class TestRepoRetriever(unittest.TestCase):
    def _make_retriever(self):
        return RepoRetriever("testowner", "testrepo")

    def test_collection_name_sanitizes_hyphens(self):
        r = RepoRetriever("my-owner", "my-repo")
        self.assertNotIn("-", r.collection_name)

    def test_collection_name_truncated_to_60_chars(self):
        r = RepoRetriever("a" * 40, "b" * 40)
        self.assertLessEqual(len(r.collection_name), 60)

    def test_initial_chunk_count_is_zero(self):
        r = self._make_retriever()
        self.assertEqual(r.chunk_count, 0)

    def test_initial_indexed_files_is_empty(self):
        r = self._make_retriever()
        self.assertEqual(r.indexed_files, [])

    def test_query_empty_collection_returns_empty_list(self):
        r = self._make_retriever()
        result = r.query("what is this?")
        self.assertEqual(result, [])

    def test_get_context_string_empty_collection(self):
        r = self._make_retriever()
        result = r.get_context_string("what is this?")
        self.assertEqual(result, "(No relevant chunks found)")

    @patch("retriever._fetch_tree_recursive")
    @patch("retriever._fetch_file_content")
    def test_index_returns_stats_dict(self, mock_fetch_content, mock_fetch_tree):
        mock_fetch_tree.return_value = [
            {"type": "blob", "path": "README.md"},
        ]
        mock_fetch_content.return_value = "# My Project\n\nThis is a test project."
        r = self._make_retriever()
        result = r.index()
        self.assertIn("files_indexed", result)
        self.assertIn("chunks_created", result)
        self.assertIn("files", result)

    @patch("retriever._fetch_tree_recursive")
    @patch("retriever._fetch_file_content")
    def test_index_handles_empty_tree(self, mock_fetch_content, mock_fetch_tree):
        mock_fetch_tree.return_value = []
        r = self._make_retriever()
        result = r.index()
        self.assertEqual(result["files_indexed"], 0)
        self.assertEqual(result["chunks_created"], 0)

    @patch("retriever._fetch_tree_recursive")
    @patch("retriever._fetch_file_content")
    def test_index_skips_files_with_no_content(self, mock_fetch_content, mock_fetch_tree):
        mock_fetch_tree.return_value = [{"type": "blob", "path": "README.md"}]
        mock_fetch_content.return_value = None  # Fetch fails
        r = self._make_retriever()
        result = r.index()
        self.assertEqual(result["files_indexed"], 0)

    @patch("retriever._fetch_tree_recursive")
    @patch("retriever._fetch_file_content")
    def test_index_populates_indexed_files(self, mock_fetch_content, mock_fetch_tree):
        mock_fetch_tree.return_value = [{"type": "blob", "path": "README.md"}]
        mock_fetch_content.return_value = "# Project\nThis is the project."
        r = self._make_retriever()
        result = r.index()
        self.assertEqual(result["files_indexed"], 1)
        self.assertIn("README.md", result["files"])

    @patch("retriever._fetch_tree_recursive")
    @patch("retriever._fetch_file_content")
    def test_query_returns_chunks_after_indexing(self, mock_fetch_content, mock_fetch_tree):
        mock_fetch_tree.return_value = [{"type": "blob", "path": "README.md"}]
        mock_fetch_content.return_value = (
            "RepoLens is an AI-powered GitHub repo assistant that helps developers onboard quickly."
        )
        r = self._make_retriever()
        r.index()
        results = r.query("GitHub repo assistant")
        self.assertIsInstance(results, list)
        if results:
            self.assertIn("content", results[0])
            self.assertIn("source", results[0])
            self.assertIn("chunk_index", results[0])

    @patch("retriever._fetch_tree_recursive")
    @patch("retriever._fetch_file_content")
    def test_get_context_string_returns_formatted_string(self, mock_fetch_content, mock_fetch_tree):
        mock_fetch_tree.return_value = [{"type": "blob", "path": "README.md"}]
        mock_fetch_content.return_value = "RepoLens is an AI-powered GitHub repo assistant."
        r = self._make_retriever()
        r.index()
        ctx = r.get_context_string("what does this project do?")
        self.assertNotEqual(ctx, "(No relevant chunks found)")
        self.assertIn("Chunk", ctx)
        self.assertIn("README.md", ctx)

    @patch("retriever._fetch_tree_recursive")
    @patch("retriever._fetch_file_content")
    def test_status_callback_called_during_index(self, mock_fetch_content, mock_fetch_tree):
        mock_fetch_tree.return_value = [{"type": "blob", "path": "README.md"}]
        mock_fetch_content.return_value = "content"
        r = self._make_retriever()
        callback_messages = []
        r.index(status_callback=callback_messages.append)
        self.assertGreater(len(callback_messages), 0)

    @patch("retriever._fetch_tree_recursive")
    @patch("retriever._fetch_file_content")
    def test_chunk_count_set_after_index(self, mock_fetch_content, mock_fetch_tree):
        mock_fetch_tree.return_value = [{"type": "blob", "path": "README.md"}]
        mock_fetch_content.return_value = "# Project\nContent here to index."
        r = self._make_retriever()
        r.index()
        self.assertGreater(r.chunk_count, 0)

    @patch("retriever._fetch_tree_recursive")
    @patch("retriever._fetch_file_content")
    def test_multiple_files_indexed(self, mock_fetch_content, mock_fetch_tree):
        mock_fetch_tree.return_value = [
            {"type": "blob", "path": "README.md"},
            {"type": "blob", "path": "requirements.txt"},
        ]
        mock_fetch_content.return_value = "file content"
        r = self._make_retriever()
        result = r.index()
        self.assertEqual(result["files_indexed"], 2)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for gh.py — GitHub auth headers and HTTP helper."""

import os
import unittest
from unittest.mock import patch, MagicMock

import gh
from gh import gh_headers, gh_get


class TestGhHeaders(unittest.TestCase):
    def test_default_accept_header(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove GITHUB_TOKEN if present
            os.environ.pop("GITHUB_TOKEN", None)
            headers = gh_headers()
        self.assertEqual(headers["Accept"], "application/vnd.github+json")

    def test_no_auth_header_without_token(self):
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            headers = gh_headers()
        self.assertNotIn("Authorization", headers)

    def test_auth_header_with_token(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_testtoken123"}, clear=True):
            headers = gh_headers()
        self.assertIn("Authorization", headers)
        self.assertEqual(headers["Authorization"], "Bearer ghp_testtoken123")

    def test_extra_headers_merged(self):
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            headers = gh_headers(extra={"X-Custom": "value", "Accept": "application/json"})
        # Extra Accept overrides the default
        self.assertEqual(headers["Accept"], "application/json")
        self.assertEqual(headers["X-Custom"], "value")

    def test_extra_headers_none_safe(self):
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            headers = gh_headers(extra=None)
        self.assertIsInstance(headers, dict)

    def test_token_not_mutated_across_calls(self):
        """gh_headers must return a new dict each call."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "tok"}, clear=True):
            h1 = gh_headers()
            h1["X-Extra"] = "junk"
            h2 = gh_headers()
        self.assertNotIn("X-Extra", h2)


class TestGhGet(unittest.TestCase):
    @patch("gh.requests.get")
    def test_passes_constructed_headers(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            result = gh_get("https://api.github.com/repos/owner/repo")

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        # headers should include Accept
        headers_used = call_kwargs[1]["headers"] if call_kwargs[1] else call_kwargs[0][1]
        self.assertIn("Accept", headers_used)
        self.assertIs(result, mock_resp)

    @patch("gh.requests.get")
    def test_custom_headers_merged(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            gh_get("https://api.github.com/test",
                   headers={"Accept": "application/vnd.github.v3.text-match+json"})

        call_headers = mock_get.call_args[1]["headers"]
        self.assertEqual(call_headers["Accept"],
                         "application/vnd.github.v3.text-match+json")

    @patch("gh.requests.get")
    def test_default_timeout_is_15(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            gh_get("https://api.github.com/test")

        self.assertEqual(mock_get.call_args[1]["timeout"], 15)

    @patch("gh.requests.get")
    def test_custom_timeout_forwarded(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            gh_get("https://api.github.com/test", timeout=30)

        self.assertEqual(mock_get.call_args[1]["timeout"], 30)

    @patch("gh.requests.get")
    def test_token_included_in_get_call(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_secret"}, clear=True):
            gh_get("https://api.github.com/repos/test")

        call_headers = mock_get.call_args[1]["headers"]
        self.assertEqual(call_headers["Authorization"], "Bearer ghp_secret")

    @patch("gh.requests.get")
    def test_extra_kwargs_forwarded(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            gh_get("https://api.github.com/search/code", params={"q": "test repo:owner/repo"})

        call_kwargs = mock_get.call_args[1]
        self.assertIn("params", call_kwargs)
        self.assertEqual(call_kwargs["params"], {"q": "test repo:owner/repo"})


if __name__ == "__main__":
    unittest.main()

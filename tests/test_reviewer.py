"""Unit tests for reviewer.py — review_answer and revise_answer."""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from reviewer import review_answer, revise_answer


def _mock_groq_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


GOOD_REVIEW = json.dumps({
    "verdict": "pass",
    "issues": [],
    "quality_score": 8,
    "summary": "Well-cited and complete answer.",
})

NEEDS_REVISION_REVIEW = json.dumps({
    "verdict": "needs_revision",
    "issues": [
        {
            "type": "unsupported",
            "description": "Claim about setup is unsupported",
            "location": "Setup section",
            "suggestion": "Add a citation to requirements.txt",
        }
    ],
    "quality_score": 4,
    "summary": "Missing citations on key claims.",
})


class TestReviewAnswer(unittest.TestCase):
    def setUp(self):
        os.environ["GROQ_API_KEY"] = "test_key"

    def tearDown(self):
        os.environ.pop("GROQ_API_KEY", None)

    @patch("reviewer.Groq")
    def test_returns_dict_with_required_keys(self, MockGroq):
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(GOOD_REVIEW)
        result = review_answer("Q?", "Answer text", ["README.md"], "chunk text", "beginner")
        for key in ("verdict", "issues", "quality_score", "summary"):
            self.assertIn(key, result)

    @patch("reviewer.Groq")
    def test_pass_verdict_returned(self, MockGroq):
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(GOOD_REVIEW)
        result = review_answer("Q?", "Good answer", ["README.md"], "evidence", "intermediate")
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["quality_score"], 8)

    @patch("reviewer.Groq")
    def test_needs_revision_verdict_returned(self, MockGroq):
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(NEEDS_REVISION_REVIEW)
        result = review_answer("Q?", "Bad answer", [], "evidence", "advanced")
        self.assertEqual(result["verdict"], "needs_revision")
        self.assertEqual(len(result["issues"]), 1)
        self.assertEqual(result["quality_score"], 4)

    @patch("reviewer.Groq")
    def test_fallback_on_json_error(self, MockGroq):
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(
            "This is not valid JSON"
        )
        result = review_answer("Q?", "Answer", ["f.py"], "chunks", "beginner")
        # Should return default pass result without crashing
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["quality_score"], 7)
        self.assertIn("Review could not be completed", result["summary"])

    @patch("reviewer.Groq")
    def test_empty_indexed_files_handled(self, MockGroq):
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(GOOD_REVIEW)
        # Should not crash when no files
        result = review_answer("Q?", "Answer", [], "", "intermediate")
        self.assertIn("verdict", result)

    @patch("reviewer.Groq")
    def test_evidence_chunks_truncated_at_4000(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response(GOOD_REVIEW)

        long_evidence = "E" * 8000
        review_answer("Q?", "Answer", ["f.py"], long_evidence, "beginner")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"] if call_args[1] else call_args[0][0]
        user_content = messages[1]["content"]
        # Should not contain more than 4000 E chars
        self.assertNotIn("E" * 4001, user_content)

    @patch("reviewer.Groq")
    def test_uses_json_response_format(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response(GOOD_REVIEW)

        review_answer("Q?", "Answer", [], "evidence", "beginner")

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_kwargs.get("response_format"), {"type": "json_object"})


class TestReviseAnswer(unittest.TestCase):
    def setUp(self):
        os.environ["GROQ_API_KEY"] = "test_key"

    def tearDown(self):
        os.environ.pop("GROQ_API_KEY", None)

    @patch("reviewer.Groq")
    def test_returns_string(self, MockGroq):
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(
            "## Revised Answer\n\nHere is the corrected answer with citations."
        )
        review_result = {
            "verdict": "needs_revision",
            "issues": [
                {"type": "missing_citation", "description": "No citation",
                 "location": "para 1", "suggestion": "Cite README.md"}
            ],
            "quality_score": 4,
            "summary": "Needs citations",
        }
        result = revise_answer("Original answer", review_result, "Q?", "evidence", "beginner")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    @patch("reviewer.Groq")
    def test_issues_text_included_in_prompt(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response("Revised.")

        review_result = {
            "issues": [
                {"type": "vague", "description": "Vague setup step",
                 "location": "section 2", "suggestion": "Specify exact command"}
            ]
        }
        revise_answer("Original", review_result, "Q?", "evidence", "intermediate")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"] if call_args[1] else call_args[0][0]
        user_content = messages[1]["content"]
        self.assertIn("Vague setup step", user_content)

    @patch("reviewer.Groq")
    def test_empty_issues_list_handled(self, MockGroq):
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response("OK")
        # Should not crash with empty issues
        result = revise_answer("Original", {"issues": []}, "Q?", "evidence", "beginner")
        self.assertIsInstance(result, str)

    @patch("reviewer.Groq")
    def test_user_level_in_system_prompt(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response("Revised")

        revise_answer("Answer", {"issues": []}, "Q?", "evidence", "advanced")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"] if call_args[1] else call_args[0][0]
        sys_content = messages[0]["content"]
        self.assertIn("advanced", sys_content)

    @patch("reviewer.Groq")
    def test_evidence_truncated(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response("Revised")

        long_evidence = "E" * 8000
        revise_answer("Answer", {"issues": []}, "Q?", long_evidence, "intermediate")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"] if call_args[1] else call_args[0][0]
        user_content = messages[1]["content"]
        self.assertNotIn("E" * 4001, user_content)


if __name__ == "__main__":
    unittest.main()

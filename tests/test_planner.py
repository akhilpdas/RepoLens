"""Unit tests for planner.py — create_plan and fallback behaviour."""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from planner import create_plan
from state import Plan, PlanStep


def _mock_groq_response(content: str) -> MagicMock:
    """Helper: build a fake Groq API response."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestCreatePlan(unittest.TestCase):
    def setUp(self):
        os.environ["GROQ_API_KEY"] = "test_key"

    def tearDown(self):
        os.environ.pop("GROQ_API_KEY", None)

    @patch("planner.Groq")
    def test_returns_plan_object(self, MockGroq):
        payload = json.dumps({
            "steps": [
                {"title": "Explore structure", "description": "List files", "suggested_tools": ["list_files"]},
                {"title": "Read README", "description": "Check readme", "suggested_tools": ["read_file"]},
                {"title": "Synthesize", "description": "Write answer", "suggested_tools": []},
            ]
        })
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(payload)

        plan = create_plan("How do I run this?", "owner/repo", "beginner", "# Readme")
        self.assertIsInstance(plan, Plan)

    @patch("planner.Groq")
    def test_plan_steps_have_correct_ids(self, MockGroq):
        payload = json.dumps({
            "steps": [
                {"title": "Step A", "description": "Desc A", "suggested_tools": []},
                {"title": "Step B", "description": "Desc B", "suggested_tools": []},
            ]
        })
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(payload)

        plan = create_plan("Q", "r/r", "intermediate", "readme")
        self.assertEqual(plan.steps[0].id, 1)
        self.assertEqual(plan.steps[1].id, 2)

    @patch("planner.Groq")
    def test_plan_question_and_repo_set(self, MockGroq):
        payload = json.dumps({"steps": [
            {"title": "T", "description": "D", "suggested_tools": []}
        ]})
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(payload)

        plan = create_plan("What is this?", "myowner/myrepo", "advanced", "")
        self.assertEqual(plan.question, "What is this?")
        self.assertEqual(plan.repo, "myowner/myrepo")
        self.assertEqual(plan.user_level, "advanced")

    @patch("planner.Groq")
    def test_plan_steps_have_suggested_tools(self, MockGroq):
        payload = json.dumps({"steps": [
            {"title": "List files", "description": "D", "suggested_tools": ["list_files", "read_file"]},
        ]})
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(payload)

        plan = create_plan("Q", "r/r", "beginner", "readme")
        self.assertEqual(plan.steps[0].suggested_tools, ["list_files", "read_file"])

    @patch("planner.Groq")
    def test_fallback_on_invalid_json(self, MockGroq):
        """When LLM returns non-JSON, should fall back to default 4-step plan."""
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(
            "Sorry I cannot provide a plan right now."
        )

        plan = create_plan("Q", "r/r", "beginner", "")
        self.assertIsInstance(plan, Plan)
        self.assertEqual(len(plan.steps), 4)

    @patch("planner.Groq")
    def test_fallback_step_titles_present(self, MockGroq):
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(
            "not json"
        )
        plan = create_plan("Q", "r/r", "intermediate", "")
        titles = [s.title for s in plan.steps]
        self.assertIn("Explore project structure", titles)
        self.assertIn("Synthesize findings", titles)

    @patch("planner.Groq")
    def test_empty_steps_list_returns_empty_plan(self, MockGroq):
        payload = json.dumps({"steps": []})
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(payload)

        plan = create_plan("Q", "r/r", "beginner", "")
        self.assertEqual(plan.steps, [])

    @patch("planner.Groq")
    def test_missing_fields_use_defaults(self, MockGroq):
        # Step missing 'suggested_tools' key
        payload = json.dumps({"steps": [
            {"title": "Check stuff", "description": "Look around"}
        ]})
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(payload)

        plan = create_plan("Q", "r/r", "beginner", "")
        self.assertEqual(plan.steps[0].suggested_tools, [])

    @patch("planner.Groq")
    def test_readme_preview_passed_to_llm(self, MockGroq):
        payload = json.dumps({"steps": [
            {"title": "T", "description": "D", "suggested_tools": []}
        ]})
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response(payload)

        readme = "This is the README content for testing"
        create_plan("Q", "r/r", "beginner", readme)

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"] if call_args[1] else call_args[0][0]
        # The README content should appear in the user message
        user_content = messages[1]["content"]
        self.assertIn("README content for testing", user_content)

    @patch("planner.Groq")
    def test_readme_preview_truncated_to_2000(self, MockGroq):
        payload = json.dumps({"steps": [
            {"title": "T", "description": "D", "suggested_tools": []}
        ]})
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response(payload)

        long_readme = "R" * 5000
        create_plan("Q", "r/r", "intermediate", long_readme)

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"] if call_args[1] else call_args[0][0]
        user_content = messages[1]["content"]
        # Should not contain more than 2000 'R' chars in the readme section
        readme_occurrences = user_content.count("R" * 2001)
        self.assertEqual(readme_occurrences, 0)


if __name__ == "__main__":
    unittest.main()

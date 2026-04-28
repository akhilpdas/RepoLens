"""Unit tests for evaluator.py — benchmark questions, score_answer, run_eval_suite."""

import json
import os
import unittest
from unittest.mock import MagicMock, patch, call

from evaluator import (
    BENCHMARK_QUESTIONS,
    score_answer,
    run_eval_suite,
)


def _mock_groq_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


GOOD_SCORE = json.dumps({
    "right_file": 1,
    "citation_present": 1,
    "answer_complete": 1,
    "no_hallucination": 1,
    "clear_for_level": 1,
    "total": 5,
    "notes": "Excellent answer.",
})

POOR_SCORE = json.dumps({
    "right_file": 0,
    "citation_present": 0,
    "answer_complete": 1,
    "no_hallucination": 1,
    "clear_for_level": 1,
    "total": 3,
    "notes": "Missing file citations.",
})


class TestBenchmarkQuestions(unittest.TestCase):
    def test_has_exactly_10_questions(self):
        self.assertEqual(len(BENCHMARK_QUESTIONS), 10)

    def test_each_question_has_required_fields(self):
        for q in BENCHMARK_QUESTIONS:
            self.assertIn("id", q)
            self.assertIn("question", q)
            self.assertIn("expected_files", q)
            self.assertIn("criteria_focus", q)

    def test_ids_are_sequential(self):
        ids = [q["id"] for q in BENCHMARK_QUESTIONS]
        self.assertEqual(ids, list(range(1, 11)))

    def test_questions_are_non_empty_strings(self):
        for q in BENCHMARK_QUESTIONS:
            self.assertIsInstance(q["question"], str)
            self.assertGreater(len(q["question"]), 0)

    def test_expected_files_are_lists(self):
        for q in BENCHMARK_QUESTIONS:
            self.assertIsInstance(q["expected_files"], list)

    def test_criteria_focus_are_non_empty(self):
        for q in BENCHMARK_QUESTIONS:
            self.assertGreater(len(q["criteria_focus"]), 0)


class TestScoreAnswer(unittest.TestCase):
    def setUp(self):
        os.environ["GROQ_API_KEY"] = "test_key"

    def tearDown(self):
        os.environ.pop("GROQ_API_KEY", None)

    @patch("evaluator.Groq")
    def test_returns_dict_with_required_keys(self, MockGroq):
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(GOOD_SCORE)
        result = score_answer("Q?", "Answer", "beginner", ["README.md"], "Check citations")
        for key in ("right_file", "citation_present", "answer_complete",
                    "no_hallucination", "clear_for_level", "total", "notes"):
            self.assertIn(key, result)

    @patch("evaluator.Groq")
    def test_perfect_score(self, MockGroq):
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(GOOD_SCORE)
        result = score_answer("Q?", "Answer", "intermediate", [], "focus")
        self.assertEqual(result["total"], 5)

    @patch("evaluator.Groq")
    def test_partial_score(self, MockGroq):
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(POOR_SCORE)
        result = score_answer("Q?", "Answer", "advanced", [], "focus")
        self.assertEqual(result["total"], 3)

    @patch("evaluator.Groq")
    def test_fallback_on_json_parse_error(self, MockGroq):
        MockGroq.return_value.chat.completions.create.return_value = _mock_groq_response(
            "Cannot score this."
        )
        result = score_answer("Q?", "Answer", "beginner", [], "focus")
        # Default values applied
        self.assertIn("total", result)
        self.assertEqual(result["notes"], "Scoring failed, default applied.")

    @patch("evaluator.Groq")
    def test_indexed_files_truncated_to_30(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response(GOOD_SCORE)

        files = [f"file_{i}.py" for i in range(50)]
        score_answer("Q?", "Answer", "intermediate", files, "focus")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"] if call_args[1] else call_args[0][0]
        user_content = messages[1]["content"]
        # Should contain at most 30 file entries
        file_lines = [line for line in user_content.splitlines() if "file_" in line]
        self.assertLessEqual(len(file_lines), 30)

    @patch("evaluator.Groq")
    def test_uses_json_response_format(self, MockGroq):
        mock_client = MockGroq.return_value
        mock_client.chat.completions.create.return_value = _mock_groq_response(GOOD_SCORE)

        score_answer("Q?", "Answer", "beginner", [], "focus")

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_kwargs.get("response_format"), {"type": "json_object"})


class TestRunEvalSuite(unittest.TestCase):
    def setUp(self):
        os.environ["GROQ_API_KEY"] = "test_key"

    def tearDown(self):
        os.environ.pop("GROQ_API_KEY", None)

    def _make_answer_fn(self, answer="A sample answer mentioning README.md"):
        return lambda q: answer

    @patch("evaluator.score_answer")
    def test_runs_all_10_questions(self, mock_score):
        mock_score.return_value = {
            "right_file": 1, "citation_present": 1, "answer_complete": 1,
            "no_hallucination": 1, "clear_for_level": 1, "total": 5, "notes": "OK"
        }
        result = run_eval_suite(self._make_answer_fn(), "owner/repo", "beginner", [])
        self.assertEqual(mock_score.call_count, 10)
        self.assertEqual(len(result["results"]), 10)

    @patch("evaluator.score_answer")
    def test_percentage_calculation_perfect(self, mock_score):
        mock_score.return_value = {
            "right_file": 1, "citation_present": 1, "answer_complete": 1,
            "no_hallucination": 1, "clear_for_level": 1, "total": 5, "notes": "OK"
        }
        result = run_eval_suite(self._make_answer_fn(), "owner/repo", "advanced", [])
        # 10 questions × 5 max score = 50 max; got 10×5=50 → 100%
        self.assertEqual(result["total_score"], 50)
        self.assertEqual(result["max_score"], 50)
        self.assertEqual(result["percentage"], 100.0)

    @patch("evaluator.score_answer")
    def test_partial_score_percentage(self, mock_score):
        mock_score.return_value = {
            "right_file": 0, "citation_present": 0, "answer_complete": 1,
            "no_hallucination": 1, "clear_for_level": 0, "total": 2, "notes": "Partial"
        }
        result = run_eval_suite(self._make_answer_fn(), "owner/repo", "beginner", [])
        # 10 questions × 2 each = 20 total, 50 max → 40%
        self.assertEqual(result["total_score"], 20)
        self.assertEqual(result["percentage"], 40.0)

    @patch("evaluator.score_answer")
    def test_result_has_required_keys(self, mock_score):
        mock_score.return_value = {"total": 4, "notes": "OK"}
        result = run_eval_suite(self._make_answer_fn(), "owner/repo", "beginner", [])
        for key in ("results", "total_score", "max_score", "percentage", "repo", "user_level"):
            self.assertIn(key, result)

    @patch("evaluator.score_answer")
    def test_results_list_contains_per_question_data(self, mock_score):
        mock_score.return_value = {"total": 5, "notes": "Great"}
        result = run_eval_suite(self._make_answer_fn(), "owner/repo", "intermediate", [])
        self.assertEqual(len(result["results"]), 10)
        for item in result["results"]:
            self.assertIn("id", item)
            self.assertIn("question", item)
            self.assertIn("scores", item)
            self.assertIn("answer_preview", item)

    @patch("evaluator.score_answer")
    def test_answer_fn_called_for_each_question(self, mock_score):
        mock_score.return_value = {"total": 3, "notes": "OK"}
        calls = []
        def tracking_fn(q):
            calls.append(q)
            return "answer"
        run_eval_suite(tracking_fn, "owner/repo", "advanced", [])
        self.assertEqual(len(calls), 10)

    @patch("evaluator.score_answer")
    def test_answer_preview_truncated_to_200(self, mock_score):
        mock_score.return_value = {"total": 3, "notes": "OK"}
        long_answer = "A" * 500
        result = run_eval_suite(lambda q: long_answer, "owner/repo", "beginner", [])
        for item in result["results"]:
            self.assertLessEqual(len(item["answer_preview"]), 200)

    @patch("evaluator.score_answer")
    def test_repo_and_user_level_in_result(self, mock_score):
        mock_score.return_value = {"total": 5, "notes": "OK"}
        result = run_eval_suite(self._make_answer_fn(), "myowner/myrepo", "advanced", [])
        self.assertEqual(result["repo"], "myowner/myrepo")
        self.assertEqual(result["user_level"], "advanced")


if __name__ == "__main__":
    unittest.main()

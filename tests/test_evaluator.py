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
    def test_runs_all_10_questions_by_default(self, mock_score):
        mock_score.return_value = {
            "right_file": 1, "citation_present": 1, "answer_complete": 1,
            "no_hallucination": 1, "clear_for_level": 1, "total": 5, "notes": "OK"
        }
        result = run_eval_suite(self._make_answer_fn(), "owner/repo", "beginner", [])
        self.assertEqual(result["questions_run"], 10)
        self.assertEqual(mock_score.call_count, 10)

    @patch("evaluator.score_answer")
    def test_limit_parameter_restricts_questions(self, mock_score):
        mock_score.return_value = {
            "right_file": 1, "citation_present": 1, "answer_complete": 1,
            "no_hallucination": 1, "clear_for_level": 1, "total": 5, "notes": "OK"
        }
        result = run_eval_suite(self._make_answer_fn(), "owner/repo", "intermediate", [], limit=3)
        self.assertEqual(result["questions_run"], 3)
        self.assertEqual(mock_score.call_count, 3)

    @patch("evaluator.score_answer")
    def test_percentage_calculation(self, mock_score):
        mock_score.return_value = {
            "right_file": 1, "citation_present": 1, "answer_complete": 1,
            "no_hallucination": 1, "clear_for_level": 1, "total": 5, "notes": "OK"
        }
        result = run_eval_suite(self._make_answer_fn(), "owner/repo", "advanced", [], limit=4)
        # 4 questions × 5 max score = 20 max; got 4×5=20
        self.assertEqual(result["total_score"], 20)
        self.assertEqual(result["max_score"], 20)
        self.assertEqual(result["percentage"], 100.0)

    @patch("evaluator.score_answer")
    def test_partial_score_percentage(self, mock_score):
        mock_score.return_value = {
            "right_file": 1, "citation_present": 0, "answer_complete": 1,
            "no_hallucination": 1, "clear_for_level": 0, "total": 3, "notes": "Partial"
        }
        result = run_eval_suite(self._make_answer_fn(), "owner/repo", "beginner", [], limit=2)
        # 2 questions × 3 each = 6 total, 2×5 = 10 max
        self.assertEqual(result["total_score"], 6)
        self.assertEqual(result["percentage"], 60.0)

    @patch("evaluator.score_answer")
    def test_result_has_required_keys(self, mock_score):
        mock_score.return_value = {"total": 4, "notes": "OK"}
        result = run_eval_suite(self._make_answer_fn(), "owner/repo", "beginner", [], limit=1)
        for key in ("results", "total_score", "max_score", "percentage", "repo",
                    "user_level", "questions_run"):
            self.assertIn(key, result)

    @patch("evaluator.score_answer")
    def test_results_list_contains_per_question_data(self, mock_score):
        mock_score.return_value = {"total": 5, "notes": "Great"}
        result = run_eval_suite(self._make_answer_fn(), "owner/repo", "intermediate", [], limit=2)
        self.assertEqual(len(result["results"]), 2)
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
        run_eval_suite(tracking_fn, "owner/repo", "advanced", [], limit=3)
        self.assertEqual(len(calls), 3)

    @patch("evaluator.score_answer")
    def test_progress_callback_called(self, mock_score):
        mock_score.return_value = {"total": 5, "notes": "OK"}
        progress_calls = []
        def on_progress(idx, total, question):
            progress_calls.append((idx, total))
        run_eval_suite(self._make_answer_fn(), "owner/repo", "beginner", [],
                       limit=3, progress_callback=on_progress)
        self.assertEqual(len(progress_calls), 3)
        self.assertEqual(progress_calls[0], (1, 3))
        self.assertEqual(progress_calls[2], (3, 3))

    @patch("evaluator.score_answer")
    def test_answer_preview_truncated_to_200(self, mock_score):
        mock_score.return_value = {"total": 3, "notes": "OK"}
        long_answer = "A" * 500
        result = run_eval_suite(lambda q: long_answer, "owner/repo", "beginner", [], limit=1)
        self.assertLessEqual(len(result["results"][0]["answer_preview"]), 200)

    @patch("evaluator.score_answer")
    def test_zero_denominator_percentage_safe(self, mock_score):
        mock_score.return_value = {"total": 0}
        # limit=0 → questions = BENCHMARK_QUESTIONS[:0] = [] → max_score=0
        result = run_eval_suite(self._make_answer_fn(), "owner/repo", "beginner", [], limit=0)
        self.assertEqual(result["percentage"], 0)


if __name__ == "__main__":
    unittest.main()

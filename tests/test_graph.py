"""Unit tests for graph.py — GraphState, routing logic, node functions, graph builders."""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from langgraph.graph import END

from graph import (
    GraphState,
    route_after_review,
    synthesize_messages,
    build_graph,
    build_pre_synth_graph,
    build_post_synth_graph,
    REVISION_CAP,
    STYLE_INSTRUCTIONS,
)
from state import Plan, PlanStep, StepStatus


def _make_plan(num_steps=2):
    steps = [
        PlanStep(id=i + 1, title=f"Step {i+1}", description=f"Do step {i+1}")
        for i in range(num_steps)
    ]
    return Plan(question="What is this?", repo="owner/repo", user_level="beginner", steps=steps)


class TestRouteAfterReview(unittest.TestCase):
    def test_needs_revision_low_score_routes_to_revise(self):
        state: GraphState = {
            "review_result": {"verdict": "needs_revision", "quality_score": 3},
            "revision_count": 0,
        }
        self.assertEqual(route_after_review(state), "revise")

    def test_pass_verdict_routes_to_end(self):
        state: GraphState = {
            "review_result": {"verdict": "pass", "quality_score": 8},
            "revision_count": 0,
        }
        self.assertEqual(route_after_review(state), END)

    def test_score_above_threshold_routes_to_end(self):
        state: GraphState = {
            "review_result": {"verdict": "needs_revision", "quality_score": 7},
            "revision_count": 0,
        }
        self.assertEqual(route_after_review(state), END)

    def test_revision_cap_reached_routes_to_end(self):
        state: GraphState = {
            "review_result": {"verdict": "needs_revision", "quality_score": 2},
            "revision_count": REVISION_CAP,
        }
        self.assertEqual(route_after_review(state), END)

    def test_empty_review_result_routes_to_end(self):
        state: GraphState = {"review_result": {}, "revision_count": 0}
        self.assertEqual(route_after_review(state), END)

    def test_missing_review_result_routes_to_end(self):
        state: GraphState = {}
        self.assertEqual(route_after_review(state), END)

    def test_revision_count_below_cap_allows_revise(self):
        state: GraphState = {
            "review_result": {"verdict": "needs_revision", "quality_score": 1},
            "revision_count": REVISION_CAP - 1,
        }
        self.assertEqual(route_after_review(state), "revise")

    def test_score_exactly_6_routes_to_end(self):
        # Threshold is < 6, so score==6 should NOT trigger revision
        state: GraphState = {
            "review_result": {"verdict": "needs_revision", "quality_score": 6},
            "revision_count": 0,
        }
        self.assertEqual(route_after_review(state), END)

    def test_score_5_triggers_revision(self):
        state: GraphState = {
            "review_result": {"verdict": "needs_revision", "quality_score": 5},
            "revision_count": 0,
        }
        self.assertEqual(route_after_review(state), "revise")


class TestRevisionCap(unittest.TestCase):
    def test_revision_cap_is_1(self):
        self.assertEqual(REVISION_CAP, 1)


class TestStyleInstructions(unittest.TestCase):
    def test_all_styles_defined(self):
        for style in ("concise", "balanced", "detailed"):
            self.assertIn(style, STYLE_INSTRUCTIONS)

    def test_style_values_are_non_empty_strings(self):
        for style, instruction in STYLE_INSTRUCTIONS.items():
            self.assertIsInstance(instruction, str)
            self.assertGreater(len(instruction), 0)


class TestSynthesizeMessages(unittest.TestCase):
    def _make_plan_with_steps(self):
        return Plan(
            question="What is this?",
            repo="owner/repo",
            user_level="beginner",
            steps=[
                PlanStep(id=1, title="Explore", description="List files"),
                PlanStep(id=2, title="Summarize", description="Write answer"),
            ],
        )

    def test_returns_two_messages(self):
        plan = self._make_plan_with_steps()
        messages = synthesize_messages(plan, ["Finding 1", "Finding 2"], "readme", "evidence", "balanced", "beginner")
        self.assertEqual(len(messages), 2)

    def test_first_message_is_system(self):
        plan = self._make_plan_with_steps()
        messages = synthesize_messages(plan, [], "readme", "evidence", "concise", "intermediate")
        self.assertEqual(messages[0]["role"], "system")

    def test_second_message_is_user(self):
        plan = self._make_plan_with_steps()
        messages = synthesize_messages(plan, [], "readme", "evidence", "concise", "intermediate")
        self.assertEqual(messages[1]["role"], "user")

    def test_user_message_contains_question(self):
        plan = self._make_plan_with_steps()
        messages = synthesize_messages(plan, ["Finding 1"], "readme", "evidence", "balanced", "beginner")
        user_content = messages[1]["content"]
        self.assertIn("What is this?", user_content)

    def test_user_message_contains_repo(self):
        plan = self._make_plan_with_steps()
        messages = synthesize_messages(plan, [], "readme", "evidence", "balanced", "advanced")
        user_content = messages[1]["content"]
        self.assertIn("owner/repo", user_content)

    def test_user_message_contains_findings(self):
        plan = self._make_plan_with_steps()
        messages = synthesize_messages(plan, ["Key finding from README.md"], "readme", "evidence", "detailed", "beginner")
        user_content = messages[1]["content"]
        self.assertIn("Key finding from README.md", user_content)

    def test_system_prompt_includes_user_level(self):
        plan = self._make_plan_with_steps()
        messages = synthesize_messages(plan, [], "readme", "evidence", "balanced", "advanced")
        sys_content = messages[0]["content"]
        self.assertIn("advanced", sys_content)

    def test_system_prompt_includes_style_instruction(self):
        plan = self._make_plan_with_steps()
        messages = synthesize_messages(plan, [], "readme", "evidence", "concise", "intermediate")
        sys_content = messages[0]["content"]
        self.assertIn(STYLE_INSTRUCTIONS["concise"], sys_content)

    def test_evidence_chunks_included(self):
        plan = self._make_plan_with_steps()
        messages = synthesize_messages(plan, [], "readme", "unique_evidence_string_xyz", "balanced", "beginner")
        user_content = messages[1]["content"]
        self.assertIn("unique_evidence_string_xyz", user_content)


class TestBuildGraphs(unittest.TestCase):
    def test_build_graph_compiles_without_error(self):
        graph = build_graph()
        self.assertIsNotNone(graph)

    def test_build_pre_synth_graph_compiles(self):
        graph = build_pre_synth_graph()
        self.assertIsNotNone(graph)

    def test_build_post_synth_graph_compiles(self):
        graph = build_post_synth_graph()
        self.assertIsNotNone(graph)

    def test_graphs_are_different_objects(self):
        g1 = build_graph()
        g2 = build_pre_synth_graph()
        g3 = build_post_synth_graph()
        self.assertIsNot(g1, g2)
        self.assertIsNot(g1, g3)


class TestNodeIndex(unittest.TestCase):
    def setUp(self):
        os.environ["GROQ_API_KEY"] = "test_key"
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("graph.RepoRetriever")
    def test_node_index_attaches_retriever(self, MockRetriever):
        mock_retriever = MagicMock()
        mock_retriever.index.return_value = {
            "files_indexed": 3, "chunks_created": 10, "files": ["README.md"], "from_cache": False
        }
        mock_retriever.get_context_string.return_value = "chunk text"
        mock_retriever.chunk_count = 10
        MockRetriever.return_value = mock_retriever

        from graph import node_index
        state: GraphState = {
            "owner": "testowner",
            "repo": "testrepo",
            "question": "What is this?",
            "force_reindex": False,
        }
        result = node_index(state)
        self.assertIn("retriever", result)
        self.assertIn("index_stats", result)
        self.assertIn("evidence_chunks", result)

    @patch("graph.RepoRetriever")
    def test_node_index_uses_existing_retriever(self, MockRetriever):
        mock_retriever = MagicMock()
        mock_retriever.index.return_value = {
            "files_indexed": 2, "chunks_created": 5, "files": [], "from_cache": True
        }
        mock_retriever.get_context_string.return_value = ""
        mock_retriever.chunk_count = 5

        from graph import node_index
        state: GraphState = {
            "owner": "testowner",
            "repo": "testrepo",
            "question": "Q",
            "retriever": mock_retriever,
        }
        node_index(state)
        # Should NOT create a new RepoRetriever since one was passed
        MockRetriever.assert_not_called()


class TestNodePlan(unittest.TestCase):
    def setUp(self):
        os.environ["GROQ_API_KEY"] = "test_key"

    def tearDown(self):
        os.environ.pop("GROQ_API_KEY", None)

    @patch("graph.create_plan")
    def test_node_plan_returns_plan_in_state(self, mock_create_plan):
        plan = _make_plan(3)
        mock_create_plan.return_value = plan

        from graph import node_plan
        state: GraphState = {
            "question": "What is this?",
            "repo_name": "owner/repo",
            "user_level": "beginner",
            "readme": "# Readme",
        }
        result = node_plan(state)
        self.assertIn("plan", result)
        self.assertEqual(result["plan"], plan)

    @patch("graph.create_plan")
    def test_node_plan_handles_exception(self, mock_create_plan):
        mock_create_plan.side_effect = Exception("LLM error")

        from graph import node_plan
        state: GraphState = {
            "question": "Q",
            "repo_name": "r/r",
            "user_level": "intermediate",
            "readme": "",
        }
        result = node_plan(state)
        self.assertIn("error", result)
        self.assertIn("Planning failed", result["error"])


class TestNodeReview(unittest.TestCase):
    def setUp(self):
        os.environ["GROQ_API_KEY"] = "test_key"

    def tearDown(self):
        os.environ.pop("GROQ_API_KEY", None)

    @patch("graph.review_answer")
    def test_node_review_returns_review_result(self, mock_review):
        mock_review.return_value = {
            "verdict": "pass", "issues": [], "quality_score": 8, "summary": "Good"
        }

        from graph import node_review
        mock_retriever = MagicMock()
        mock_retriever.indexed_files = ["README.md"]

        state: GraphState = {
            "question": "Q?",
            "final_answer": "Answer text",
            "evidence_chunks": "evidence",
            "user_level": "intermediate",
            "retriever": mock_retriever,
        }
        result = node_review(state)
        self.assertIn("review_result", result)
        self.assertEqual(result["review_result"]["verdict"], "pass")

    @patch("graph.review_answer")
    def test_node_review_fallback_on_error(self, mock_review):
        mock_review.side_effect = Exception("API error")

        from graph import node_review
        state: GraphState = {
            "question": "Q?",
            "final_answer": "Answer",
            "evidence_chunks": "",
            "user_level": "beginner",
        }
        result = node_review(state)
        # Should fallback gracefully
        self.assertIn("review_result", result)
        self.assertEqual(result["review_result"]["verdict"], "pass")


class TestNodeRevise(unittest.TestCase):
    def setUp(self):
        os.environ["GROQ_API_KEY"] = "test_key"

    def tearDown(self):
        os.environ.pop("GROQ_API_KEY", None)

    @patch("graph.revise_answer")
    def test_node_revise_increments_revision_count(self, mock_revise):
        mock_revise.return_value = "Revised answer text"

        from graph import node_revise
        state: GraphState = {
            "question": "Q?",
            "final_answer": "Original answer",
            "review_result": {"issues": [], "verdict": "needs_revision"},
            "evidence_chunks": "evidence",
            "user_level": "intermediate",
            "revision_count": 0,
        }
        result = node_revise(state)
        self.assertEqual(result["revision_count"], 1)

    @patch("graph.revise_answer")
    def test_node_revise_updates_final_answer(self, mock_revise):
        mock_revise.return_value = "Improved revised answer"

        from graph import node_revise
        state: GraphState = {
            "question": "Q?",
            "final_answer": "Original",
            "review_result": {"issues": []},
            "evidence_chunks": "",
            "user_level": "advanced",
            "revision_count": 0,
        }
        result = node_revise(state)
        self.assertEqual(result["final_answer"], "Improved revised answer")

    @patch("graph.revise_answer")
    def test_node_revise_fallback_on_error(self, mock_revise):
        mock_revise.side_effect = Exception("Revision failed")

        from graph import node_revise
        original = "Original answer preserved"
        state: GraphState = {
            "question": "Q?",
            "final_answer": original,
            "review_result": {"issues": []},
            "evidence_chunks": "",
            "user_level": "beginner",
            "revision_count": 0,
        }
        result = node_revise(state)
        # On failure, original answer preserved
        self.assertEqual(result["final_answer"], original)
        self.assertEqual(result["revision_count"], 1)


if __name__ == "__main__":
    unittest.main()

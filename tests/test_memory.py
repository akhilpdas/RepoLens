"""Unit tests for memory.py — SQLite-backed user profile and question history."""

import os
import tempfile
import unittest
from unittest.mock import patch

import memory
from memory import (
    get_profile,
    update_profile,
    add_question,
    get_history,
    get_repo_history,
    get_memory_context,
)


class TestMemoryBase(unittest.TestCase):
    """Base class that redirects the DB to a temp file per test."""

    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmpfile.close()
        self._orig_db_path = memory.DB_PATH
        memory.DB_PATH = self.tmpfile.name

    def tearDown(self):
        memory.DB_PATH = self._orig_db_path
        os.unlink(self.tmpfile.name)


class TestGetProfile(TestMemoryBase):
    def test_default_profile_values(self):
        profile = get_profile()
        self.assertEqual(profile["skill_level"], "intermediate")
        self.assertEqual(profile["explanation_style"], "balanced")
        self.assertEqual(profile["last_repo"], "")

    def test_profile_has_required_keys(self):
        profile = get_profile()
        for key in ("skill_level", "explanation_style", "last_repo", "updated_at"):
            self.assertIn(key, profile)


class TestUpdateProfile(TestMemoryBase):
    def test_update_skill_level(self):
        update_profile(skill_level="advanced")
        profile = get_profile()
        self.assertEqual(profile["skill_level"], "advanced")

    def test_update_explanation_style(self):
        update_profile(explanation_style="detailed")
        profile = get_profile()
        self.assertEqual(profile["explanation_style"], "detailed")

    def test_update_last_repo(self):
        update_profile(last_repo="owner/myrepo")
        profile = get_profile()
        self.assertEqual(profile["last_repo"], "owner/myrepo")

    def test_update_multiple_fields(self):
        update_profile(skill_level="beginner", explanation_style="concise")
        profile = get_profile()
        self.assertEqual(profile["skill_level"], "beginner")
        self.assertEqual(profile["explanation_style"], "concise")

    def test_updated_at_set_after_update(self):
        update_profile(skill_level="advanced")
        profile = get_profile()
        self.assertNotEqual(profile["updated_at"], "")

    def test_update_with_no_args_no_error(self):
        # Calling with no args should not crash
        update_profile()
        profile = get_profile()
        self.assertEqual(profile["skill_level"], "intermediate")  # unchanged

    def test_partial_update_preserves_other_fields(self):
        update_profile(skill_level="advanced", explanation_style="detailed")
        update_profile(last_repo="new/repo")
        profile = get_profile()
        self.assertEqual(profile["skill_level"], "advanced")
        self.assertEqual(profile["explanation_style"], "detailed")
        self.assertEqual(profile["last_repo"], "new/repo")


class TestAddQuestion(TestMemoryBase):
    def test_question_stored_and_retrievable(self):
        add_question("owner/repo", "What is this?", "beginner")
        history = get_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["question"], "What is this?")
        self.assertEqual(history[0]["repo"], "owner/repo")

    def test_answer_preview_stored(self):
        add_question("owner/repo", "Q?", "intermediate", answer_preview="It is a test app.")
        history = get_history()
        self.assertIn("It is a test app", history[0]["answer_preview"])

    def test_quality_score_stored(self):
        add_question("owner/repo", "Q?", "advanced", quality_score=9)
        history = get_history()
        self.assertEqual(history[0]["quality_score"], 9)

    def test_answer_preview_truncated_to_500(self):
        long_preview = "x" * 600
        add_question("owner/repo", "Q?", "beginner", answer_preview=long_preview)
        history = get_history()
        self.assertLessEqual(len(history[0]["answer_preview"]), 500)

    def test_max_20_questions_kept(self):
        for i in range(25):
            add_question("owner/repo", f"Question {i}", "intermediate")
        history = get_history(limit=25)
        self.assertLessEqual(len(history), 20)

    def test_oldest_questions_pruned_first(self):
        for i in range(25):
            add_question("owner/repo", f"Q{i}", "intermediate")
        history = get_history(limit=25)
        questions_in_history = {h["question"] for h in history}
        # The earliest questions should have been pruned
        self.assertNotIn("Q0", questions_in_history)
        self.assertIn("Q24", questions_in_history)


class TestGetHistory(TestMemoryBase):
    def test_returns_most_recent_first(self):
        add_question("repo/a", "First", "beginner")
        add_question("repo/b", "Second", "intermediate")
        history = get_history()
        self.assertEqual(history[0]["question"], "Second")
        self.assertEqual(history[1]["question"], "First")

    def test_respects_limit(self):
        for i in range(5):
            add_question("owner/repo", f"Q{i}", "intermediate")
        history = get_history(limit=3)
        self.assertEqual(len(history), 3)

    def test_empty_history_returns_empty_list(self):
        history = get_history()
        self.assertEqual(history, [])

    def test_history_item_has_required_keys(self):
        add_question("owner/repo", "Test?", "advanced", answer_preview="Answer", quality_score=8)
        item = get_history()[0]
        for key in ("repo", "question", "user_level", "answer_preview", "quality_score", "asked_at"):
            self.assertIn(key, item)


class TestGetRepoHistory(TestMemoryBase):
    def test_filters_by_repo(self):
        add_question("owner/repoA", "QA", "beginner")
        add_question("owner/repoB", "QB", "beginner")
        history = get_repo_history("owner/repoA")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["question"], "QA")

    def test_returns_empty_for_unknown_repo(self):
        add_question("owner/repoA", "QA", "beginner")
        history = get_repo_history("owner/nonexistent")
        self.assertEqual(history, [])

    def test_respects_limit(self):
        for i in range(10):
            add_question("owner/repo", f"Q{i}", "intermediate")
        history = get_repo_history("owner/repo", limit=3)
        self.assertEqual(len(history), 3)

    def test_item_structure(self):
        add_question("owner/repo", "Test?", "advanced", quality_score=7)
        item = get_repo_history("owner/repo")[0]
        for key in ("question", "user_level", "answer_preview", "quality_score", "asked_at"):
            self.assertIn(key, item)


class TestGetMemoryContext(TestMemoryBase):
    def test_returns_user_level(self):
        ctx = get_memory_context("owner/repo", "beginner")
        self.assertIn("beginner", ctx)

    def test_returns_explanation_style(self):
        ctx = get_memory_context("owner/repo", "intermediate")
        self.assertIn("balanced", ctx)  # default style

    def test_includes_previous_questions_for_same_repo(self):
        add_question("owner/repo", "What is this?", "beginner", quality_score=8)
        ctx = get_memory_context("owner/repo", "beginner")
        self.assertIn("What is this?", ctx)

    def test_does_not_include_questions_from_other_repos(self):
        add_question("other/repo", "Unrelated question", "beginner")
        ctx = get_memory_context("owner/repo", "beginner")
        self.assertNotIn("Unrelated question", ctx)

    def test_includes_previously_explored_repo(self):
        update_profile(last_repo="other/coolrepo")
        ctx = get_memory_context("owner/repo", "intermediate")
        self.assertIn("other/coolrepo", ctx)

    def test_no_prev_repo_shown_if_same_as_current(self):
        update_profile(last_repo="owner/repo")
        ctx = get_memory_context("owner/repo", "intermediate")
        self.assertNotIn("Previously explored", ctx)


if __name__ == "__main__":
    unittest.main()

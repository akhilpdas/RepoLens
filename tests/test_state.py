"""Unit tests for state.py — dataclasses and enums."""

import unittest
from state import StepStatus, PlanStep, Plan, SessionState


class TestStepStatus(unittest.TestCase):
    def test_enum_values(self):
        self.assertEqual(StepStatus.PENDING.value, "pending")
        self.assertEqual(StepStatus.RUNNING.value, "running")
        self.assertEqual(StepStatus.DONE.value, "done")
        self.assertEqual(StepStatus.SKIPPED.value, "skipped")

    def test_str_comparison(self):
        # StepStatus inherits from str — can compare directly to string literals
        self.assertEqual(StepStatus.DONE, "done")
        self.assertNotEqual(StepStatus.PENDING, "done")


class TestPlanStep(unittest.TestCase):
    def test_default_values(self):
        step = PlanStep(id=1, title="T", description="D")
        self.assertEqual(step.status, StepStatus.PENDING)
        self.assertEqual(step.suggested_tools, [])
        self.assertEqual(step.result_summary, "")

    def test_custom_values(self):
        step = PlanStep(
            id=2,
            title="Read README",
            description="Check readme",
            suggested_tools=["read_file"],
            status=StepStatus.DONE,
            result_summary="Found overview",
        )
        self.assertEqual(step.id, 2)
        self.assertEqual(step.title, "Read README")
        self.assertEqual(step.suggested_tools, ["read_file"])
        self.assertEqual(step.status, StepStatus.DONE)

    def test_suggested_tools_is_independent(self):
        # Each PlanStep should have its own list, not a shared default
        a = PlanStep(id=1, title="A", description="")
        b = PlanStep(id=2, title="B", description="")
        a.suggested_tools.append("read_file")
        self.assertEqual(b.suggested_tools, [])


class TestPlan(unittest.TestCase):
    def _make_plan(self, statuses=None):
        statuses = statuses or [StepStatus.PENDING, StepStatus.PENDING]
        steps = [
            PlanStep(id=i + 1, title=f"Step {i+1}", description="", status=s)
            for i, s in enumerate(statuses)
        ]
        return Plan(question="Q?", repo="owner/repo", user_level="beginner", steps=steps)

    def test_is_complete_false_when_pending(self):
        plan = self._make_plan([StepStatus.DONE, StepStatus.PENDING])
        self.assertFalse(plan.is_complete)

    def test_is_complete_true_all_done(self):
        plan = self._make_plan([StepStatus.DONE, StepStatus.DONE])
        self.assertTrue(plan.is_complete)

    def test_is_complete_true_mixed_done_skipped(self):
        plan = self._make_plan([StepStatus.DONE, StepStatus.SKIPPED])
        self.assertTrue(plan.is_complete)

    def test_is_complete_empty_plan(self):
        plan = Plan(question="Q?", repo="r", user_level="beginner", steps=[])
        self.assertTrue(plan.is_complete)

    def test_current_step_returns_first_pending(self):
        plan = self._make_plan([StepStatus.DONE, StepStatus.PENDING])
        current = plan.current_step
        self.assertIsNotNone(current)
        self.assertEqual(current.id, 2)

    def test_current_step_none_when_all_done(self):
        plan = self._make_plan([StepStatus.DONE, StepStatus.DONE])
        self.assertIsNone(plan.current_step)

    def test_progress_counts_done_and_skipped(self):
        plan = self._make_plan([StepStatus.DONE, StepStatus.SKIPPED, StepStatus.PENDING])
        done, total = plan.progress
        self.assertEqual(done, 2)
        self.assertEqual(total, 3)

    def test_progress_all_pending(self):
        plan = self._make_plan([StepStatus.PENDING, StepStatus.PENDING])
        done, total = plan.progress
        self.assertEqual(done, 0)
        self.assertEqual(total, 2)

    def test_created_at_is_set(self):
        plan = Plan(question="Q", repo="r", user_level="intermediate", steps=[])
        self.assertIsNotNone(plan.created_at)
        self.assertIsInstance(plan.created_at, str)
        self.assertGreater(len(plan.created_at), 0)


class TestSessionState(unittest.TestCase):
    def test_default_values(self):
        s = SessionState()
        self.assertEqual(s.owner, "")
        self.assertEqual(s.repo, "")
        self.assertEqual(s.user_level, "intermediate")
        self.assertEqual(s.readme, "")
        self.assertIsNone(s.plan)
        self.assertEqual(s.tool_calls_log, [])
        self.assertEqual(s.final_answer, "")

    def test_tool_calls_log_is_independent(self):
        a = SessionState()
        b = SessionState()
        a.tool_calls_log.append({"tool": "x"})
        self.assertEqual(b.tool_calls_log, [])


if __name__ == "__main__":
    unittest.main()

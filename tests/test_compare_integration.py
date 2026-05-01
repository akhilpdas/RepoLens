"""Integration tests for compare-mode end-to-end flow.

Exercises the namespacing + stage-machine logic by simulating two pipelines
running side-by-side, using fixture state and a mocked LangGraph invocation.
The goal is NOT to test LangGraph itself (that's covered in test_graph.py)
but to verify that:

1. Both slots progress through their stage machines independently.
2. Approving slot A does not advance slot B (and vice versa).
3. Discarding one slot leaves the other untouched.
4. Reset of one slot clears only its keys.
5. The keyer pattern produces no cross-slot key collisions.
"""

import unittest

from compare import (
    PIPELINE_KEYS,
    SLOTS,
    slot_key,
    ss_get,
    ss_set,
    ss_pop,
    reset_slot,
    reset_all_slots,
    widget_key,
)


class FakeStateMachine:
    """Tiny stand-in for run_pipeline_for_slot — drives one slot through stages.

    Stages: input → running → approval → approved → done

    This lets us test the namespacing without bringing up Streamlit/LangGraph.
    """

    def __init__(self, state: dict, slot, repo_name: str):
        self.state = state
        self.slot = slot
        self.repo_name = repo_name

    def kick_off(self, question: str):
        ss_set(self.state, "active_question", question, slot=self.slot)
        ss_set(self.state, "stage", "running", slot=self.slot)

    def run_synth(self, fake_answer: str):
        """Simulate pre_synth + streaming synth."""
        assert ss_get(self.state, "stage", slot=self.slot) == "running"
        ss_set(self.state, "draft", {
            "question": ss_get(self.state, "active_question", slot=self.slot),
            "final_answer": fake_answer,
            "repo_name": self.repo_name,
        }, slot=self.slot)
        ss_set(self.state, "evidence_chunks", f"chunks for {self.repo_name}", slot=self.slot)
        ss_set(self.state, "stage", "approval", slot=self.slot)

    def approve(self):
        assert ss_get(self.state, "stage", slot=self.slot) == "approval"
        ss_set(self.state, "stage", "approved", slot=self.slot)

    def request_revise(self):
        assert ss_get(self.state, "stage", slot=self.slot) == "approval"
        ss_set(self.state, "stage", "user_revise", slot=self.slot)

    def apply_revision(self, new_answer: str):
        assert ss_get(self.state, "stage", slot=self.slot) == "user_revise"
        draft = ss_get(self.state, "draft", slot=self.slot)
        draft["final_answer"] = new_answer
        ss_set(self.state, "draft", draft, slot=self.slot)
        ss_set(self.state, "stage", "approval", slot=self.slot)

    def discard(self):
        reset_slot(self.state, slot=self.slot)

    def finalize(self, quality: int = 9):
        """Simulate post_synth_graph + memory persist + advance to done."""
        assert ss_get(self.state, "stage", slot=self.slot) == "approved"
        draft = ss_get(self.state, "draft", slot=self.slot)
        ss_set(self.state, "final_state", {
            "final_answer": draft["final_answer"],
            "review_result": {"quality_score": quality, "verdict": "pass"},
            "repo_name": self.repo_name,
        }, slot=self.slot)
        ss_set(self.state, "stage", "done", slot=self.slot)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestCompareTwoSlotsIndependent(unittest.TestCase):
    """Both slots progress through stages with no cross-talk."""

    def setUp(self):
        self.state = {}
        self.a = FakeStateMachine(self.state, "a", "tiangolo/fastapi")
        self.b = FakeStateMachine(self.state, "b", "pallets/flask")

    def test_initial_state_clean(self):
        for s in ("a", "b"):
            self.assertIsNone(ss_get(self.state, "stage", slot=s))
            self.assertIsNone(ss_get(self.state, "draft", slot=s))

    def test_kick_off_both_slots(self):
        self.a.kick_off("How does routing work?")
        self.b.kick_off("How does routing work?")
        self.assertEqual(ss_get(self.state, "stage", slot="a"), "running")
        self.assertEqual(ss_get(self.state, "stage", slot="b"), "running")
        self.assertEqual(
            ss_get(self.state, "active_question", slot="a"),
            ss_get(self.state, "active_question", slot="b"),
        )

    def test_full_happy_path_both_slots(self):
        self.a.kick_off("Q?")
        self.b.kick_off("Q?")
        self.a.run_synth("FastAPI uses path operations")
        self.b.run_synth("Flask uses route decorators")
        self.assertEqual(ss_get(self.state, "stage", slot="a"), "approval")
        self.assertEqual(ss_get(self.state, "stage", slot="b"), "approval")
        # Drafts must NOT have leaked between slots
        self.assertIn("path operations", ss_get(self.state, "draft", slot="a")["final_answer"])
        self.assertIn("route decorators", ss_get(self.state, "draft", slot="b")["final_answer"])
        self.assertNotIn("decorators", ss_get(self.state, "draft", slot="a")["final_answer"])

        self.a.approve()
        self.b.approve()
        self.a.finalize(quality=9)
        self.b.finalize(quality=8)
        self.assertEqual(ss_get(self.state, "stage", slot="a"), "done")
        self.assertEqual(ss_get(self.state, "stage", slot="b"), "done")
        self.assertEqual(
            ss_get(self.state, "final_state", slot="a")["review_result"]["quality_score"], 9
        )
        self.assertEqual(
            ss_get(self.state, "final_state", slot="b")["review_result"]["quality_score"], 8
        )


class TestApproveOneRevisingTheOther(unittest.TestCase):
    """User can approve A while still revising B (or vice versa)."""

    def setUp(self):
        self.state = {}
        self.a = FakeStateMachine(self.state, "a", "owner/A")
        self.b = FakeStateMachine(self.state, "b", "owner/B")
        self.a.kick_off("Q?")
        self.b.kick_off("Q?")
        self.a.run_synth("answer A")
        self.b.run_synth("answer B")

    def test_approve_a_while_b_in_revise(self):
        self.b.request_revise()
        self.assertEqual(ss_get(self.state, "stage", slot="b"), "user_revise")
        # Approving A must not affect B
        self.a.approve()
        self.a.finalize()
        self.assertEqual(ss_get(self.state, "stage", slot="a"), "done")
        self.assertEqual(ss_get(self.state, "stage", slot="b"), "user_revise")

    def test_revise_b_then_approve_a_already_done(self):
        self.a.approve()
        self.a.finalize()
        # Now revise B
        self.b.request_revise()
        self.b.apply_revision("revised answer B")
        self.assertEqual(
            ss_get(self.state, "draft", slot="b")["final_answer"],
            "revised answer B",
        )
        # A's draft must remain untouched
        self.assertEqual(
            ss_get(self.state, "final_state", slot="a")["final_answer"],
            "answer A",
        )

    def test_revision_loop_only_affects_one_slot(self):
        self.a.request_revise()
        self.a.apply_revision("revised A v1")
        self.a.request_revise()
        self.a.apply_revision("revised A v2")
        self.assertEqual(
            ss_get(self.state, "draft", slot="a")["final_answer"],
            "revised A v2",
        )
        # B never moved past approval
        self.assertEqual(ss_get(self.state, "stage", slot="b"), "approval")
        self.assertEqual(ss_get(self.state, "draft", slot="b")["final_answer"], "answer B")


class TestDiscardOneSlot(unittest.TestCase):
    """Discarding a draft must only clear that slot's keys."""

    def setUp(self):
        self.state = {}
        self.a = FakeStateMachine(self.state, "a", "owner/A")
        self.b = FakeStateMachine(self.state, "b", "owner/B")
        self.a.kick_off("Q?")
        self.b.kick_off("Q?")
        self.a.run_synth("answer A")
        self.b.run_synth("answer B")

    def test_discard_a_keeps_b(self):
        self.a.discard()
        # All A keys must be gone
        for base in PIPELINE_KEYS:
            self.assertNotIn(slot_key(base, "a"), self.state, f"{base}_a leaked")
        # B keys must persist
        self.assertEqual(ss_get(self.state, "stage", slot="b"), "approval")
        self.assertIsNotNone(ss_get(self.state, "draft", slot="b"))
        self.assertEqual(
            ss_get(self.state, "draft", slot="b")["final_answer"], "answer B"
        )

    def test_discard_b_keeps_a(self):
        self.b.discard()
        self.assertNotIn(slot_key("draft", "b"), self.state)
        self.assertEqual(ss_get(self.state, "stage", slot="a"), "approval")


class TestNewQuestionResetAllSlots(unittest.TestCase):
    """The 'New question' button must clear every slot's pipeline state."""

    def test_reset_all_slots_clears_compare_keys(self):
        state = {}
        a = FakeStateMachine(state, "a", "owner/A")
        b = FakeStateMachine(state, "b", "owner/B")
        a.kick_off("Q?")
        b.kick_off("Q?")
        a.run_synth("ans A")
        b.run_synth("ans B")
        a.approve()
        a.finalize(quality=8)
        # Add an unrelated key — must survive reset
        state["theme_choice"] = "🌙 Dark"
        state["last_eval"] = {"score": 80}

        reset_all_slots(state)

        # All pipeline keys gone for canonical, a, b
        for slot in (None, "a", "b"):
            for base in PIPELINE_KEYS:
                self.assertNotIn(slot_key(base, slot), state)
        # Unrelated keys preserved
        self.assertEqual(state["theme_choice"], "🌙 Dark")
        self.assertEqual(state["last_eval"], {"score": 80})


class TestNoCrossSlotKeyCollision(unittest.TestCase):
    """Every pipeline key must produce a unique storage location per slot."""

    def test_pipeline_keys_unique_across_slots(self):
        seen = set()
        for slot in (None, *SLOTS):
            for base in PIPELINE_KEYS:
                k = slot_key(base, slot)
                self.assertNotIn(k, seen,
                                 f"key {k} duplicated across slots")
                seen.add(k)

    def test_widget_keys_unique_across_slots(self):
        button_bases = (
            "btn_approve", "btn_revise", "btn_discard",
            "btn_apply_revise", "btn_revise_cancel",
            "dl_md", "dl_pdf", "custom_q", "revise_feedback_input",
        )
        seen = set()
        for slot in (None, *SLOTS):
            for base in button_bases:
                k = widget_key(base, slot)
                self.assertNotIn(k, seen, f"widget key {k} duplicated")
                seen.add(k)


class TestInterleavedExecutionAcrossReruns(unittest.TestCase):
    """Simulate Streamlit's rerun model: only one slot advances per 'rerun'."""

    def test_a_running_then_b_running_then_both_approval(self):
        state = {}
        a = FakeStateMachine(state, "a", "owner/A")
        b = FakeStateMachine(state, "b", "owner/B")

        # Initial: shared question kicks both into "running"
        a.kick_off("Q?")
        b.kick_off("Q?")

        # Rerun 1: A's running block executes (mimicking streamlit's flow)
        a.run_synth("ans A")
        # B still running
        self.assertEqual(ss_get(state, "stage", slot="a"), "approval")
        self.assertEqual(ss_get(state, "stage", slot="b"), "running")

        # Rerun 2: B's running block executes
        b.run_synth("ans B")
        self.assertEqual(ss_get(state, "stage", slot="a"), "approval")
        self.assertEqual(ss_get(state, "stage", slot="b"), "approval")

        # User approves A first (rerun 3)
        a.approve()
        # Rerun 4 — A finalizes, B still in approval
        a.finalize(quality=9)
        self.assertEqual(ss_get(state, "stage", slot="a"), "done")
        self.assertEqual(ss_get(state, "stage", slot="b"), "approval")

        # Now user approves B (rerun 5+6)
        b.approve()
        b.finalize(quality=8)
        self.assertEqual(ss_get(state, "stage", slot="b"), "done")


if __name__ == "__main__":
    unittest.main()

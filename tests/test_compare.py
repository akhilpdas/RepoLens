"""Unit tests for compare.py — session-state namespacing for multi-repo mode."""

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
    slot_label,
    widget_key,
)


class TestSlotKey(unittest.TestCase):
    def test_no_slot_returns_base(self):
        self.assertEqual(slot_key("stage"), "stage")
        self.assertEqual(slot_key("stage", None), "stage")

    def test_slot_a_appends_suffix(self):
        self.assertEqual(slot_key("stage", "a"), "stage_a")
        self.assertEqual(slot_key("draft", "a"), "draft_a")

    def test_slot_b_appends_suffix(self):
        self.assertEqual(slot_key("stage", "b"), "stage_b")
        self.assertEqual(slot_key("trace", "b"), "trace_b")

    def test_invalid_slot_raises(self):
        with self.assertRaises(ValueError):
            slot_key("stage", "c")
        with self.assertRaises(ValueError):
            slot_key("stage", "")
        with self.assertRaises(ValueError):
            slot_key("stage", "ab")

    def test_constants(self):
        self.assertEqual(SLOTS, ("a", "b"))
        # Confirm key pipeline state names are tracked
        for k in ("stage", "active_question", "draft", "final_state",
                  "retriever", "evidence_chunks", "trace"):
            self.assertIn(k, PIPELINE_KEYS)


class TestSsGetSet(unittest.TestCase):
    def test_get_default(self):
        state = {}
        self.assertIsNone(ss_get(state, "stage"))
        self.assertEqual(ss_get(state, "stage", default="input"), "input")

    def test_set_then_get_no_slot(self):
        state = {}
        ss_set(state, "stage", "running")
        self.assertEqual(state["stage"], "running")
        self.assertEqual(ss_get(state, "stage"), "running")

    def test_set_then_get_slot_a(self):
        state = {}
        ss_set(state, "stage", "running", slot="a")
        self.assertEqual(state["stage_a"], "running")
        self.assertEqual(ss_get(state, "stage", slot="a"), "running")

    def test_slots_independent(self):
        state = {}
        ss_set(state, "stage", "running", slot="a")
        ss_set(state, "stage", "approval", slot="b")
        self.assertEqual(ss_get(state, "stage", slot="a"), "running")
        self.assertEqual(ss_get(state, "stage", slot="b"), "approval")
        self.assertIsNone(ss_get(state, "stage"))

    def test_canonical_independent_from_slots(self):
        state = {}
        ss_set(state, "stage", "input")  # canonical
        ss_set(state, "stage", "running", slot="a")
        self.assertEqual(ss_get(state, "stage"), "input")
        self.assertEqual(ss_get(state, "stage", slot="a"), "running")


class TestSsPop(unittest.TestCase):
    def test_pop_no_slot(self):
        state = {"stage": "running"}
        self.assertEqual(ss_pop(state, "stage"), "running")
        self.assertNotIn("stage", state)

    def test_pop_with_slot(self):
        state = {"stage_a": "running"}
        self.assertEqual(ss_pop(state, "stage", slot="a"), "running")
        self.assertNotIn("stage_a", state)

    def test_pop_default(self):
        self.assertEqual(ss_pop({}, "stage", default="input"), "input")
        self.assertEqual(ss_pop({}, "stage", slot="a", default="input"), "input")


class TestResetSlot(unittest.TestCase):
    def test_reset_canonical(self):
        state = {
            "stage": "done",
            "active_question": "q1",
            "draft": {"x": 1},
            "final_state": {"y": 2},
            "retriever": object(),
            "trace": object(),
            "evidence_chunks": "stuff",
            "session": object(),
            "last_review": {"score": 8},
            "force_reindex": True,
            "unrelated_key": "preserved",
        }
        reset_slot(state, slot=None)
        for k in PIPELINE_KEYS:
            self.assertNotIn(k, state, f"{k} should have been removed")
        self.assertEqual(state["unrelated_key"], "preserved")

    def test_reset_slot_a_only(self):
        state = {
            "stage_a": "done",
            "stage_b": "running",
            "draft_a": {"x": 1},
            "draft_b": {"y": 2},
            "stage": "input",
        }
        reset_slot(state, slot="a")
        self.assertNotIn("stage_a", state)
        self.assertNotIn("draft_a", state)
        self.assertEqual(state["stage_b"], "running")
        self.assertEqual(state["draft_b"], {"y": 2})
        self.assertEqual(state["stage"], "input")

    def test_reset_slot_b_only(self):
        state = {"stage_a": "done", "stage_b": "running"}
        reset_slot(state, slot="b")
        self.assertEqual(state["stage_a"], "done")
        self.assertNotIn("stage_b", state)

    def test_reset_no_op_when_empty(self):
        state = {}
        reset_slot(state, slot="a")
        self.assertEqual(state, {})

    def test_reset_all_slots(self):
        state = {
            "stage": "done",
            "stage_a": "running",
            "stage_b": "approval",
            "draft": {},
            "draft_a": {},
            "draft_b": {},
            "preserved_key": "stays",
        }
        reset_all_slots(state)
        self.assertNotIn("stage", state)
        self.assertNotIn("stage_a", state)
        self.assertNotIn("stage_b", state)
        self.assertNotIn("draft", state)
        self.assertNotIn("draft_a", state)
        self.assertNotIn("draft_b", state)
        self.assertEqual(state["preserved_key"], "stays")


class TestSlotLabelAndWidget(unittest.TestCase):
    def test_slot_label(self):
        self.assertEqual(slot_label(None), "")
        self.assertEqual(slot_label("a"), "🅰️ ")
        self.assertEqual(slot_label("b"), "🅱️ ")

    def test_widget_key_basic(self):
        self.assertEqual(widget_key("custom_q"), "custom_q")
        self.assertEqual(widget_key("custom_q", "a"), "custom_q_a")
        self.assertEqual(widget_key("custom_q", "b"), "custom_q_b")

    def test_widget_keys_unique_across_slots(self):
        keys = {widget_key("revise_feedback", s) for s in (None, "a", "b")}
        self.assertEqual(len(keys), 3)


if __name__ == "__main__":
    unittest.main()

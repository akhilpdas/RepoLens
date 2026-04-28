"""Unit tests for tracer.py — Timer, TraceEvent, RunTrace."""

import time
import unittest
from tracer import Timer, TraceEvent, RunTrace


class TestTimer(unittest.TestCase):
    def test_elapsed_ms_is_non_negative(self):
        with Timer() as t:
            pass
        self.assertGreaterEqual(t.elapsed_ms, 0)

    def test_elapsed_ms_reflects_real_time(self):
        with Timer() as t:
            time.sleep(0.05)
        # Should be at least 40ms (allowing some margin)
        self.assertGreater(t.elapsed_ms, 40)

    def test_elapsed_ms_starts_at_zero(self):
        t = Timer()
        self.assertEqual(t.elapsed_ms, 0)

    def test_returns_self_on_enter(self):
        t = Timer()
        result = t.__enter__()
        self.assertIs(result, t)
        t.__exit__(None, None, None)


class TestTraceEvent(unittest.TestCase):
    def test_basic_creation(self):
        event = TraceEvent(phase="plan", step=None, action="Created plan", duration_ms=123.0)
        self.assertEqual(event.phase, "plan")
        self.assertIsNone(event.step)
        self.assertEqual(event.action, "Created plan")
        self.assertAlmostEqual(event.duration_ms, 123.0)
        self.assertEqual(event.detail, "")
        self.assertEqual(event.error, "")

    def test_with_all_fields(self):
        event = TraceEvent(
            phase="research",
            step=2,
            action="Read file",
            duration_ms=450.5,
            detail="app.py",
            error="",
        )
        self.assertEqual(event.step, 2)
        self.assertEqual(event.detail, "app.py")

    def test_timestamp_auto_set(self):
        event = TraceEvent(phase="review", step=None, action="Done", duration_ms=0)
        self.assertIsNotNone(event.timestamp)
        self.assertIsInstance(event.timestamp, str)


class TestRunTrace(unittest.TestCase):
    def _make_trace(self):
        return RunTrace(repo="owner/repo", question="What is this?", user_level="beginner")

    def test_initial_state(self):
        trace = self._make_trace()
        self.assertEqual(trace.repo, "owner/repo")
        self.assertEqual(trace.events, [])
        self.assertEqual(trace.quality_score, 0)
        self.assertEqual(trace.total_duration_ms, 0)

    def test_add_event(self):
        trace = self._make_trace()
        trace.add_event("plan", "Created 4-step plan", 250.0)
        self.assertEqual(len(trace.events), 1)
        self.assertEqual(trace.events[0].phase, "plan")
        self.assertEqual(trace.events[0].action, "Created 4-step plan")
        self.assertAlmostEqual(trace.events[0].duration_ms, 250.0)

    def test_add_event_with_optional_fields(self):
        trace = self._make_trace()
        trace.add_event("research", "Step failed", 100.0, step=3, detail="tools.py", error="timeout")
        event = trace.events[0]
        self.assertEqual(event.step, 3)
        self.assertEqual(event.detail, "tools.py")
        self.assertEqual(event.error, "timeout")

    def test_finalize_sums_durations(self):
        trace = self._make_trace()
        trace.add_event("plan", "Done", 100.0)
        trace.add_event("research", "Done", 200.0)
        trace.add_event("synthesis", "Done", 300.0)
        trace.finalize()
        self.assertAlmostEqual(trace.total_duration_ms, 600.0)

    def test_finalize_zero_events(self):
        trace = self._make_trace()
        trace.finalize()
        self.assertEqual(trace.total_duration_ms, 0)

    def test_summary_structure(self):
        trace = self._make_trace()
        trace.quality_score = 8
        trace.review_verdict = "pass"
        trace.files_indexed = 12
        trace.chunks_retrieved = 5
        trace.tool_calls_count = 7
        trace.final_answer_length = 1500
        trace.add_event("plan", "Done", 100.0)
        trace.add_event("research", "Step 1", 200.0)
        trace.finalize()

        s = trace.summary()
        self.assertEqual(s["repo"], "owner/repo")
        self.assertIn("plan", s["phase_times"])
        self.assertIn("research", s["phase_times"])
        self.assertEqual(s["quality_score"], 8)
        self.assertEqual(s["review_verdict"], "pass")
        self.assertEqual(s["files_indexed"], 12)
        self.assertEqual(s["tool_calls"], 7)
        self.assertEqual(s["answer_length"], 1500)

    def test_summary_question_truncated_at_80(self):
        long_q = "x" * 100
        trace = RunTrace(repo="r", question=long_q, user_level="intermediate")
        s = trace.summary()
        self.assertEqual(len(s["question"]), 80)

    def test_summary_errors_list(self):
        trace = self._make_trace()
        trace.add_event("research", "Failed", 10.0, error="HTTP 404")
        trace.add_event("plan", "OK", 50.0)
        s = trace.summary()
        self.assertIn("HTTP 404", s["errors"])
        self.assertEqual(len(s["errors"]), 1)  # only events with errors

    def test_event_log_format(self):
        trace = self._make_trace()
        trace.add_event("plan", "Created plan", 150.0)
        trace.add_event("research", "Step ran", 200.0, step=2)
        trace.add_event("review", "Failed", 50.0, error="timeout")
        log = trace.event_log()
        self.assertEqual(len(log), 3)
        self.assertIn("[plan]", log[0])
        self.assertIn("150", log[0])
        self.assertIn("(step 2)", log[1])
        self.assertIn("timeout", log[2])

    def test_event_log_no_step_info_when_none(self):
        trace = self._make_trace()
        trace.add_event("plan", "Created", 10.0, step=None)
        log = trace.event_log()
        self.assertNotIn("(step", log[0])


if __name__ == "__main__":
    unittest.main()

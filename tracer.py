"""RepoLens tracer — lightweight observability for each run.

Captures:
- Timestamps for each phase (plan, research steps, review, synthesis)
- Token usage estimates
- Tool calls with timings
- Quality scores
- Errors

Designed for Day 8 evals and debugging.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TraceEvent:
    """A single event in a trace."""
    phase: str          # "plan", "research", "review", "synthesis"
    step: Optional[int]    # step number if applicable
    action: str         # what happened
    duration_ms: float  # how long it took
    detail: str = ""    # extra info
    error: str = ""     # error if any
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RunTrace:
    """Full trace for a single RepoLens run."""
    repo: str
    question: str
    user_level: str
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    events: list[TraceEvent] = field(default_factory=list)
    total_duration_ms: float = 0
    quality_score: int = 0
    review_verdict: str = ""
    chunks_retrieved: int = 0
    files_indexed: int = 0
    tool_calls_count: int = 0
    final_answer_length: int = 0

    def add_event(self, phase: str, action: str, duration_ms: float,
                  step: Optional[int] = None, detail: str = "", error: str = ""):
        self.events.append(TraceEvent(
            phase=phase, step=step, action=action,
            duration_ms=duration_ms, detail=detail, error=error,
        ))

    def finalize(self):
        self.total_duration_ms = sum(e.duration_ms for e in self.events)

    def summary(self) -> dict:
        """Return a summary dict for display."""
        phase_times = {}
        for e in self.events:
            phase_times[e.phase] = phase_times.get(e.phase, 0) + e.duration_ms

        return {
            "repo": self.repo,
            "question": self.question[:80],
            "user_level": self.user_level,
            "total_time": f"{self.total_duration_ms / 1000:.1f}s",
            "phase_times": {k: f"{v / 1000:.1f}s" for k, v in phase_times.items()},
            "files_indexed": self.files_indexed,
            "chunks_retrieved": self.chunks_retrieved,
            "tool_calls": self.tool_calls_count,
            "quality_score": self.quality_score,
            "review_verdict": self.review_verdict,
            "answer_length": self.final_answer_length,
            "errors": [e.error for e in self.events if e.error],
        }

    def event_log(self) -> list[str]:
        """Return a human-readable event log."""
        lines = []
        for e in self.events:
            step_str = f" (step {e.step})" if e.step else ""
            err_str = f" ❌ {e.error}" if e.error else ""
            lines.append(
                f"[{e.phase}{step_str}] {e.action} — {e.duration_ms:.0f}ms{err_str}"
            )
        return lines


class Timer:
    """Context manager for timing operations."""

    def __init__(self):
        self.start_time = 0
        self.elapsed_ms = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.time() - self.start_time) * 1000

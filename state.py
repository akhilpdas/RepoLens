"""RepoLens state — structured session state for the agentic workflow."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """A single step in the investigation plan."""
    id: int
    title: str
    description: str
    suggested_tools: list[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result_summary: str = ""


@dataclass
class Plan:
    """A structured investigation plan created by the planner."""
    question: str
    repo: str
    user_level: str
    steps: list[PlanStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_complete(self) -> bool:
        return all(s.status in (StepStatus.DONE, StepStatus.SKIPPED) for s in self.steps)

    @property
    def current_step(self) -> Optional[PlanStep]:
        for s in self.steps:
            if s.status == StepStatus.PENDING:
                return s
        return None

    @property
    def progress(self) -> tuple[int, int]:
        done = sum(1 for s in self.steps if s.status in (StepStatus.DONE, StepStatus.SKIPPED))
        return done, len(self.steps)


@dataclass
class SessionState:
    """Top-level state container for a single analysis session."""
    owner: str = ""
    repo: str = ""
    user_level: str = "intermediate"
    readme: str = ""
    plan: Optional[Plan] = None
    tool_calls_log: list[dict] = field(default_factory=list)
    final_answer: str = ""

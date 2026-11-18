"""Closed payloads for Slice 7 reasoner and critic."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


PriorityLevel = Literal["high", "medium", "low"]
SkipReason = Literal[
    "ok",
    "malformed",
    "llm_unavailable",
    "deadline",
    "budget",
    "replay_miss",
]
CriticDimension = Literal["relevance", "diversity", "narrative"]
CriticStance = Literal["pass", "fail", "unknown"]


class ReasonerPriorityItem(BaseModel):
    place_id: UUID
    priority: PriorityLevel


class ReasonerModelOut(BaseModel):
    priorities: list[ReasonerPriorityItem] = Field(default_factory=list)


class ReasonerResult(BaseModel):
    skipped: bool
    reason: SkipReason
    model: str
    priorities: dict[UUID, PriorityLevel] = Field(default_factory=dict)
    dropped_unknown: int = 0
    dropped_invalid: int = 0
    usage: dict[str, int] = Field(default_factory=dict)
    prompt_version: str = ""
    ms: float = 0.0
    mode: Literal["live", "shadow"] = "live"

    def as_trace_diagnostics(self) -> dict[str, Any]:
        return {
            "skipped": self.skipped,
            "reason": self.reason,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "dropped_unknown": self.dropped_unknown,
            "dropped_invalid": self.dropped_invalid,
            "priority_count": len(self.priorities),
            "mode": self.mode,
        }


class CriticNote(BaseModel):
    dimension: CriticDimension
    stance: CriticStance
    message: str = ""


class CriticModelOut(BaseModel):
    notes: list[CriticNote] = Field(default_factory=list)
    prompt_version: str
    rubric_version: str


class CriticResult(BaseModel):
    skipped: bool
    reason: SkipReason
    model: str
    notes: list[CriticNote] = Field(default_factory=list)
    prompt_version: str = ""
    rubric_version: str = ""
    usage: dict[str, int] = Field(default_factory=dict)
    ms: float = 0.0
    mode: Literal["live", "shadow"] = "live"

    def as_trace_diagnostics(self) -> dict[str, Any]:
        return {
            "skipped": self.skipped,
            "reason": self.reason,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "rubric_version": self.rubric_version,
            "note_count": len(self.notes),
            "notes": [n.model_dump(mode="json") for n in self.notes],
            "mode": self.mode,
        }

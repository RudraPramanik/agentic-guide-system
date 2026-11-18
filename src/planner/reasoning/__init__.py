"""Slice 7 experimental reasoning roles — flag-gated, not registry tools."""

from src.planner.reasoning.budget import InvocationBudget, role_deadline_seconds
from src.planner.reasoning.critic import run_critic
from src.planner.reasoning.experience_reasoner import run_experience_reasoner
from src.planner.reasoning.schemas import CriticResult, ReasonerResult
from src.planner.reasoning.shadow import is_shadow_selected

__all__ = [
    "CriticResult",
    "InvocationBudget",
    "ReasonerResult",
    "is_shadow_selected",
    "role_deadline_seconds",
    "run_critic",
    "run_experience_reasoner",
]

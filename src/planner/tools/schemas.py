"""Minimal tool I/O envelope for P4 — full registry is P5."""

from __future__ import annotations

from pydantic import BaseModel


class ToolResult(BaseModel):
    ok: bool
    code: str | None = None
    message: str | None = None
    data: dict | None = None

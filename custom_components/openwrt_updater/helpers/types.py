"""Typed helpers for coordinator payloads (dataclasses, no TypedDict)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TohItem:
    """Normalized view of a single device entry from TOH cache."""

    version: str | None = None
    target: str | None = None
    subtarget: str | None = None
    snapshot_url: str | None = None
    compatibles: str | None = None

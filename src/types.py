"""Shared data structures used across pipeline stages (plan.md Phase 1).

Every stage from Phase 3 onward reads and writes these shapes, so they're
defined once here rather than reinvented per module.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Detection:
    frame: int
    cls: str  # "player" | "referee" | "ball"
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    track_id: int | None = None


@dataclass
class CourtPosition:
    frame: int
    t: float  # seconds from clip start
    x_ft: float
    y_ft: float


@dataclass
class Track:
    track_id: int
    team: str | None = None  # "offense" | "defense" | "referee" | None
    positions: list[CourtPosition] = field(default_factory=list)


@dataclass
class Event:
    type: str  # "pass" | "drive" | ...
    frame: int
    actor_track_id: int
    target_track_id: int | None = None

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum, StrEnum
from typing import Any, Protocol

from ins_ei.models import Point, Quality
from ins_ei.site_graph import SiteGraph
from ins_ei.state import StateStore


class Priority(IntEnum):
    SAFETY = 1000
    MANDATORY = 800
    SITE_RULE = 600
    OPTIMIZATION = 400
    FALLBACK = 0


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class Intent:
    target: str
    command: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Proposal:
    strategy: str
    action: str
    priority: Priority
    reason: str
    intents: tuple[Intent, ...] = ()
    confidence: Confidence = Confidence.MEDIUM
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    winning_strategy: str
    priority: Priority
    confidence: Confidence
    intents: tuple[Intent, ...]
    considered: tuple[Proposal, ...]
    decided_at: datetime


class StrategyContext:
    def __init__(self, graph: SiteGraph, state: StateStore, now: datetime | None = None) -> None:
        self.graph = graph
        self.state = state
        self.now = now or datetime.now().astimezone()

    def point(self, component_id: str, point_name: str) -> Point | None:
        return self.state.get(component_id, point_name)

    def good_value(self, component_id: str, point_name: str) -> Any | None:
        point = self.point(component_id, point_name)
        if point is None or point.quality != Quality.GOOD:
            return None
        return point.value


class StrategyModule(Protocol):
    id: str
    priority: Priority

    def evaluate(self, context: StrategyContext) -> Proposal | None: ...


class HoldStrategy:
    id = "hold"
    priority = Priority.FALLBACK

    def evaluate(self, context: StrategyContext) -> Proposal:
        return Proposal(
            strategy=self.id,
            action="HOLD",
            priority=self.priority,
            reason="No higher-priority strategy requested an action.",
            confidence=Confidence.HIGH,
        )


class StrategyEngine:
    def __init__(self, modules: list[StrategyModule] | None = None) -> None:
        self.modules = list(modules or [])
        self.fallback = HoldStrategy()

    def evaluate(self, context: StrategyContext) -> Decision:
        proposals: list[Proposal] = []
        for module in self.modules:
            proposal = module.evaluate(context)
            if proposal is not None:
                proposals.append(proposal)

        proposals.append(self.fallback.evaluate(context))

        # Highest priority wins. For equal priority, configured module order wins.
        indexed = list(enumerate(proposals))
        _, winner = max(indexed, key=lambda item: (int(item[1].priority), -item[0]))

        return Decision(
            action=winner.action,
            reason=winner.reason,
            winning_strategy=winner.strategy,
            priority=winner.priority,
            confidence=winner.confidence,
            intents=winner.intents,
            considered=tuple(proposals),
            decided_at=context.now,
        )

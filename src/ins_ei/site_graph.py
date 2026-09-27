from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ins_ei.config import ComponentConfig, SiteConfig


ALLOWED_RELATIONS = {
    "HEATS",
    "CHARGES",
    "SUPPLIES",
    "MEASURES",
    "CONTROLS",
    "CONNECTED_TO",
}

ALLOWED_COMPONENT_KINDS = {
    "GRID",
    "PV",
    "BATTERY",
    "HEAT_GENERATOR",
    "BUFFER",
    "DHW",
    "POWER_TO_HEAT",
    "HEAT_METER",
    "ELECTRIC_METER",
    "PUMP",
    "VALVE",
    "MARKET",
    "FORECAST",
    "WEATHER",
    "HEATING_CIRCUIT",
}


@dataclass(frozen=True)
class Relation:
    source: str
    target: str
    type: str


@dataclass(frozen=True)
class Constraint:
    id: str
    type: str
    target: str
    value: Any = None
    unit: str | None = None
    raw: dict[str, Any] | None = None


class SiteGraph:
    """Validated physical/logical topology of one INS-EI site.

    The graph describes what is connected and constrained. It does not decide
    what should run or optimize energy flows.
    """

    def __init__(self, site: SiteConfig) -> None:
        self.site = site
        self.components: dict[str, ComponentConfig] = {}
        self.relations: list[Relation] = []
        self.constraints: list[Constraint] = []
        self._outgoing: dict[str, list[Relation]] = {}
        self._incoming: dict[str, list[Relation]] = {}
        self._build()

    def _build(self) -> None:
        providers = {p.id for p in self.site.plugin_instances}

        for component in self.site.components:
            if component.id in self.components:
                raise ValueError(f"SITE_DUPLICATE_COMPONENT:{component.id}")
            if component.kind not in ALLOWED_COMPONENT_KINDS:
                raise ValueError(f"SITE_COMPONENT_KIND_UNKNOWN:{component.kind}")
            if component.provider and component.provider not in providers:
                raise ValueError(
                    f"SITE_PROVIDER_UNKNOWN:{component.id}:{component.provider}"
                )
            self.components[component.id] = component
            self._outgoing[component.id] = []
            self._incoming[component.id] = []

        for raw in self.site.relations:
            source = str(raw.get("from", ""))
            target = str(raw.get("to", ""))
            relation_type = str(raw.get("type", ""))
            if source not in self.components:
                raise ValueError(f"SITE_RELATION_SOURCE_UNKNOWN:{source}")
            if target not in self.components:
                raise ValueError(f"SITE_RELATION_TARGET_UNKNOWN:{target}")
            if relation_type not in ALLOWED_RELATIONS:
                raise ValueError(f"SITE_RELATION_TYPE_UNKNOWN:{relation_type}")
            relation = Relation(source, target, relation_type)
            self.relations.append(relation)
            self._outgoing[source].append(relation)
            self._incoming[target].append(relation)

        seen_constraints: set[str] = set()
        for raw in self.site.constraints:
            constraint_id = str(raw.get("id", ""))
            target = str(raw.get("target", ""))
            if not constraint_id:
                raise ValueError("SITE_CONSTRAINT_ID_MISSING")
            if constraint_id in seen_constraints:
                raise ValueError(f"SITE_DUPLICATE_CONSTRAINT:{constraint_id}")
            seen_constraints.add(constraint_id)

            component_id = target.split(".", 1)[0]
            if component_id not in self.components:
                raise ValueError(f"SITE_CONSTRAINT_TARGET_UNKNOWN:{target}")

            self.constraints.append(Constraint(
                id=constraint_id,
                type=str(raw.get("type", "")),
                target=target,
                value=raw.get("value"),
                unit=raw.get("unit"),
                raw=dict(raw),
            ))

    def component(self, component_id: str) -> ComponentConfig:
        try:
            return self.components[component_id]
        except KeyError as exc:
            raise ValueError(f"SITE_COMPONENT_UNKNOWN:{component_id}") from exc

    def outgoing(self, component_id: str, relation_type: str | None = None) -> list[Relation]:
        relations = list(self._outgoing.get(component_id, []))
        return [r for r in relations if r.type == relation_type] if relation_type else relations

    def incoming(self, component_id: str, relation_type: str | None = None) -> list[Relation]:
        relations = list(self._incoming.get(component_id, []))
        return [r for r in relations if r.type == relation_type] if relation_type else relations

    def targets(self, component_id: str, relation_type: str) -> list[ComponentConfig]:
        return [self.components[r.target] for r in self.outgoing(component_id, relation_type)]

    def sources(self, component_id: str, relation_type: str) -> list[ComponentConfig]:
        return [self.components[r.source] for r in self.incoming(component_id, relation_type)]

    def constraints_for(self, component_id: str) -> list[Constraint]:
        prefix = component_id + "."
        return [c for c in self.constraints if c.target == component_id or c.target.startswith(prefix)]

    def describe(self) -> dict[str, Any]:
        return {
            "site": self.site.site.id,
            "components": [
                {
                    "id": c.id,
                    "kind": c.kind,
                    "provider": c.provider,
                    "properties": c.properties,
                }
                for c in self.components.values()
            ],
            "relations": [
                {"from": r.source, "to": r.target, "type": r.type}
                for r in self.relations
            ],
            "constraints": [
                {
                    "id": c.id,
                    "type": c.type,
                    "target": c.target,
                    "value": c.value,
                    "unit": c.unit,
                }
                for c in self.constraints
            ],
        }

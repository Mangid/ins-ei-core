from __future__ import annotations

from typing import Any

from ins_ei.site_graph import SiteGraph
from ins_ei.state import StateStore


def build_site_view(graph: SiteGraph, state: StateStore) -> dict[str, Any]:
    """Build a vendor-neutral UI/read model from SiteGraph + live state."""
    components = []
    for component in graph.components.values():
        points = [
            {
                **point.model_dump(mode="json"),
                "age_seconds": state.age_seconds(point),
                "stale_after_seconds": state.stale_after_seconds(
                    point.component_id, point.point
                ),
            }
            for point in state.snapshot()
            if point.component_id == component.id
        ]
        components.append({
            "id": component.id,
            "kind": component.kind,
            "provider": component.provider,
            "properties": component.properties,
            "ports": [
                {
                    "id": port.id,
                    "type": port.type,
                    "properties": port.properties,
                }
                for port in component.ports
            ],
            "sensors": [
                {
                    "id": sensor.id,
                    "point": sensor.point,
                    "position": sensor.position,
                    "port": sensor.port,
                    "properties": sensor.properties,
                    "value": _sensor_value(state, component.id, sensor.point),
                }
                for sensor in component.sensors
            ],
            "points": points,
        })

    return {
        "site": graph.site.site.id,
        "components": components,
        "relations": [
            {"from": r.source, "to": r.target, "type": r.type}
            for r in graph.relations
        ],
        "connections": [
            {
                "from": f"{c.source_component}.{c.source_port}",
                "to": f"{c.target_component}.{c.target_port}",
                "medium": c.medium,
            }
            for c in graph.connections
        ],
        "constraints": [
            {
                "id": c.id,
                "type": c.type,
                "target": c.target,
                "value": c.value,
                "unit": c.unit,
            }
            for c in graph.constraints
        ],
    }


def _sensor_value(state: StateStore, component_id: str, point_name: str | None):
    if not point_name:
        return None
    point = state.get(component_id, point_name)
    if point is None:
        return None
    return {
        "value": point.value,
        "unit": point.unit,
        "quality": point.quality,
        "observed_at": point.observed_at.isoformat(),
        "age_seconds": state.age_seconds(point),
    }

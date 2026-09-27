from __future__ import annotations

from html import escape
from typing import Any


def render_svg(view: dict[str, Any], width: int = 1200, height: int = 700) -> str:
    """Render a simple vendor-neutral SVG schematic from Site View data.

    V0.1 uses deterministic semantic placement. It is intentionally dependency
    free; later layout engines/frontends may replace presentation without
    changing SiteGraph.
    """
    components = view.get("components", [])
    positions = _layout(components, width, height)
    component_by_id = {c["id"]: c for c in components}

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        ".box{fill:white;stroke:currentColor;stroke-width:2}.pipe{fill:none;stroke:currentColor;stroke-width:3}",
        ".label{font:16px sans-serif}.small{font:12px sans-serif}.sensor{fill:white;stroke:currentColor}",
        "</style>",
        f'<text x="30" y="35" class="label">INS-EI · {escape(str(view.get("site","")))}</text>',
    ]

    # Connections first so components render above lines.
    for connection in view.get("connections", []):
        source_id = connection["from"].rsplit(".", 1)[0]
        target_id = connection["to"].rsplit(".", 1)[0]
        if source_id not in positions or target_id not in positions:
            continue
        sx, sy = _center(positions[source_id])
        tx, ty = _center(positions[target_id])
        lines.append(
            f'<path class="pipe" d="M {sx} {sy} L {tx} {ty}">'
            f'<title>{escape(connection["from"])} → {escape(connection["to"])}</title></path>'
        )

    for component in components:
        x, y, w, h = positions[component["id"]]
        shape = component.get("presentation", {}).get("shape", "component")
        lines.extend(_render_component(component, shape, x, y, w, h))

    lines.append("</svg>")
    return "\n".join(lines)


def _layout(components: list[dict[str, Any]], width: int, height: int):
    groups = {"source": [], "converter": [], "storage": [], "transport": [], "consumer": [], "other": []}
    for component in components:
        role = component.get("presentation", {}).get("role", "generic")
        if role in {"source", "source_sink"}:
            groups["source"].append(component)
        elif role == "converter":
            groups["converter"].append(component)
        elif role == "storage":
            groups["storage"].append(component)
        elif role in {"transport", "control", "junction"}:
            groups["transport"].append(component)
        elif role in {"consumer", "network"}:
            groups["consumer"].append(component)
        else:
            groups["other"].append(component)

    columns = {
        "source": 130,
        "converter": 350,
        "storage": 600,
        "transport": 820,
        "consumer": 1040,
        "other": 1040,
    }
    positions = {}
    for group, items in groups.items():
        for index, component in enumerate(items):
            x = columns[group] - 70
            y = 90 + index * 135
            is_tank = component.get("presentation", {}).get("orientation") == "vertical"
            w, h = (150, 210) if is_tank else (150, 85)
            positions[component["id"]] = (x, min(y, height - h - 30), w, h)
    return positions


def _center(box):
    x, y, w, h = box
    return x + w / 2, y + h / 2


def _render_component(component, shape, x, y, w, h):
    cid = escape(component["id"])
    kind = escape(component["kind"])
    out = [
        f'<rect class="box" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>',
        f'<text x="{x+10}" y="{y+24}" class="label">{cid}</text>',
        f'<text x="{x+10}" y="{y+43}" class="small">{kind}</text>',
    ]

    points = component.get("points", [])
    shown = 0
    for point in points:
        if shown >= 3:
            break
        value = point.get("value")
        unit = point.get("unit") or ""
        name = escape(str(point.get("point", "")))
        quality = escape(str(point.get("quality", "")))
        out.append(
            f'<text x="{x+10}" y="{y+62+shown*16}" class="small">'
            f'{name}: {escape(str(value))} {escape(unit)} [{quality}]</text>'
        )
        shown += 1

    if shape in {"tank", "dhw_tank"}:
        for sensor in component.get("sensors", []):
            position = sensor.get("position")
            if position is None:
                continue
            sy = y + 55 + float(position) * max(1, h - 70)
            out.append(f'<circle class="sensor" cx="{x+w-12}" cy="{sy}" r="5"/>')
            value = sensor.get("value")
            if value:
                label = f'{value.get("value")} {value.get("unit") or ""}'
                out.append(
                    f'<text x="{x+w-75}" y="{sy-7}" class="small">{escape(label)}</text>'
                )
    return out

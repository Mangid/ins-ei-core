from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime

from ins_ei.autonomy import AutonomyGate
from ins_ei.historian import Historian
from ins_ei.model_registry import (
    LearningModelRecord,
    ModelDependency,
    ModelRegistry,
    ModelStatus,
)
from ins_ei.config import SiteConfig
from ins_ei.readiness import (
    OutcomeEvidence,
    ReadinessAssessment,
    ReadinessPolicy,
    assess_readiness,
)


class LearningCoordinator:
    """Connects persisted outcome evidence, model readiness and autonomy."""

    def __init__(
        self,
        site_id: str,
        historian: Historian,
        models: ModelRegistry,
        autonomy: AutonomyGate,
    ) -> None:
        self.site_id = site_id
        self.historian = historian
        self.models = models
        self.autonomy = autonomy
        self.policies: dict[str, ReadinessPolicy] = {}
        self.component_kinds: dict[str, str] = {}
        self.component_properties: dict[str, dict] = {}
        self.site_relations: list[dict] = []

    def restore(self) -> None:
        for row in self.historian.load_models():
            dependencies = [
                ModelDependency(**item)
                for item in json.loads(row["dependencies_json"] or "[]")
            ]
            model = LearningModelRecord(
                id=row["model_id"],
                version=row["version"],
                capability=row["capability"],
                status=ModelStatus(row["status"]),
                dependencies=dependencies,
                created_at=datetime.fromisoformat(row["created_at"]),
                status_changed_at=datetime.fromisoformat(row["status_changed_at"]),
                metadata=json.loads(row["metadata_json"] or "{}"),
                reason=row["reason"],
            )
            self.models.register(model)
            if row["readiness_policy_json"]:
                self.policies[model.id] = ReadinessPolicy(
                    **json.loads(row["readiness_policy_json"])
                )


    def ensure_baseline_models(self, site: SiteConfig) -> None:
        """Register observation-only V1 models from the configured SiteGraph."""
        self.component_kinds = {c.id: c.kind for c in site.components}
        self.component_properties = {c.id: dict(c.properties) for c in site.components}
        self.site_relations = list(site.relations)
        existing = {m.id for m in self.models.all()}
        kinds = {c.kind for c in site.components}
        definitions = [
            ("thermal-baseline", "thermal_behavior", {"BUFFER", "DHW", "HEAT_GENERATOR"}),
            ("electrical-baseline", "electrical_behavior", {"GRID", "PV", "PV_INVERTER", "PV_INPUT", "BATTERY"}),
            ("battery-baseline", "battery_behavior", {"BATTERY"}),
            ("pv-orientation-baseline", "pv_orientation_behavior", {"PV_INPUT"}),
        ]
        # Refresh commissioned PV provenance while the model is still learning.
        if "pv-orientation-baseline" in existing:
            model = self.models.get("pv-orientation-baseline")
            if model.status == ModelStatus.LEARNING:
                pv_orientation, commissioned_inputs = {}, {}
                for component in site.components:
                    if component.kind != "PV_INPUT":
                        continue
                    orientation = component.properties.get("orientation")
                    if not orientation:
                        continue
                    capacity = float(component.properties.get("capacity_kwp") or 0.0)
                    entry = pv_orientation.setdefault(orientation, {"capacity_kwp": 0.0, "inputs": []})
                    entry["inputs"].append(component.id)
                    entry["capacity_kwp"] += capacity
                    commissioned_inputs[component.id] = {
                        "label": component.properties.get("label"),
                        "orientation": orientation,
                        "capacity_kwp": capacity,
                    }
                model.metadata["pv_orientations"] = pv_orientation
                model.metadata["commissioned_inputs"] = commissioned_inputs
                model.metadata["commissioning_status"] = site.commissioning.status
                self.historian.save_model(model)

        for model_id, capability, required_kinds in definitions:
            if model_id in existing or not (kinds & required_kinds):
                continue
            dependencies = [
                ModelDependency(kind="component", id=c.id)
                for c in site.components if c.kind in required_kinds
            ]
            pv_orientation = {}
            commissioned_inputs = {}
            if model_id == "pv-orientation-baseline":
                for component in site.components:
                    if component.kind != "PV_INPUT":
                        continue
                    orientation = component.properties.get("orientation")
                    if not orientation:
                        continue
                    capacity = float(component.properties.get("capacity_kwp") or 0.0)
                    entry = pv_orientation.setdefault(orientation, {"capacity_kwp": 0.0, "inputs": []})
                    entry["inputs"].append(component.id)
                    entry["capacity_kwp"] += capacity
                    commissioned_inputs[component.id] = {
                        "label": component.properties.get("label"),
                        "orientation": orientation,
                        "capacity_kwp": capacity,
                    }
            model = LearningModelRecord(
                id=model_id,
                version="1",
                capability=capability,
                status=ModelStatus.LEARNING,
                dependencies=dependencies,
                metadata={
                    "phase": "OBSERVATION",
                    "algorithm": "baseline-v1",
                    "commissioning_status": site.commissioning.status,
                    "topology_confirmed": site.commissioning.topology_confirmed,
                    "constraints_confirmed": site.commissioning.constraints_confirmed,
                    "pv_orientations": pv_orientation if model_id == "pv-orientation-baseline" else {},
                    "commissioned_inputs": commissioned_inputs if model_id == "pv-orientation-baseline" else {},
                },
                reason="Collecting historical observations before model fitting.",
            )
            self.models.register(model)
            self.historian.save_model(model)

    def baseline_status(self) -> dict:
        summary = self.historian.observation_summary(self.site_id)
        duration_h = summary["duration_seconds"] / 3600.0
        if duration_h < 6:
            phase = "COLLECTING"
            reason = f"Collecting baseline data ({duration_h:.1f} h / 6 h minimum first assessment)."
        elif duration_h < 24:
            phase = "BASELINE_READY"
            reason = f"Initial baseline available after {duration_h:.1f} h; continue collecting for daily behavior."
        else:
            phase = "LEARNING"
            reason = f"{duration_h:.1f} h historical coverage available for model fitting."
        return {
            "phase": phase,
            "reason": reason,
            "duration_hours": duration_h,
            "signals": summary["signals"],
            "samples": summary["samples"],
            "first_observed_at": summary["first_observed_at"],
            "last_observed_at": summary["last_observed_at"],
            "coverage": summary["coverage"],
        }


    def fit_passive_baselines(self) -> dict:
        """Fit simple observation-only baselines once enough history exists."""
        status = self.baseline_status()
        if status["duration_hours"] < 6:
            return {"fitted": False, "reason": status["reason"], "models": {}}

        fitted = {}
        specs = {
            "buffer_temperature": ("buffer", "thermal.temperature_upper"),
            "dhw_temperature": ("dhw", "thermal.temperature"),
            "battery_soc": ("battery", "battery.soc"),
        }
        for name, (component, point) in specs.items():
            rows = self.historian.numeric_series(self.site_id, component, point)
            rates = []
            for a, b in zip(rows, rows[1:]):
                ta = datetime.fromisoformat(a["observed_at"])
                tb = datetime.fromisoformat(b["observed_at"])
                dt_h = (tb - ta).total_seconds() / 3600.0
                if dt_h <= 0 or dt_h > 0.25:
                    continue
                rates.append((b["value"] - a["value"]) / dt_h)
            if rows:
                values = [x["value"] for x in rows]
                fitted[name] = {
                    "samples": len(rows),
                    "minimum": min(values),
                    "maximum": max(values),
                    "mean": sum(values) / len(values),
                    "rate_samples": len(rates),
                    "mean_rate_per_hour": (sum(rates) / len(rates)) if rates else None,
                }

        for model in self.models.all():
            if model.status != ModelStatus.LEARNING:
                continue
            if model.metadata.get("phase") in {None, "OBSERVATION", "PASSIVE_BASELINE"}:
                model.metadata["phase"] = "PASSIVE_BASELINE"
            model.metadata["last_fit_at"] = datetime.now().astimezone().isoformat()
            if model.id == "thermal-baseline":
                model.metadata["generic_fit"] = {k: v for k, v in fitted.items() if k in {"buffer_temperature", "dhw_temperature"}}
            elif model.id == "battery-baseline":
                model.metadata["generic_fit"] = {k: v for k, v in fitted.items() if k == "battery_soc"}
            # Specialized electrical/PV models own their own result namespaces.
            model.reason = "Passive baseline fitted from GOOD historical observations; no control authority."
            self.historian.save_model(model)

        return {"fitted": True, "models": fitted}


    def fit_thermal_context_baseline(self) -> dict:
        """Learn context-separated buffer temperature rates without control."""
        status = self.baseline_status()
        if status["duration_hours"] < 6:
            return {"fitted": False, "reason": status["reason"]}

        buffer_rows = self.historian.numeric_series(
            self.site_id, "buffer", "thermal.temperature_upper", limit=20000
        )
        pellet_rows = self.historian.numeric_series(
            self.site_id, "pellet_boiler", "power.modulation", limit=20000
        )
        p2h_rows = self.historian.numeric_series(
            self.site_id, "power_to_heat", "power.electrical", limit=20000
        )
        outdoor_rows = self.historian.numeric_series(
            self.site_id, "weather", "weather.outdoor_temperature", limit=20000
        )

        def nearest(rows, ts, max_age_s=90):
            if not rows:
                return None
            best = min(rows, key=lambda r: abs((datetime.fromisoformat(r["observed_at"]) - ts).total_seconds()))
            age = abs((datetime.fromisoformat(best["observed_at"]) - ts).total_seconds())
            return best["value"] if age <= max_age_s else None

        buckets = {
            "PASSIVE_COOLING": [],
            "PELLET_HEATING": [],
            "POWER_TO_HEAT": [],
            "MIXED": [],
        }
        outdoor_by_bucket = {k: [] for k in buckets}
        # Thermal dynamics are evaluated over multi-minute windows so sensor
        # quantisation/noise at the 10 s collection cadence does not dominate.
        for i, a in enumerate(buffer_rows):
            ta = datetime.fromisoformat(a["observed_at"])
            b = None
            for candidate in buffer_rows[i+1:]:
                dt_s = (datetime.fromisoformat(candidate["observed_at"]) - ta).total_seconds()
                if 300 <= dt_s <= 900:
                    b = candidate
                    break
                if dt_s > 900:
                    break
            if b is None:
                continue
            tb = datetime.fromisoformat(b["observed_at"])
            dt_h = (tb - ta).total_seconds() / 3600.0
            rate = (b["value"] - a["value"]) / dt_h
            pellet = nearest(pellet_rows, tb)
            p2h = nearest(p2h_rows, tb)
            outdoor = nearest(outdoor_rows, tb, 600)
            pellet_on = pellet is not None and pellet > 1.0
            p2h_on = p2h is not None and p2h > 100.0
            if pellet_on and p2h_on:
                bucket = "MIXED"
            elif pellet_on:
                bucket = "PELLET_HEATING"
            elif p2h_on:
                bucket = "POWER_TO_HEAT"
            else:
                bucket = "PASSIVE_COOLING"
            buckets[bucket].append(rate)
            if outdoor is not None:
                outdoor_by_bucket[bucket].append(outdoor)

        fit = {}
        for bucket, rates in buckets.items():
            if not rates:
                continue
            ordered = sorted(rates)
            trim = int(len(ordered) * 0.025) if len(ordered) >= 40 else 0
            robust = ordered[trim:len(ordered)-trim] if trim and len(ordered) > 2*trim else ordered
            fit[bucket] = {
                "samples": len(rates),
                "robust_samples": len(robust),
                "mean_delta_c_per_h": sum(robust) / len(robust),
                "median_delta_c_per_h": robust[len(robust)//2],
                "p025_delta_c_per_h": robust[0],
                "p975_delta_c_per_h": robust[-1],
                "raw_min_delta_c_per_h": ordered[0],
                "raw_max_delta_c_per_h": ordered[-1],
                "mean_outdoor_c": (
                    sum(outdoor_by_bucket[bucket]) / len(outdoor_by_bucket[bucket])
                    if outdoor_by_bucket[bucket] else None
                ),
            }

        # Power-to-Heat V2: learn response by actual electrical power and
        # starting buffer temperature instead of treating every active period equally.
        p2h_v2_samples = []
        for i, a in enumerate(buffer_rows):
            ta = datetime.fromisoformat(a["observed_at"])
            b = None
            for candidate in buffer_rows[i+1:]:
                dt_s = (datetime.fromisoformat(candidate["observed_at"]) - ta).total_seconds()
                if 300 <= dt_s <= 900:
                    b = candidate
                    break
                if dt_s > 900:
                    break
            if b is None:
                continue
            tb = datetime.fromisoformat(b["observed_at"])
            p2h = nearest(p2h_rows, tb)
            pellet = nearest(pellet_rows, tb)
            if p2h is None or p2h <= 100.0 or (pellet is not None and pellet > 1.0):
                continue
            dt_h = (tb - ta).total_seconds() / 3600.0
            rate = (b["value"] - a["value"]) / dt_h
            outdoor = nearest(outdoor_rows, tb, 600)
            power_band = (
                "0_3KW" if p2h < 3000 else
                "3_6KW" if p2h < 6000 else
                "6_9KW"
            )
            temp = float(a["value"])
            temp_band = (
                "LT45C" if temp < 45 else
                "45_55C" if temp < 55 else
                "55_65C" if temp < 65 else
                "GE65C"
            )
            p2h_v2_samples.append({
                "power_w": p2h, "start_buffer_c": temp, "rate_c_per_h": rate,
                "outdoor_c": outdoor, "power_band": power_band, "temp_band": temp_band,
            })

        p2h_v2 = {}
        grouped = {}
        for sample in p2h_v2_samples:
            key = f"{sample['power_band']}__{sample['temp_band']}"
            grouped.setdefault(key, []).append(sample)
        for key, samples in grouped.items():
            rates = sorted(x["rate_c_per_h"] for x in samples)
            trim = int(len(rates) * 0.025) if len(rates) >= 40 else 0
            robust = rates[trim:len(rates)-trim] if trim and len(rates) > 2 * trim else rates
            outdoors = [x["outdoor_c"] for x in samples if x["outdoor_c"] is not None]
            powers = [x["power_w"] for x in samples]
            p2h_v2[key] = {
                "samples": len(samples),
                "robust_samples": len(robust),
                "mean_power_w": sum(powers) / len(powers),
                "mean_start_buffer_c": sum(x["start_buffer_c"] for x in samples) / len(samples),
                "mean_delta_c_per_h": sum(robust) / len(robust),
                "median_delta_c_per_h": robust[len(robust)//2],
                "p025_delta_c_per_h": robust[0],
                "p975_delta_c_per_h": robust[-1],
                "mean_outdoor_c": sum(outdoors) / len(outdoors) if outdoors else None,
            }

        try:
            model = self.models.get("thermal-baseline")
        except ValueError:
            return {"fitted": False, "reason": "thermal-baseline model missing"}
        model.metadata["phase"] = "POWER_TO_HEAT_V2"
        model.metadata["thermal_context_fit"] = fit
        model.metadata["power_to_heat_v2_fit"] = p2h_v2
        model.metadata["last_fit_at"] = datetime.now().astimezone().isoformat()
        model.reason = "Thermal baseline with Power-to-Heat V2 power/temperature contexts; no control authority."
        self.historian.save_model(model)
        return {"fitted": True, "contexts": fit}


    def fit_buffer_state_v1(self) -> dict:
        """Learn observed buffer state and topology context without inventing heat flows."""
        status = self.baseline_status()
        if status["duration_hours"] < 6:
            return {"fitted": False, "reason": status["reason"]}
        buffers = [cid for cid, kind in self.component_kinds.items() if kind == "BUFFER"]
        result = {}
        for buffer_id in buffers:
            props = self.component_properties.get(buffer_id, {})
            configured = props.get("temperature_sensor_positions") or {}
            sensors = {}
            for position, point in configured.items():
                rows = self.historian.numeric_series(self.site_id, buffer_id, point, limit=20000)
                values = [r["value"] for r in rows]
                sensors[position] = {
                    "point": point, "samples": len(values),
                    "minimum_c": min(values) if values else None,
                    "maximum_c": max(values) if values else None,
                    "mean_c": (sum(values) / len(values)) if values else None,
                }

            incoming, outgoing = [], []
            for rel in self.site_relations:
                if rel.get("to") == buffer_id and rel.get("type") in {"HEATS", "CHARGES"}:
                    incoming.append({"component": rel.get("from"), "relation": rel.get("type"),
                                     "kind": self.component_kinds.get(rel.get("from"))})
                if rel.get("from") == buffer_id and rel.get("type") in {"SUPPLIES", "HEATS"}:
                    outgoing.append({"component": rel.get("to"), "relation": rel.get("type"),
                                     "kind": self.component_kinds.get(rel.get("to"))})

            observed_positions = [p for p in ("TOP","UPPER_MIDDLE","LOWER_MIDDLE","BOTTOM") if p in sensors and sensors[p]["samples"]]
            coverage = len(observed_positions) / 4.0
            observability = "FULL" if coverage == 1 else ("PARTIAL" if coverage >= 0.5 else ("LIMITED" if coverage > 0 else "NONE"))
            result[buffer_id] = {
                "volume_l": props.get("volume_l"),
                "observed_positions": observed_positions,
                "observability": observability,
                "coverage_fraction": coverage,
                "sensors": sensors,
                "incoming": incoming,
                "outgoing": outgoing,
                "energy_content_claimed": False,
                "note": "State model uses observed temperatures/topology only; no unmeasured thermal power is invented.",
            }

        try:
            model = self.models.get("thermal-baseline")
        except ValueError:
            return {"fitted": False, "reason": "thermal-baseline model missing"}
        model.metadata["buffer_state_v1_fit"] = result
        model.metadata["phase"] = "BUFFER_STATE_V1"
        model.metadata["last_fit_at"] = datetime.now().astimezone().isoformat()
        model.reason = "Buffer State V1 from commissioned sensor positions and SiteGraph topology; no energy-content claim and no control authority."
        self.historian.save_model(model)
        return {"fitted": True, "buffers": result}


    def fit_buffer_state_v2(self) -> dict:
        """Learn multi-sensor buffer response by observed SiteGraph operating context."""
        v1 = self.fit_buffer_state_v1()
        if not v1.get("fitted"):
            return v1

        def series(component, point):
            return self.historian.numeric_series(self.site_id, component, point, limit=20000)

        def nearest(rows, ts, max_age_s=120):
            if not rows:
                return None
            best = min(rows, key=lambda r: abs((datetime.fromisoformat(r["observed_at"]) - ts).total_seconds()))
            age = abs((datetime.fromisoformat(best["observed_at"]) - ts).total_seconds())
            return best["value"] if age <= max_age_s else None

        result = {}
        for buffer_id, meta in v1["buffers"].items():
            sensor_series = {p: series(buffer_id, s["point"]) for p, s in meta["sensors"].items() if s["samples"]}
            if not sensor_series:
                continue
            driver_series = {}
            for x in meta["incoming"] + meta["outgoing"]:
                cid, kind = x["component"], x["kind"]
                candidates = (
                    ["power.electrical"] if kind == "POWER_TO_HEAT" else
                    ["power.modulation", "state.burner"] if kind == "HEAT_GENERATOR" else
                    ["state.pump", "state.operating"] if kind in {"HEATING_CIRCUIT", "DHW"} else []
                )
                driver_series[cid] = {p: series(cid, p) for p in candidates}

            contexts = {}
            reference_position = next((p for p in ("TOP","UPPER_MIDDLE","LOWER_MIDDLE","BOTTOM") if p in sensor_series), None)
            rows = sensor_series[reference_position]
            for i, a in enumerate(rows):
                ta = datetime.fromisoformat(a["observed_at"])
                b = None
                for candidate in rows[i+1:]:
                    dt_s = (datetime.fromisoformat(candidate["observed_at"]) - ta).total_seconds()
                    if 300 <= dt_s <= 900:
                        b = candidate; break
                    if dt_s > 900: break
                if b is None:
                    continue
                tb = datetime.fromisoformat(b["observed_at"])
                dt_h = (tb-ta).total_seconds()/3600.0
                labels, drivers = [], {}
                for x in meta["incoming"] + meta["outgoing"]:
                    cid, kind = x["component"], x["kind"]
                    ds = driver_series.get(cid, {})
                    if kind == "POWER_TO_HEAT":
                        val = nearest(ds.get("power.electrical", []), tb)
                        active = val is not None and val > 100
                        labels.append(f"{cid}={'ON' if active else 'OFF'}")
                        drivers[cid] = {"kind": kind, "active": active, "power_w": val}
                    elif kind == "HEAT_GENERATOR":
                        mod = nearest(ds.get("power.modulation", []), tb)
                        burner = nearest(ds.get("state.burner", []), tb)
                        active = (mod is not None and mod > 1) or burner in {True, 1, "true", "on", "ON"}
                        labels.append(f"{cid}={'ON' if active else 'OFF'}")
                        drivers[cid] = {"kind": kind, "active": active, "modulation": mod}
                    elif kind in {"HEATING_CIRCUIT", "DHW"}:
                        pump = nearest(ds.get("state.pump", []), tb)
                        active = pump in {True, 1, "true", "on", "ON"}
                        labels.append(f"{cid}={'ON' if active else 'OFF'}")
                        drivers[cid] = {"kind": kind, "active": active}
                key = "__".join(labels) if labels else "NO_DRIVERS"
                item = contexts.setdefault(key, {"samples": 0, "sensor_rates": {}, "drivers": drivers})
                item["samples"] += 1
                for position, srows in sensor_series.items():
                    av = nearest(srows, ta, 45); bv = nearest(srows, tb, 45)
                    if av is None or bv is None:
                        continue
                    item["sensor_rates"].setdefault(position, []).append((bv-av)/dt_h)

            summarized = {}
            for key, item in contexts.items():
                sensor_rates = {}
                for position, rates in item["sensor_rates"].items():
                    ordered = sorted(rates)
                    sensor_rates[position] = {
                        "samples": len(rates),
                        "mean_delta_c_per_h": sum(rates)/len(rates),
                        "median_delta_c_per_h": ordered[len(ordered)//2],
                        "minimum_delta_c_per_h": ordered[0],
                        "maximum_delta_c_per_h": ordered[-1],
                    }
                summarized[key] = {"samples": item["samples"], "drivers": item["drivers"], "sensor_rates": sensor_rates}
            result[buffer_id] = {"observability": meta["observability"], "contexts": summarized}

        model = self.models.get("thermal-baseline")
        model.metadata["buffer_state_v2_fit"] = result
        model.metadata["phase"] = "BUFFER_STATE_V2"
        model.metadata["last_fit_at"] = datetime.now().astimezone().isoformat()
        model.reason = "Buffer State V2 learns observed multi-sensor response by SiteGraph operating context; no unmeasured heat flow and no control authority."
        self.historian.save_model(model)
        return {"fitted": True, "buffers": result}


    def fit_dhw_baseline(self) -> dict:
        status = self.baseline_status()
        if status["duration_hours"] < 6:
            return {"fitted": False, "reason": status["reason"]}
        rows = self.historian.numeric_series(
            self.site_id, "dhw", "thermal.temperature", limit=20000
        )
        cooling, heating = [], []
        for i, a in enumerate(rows):
            ta = datetime.fromisoformat(a["observed_at"])
            b = None
            for candidate in rows[i+1:]:
                dt_s = (datetime.fromisoformat(candidate["observed_at"]) - ta).total_seconds()
                if 300 <= dt_s <= 900:
                    b = candidate
                    break
                if dt_s > 900:
                    break
            if b is None:
                continue
            tb = datetime.fromisoformat(b["observed_at"])
            dt_h = (tb - ta).total_seconds() / 3600.0
            rate = (b["value"] - a["value"]) / dt_h
            (heating if rate > 0.5 else cooling).append(rate)

        def summary(values):
            if not values:
                return None
            ordered = sorted(values)
            return {
                "samples": len(values),
                "mean_delta_c_per_h": sum(values)/len(values),
                "median_delta_c_per_h": ordered[len(ordered)//2],
            }

        fit = {"cooling": summary(cooling), "heating_events": summary(heating)}
        try:
            model = self.models.get("thermal-baseline")
        except ValueError:
            return {"fitted": False, "reason": "thermal-baseline model missing"}
        model.metadata["dhw_fit"] = fit
        model.metadata["last_fit_at"] = datetime.now().astimezone().isoformat()
        self.historian.save_model(model)
        return {"fitted": True, "dhw": fit}


    def fit_pv_orientation_baseline(self) -> dict:
        """Learn per-input and per-orientation PV yield from commissioned Site metadata."""
        status = self.baseline_status()
        if status["duration_hours"] < 6:
            return {"fitted": False, "reason": status["reason"]}
        try:
            model = self.models.get("pv-orientation-baseline")
        except ValueError:
            return {"fitted": False, "reason": "pv-orientation-baseline model missing"}

        orientations = model.metadata.get("pv_orientations") or {}
        if not orientations:
            return {"fitted": False, "reason": "No commissioned PV input orientations."}

        input_capacity = {}
        for orientation, meta in orientations.items():
            inputs = meta.get("inputs") or []
            total_capacity = float(meta.get("capacity_kwp") or 0.0)
            # Capacity per input is recovered from model dependencies only when
            # there is one input; multi-input orientation capacity remains an
            # aggregate until explicit per-input capacities are stored below.
            if len(inputs) == 1:
                input_capacity[inputs[0]] = total_capacity

        # Explicit per-input capacities are stored in model metadata on first fit
        # by matching commissioned dependency metadata when available.
        commissioned_inputs = model.metadata.get("commissioned_inputs") or {}
        for cid, meta in commissioned_inputs.items():
            if meta.get("capacity_kwp"):
                input_capacity[cid] = float(meta["capacity_kwp"])

        input_fit = {}
        orientation_fit = {}
        for orientation, meta in orientations.items():
            per_input_rows = {}
            orientation_energy_wh = 0.0
            orientation_capacity = float(meta.get("capacity_kwp") or 0.0)
            for component_id in meta.get("inputs") or []:
                rows = self.historian.numeric_series(
                    self.site_id, component_id, "pv.generation_power", limit=50000
                )
                per_input_rows[component_id] = rows
                values = [max(0.0, r["value"]) for r in rows]
                energy_wh = 0.0
                for a, b in zip(rows, rows[1:]):
                    ta = datetime.fromisoformat(a["observed_at"])
                    tb = datetime.fromisoformat(b["observed_at"])
                    dt_h = (tb - ta).total_seconds() / 3600.0
                    if 0 < dt_h <= 0.1:
                        energy_wh += ((max(0.0, a["value"]) + max(0.0, b["value"])) / 2.0) * dt_h
                cap = input_capacity.get(component_id)
                input_fit[component_id] = {
                    "samples": len(values),
                    "maximum_w": max(values) if values else None,
                    "mean_w": (sum(values) / len(values)) if values else None,
                    "energy_wh_observed": energy_wh,
                    "maximum_w_per_kwp": (max(values) / cap) if values and cap else None,
                }
                orientation_energy_wh += energy_wh

            # Synchronize inputs in one-minute buckets before summing an orientation.
            buckets = {}
            for component_id, rows in per_input_rows.items():
                for row in rows:
                    ts = datetime.fromisoformat(row["observed_at"])
                    key = ts.replace(second=0, microsecond=0).isoformat()
                    buckets.setdefault(key, {})[component_id] = max(0.0, row["value"])
            required = set(per_input_rows)
            summed = [
                sum(values.values()) for values in buckets.values()
                if required and required.issubset(values)
            ]
            orientation_fit[orientation] = {
                "inputs": list(meta.get("inputs") or []),
                "capacity_kwp": orientation_capacity,
                "synchronized_samples": len(summed),
                "maximum_w": max(summed) if summed else None,
                "mean_w": (sum(summed) / len(summed)) if summed else None,
                "maximum_w_per_kwp": (
                    max(summed) / orientation_capacity
                    if summed and orientation_capacity > 0 else None
                ),
                "energy_wh_observed": orientation_energy_wh,
                "energy_wh_per_kwp": (
                    orientation_energy_wh / orientation_capacity
                    if orientation_capacity > 0 else None
                ),
            }

        model.metadata["phase"] = "PV_ORIENTATION_BASELINE"
        model.metadata["input_fit"] = input_fit
        model.metadata["orientation_fit"] = orientation_fit
        model.metadata["last_fit_at"] = datetime.now().astimezone().isoformat()
        model.reason = "Passive PV orientation baseline from GOOD input telemetry; no control authority."
        self.historian.save_model(model)
        return {"fitted": True, "orientations": orientation_fit, "inputs": input_fit}


    def fit_electrical_baseline(self) -> dict:
        status = self.baseline_status()
        if status["duration_hours"] < 6:
            return {"fitted": False, "reason": status["reason"]}
        points_by_kind = {
            "PV": ["pv.generation_power"],
            "PV_INVERTER": ["pv.generation_power", "power.electrical"],
            "PV_INPUT": ["pv.generation_power"],
            "GRID": ["grid.import_power", "grid.export_power"],
            "GRID_METER": ["grid.import_power", "grid.export_power"],
            "ELECTRIC_METER": ["grid.import_power", "grid.export_power"],
            "BATTERY": ["battery.soc", "battery.charge_power", "battery.discharge_power"],
        }
        fit = {}
        for component, kind in self.component_kinds.items():
            for point in points_by_kind.get(kind, []):
                rows = self.historian.numeric_series(self.site_id, component, point, limit=50000)
                values = [r["value"] for r in rows]
                if values:
                    fit[f"{component}.{point}"] = {
                        "component": component, "kind": kind, "point": point,
                        "samples": len(values), "minimum": min(values),
                        "maximum": max(values), "mean": sum(values) / len(values),
                    }
        try:
            model = self.models.get("electrical-baseline")
        except ValueError:
            return {"fitted": False, "reason": "electrical-baseline model missing"}
        model.metadata["phase"] = "ELECTRICAL_BASELINE"
        model.metadata["electrical_fit"] = fit
        model.metadata.pop("fit", None)
        model.metadata["last_fit_at"] = datetime.now().astimezone().isoformat()
        model.reason = "Passive SiteGraph-based electrical baseline; no control authority."
        self.historian.save_model(model)
        return {"fitted": True, "fit": fit}


    def fit_battery_behavior_baseline(self) -> dict:
        """Learn vendor-neutral battery behavior split into charge/discharge/idle states."""
        status = self.baseline_status()
        if status["duration_hours"] < 6:
            return {"fitted": False, "reason": status["reason"]}

        def stats(rows):
            values = [x["value"] for x in rows]
            return {"samples": len(values), "minimum": min(values) if values else None,
                    "maximum": max(values) if values else None,
                    "mean": (sum(values) / len(values)) if values else None}

        def integrate_wh(rows):
            total = 0.0
            for a, b in zip(rows, rows[1:]):
                ta, tb = datetime.fromisoformat(a["observed_at"]), datetime.fromisoformat(b["observed_at"])
                dt_h = (tb - ta).total_seconds() / 3600.0
                if 0 < dt_h <= 0.1:
                    total += ((max(0.0, a["value"]) + max(0.0, b["value"])) / 2.0) * dt_h
            return total

        def nearest(rows, ts, max_age_s=45):
            if not rows:
                return None
            best = min(rows, key=lambda r: abs((datetime.fromisoformat(r["observed_at"]) - ts).total_seconds()))
            age = abs((datetime.fromisoformat(best["observed_at"]) - ts).total_seconds())
            return best if age <= max_age_s else None

        per_battery = {}
        for battery, kind in self.component_kinds.items():
            if kind != "BATTERY":
                continue
            soc = self.historian.numeric_series(self.site_id, battery, "battery.soc", limit=50000)
            charge = self.historian.numeric_series(self.site_id, battery, "battery.charge_power", limit=50000)
            discharge = self.historian.numeric_series(self.site_id, battery, "battery.discharge_power", limit=50000)
            voltage = self.historian.numeric_series(self.site_id, battery, "electrical.voltage_dc", limit=50000)
            current = self.historian.numeric_series(self.site_id, battery, "electrical.current_dc", limit=50000)

            state_samples = {"CHARGING": [], "DISCHARGING": [], "IDLE": []}
            soc_rates = {"CHARGING": [], "DISCHARGING": [], "IDLE": []}
            threshold_w = 100.0
            classified = []
            for row in soc:
                ts = datetime.fromisoformat(row["observed_at"])
                ch = nearest(charge, ts)
                dis = nearest(discharge, ts)
                ch_w = max(0.0, ch["value"]) if ch else 0.0
                dis_w = max(0.0, dis["value"]) if dis else 0.0
                state = "CHARGING" if ch_w > threshold_w and ch_w >= dis_w else ("DISCHARGING" if dis_w > threshold_w else "IDLE")
                sample = {"state": state, "soc": row["value"], "power_w": max(ch_w, dis_w), "observed_at": row["observed_at"]}
                classified.append(sample)
                state_samples[state].append(sample)

            # Rates are valid only across adjacent original SOC observations that
            # remain in the same state. A CHARGING/DISCHARGING transition must
            # never be bridged merely because filtered samples share a label.
            for a, b in zip(classified, classified[1:]):
                if a["state"] != b["state"]:
                    continue
                ta, tb = datetime.fromisoformat(a["observed_at"]), datetime.fromisoformat(b["observed_at"])
                dt_h = (tb - ta).total_seconds() / 3600.0
                if 0 < dt_h <= 0.25:
                    soc_rates[a["state"]].append((b["soc"] - a["soc"]) / dt_h)

            states = {}
            for state, rows in state_samples.items():
                powers = [x["power_w"] for x in rows]
                rates = soc_rates[state]
                states[state] = {
                    "samples": len(rows),
                    "mean_power_w": (sum(powers) / len(powers)) if powers else None,
                    "max_power_w": max(powers) if powers else None,
                    "mean_soc_rate_pct_per_h": (sum(rates) / len(rates)) if rates else None,
                    "rate_samples": len(rates),
                }

            fit = {
                "soc": stats(soc), "voltage_dc": stats(voltage), "current_dc": stats(current),
                "charge_power": stats(charge), "discharge_power": stats(discharge),
                "observed_charge_wh": integrate_wh(charge), "observed_discharge_wh": integrate_wh(discharge),
                "states": states, "state_threshold_w": threshold_w,
            }
            if soc:
                fit["observed_soc_span_pct"] = max(x["value"] for x in soc) - min(x["value"] for x in soc)
            if any(v["samples"] for v in (fit["soc"], fit["charge_power"], fit["discharge_power"])):
                per_battery[battery] = fit

        try:
            model = self.models.get("battery-baseline")
        except ValueError:
            return {"fitted": False, "reason": "battery-baseline model missing"}
        model.metadata["phase"] = "BATTERY_BEHAVIOR_V2_1"
        model.metadata["battery_fit"] = per_battery
        model.metadata["last_fit_at"] = datetime.now().astimezone().isoformat()
        model.reason = "Passive battery behavior V2.1 using contiguous charging, discharging and idle sequences; no control authority."
        self.historian.save_model(model)
        return {"fitted": True, "fit": per_battery}


    def summary(self) -> dict:
        """Stable, transport-safe diagnostic projection of local learning state."""
        baseline = self.baseline_status()
        models = []
        for model in self.models.all():
            md = model.metadata or {}
            item = {
                "id": model.id,
                "version": model.version,
                "capability": model.capability,
                "status": model.status.value if hasattr(model.status, "value") else str(model.status),
                "phase": md.get("phase"),
                "last_fit_at": md.get("last_fit_at"),
                "reason": model.reason,
                "commissioning_status": md.get("commissioning_status"),
            }
            if model.id == "thermal-baseline":
                item["thermal_context"] = md.get("thermal_context_fit") or {}
                item["dhw"] = md.get("dhw_fit") or {}
                contexts = item["thermal_context"]
                item["evidence_gaps"] = [
                    name for name in ("PASSIVE_COOLING", "PELLET_HEATING", "POWER_TO_HEAT")
                    if name not in contexts
                ]
            elif model.id == "battery-baseline":
                item["battery"] = md.get("battery_fit") or md.get("fit") or {}
            elif model.id == "electrical-baseline":
                item["electrical"] = md.get("electrical_fit") or md.get("fit") or {}
            elif model.id == "pv-orientation-baseline":
                item["orientations"] = md.get("orientation_fit") or {}
                item["inputs"] = md.get("input_fit") or {}
                item["commissioned_inputs"] = md.get("commissioned_inputs") or {}
            models.append(item)
        return {
            "site_id": self.site_id,
            "generated_at": datetime.now().astimezone().isoformat(),
            "history": {
                "duration_hours": baseline["duration_hours"],
                "samples": baseline["samples"],
                "signals": baseline["signals"],
                "first_observed_at": baseline["first_observed_at"],
                "last_observed_at": baseline["last_observed_at"],
            },
            "phase": baseline["phase"],
            "models": models,
        }

    def register_model(
        self,
        model: LearningModelRecord,
        policy: ReadinessPolicy,
    ) -> None:
        self.models.register(model)
        self.policies[model.id] = policy
        self.historian.save_model(model, asdict(policy))

    def ingest_outcome(self, result, context_bucket: str | None = None) -> ReadinessAssessment | None:
        if not result.model_id or not result.model_version:
            return None

        self.historian.record_model_evidence(
            self.site_id,
            result.model_id,
            result.model_version,
            result.correlation_id,
            result.status,
            result.residual,
            context_bucket,
        )
        return self.reassess(result.model_id)

    def reassess(self, model_id: str) -> ReadinessAssessment:
        model = self.models.get(model_id)
        policy = self.policies.get(model_id)
        if policy is None:
            raise ValueError(f"MODEL_READINESS_POLICY_MISSING:{model_id}")

        rows = self.historian.model_evidence(
            self.site_id, model.id, model.version
        )
        evidence = [
            OutcomeEvidence(
                status=row["status"],
                residual=row["residual"],
                context_bucket=row["context_bucket"],
            )
            for row in rows
        ]
        assessment = assess_readiness(evidence, policy)

        previous = model.status
        if previous != ModelStatus.INVALIDATED:
            if assessment.status == ModelStatus.READY:
                self.models.set_status(
                    model_id, ModelStatus.READY,
                    "Readiness policy satisfied by persisted outcome evidence.",
                )
            elif previous == ModelStatus.READY:
                self.models.set_status(
                    model_id, ModelStatus.DEGRADED,
                    "; ".join(assessment.reasons) or "Readiness degraded.",
                )
                self.autonomy.degrade_for_model(
                    model_id,
                    f"Model {model_id} readiness degraded.",
                )
            else:
                self.models.set_status(
                    model_id, ModelStatus.LEARNING,
                    "; ".join(assessment.reasons) or "More evidence required.",
                )

        self.historian.save_model(
            self.models.get(model_id), asdict(policy)
        )
        self.historian.record_event(
            self.site_id,
            "learning.readiness_assessed",
            {
                "model_id": model_id,
                "model_version": model.version,
                "previous_status": str(previous),
                "new_status": str(self.models.get(model_id).status),
                "observed": assessment.observed,
                "unobservable": assessment.unobservable,
                "mae": assessment.mae,
                "rmse": assessment.rmse,
                "context_buckets": assessment.context_buckets,
                "reasons": assessment.reasons,
            },
        )
        return assessment

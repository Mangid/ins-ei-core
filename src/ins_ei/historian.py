from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Iterable

from ins_ei.models import Point


class Historian:
    """Persistent local INS-EI history store.

    SQLite is the V0.1 edge-store: transactional, dependency-free and easy to
    back up/export. Server synchronization can be layered above this contract.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._init_schema()

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_schema(self) -> None:
        with self._connection() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observed_at TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                site_id TEXT NOT NULL,
                component_id TEXT NOT NULL,
                point TEXT NOT NULL,
                value_json TEXT NOT NULL,
                unit TEXT,
                quality TEXT NOT NULL,
                plugin_instance TEXT,
                context_version TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_observations_lookup
              ON observations(site_id, component_id, point, observed_at);

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                occurred_at TEXT NOT NULL,
                site_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                correlation_id TEXT,
                payload_json TEXT NOT NULL,
                context_version TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_correlation
              ON events(site_id, correlation_id, occurred_at);

            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decided_at TEXT NOT NULL,
                site_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                action TEXT NOT NULL,
                strategy TEXT NOT NULL,
                priority TEXT NOT NULL,
                confidence TEXT NOT NULL,
                reason TEXT NOT NULL,
                intents_json TEXT NOT NULL,
                considered_json TEXT NOT NULL,
                context_version TEXT
            );

            CREATE TABLE IF NOT EXISTS learning_models (
                model_id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                capability TEXT NOT NULL,
                status TEXT NOT NULL,
                dependencies_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL,
                status_changed_at TEXT NOT NULL,
                readiness_policy_json TEXT
            );

            CREATE TABLE IF NOT EXISTS model_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                occurred_at TEXT NOT NULL,
                site_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                status TEXT NOT NULL,
                residual REAL,
                context_bucket TEXT,
                UNIQUE(model_id, model_version, correlation_id)
            );
            CREATE INDEX IF NOT EXISTS idx_model_evidence
              ON model_evidence(site_id, model_id, model_version, occurred_at);

            CREATE TABLE IF NOT EXISTS forecast_snapshots (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                site_id TEXT NOT NULL,\n                series TEXT NOT NULL,\n                target_start TEXT NOT NULL,\n                generated_at TEXT NOT NULL,\n                forecast_value REAL NOT NULL,\n                model TEXT,\n                quality TEXT\n            );\n            CREATE INDEX IF NOT EXISTS idx_forecast_snapshots_target ON forecast_snapshots(site_id,series,target_start,generated_at);\n\n            CREATE TABLE IF NOT EXISTS runtime_cache (\n                cache_key TEXT PRIMARY KEY,\n                updated_at TEXT NOT NULL,\n                payload_json TEXT NOT NULL\n            );\n\n            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                occurred_at TEXT NOT NULL,
                site_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                target TEXT NOT NULL,
                command TEXT NOT NULL,
                plugin_instance TEXT,
                parameters_json TEXT NOT NULL,
                status TEXT NOT NULL,
                result_json TEXT,
                error TEXT,
                context_version TEXT
            );
            """)

    @staticmethod
    def new_correlation_id() -> str:
        return uuid.uuid4().hex

    def record_points(
        self,
        site_id: str,
        points: Iterable[Point],
        context_version: str | None = None,
    ) -> None:
        recorded_at = datetime.now().astimezone().isoformat()
        rows = [
            (
                p.observed_at.isoformat(), recorded_at, site_id, p.component_id,
                p.point, json.dumps(p.value, ensure_ascii=False, default=str),
                p.unit, str(p.quality), p.source.plugin_instance, context_version,
            )
            for p in points
        ]
        if not rows:
            return
        with self._lock, self._connection() as db:
            db.executemany("""
                INSERT INTO observations(
                    observed_at, recorded_at, site_id, component_id, point,
                    value_json, unit, quality, plugin_instance, context_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)

    def record_event(
        self,
        site_id: str,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        context_version: str | None = None,
    ) -> None:
        with self._lock, self._connection() as db:
            db.execute("""
                INSERT INTO events(
                    occurred_at, site_id, event_type, correlation_id,
                    payload_json, context_version
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().astimezone().isoformat(), site_id, event_type,
                correlation_id, json.dumps(payload, ensure_ascii=False, default=str),
                context_version,
            ))

    def record_decision(
        self,
        site_id: str,
        decision,
        correlation_id: str,
        context_version: str | None = None,
    ) -> None:
        intents = [
            {"target": i.target, "command": i.command, "parameters": i.parameters}
            for i in decision.intents
        ]
        considered = [
            {
                "strategy": p.strategy, "action": p.action,
                "priority": p.priority.name, "confidence": str(p.confidence),
                "reason": p.reason, "evidence": p.evidence,
            }
            for p in decision.considered
        ]
        with self._lock, self._connection() as db:
            db.execute("""
                INSERT INTO decisions(
                    decided_at, site_id, correlation_id, action, strategy,
                    priority, confidence, reason, intents_json,
                    considered_json, context_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.decided_at.isoformat(), site_id, correlation_id,
                decision.action, decision.winning_strategy, decision.priority.name,
                str(decision.confidence), decision.reason,
                json.dumps(intents, ensure_ascii=False, default=str),
                json.dumps(considered, ensure_ascii=False, default=str),
                context_version,
            ))

    def record_command(
        self,
        site_id: str,
        correlation_id: str,
        target: str,
        command: str,
        parameters: dict[str, Any],
        status: str,
        plugin_instance: str | None = None,
        result: Any = None,
        error: str | None = None,
        context_version: str | None = None,
    ) -> None:
        with self._lock, self._connection() as db:
            db.execute("""
                INSERT INTO commands(
                    occurred_at, site_id, correlation_id, target, command,
                    plugin_instance, parameters_json, status, result_json,
                    error, context_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().astimezone().isoformat(), site_id, correlation_id,
                target, command, plugin_instance,
                json.dumps(parameters, ensure_ascii=False, default=str), status,
                json.dumps(result, ensure_ascii=False, default=str)
                if result is not None else None,
                error, context_version,
            ))




    def series(self, site_id: str, component_id: str, point: str, limit: int = 10000) -> list[dict[str, Any]]:
        """Return GOOD observations of any JSON scalar type in chronological order."""
        with self._connection() as db:
            rows = db.execute("""
                SELECT observed_at, value_json, unit, quality, plugin_instance
                FROM observations
                WHERE site_id=? AND component_id=? AND point=?
                  AND quality IN ('GOOD','Quality.GOOD')
                ORDER BY observed_at DESC LIMIT ?
            """, (site_id, component_id, point, int(limit))).fetchall()
        result = []
        for row in reversed(rows):
            try:
                value = json.loads(row["value_json"])
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            result.append({"observed_at": row["observed_at"], "value": value,
                           "unit": row["unit"], "plugin_instance": row["plugin_instance"]})
        return result

    def numeric_series(self, site_id: str, component_id: str, point: str, limit: int = 10000) -> list[dict[str, Any]]:
        """Return GOOD numeric observations in chronological order."""
        with self._connection() as db:
            rows = db.execute("""
                SELECT observed_at, value_json, unit, quality, plugin_instance
                FROM observations
                WHERE site_id=? AND component_id=? AND point=?
                  AND quality IN ('GOOD','Quality.GOOD')
                ORDER BY observed_at DESC LIMIT ?
            """, (site_id, component_id, point, int(limit))).fetchall()
        result = []
        for row in reversed(rows):
            try:
                value = json.loads(row["value_json"])
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    continue
                result.append({
                    "observed_at": row["observed_at"],
                    "value": float(value),
                    "unit": row["unit"],
                    "plugin_instance": row["plugin_instance"],
                })
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return result

    def observation_coverage(self, site_id: str) -> list[dict[str, Any]]:
        """Summarize persisted observation coverage per canonical signal."""
        with self._connection() as db:
            rows = db.execute("""
                SELECT component_id, point, unit,
                       COUNT(*) AS samples,
                       MIN(observed_at) AS first_observed_at,
                       MAX(observed_at) AS last_observed_at,
                       SUM(CASE WHEN quality IN ('GOOD','Quality.GOOD') THEN 1 ELSE 0 END) AS good_samples,
                       COUNT(DISTINCT plugin_instance) AS providers
                FROM observations
                WHERE site_id=?
                GROUP BY component_id, point, unit
                ORDER BY component_id, point
            """, (site_id,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            samples = int(item["samples"] or 0)
            good = int(item["good_samples"] or 0)
            item["good_ratio"] = (good / samples) if samples else 0.0
            if item["first_observed_at"] and item["last_observed_at"]:
                first = datetime.fromisoformat(item["first_observed_at"])
                last = datetime.fromisoformat(item["last_observed_at"])
                item["duration_seconds"] = max(0.0, (last - first).total_seconds())
            else:
                item["duration_seconds"] = 0.0
            result.append(item)
        return result

    def observation_summary(self, site_id: str) -> dict[str, Any]:
        coverage = self.observation_coverage(site_id)
        samples = sum(int(x["samples"]) for x in coverage)
        first_values = [x["first_observed_at"] for x in coverage if x["first_observed_at"]]
        last_values = [x["last_observed_at"] for x in coverage if x["last_observed_at"]]
        first = min(first_values) if first_values else None
        last = max(last_values) if last_values else None
        duration = 0.0
        if first and last:
            duration = max(0.0, (datetime.fromisoformat(last) - datetime.fromisoformat(first)).total_seconds())
        return {
            "signals": len(coverage),
            "samples": samples,
            "first_observed_at": first,
            "last_observed_at": last,
            "duration_seconds": duration,
            "coverage": coverage,
        }

    def save_model(self, model, readiness_policy: dict[str, Any] | None = None) -> None:
        dependencies = [
            {"kind": d.kind, "id": d.id, "version": d.version}
            for d in model.dependencies
        ]
        with self._lock, self._connection() as db:
            db.execute("""
                INSERT INTO learning_models(
                    model_id, version, capability, status, dependencies_json,
                    metadata_json, reason, created_at, status_changed_at,
                    readiness_policy_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_id) DO UPDATE SET
                    version=excluded.version,
                    capability=excluded.capability,
                    status=excluded.status,
                    dependencies_json=excluded.dependencies_json,
                    metadata_json=excluded.metadata_json,
                    reason=excluded.reason,
                    status_changed_at=excluded.status_changed_at,
                    readiness_policy_json=excluded.readiness_policy_json
            """, (
                model.id, model.version, model.capability, str(model.status),
                json.dumps(dependencies, ensure_ascii=False),
                json.dumps(model.metadata, ensure_ascii=False, default=str),
                model.reason, model.created_at.isoformat(),
                model.status_changed_at.isoformat(),
                json.dumps(readiness_policy, ensure_ascii=False)
                if readiness_policy is not None else None,
            ))

    def load_models(self) -> list[dict[str, Any]]:
        with self._connection() as db:
            rows = db.execute("SELECT * FROM learning_models ORDER BY model_id").fetchall()
        return [dict(row) for row in rows]

    def record_model_evidence(
        self, site_id: str, model_id: str, model_version: str,
        correlation_id: str, status: str, residual: float | None,
        context_bucket: str | None = None,
    ) -> None:
        with self._lock, self._connection() as db:
            db.execute("""
                INSERT OR REPLACE INTO model_evidence(
                    occurred_at, site_id, model_id, model_version,
                    correlation_id, status, residual, context_bucket
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().astimezone().isoformat(), site_id, model_id,
                model_version, correlation_id, status, residual, context_bucket,
            ))

    def model_evidence(self, site_id: str, model_id: str, model_version: str) -> list[dict[str, Any]]:
        with self._connection() as db:
            rows = db.execute("""
                SELECT * FROM model_evidence
                WHERE site_id=? AND model_id=? AND model_version=?
                ORDER BY occurred_at
            """, (site_id, model_id, model_version)).fetchall()
        return [dict(row) for row in rows]

    def record_forecast_slots(self, site_id: str, series: str, slots: Iterable[Any]) -> None:
        rows=[(site_id,series,s.start.isoformat(),(s.generated_at or datetime.now().astimezone()).isoformat(),float(s.value),s.source,str(s.quality)) for s in slots]
        if not rows:return
        with self._lock,self._connection() as db:
            db.executemany("""INSERT INTO forecast_snapshots(site_id,series,target_start,generated_at,forecast_value,model,quality)
                VALUES(?,?,?,?,?,?,?)""",rows)

    def forecast_snapshots(self, site_id: str, series: str, since: datetime) -> list[dict[str,Any]]:
        with self._connection() as db:
            rows=db.execute("""SELECT * FROM forecast_snapshots WHERE site_id=? AND series=? AND target_start>=?
                ORDER BY target_start,generated_at""",(site_id,series,since.isoformat())).fetchall()
        return [dict(r) for r in rows]

    def cache_put(self, key: str, payload: dict[str, Any]) -> None:
        with self._lock, self._connection() as db:
            db.execute("""INSERT INTO runtime_cache(cache_key,updated_at,payload_json)
                VALUES(?,?,?) ON CONFLICT(cache_key) DO UPDATE SET
                updated_at=excluded.updated_at,payload_json=excluded.payload_json""",
                (key, datetime.now().astimezone().isoformat(), json.dumps(payload,ensure_ascii=False,default=str)))

    def cache_get(self, key: str) -> dict[str, Any] | None:
        with self._connection() as db:
            row=db.execute("SELECT updated_at,payload_json FROM runtime_cache WHERE cache_key=?",(key,)).fetchone()
        if not row:return None
        payload=json.loads(row["payload_json"]);payload["_cached_at"]=row["updated_at"];return payload

    def correlation(self, site_id: str, correlation_id: str) -> dict[str, Any]:
        with self._connection() as db:
            decision = db.execute(
                "SELECT * FROM decisions WHERE site_id=? AND correlation_id=? ORDER BY id DESC LIMIT 1",
                (site_id, correlation_id),
            ).fetchone()
            commands = db.execute(
                "SELECT * FROM commands WHERE site_id=? AND correlation_id=? ORDER BY id",
                (site_id, correlation_id),
            ).fetchall()
            events = db.execute(
                "SELECT * FROM events WHERE site_id=? AND correlation_id=? ORDER BY id",
                (site_id, correlation_id),
            ).fetchall()
        return {
            "decision": dict(decision) if decision else None,
            "commands": [dict(row) for row in commands],
            "events": [dict(row) for row in events],
        }


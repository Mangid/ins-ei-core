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

            CREATE TABLE IF NOT EXISTS commands (
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

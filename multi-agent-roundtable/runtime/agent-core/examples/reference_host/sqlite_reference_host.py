"""SQLite-backed reference host ports.

This module is an executable example, not a production persistence layer. It
shows how a host can implement the core ports with durable tables, transactions,
idempotent event appends, and continuation parent linkage without importing any
private SDK internals.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from rd_agent_contracts import (
    AgentEvent,
    AgentKind,
    ContinuationJobRecord,
    ContinuationJobSpec,
    ContinuationJobStatus,
    EventDraft,
    RunBudget,
    RunCompletion,
    RunFailure,
    RunRecord,
    RunResultMetadata,
    RunScope,
    RunStatus,
)


def connect_sqlite_reference_host(
    database_path: str | Path = ":memory:",
) -> SQLiteReferenceHost:
    connection = sqlite3.connect(str(database_path))
    connection.row_factory = sqlite3.Row
    event_log = SQLiteEventLog(connection)
    persistence = SQLiteRunPersistence(connection)
    continuation_queue = SQLiteContinuationQueue(connection)
    return SQLiteReferenceHost(
        connection=connection,
        event_log=event_log,
        persistence=persistence,
        continuation_queue=continuation_queue,
    )


@dataclass
class SQLiteReferenceHost:
    connection: sqlite3.Connection
    event_log: SQLiteEventLog
    persistence: SQLiteRunPersistence
    continuation_queue: SQLiteContinuationQueue

    def close(self) -> None:
        self.connection.close()


class SQLiteEventLog:
    """SQLite ``EventLogPort`` implementation with per-run idempotency."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.row_factory = sqlite3.Row
        self._create_schema()

    def append_event(
        self,
        run_id: str,
        draft: EventDraft,
        *,
        idempotency_key: str | None = None,
    ) -> AgentEvent:
        with self._connection:
            if idempotency_key is not None:
                existing = self._connection.execute(
                    """
                    SELECT e.*
                    FROM reference_event_idempotency i
                    JOIN reference_events e
                      ON e.run_id = i.run_id AND e.seq = i.seq
                    WHERE i.run_id = ? AND i.idempotency_key = ?
                    """,
                    (run_id, idempotency_key),
                ).fetchone()
                if existing is not None:
                    return _event_from_row(existing)

            next_seq = int(
                self._connection.execute(
                    "SELECT COALESCE(MAX(seq), 0) + 1 FROM reference_events WHERE run_id = ?",
                    (run_id,),
                ).fetchone()[0]
            )
            timestamp_ms = draft.timestamp_ms if draft.timestamp_ms is not None else _now_ms()
            self._connection.execute(
                """
                INSERT INTO reference_events (
                    run_id, seq, timestamp_ms, turn_id, event_type, payload_json,
                    schema_version, message_id, action_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    next_seq,
                    timestamp_ms,
                    draft.turn_id,
                    draft.event_type,
                    json.dumps(draft.payload, ensure_ascii=False, sort_keys=True),
                    draft.schema_version,
                    draft.message_id,
                    draft.action_id,
                ),
            )
            if idempotency_key is not None:
                self._connection.execute(
                    """
                    INSERT INTO reference_event_idempotency (run_id, idempotency_key, seq)
                    VALUES (?, ?, ?)
                    """,
                    (run_id, idempotency_key, next_seq),
                )

        return AgentEvent(
            run_id=run_id,
            seq=next_seq,
            timestamp_ms=timestamp_ms,
            turn_id=draft.turn_id,
            event_type=draft.event_type,
            payload=dict(draft.payload),
            schema_version=draft.schema_version,
            message_id=draft.message_id,
            action_id=draft.action_id,
        )

    def stream_events(
        self,
        run_id: str,
        *,
        from_seq: int = 0,
        limit: int | None = None,
    ) -> Iterable[AgentEvent]:
        query = """
            SELECT *
            FROM reference_events
            WHERE run_id = ? AND seq > ?
            ORDER BY seq ASC
        """
        params: tuple[Any, ...]
        if limit is not None:
            query += " LIMIT ?"
            params = (run_id, from_seq, limit)
        else:
            params = (run_id, from_seq)
        rows = self._connection.execute(query, params).fetchall()
        return tuple(_event_from_row(row) for row in rows)

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reference_events (
                    run_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    timestamp_ms INTEGER NOT NULL,
                    turn_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    message_id TEXT,
                    action_id TEXT,
                    PRIMARY KEY (run_id, seq)
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reference_event_idempotency (
                    run_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    PRIMARY KEY (run_id, idempotency_key),
                    FOREIGN KEY (run_id, seq)
                      REFERENCES reference_events (run_id, seq)
                )
                """
            )


class SQLiteRunPersistence:
    """SQLite ``RunPersistencePort`` implementation for host integration tests."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.row_factory = sqlite3.Row
        self._create_schema()

    def create_root_run(
        self,
        *,
        scope: RunScope,
        budget: RunBudget,
        max_continuations: int = 0,
        run_id: str | None = None,
    ) -> RunRecord:
        return self._create_run(
            scope=scope,
            budget=budget,
            max_continuations=max_continuations,
            continuation_index=0,
            engine_state_json=None,
            run_id=run_id,
        )

    def create_subagent_run(
        self,
        *,
        scope: RunScope,
        budget: RunBudget,
        max_continuations: int = 0,
        run_id: str | None = None,
    ) -> RunRecord:
        return self._create_run(
            scope=scope,
            budget=budget,
            max_continuations=max_continuations,
            continuation_index=0,
            engine_state_json=None,
            run_id=run_id,
        )

    def create_continuation_run(
        self,
        *,
        previous_run_id: str,
        engine_state_json: str,
        run_id: str | None = None,
    ) -> RunRecord | None:
        previous = self.load_run(previous_run_id)
        if previous is None:
            return None
        next_continuation = previous.continuation_index + 1
        if next_continuation > previous.max_continuations:
            return None
        return self._create_run(
            scope=replace(previous.scope, parent_run_id=previous.run_id),
            budget=previous.budget,
            max_continuations=previous.max_continuations,
            continuation_index=next_continuation,
            engine_state_json=engine_state_json,
            run_id=run_id,
        )

    def mark_running(
        self,
        run_id: str,
        *,
        started_at_ms: int | None = None,
    ) -> RunRecord | None:
        return self._update(
            run_id,
            status=RunStatus.RUNNING.value,
            started_at_ms=started_at_ms if started_at_ms is not None else _now_ms(),
        )

    def mark_completed(
        self,
        run_id: str,
        *,
        completion: RunCompletion,
    ) -> RunRecord | None:
        return self._update(
            run_id,
            status=RunStatus.COMPLETED.value,
            stop_reason=completion.stop_reason,
            result_metadata=completion.metadata,
            engine_state_json=completion.engine_state_json,
            completed_at_ms=(
                completion.completed_at_ms
                if completion.completed_at_ms is not None
                else _now_ms()
            ),
        )

    def mark_failed(
        self,
        run_id: str,
        *,
        failure: RunFailure,
    ) -> RunRecord | None:
        return self._update(
            run_id,
            status=RunStatus.FAILED.value,
            error_message=failure.error_message,
            completed_at_ms=(
                failure.completed_at_ms
                if failure.completed_at_ms is not None
                else _now_ms()
            ),
        )

    def mark_resumed(self, run_id: str) -> RunRecord | None:
        return self._update(run_id, status=RunStatus.RESUMED.value)

    def mark_waiting_user(self, run_id: str) -> RunRecord | None:
        """Reference-host convenience used to demonstrate resume claiming."""

        return self._update(run_id, status=RunStatus.WAITING_USER.value)

    def claim_latest_waiting_orchestrator_run(
        self,
        *,
        project_id: str,
    ) -> RunRecord | None:
        rows = self._connection.execute(
            """
            SELECT *
            FROM reference_runs
            WHERE status = ?
            ORDER BY created_at_ms DESC, run_index DESC
            """,
            (RunStatus.WAITING_USER.value,),
        ).fetchall()
        for row in rows:
            record = _run_from_row(row)
            if (
                record.scope.project_id == project_id
                and record.scope.agent_kind == AgentKind.ORCHESTRATOR
            ):
                return self._update(record.run_id, status=RunStatus.RESUMING.value)
        return None

    def load_run(self, run_id: str) -> RunRecord | None:
        row = self._connection.execute(
            "SELECT * FROM reference_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return _run_from_row(row) if row is not None else None

    def load_run_with_parent(
        self,
        run_id: str,
    ) -> tuple[RunRecord, RunRecord | None] | None:
        record = self.load_run(run_id)
        if record is None:
            return None
        parent = (
            self.load_run(record.scope.parent_run_id)
            if record.scope.parent_run_id
            else None
        )
        return record, parent

    def _create_run(
        self,
        *,
        scope: RunScope,
        budget: RunBudget | None,
        max_continuations: int,
        continuation_index: int,
        engine_state_json: str | None,
        run_id: str | None,
    ) -> RunRecord:
        if max_continuations < 0:
            raise ValueError("max_continuations must be >= 0")
        resolved_run_id = run_id or f"run-{uuid.uuid4()}"
        if self.load_run(resolved_run_id) is not None:
            raise ValueError(f"run_id already exists: {resolved_run_id}")
        record = RunRecord(
            run_id=resolved_run_id,
            scope=scope,
            status=RunStatus.PENDING.value,
            run_index=0,
            continuation_index=continuation_index,
            max_continuations=max_continuations,
            budget=budget,
            engine_state_json=engine_state_json,
            created_at_ms=_now_ms(),
        )
        with self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO reference_runs (
                    run_id, scope_json, status, continuation_index,
                    max_continuations, budget_json, stop_reason, error_message,
                    result_metadata_json, engine_state_json, created_at_ms,
                    started_at_ms, completed_at_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _run_insert_params(record),
            )
            run_index = int(cursor.lastrowid)
            self._connection.execute(
                "UPDATE reference_runs SET run_index = ? WHERE run_id = ?",
                (run_index, resolved_run_id),
            )
        loaded = self.load_run(resolved_run_id)
        if loaded is None:
            raise RuntimeError(f"created run disappeared: {resolved_run_id}")
        return loaded

    def _update(self, run_id: str, **changes: Any) -> RunRecord | None:
        record = self.load_run(run_id)
        if record is None:
            return None
        updated = replace(record, **changes)
        with self._connection:
            self._connection.execute(
                """
                UPDATE reference_runs
                SET scope_json = ?,
                    status = ?,
                    continuation_index = ?,
                    max_continuations = ?,
                    budget_json = ?,
                    stop_reason = ?,
                    error_message = ?,
                    result_metadata_json = ?,
                    engine_state_json = ?,
                    created_at_ms = ?,
                    started_at_ms = ?,
                    completed_at_ms = ?
                WHERE run_id = ?
                """,
                _run_update_params(updated),
            )
        return self.load_run(run_id)

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reference_runs (
                    run_index INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL UNIQUE,
                    scope_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    continuation_index INTEGER NOT NULL,
                    max_continuations INTEGER NOT NULL,
                    budget_json TEXT,
                    stop_reason TEXT,
                    error_message TEXT,
                    result_metadata_json TEXT NOT NULL,
                    engine_state_json TEXT,
                    created_at_ms INTEGER,
                    started_at_ms INTEGER,
                    completed_at_ms INTEGER
                )
                """
            )


class SQLiteContinuationQueue:
    """SQLite ``ContinuationQueuePort`` example with retry and reclaim semantics."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._connection.row_factory = sqlite3.Row
        self._create_schema()

    def enqueue_for_run(
        self,
        spec: ContinuationJobSpec,
        *,
        job_id: str | None = None,
    ) -> ContinuationJobRecord:
        record = ContinuationJobRecord(
            job_id=job_id or f"job-{uuid.uuid4()}",
            user_request_id=spec.user_request_id,
            project_id=spec.project_id,
            previous_run_id=spec.previous_run_id,
            next_run_id=spec.next_run_id,
            status=ContinuationJobStatus.QUEUED.value,
            attempts=0,
            max_attempts=spec.max_attempts,
            correlation_id=spec.correlation_id,
            available_at_ms=spec.available_at_ms,
            created_at_ms=_now_ms(),
            updated_at_ms=_now_ms(),
        )
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO reference_continuation_jobs (
                    job_id, user_request_id, project_id, previous_run_id, next_run_id,
                    status, attempts, max_attempts, worker_id, last_error,
                    correlation_id, available_at_ms, locked_at_ms, heartbeat_at_ms,
                    completed_at_ms, created_at_ms, updated_at_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _continuation_job_params(record),
            )
        loaded = self.load_job(record.job_id)
        if loaded is None:
            raise RuntimeError(f"created continuation job disappeared: {record.job_id}")
        return loaded

    def claim_next(
        self,
        *,
        worker_id: str,
        available_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None:
        cutoff_ms = available_at_ms if available_at_ms is not None else _now_ms()
        with self._connection:
            row = self._connection.execute(
                """
                SELECT *
                FROM reference_continuation_jobs
                WHERE status = ?
                  AND (available_at_ms IS NULL OR available_at_ms <= ?)
                ORDER BY created_at_ms ASC, job_id ASC
                LIMIT 1
                """,
                (ContinuationJobStatus.QUEUED.value, cutoff_ms),
            ).fetchone()
            if row is None:
                return None
            now_ms = _now_ms()
            self._connection.execute(
                """
                UPDATE reference_continuation_jobs
                SET status = ?, worker_id = ?, locked_at_ms = ?,
                    heartbeat_at_ms = ?, updated_at_ms = ?
                WHERE job_id = ?
                """,
                (
                    ContinuationJobStatus.RUNNING.value,
                    worker_id,
                    now_ms,
                    now_ms,
                    now_ms,
                    row["job_id"],
                ),
            )
        return self.load_job(str(row["job_id"]))

    def mark_attempt_started(
        self,
        job_id: str,
        *,
        heartbeat_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None:
        record = self.load_job(job_id)
        if record is None:
            return None
        if record.status != ContinuationJobStatus.RUNNING.value:
            return record
        if record.attempts >= record.max_attempts:
            return self._update(
                record,
                status=ContinuationJobStatus.DEAD_LETTER.value,
                completed_at_ms=_now_ms(),
            )
        return self._update(
            record,
            attempts=record.attempts + 1,
            heartbeat_at_ms=heartbeat_at_ms if heartbeat_at_ms is not None else _now_ms(),
        )

    def heartbeat(
        self,
        job_id: str,
        *,
        heartbeat_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None:
        record = self.load_job(job_id)
        if record is None:
            return None
        return self._update(
            record,
            heartbeat_at_ms=heartbeat_at_ms if heartbeat_at_ms is not None else _now_ms(),
        )

    def complete_success(
        self,
        job_id: str,
        *,
        completed_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None:
        record = self.load_job(job_id)
        if record is None:
            return None
        now_ms = completed_at_ms if completed_at_ms is not None else _now_ms()
        return self._update(
            record,
            status=ContinuationJobStatus.SUCCEEDED.value,
            completed_at_ms=now_ms,
        )

    def complete_failure(
        self,
        job_id: str,
        *,
        error: str,
        retry_available_at_ms: int | None = None,
        completed_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None:
        record = self.load_job(job_id)
        if record is None:
            return None
        if record.attempts < record.max_attempts:
            return self.release_for_retry(
                job_id,
                error=error,
                available_at_ms=retry_available_at_ms,
            )
        now_ms = completed_at_ms if completed_at_ms is not None else _now_ms()
        return self._update(
            record,
            status=ContinuationJobStatus.DEAD_LETTER.value,
            last_error=error,
            completed_at_ms=now_ms,
        )

    def release_for_retry(
        self,
        job_id: str,
        *,
        error: str,
        available_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None:
        record = self.load_job(job_id)
        if record is None:
            return None
        if record.attempts >= record.max_attempts:
            return self._update(
                record,
                status=ContinuationJobStatus.DEAD_LETTER.value,
                last_error=error,
                completed_at_ms=_now_ms(),
            )
        return self._update(
            record,
            status=ContinuationJobStatus.QUEUED.value,
            worker_id=None,
            last_error=error,
            available_at_ms=available_at_ms,
            locked_at_ms=None,
            heartbeat_at_ms=None,
        )

    def reclaim_stale(
        self,
        *,
        stale_before_ms: int,
    ) -> int:
        rows = self._connection.execute(
            """
            SELECT *
            FROM reference_continuation_jobs
            WHERE status = ?
              AND COALESCE(heartbeat_at_ms, locked_at_ms, created_at_ms, 0) < ?
            """,
            (ContinuationJobStatus.RUNNING.value, stale_before_ms),
        ).fetchall()
        for row in rows:
            record = _continuation_job_from_row(row)
            if record.attempts >= record.max_attempts:
                self._update(
                    record,
                    status=ContinuationJobStatus.DEAD_LETTER.value,
                    last_error="stale continuation job exceeded max attempts",
                    completed_at_ms=_now_ms(),
                )
            else:
                self._update(
                    record,
                    status=ContinuationJobStatus.QUEUED.value,
                    worker_id=None,
                    last_error="stale continuation job reclaimed",
                    locked_at_ms=None,
                    heartbeat_at_ms=None,
                )
        return len(rows)

    def load_job(self, job_id: str) -> ContinuationJobRecord | None:
        row = self._connection.execute(
            "SELECT * FROM reference_continuation_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        return _continuation_job_from_row(row) if row is not None else None

    def _update(self, record: ContinuationJobRecord, **changes: Any) -> ContinuationJobRecord:
        updated = replace(record, updated_at_ms=_now_ms(), **changes)
        with self._connection:
            self._connection.execute(
                """
                UPDATE reference_continuation_jobs
                SET user_request_id = ?,
                    project_id = ?,
                    previous_run_id = ?,
                    next_run_id = ?,
                    status = ?,
                    attempts = ?,
                    max_attempts = ?,
                    worker_id = ?,
                    last_error = ?,
                    correlation_id = ?,
                    available_at_ms = ?,
                    locked_at_ms = ?,
                    heartbeat_at_ms = ?,
                    completed_at_ms = ?,
                    created_at_ms = ?,
                    updated_at_ms = ?
                WHERE job_id = ?
                """,
                (*_continuation_job_params(updated)[1:], updated.job_id),
            )
        loaded = self.load_job(record.job_id)
        if loaded is None:
            raise RuntimeError(f"updated continuation job disappeared: {record.job_id}")
        return loaded

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reference_continuation_jobs (
                    job_id TEXT PRIMARY KEY,
                    user_request_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    previous_run_id TEXT NOT NULL,
                    next_run_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    worker_id TEXT,
                    last_error TEXT,
                    correlation_id TEXT,
                    available_at_ms INTEGER,
                    locked_at_ms INTEGER,
                    heartbeat_at_ms INTEGER,
                    completed_at_ms INTEGER,
                    created_at_ms INTEGER,
                    updated_at_ms INTEGER
                )
                """
            )


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


def _event_from_row(row: sqlite3.Row) -> AgentEvent:
    return AgentEvent(
        seq=int(row["seq"]),
        timestamp_ms=int(row["timestamp_ms"]),
        run_id=str(row["run_id"]),
        turn_id=str(row["turn_id"]),
        event_type=str(row["event_type"]),
        payload=json.loads(str(row["payload_json"])),
        schema_version=str(row["schema_version"]),
        message_id=row["message_id"],
        action_id=row["action_id"],
    )


def _json_or_none(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _run_insert_params(record: RunRecord) -> tuple[Any, ...]:
    return (
        record.run_id,
        json.dumps(asdict(record.scope), ensure_ascii=False, sort_keys=True),
        record.status,
        record.continuation_index,
        record.max_continuations,
        _json_or_none(record.budget.to_json() if record.budget is not None else None),
        record.stop_reason,
        record.error_message,
        json.dumps(record.result_metadata.to_json(), ensure_ascii=False, sort_keys=True),
        record.engine_state_json,
        record.created_at_ms,
        record.started_at_ms,
        record.completed_at_ms,
    )


def _run_update_params(record: RunRecord) -> tuple[Any, ...]:
    return (
        json.dumps(asdict(record.scope), ensure_ascii=False, sort_keys=True),
        record.status,
        record.continuation_index,
        record.max_continuations,
        _json_or_none(record.budget.to_json() if record.budget is not None else None),
        record.stop_reason,
        record.error_message,
        json.dumps(record.result_metadata.to_json(), ensure_ascii=False, sort_keys=True),
        record.engine_state_json,
        record.created_at_ms,
        record.started_at_ms,
        record.completed_at_ms,
        record.run_id,
    )


def _run_from_row(row: sqlite3.Row) -> RunRecord:
    budget_json = row["budget_json"]
    budget = RunBudget.from_json(json.loads(budget_json)) if budget_json else None
    return RunRecord(
        run_id=str(row["run_id"]),
        scope=RunScope(**json.loads(str(row["scope_json"]))),
        status=str(row["status"]),
        run_index=int(row["run_index"]),
        continuation_index=int(row["continuation_index"]),
        max_continuations=int(row["max_continuations"]),
        budget=budget,
        stop_reason=row["stop_reason"],
        error_message=row["error_message"],
        result_metadata=RunResultMetadata.from_json(
            json.loads(str(row["result_metadata_json"]))
        ),
        engine_state_json=row["engine_state_json"],
        created_at_ms=row["created_at_ms"],
        started_at_ms=row["started_at_ms"],
        completed_at_ms=row["completed_at_ms"],
    )


def _continuation_job_params(record: ContinuationJobRecord) -> tuple[Any, ...]:
    return (
        record.job_id,
        record.user_request_id,
        record.project_id,
        record.previous_run_id,
        record.next_run_id,
        record.status,
        record.attempts,
        record.max_attempts,
        record.worker_id,
        record.last_error,
        record.correlation_id,
        record.available_at_ms,
        record.locked_at_ms,
        record.heartbeat_at_ms,
        record.completed_at_ms,
        record.created_at_ms,
        record.updated_at_ms,
    )


def _continuation_job_from_row(row: sqlite3.Row) -> ContinuationJobRecord:
    return ContinuationJobRecord(
        job_id=str(row["job_id"]),
        user_request_id=str(row["user_request_id"]),
        project_id=str(row["project_id"]),
        previous_run_id=str(row["previous_run_id"]),
        next_run_id=str(row["next_run_id"]),
        status=str(row["status"]),
        attempts=int(row["attempts"]),
        max_attempts=int(row["max_attempts"]),
        worker_id=row["worker_id"],
        last_error=row["last_error"],
        correlation_id=row["correlation_id"],
        available_at_ms=row["available_at_ms"],
        locked_at_ms=row["locked_at_ms"],
        heartbeat_at_ms=row["heartbeat_at_ms"],
        completed_at_ms=row["completed_at_ms"],
        created_at_ms=row["created_at_ms"],
        updated_at_ms=row["updated_at_ms"],
    )

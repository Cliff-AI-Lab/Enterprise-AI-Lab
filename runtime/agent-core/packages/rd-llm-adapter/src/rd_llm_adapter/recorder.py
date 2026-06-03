from __future__ import annotations

import fnmatch
import gzip
import json
import logging
import os
import random
import re
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Protocol
from uuid import uuid4

from .events import StandardEvent, TurnDone
from .openai_compat import (
    legacy_response_from_turn_done,
    standard_events_to_legacy_deltas,
    terminal_events_from_turn_done,
)

RECORDED_TURN_KIND = "model_adapter_recorded_turn"
RECORDED_TURN_VERSION = 1
RECORD_TURNS_ENV = "MODEL_ADAPTER_RECORD_TURNS"
RECORD_DIR_ENV = "MODEL_ADAPTER_RECORD_DIR"
RECORD_SAMPLE_RATE_ENV = "MODEL_ADAPTER_RECORD_SAMPLE_RATE"
RECORD_MODEL_PATTERNS_ENV = "MODEL_ADAPTER_RECORD_MODEL_PATTERNS"
RECORD_INCLUDE_MESSAGES_ENV = "MODEL_ADAPTER_RECORD_INCLUDE_MESSAGES"
DEFAULT_RECORD_DIR = "/tmp/model_adapter_recordings"

logger = logging.getLogger(__name__)

_SECRET_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "access_token",
    "refresh_token",
    "secret",
    "password",
)


class ReplayAdapter(Protocol):
    def create_parser_session(self, profile: Any | None = None) -> Any: ...


class ReplayEvents(list[StandardEvent]):
    """Flat standard events plus exact legacy events rebuilt per raw chunk."""

    def __init__(
        self,
        events: Iterable[StandardEvent],
        *,
        legacy_events: list[dict[str, Any]],
    ) -> None:
        super().__init__(events)
        self.legacy_events = legacy_events


@dataclass(frozen=True)
class RecordedTurn:
    """A single LLM turn captured at the model adapter boundary."""

    turn_id: str
    timestamp: str
    profile_snapshot: dict[str, Any]
    request_body: dict[str, Any]
    raw_chunks: list[dict[str, Any]]
    expected_events: list[dict[str, Any]]
    expected_legacy_dict: dict[str, Any]

    @classmethod
    def create(
        cls,
        *,
        turn_id: str,
        profile_snapshot: dict[str, Any],
        request_body: dict[str, Any],
        raw_chunks: list[Any],
        expected_events: list[dict[str, Any]],
        expected_legacy_dict: dict[str, Any],
        timestamp: str | None = None,
    ) -> RecordedTurn:
        return cls(
            turn_id=turn_id,
            timestamp=timestamp or datetime.now(UTC).isoformat(),
            profile_snapshot=_redact_secrets(_to_jsonable(profile_snapshot)),
            request_body=_to_jsonable(request_body),
            raw_chunks=[_to_jsonable(chunk) for chunk in raw_chunks],
            expected_events=_to_jsonable(expected_events),
            expected_legacy_dict=_to_jsonable(expected_legacy_dict),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "timestamp": self.timestamp,
            "profile_snapshot": self.profile_snapshot,
            "request_body": self.request_body,
            "raw_chunks": self.raw_chunks,
            "expected_events": self.expected_events,
            "expected_legacy_dict": self.expected_legacy_dict,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RecordedTurn:
        return cls(
            turn_id=str(payload["turn_id"]),
            timestamp=str(payload["timestamp"]),
            profile_snapshot=dict(payload.get("profile_snapshot") or {}),
            request_body=dict(payload.get("request_body") or {}),
            raw_chunks=list(payload.get("raw_chunks") or []),
            expected_events=list(payload.get("expected_events") or []),
            expected_legacy_dict=dict(payload.get("expected_legacy_dict") or {}),
        )


class StreamRecorder:
    """Record and replay raw model stream chunks for adapter regression tests."""

    def record_turn(
        self,
        turn: RecordedTurn,
        output_dir: Path,
        *,
        redact_request_body: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = turn.to_dict()
        payload["profile_snapshot"] = _redact_secrets(payload["profile_snapshot"])
        if redact_request_body is not None:
            payload["request_body"] = _to_jsonable(
                redact_request_body(payload["request_body"])
            )

        path = output_dir / f"{_safe_filename(turn.turn_id)}.jsonl.gz"
        wrapped = {
            "_kind": RECORDED_TURN_KIND,
            "_version": RECORDED_TURN_VERSION,
            **payload,
        }
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(json.dumps(wrapped, ensure_ascii=False, sort_keys=True))
            f.write("\n")
        return path

    def load_turn(self, path: Path) -> RecordedTurn:
        text = _read_text(path)
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if payload.get("_kind") == RECORDED_TURN_KIND:
                payload = {
                    key: value
                    for key, value in payload.items()
                    if not key.startswith("_")
                }
            return RecordedTurn.from_dict(payload)
        raise ValueError(f"recorded turn file is empty: {path}")

    def replay_through_adapter(
        self,
        recorded: RecordedTurn,
        adapter: ReplayAdapter,
    ) -> tuple[ReplayEvents, TurnDone]:
        session = adapter.create_parser_session(
            SimpleNamespace(**recorded.profile_snapshot)
        )
        events: list[StandardEvent] = []
        legacy_events: list[dict[str, Any]] = []
        turn_done: TurnDone | None = None

        for raw_chunk in recorded.raw_chunks:
            chunk_events = list(session.feed(raw_chunk))
            events.extend(chunk_events)
            legacy_events.extend(standard_events_to_legacy_deltas(chunk_events))
            turn_done = _last_turn_done(chunk_events) or turn_done

        final_events = list(session.finalize())
        events.extend(final_events)
        legacy_events.extend(standard_events_to_legacy_deltas(final_events))
        turn_done = _last_turn_done(final_events) or turn_done
        if turn_done is None:
            raise ValueError("adapter replay did not produce TurnDone")
        legacy_events.extend(terminal_events_from_turn_done(turn_done))
        return ReplayEvents(events, legacy_events=legacy_events), turn_done

    def diff_against_legacy(
        self,
        recorded: RecordedTurn,
        new_events: list[StandardEvent],
    ) -> list[str]:
        diffs: list[str] = []
        new_legacy_events = getattr(new_events, "legacy_events", None)
        if new_legacy_events is None:
            new_legacy_events = legacy_events_from_standard_events(new_events)
        new_legacy_events_for_diff = _normalize_actual_legacy_for_diff(
            recorded.expected_events, new_legacy_events
        )
        if new_legacy_events_for_diff != recorded.expected_events:
            diffs.append(
                "events differ: "
                + _json_diff_summary(
                    recorded.expected_events, new_legacy_events_for_diff
                )
            )

        turn_done = _last_turn_done(new_events)
        if turn_done is None:
            diffs.append("legacy response differs: replay produced no TurnDone")
            return diffs

        expected_latency = int(recorded.expected_legacy_dict.get("latency_ms") or 0)
        expected_first_chunk_latency = recorded.expected_legacy_dict.get(
            "first_chunk_latency_ms"
        )
        if expected_first_chunk_latency is not None:
            expected_first_chunk_latency = int(expected_first_chunk_latency)
        new_legacy_dict = legacy_response_from_turn_done(
            turn_done,
            latency_ms=expected_latency,
            first_chunk_latency_ms=expected_first_chunk_latency,
        )
        new_legacy_dict_for_diff = _normalize_actual_legacy_for_diff(
            recorded.expected_legacy_dict, new_legacy_dict
        )
        if new_legacy_dict_for_diff != recorded.expected_legacy_dict:
            diffs.append(
                "legacy response differs: "
                + _json_diff_summary(
                    recorded.expected_legacy_dict, new_legacy_dict_for_diff
                )
            )
        return diffs


def record_turn_if_enabled(
    *,
    profile: Any | None,
    requested_model: str,
    provider_model: str,
    base_url: str,
    adapter_kind: str = "openai_compat",
    request_body: dict[str, Any],
    raw_chunks: list[Any],
    expected_events: list[dict[str, Any]],
    expected_legacy_dict: dict[str, Any],
) -> Path | None:
    """Best-effort production sampling hook for model adapter replay fixtures."""

    if not _recording_enabled():
        return None
    if not _recording_model_selected(requested_model, provider_model):
        return None
    if not _sample_selected():
        return None

    try:
        turn = RecordedTurn.create(
            turn_id=_recording_turn_id(provider_model),
            profile_snapshot=_profile_snapshot(
                profile=profile,
                requested_model=requested_model,
                provider_model=provider_model,
                base_url=base_url,
                adapter_kind=adapter_kind,
            ),
            request_body=request_body,
            raw_chunks=raw_chunks,
            expected_events=expected_events,
            expected_legacy_dict=expected_legacy_dict,
        )
        recorder = StreamRecorder()
        path = recorder.record_turn(
            turn,
            _record_dir(),
            redact_request_body=(
                None if _include_request_messages() else _redact_request_body_messages
            ),
        )
        logger.info(
            "model_adapter_recorded_turn: path=%s provider_model=%s adapter_kind=%s "
            "chunks=%d events=%d",
            path,
            provider_model,
            adapter_kind,
            len(raw_chunks),
            len(expected_events),
        )
        return path
    except Exception:
        logger.warning(
            "model_adapter_record_turn_failed: provider_model=%s",
            provider_model,
            exc_info=True,
        )
        return None


def legacy_events_from_standard_events(
    events: Iterable[StandardEvent],
) -> list[dict[str, Any]]:
    event_list = list(events)
    legacy_events = standard_events_to_legacy_deltas(event_list)
    turn_done = _last_turn_done(event_list)
    if turn_done is not None:
        legacy_events.extend(terminal_events_from_turn_done(turn_done))
    return legacy_events


def _last_turn_done(events: Iterable[StandardEvent]) -> TurnDone | None:
    result: TurnDone | None = None
    for event in events:
        if isinstance(event, TurnDone):
            result = event
    return result


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _to_jsonable(value.model_dump())
    if hasattr(value, "to_dict"):
        return _to_jsonable(value.to_dict())
    if hasattr(value, "__dict__"):
        return _to_jsonable(vars(value))
    return str(value)


def _profile_snapshot(
    *,
    profile: Any | None,
    requested_model: str,
    provider_model: str,
    base_url: str,
    adapter_kind: str,
) -> dict[str, Any]:
    if profile is None:
        return {
            "requested_model": requested_model,
            "provider_model_name": provider_model,
            "base_url": base_url,
            "adapter_kind": adapter_kind,
        }
    snapshot = _to_jsonable(profile)
    if isinstance(snapshot, dict):
        snapshot["adapter_kind"] = adapter_kind
        return snapshot
    return {
        "requested_model": requested_model,
        "provider_model_name": provider_model,
        "base_url": base_url,
        "adapter_kind": adapter_kind,
        "profile": snapshot,
    }


def _recording_enabled() -> bool:
    return os.getenv(RECORD_TURNS_ENV) == "1"


def _record_dir() -> Path:
    return Path(os.getenv(RECORD_DIR_ENV, DEFAULT_RECORD_DIR))


def _sample_selected() -> bool:
    raw = os.getenv(RECORD_SAMPLE_RATE_ENV, "1")
    try:
        sample_rate = float(raw)
    except ValueError:
        sample_rate = 1.0
    sample_rate = min(1.0, max(0.0, sample_rate))
    return random.random() < sample_rate


def _recording_model_selected(requested_model: str, provider_model: str) -> bool:
    raw = (os.getenv(RECORD_MODEL_PATTERNS_ENV) or "").strip()
    if not raw:
        return True
    patterns = [
        item.strip()
        for item in raw.replace(";", ",").split(",")
        if item.strip()
    ]
    if not patterns:
        return True
    candidates = [
        (requested_model or "").strip().lower(),
        (provider_model or "").strip().lower(),
    ]
    return any(
        fnmatch.fnmatchcase(candidate, pattern.lower())
        for candidate in candidates
        if candidate
        for pattern in patterns
    )


def _include_request_messages() -> bool:
    return os.getenv(RECORD_INCLUDE_MESSAGES_ENV) == "1"


def _recording_turn_id(provider_model: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}_{provider_model}_{uuid4().hex[:8]}"


def _redact_request_body_messages(request_body: dict[str, Any]) -> dict[str, Any]:
    scrubbed = _to_jsonable(request_body)
    if not isinstance(scrubbed, dict):
        return {}
    messages = scrubbed.get("messages")
    if isinstance(messages, list):
        scrubbed["messages"] = [_redact_message_for_recording(msg) for msg in messages]
    return scrubbed


def _redact_message_for_recording(message: Any) -> Any:
    if not isinstance(message, dict):
        return message
    redacted = dict(message)
    if "content" in redacted:
        redacted["content"] = _redact_content_for_recording(redacted["content"])
    if isinstance(redacted.get("tool_calls"), list):
        redacted["tool_calls"] = [
            _redact_tool_call_for_recording(tool_call)
            for tool_call in redacted["tool_calls"]
        ]
    return redacted


def _redact_tool_call_for_recording(tool_call: Any) -> Any:
    if not isinstance(tool_call, dict):
        return tool_call
    redacted = dict(tool_call)
    function = redacted.get("function")
    if isinstance(function, dict):
        function = dict(function)
        if "arguments" in function:
            function["arguments"] = _redaction_marker(function["arguments"])
        redacted["function"] = function
    return redacted


def _redact_content_for_recording(content: Any) -> Any:
    if isinstance(content, str):
        return _redaction_marker(content)
    if isinstance(content, list):
        redacted_blocks: list[Any] = []
        for block in content:
            if isinstance(block, dict):
                redacted = dict(block)
                if "text" in redacted:
                    redacted["text"] = _redaction_marker(redacted["text"])
                if "content" in redacted:
                    redacted["content"] = _redaction_marker(redacted["content"])
                if "input" in redacted:
                    redacted["input"] = _redaction_marker(redacted["input"])
                redacted_blocks.append(redacted)
            else:
                redacted_blocks.append(_redaction_marker(block))
        return redacted_blocks
    return _redaction_marker(content)


def _redaction_marker(value: Any) -> str:
    if value is None:
        return "[redacted:null]"
    text = str(value)
    return f"[redacted:{len(text)} chars]"


def _redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in _SECRET_KEY_PARTS):
                redacted[key] = _redact_secret_value(item)
            else:
                redacted[key] = _redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [_redact_secrets(item) for item in value]
    return value


def _redact_secret_value(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}...{text[-4:]}"


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return safe or "turn"


def _read_text(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return f.read()
    return path.read_text(encoding="utf-8")


def _normalize_actual_legacy_for_diff(expected: Any, actual: Any) -> Any:
    if isinstance(expected, dict) and isinstance(actual, dict):
        normalized: dict[str, Any] = {}
        for key, value in actual.items():
            if key == "reasoning_text" and not expected.get("reasoning_text"):
                normalized[key] = expected.get("reasoning_text", "")
                continue
            if (
                key
                in {
                    "cached_input_tokens",
                    "cache_read_input_tokens",
                    "cache_creation_input_tokens",
                    "reasoning_tokens",
                }
                and key not in expected
            ):
                continue
            if (
                expected.get("input_parse_error")
                and key in {"raw_args", "parse_error", "index"}
                and key not in expected
            ):
                continue
            normalized[key] = _normalize_actual_legacy_for_diff(
                expected.get(key), value
            )
        return normalized
    if isinstance(expected, list) and isinstance(actual, list):
        actual_items = actual
        if not _legacy_events_have_reasoning(expected):
            actual_items = [
                item for item in actual if not _legacy_event_is_reasoning(item)
            ]
        normalized_list: list[Any] = []
        for index, value in enumerate(actual_items):
            expected_item = expected[index] if index < len(expected) else None
            normalized_list.append(
                _normalize_actual_legacy_for_diff(expected_item, value)
            )
        return normalized_list
    return actual


def _legacy_events_have_reasoning(events: list[Any]) -> bool:
    return any(_legacy_event_is_reasoning(event) for event in events)


def _legacy_event_is_reasoning(event: Any) -> bool:
    return isinstance(event, dict) and event.get("type") in {
        "reasoning_delta",
        "reasoning",
    }


def _json_diff_summary(expected: Any, actual: Any) -> str:
    expected_json = json.dumps(expected, ensure_ascii=False, sort_keys=True)
    actual_json = json.dumps(actual, ensure_ascii=False, sort_keys=True)
    if len(expected_json) > 500:
        expected_json = expected_json[:500] + "..."
    if len(actual_json) > 500:
        actual_json = actual_json[:500] + "..."
    return f"expected={expected_json} actual={actual_json}"

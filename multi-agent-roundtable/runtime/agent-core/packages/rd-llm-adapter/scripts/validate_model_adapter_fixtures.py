#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rd_llm_adapter.anthropic_native import AnthropicNativeAdapter
from rd_llm_adapter.events import TurnDone
from rd_llm_adapter.messages import (
    InvalidToolCall,
    ReasoningBlock,
    TextBlock,
    ToolUseBlock,
)
from rd_llm_adapter.recorder import StreamRecorder
from rd_llm_adapter.registry import resolve_adapter

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORDED_FIXTURE_DIR = _PACKAGE_ROOT / "tests" / "fixtures" / "recorded" / "model_adapter"
DEFAULT_ANTHROPIC_FIXTURE_DIR = _PACKAGE_ROOT / "tests" / "fixtures" / "anthropic_native"


@dataclass
class ValidationResult:
    name: str
    checked: int = 0
    raw_chunks: int = 0
    skipped: bool = False
    failures: list[str] = field(default_factory=list)
    by_adapter_kind: dict[str, int] = field(default_factory=dict)
    by_model: dict[str, int] = field(default_factory=dict)
    scenarios: set[str] = field(default_factory=set)

    @property
    def ok(self) -> bool:
        return not self.failures


def validate_recorded_fixtures(
    fixture_dir: Path,
    *,
    require: bool = False,
    required_adapter_counts: dict[str, int] | None = None,
    required_model_counts: dict[str, int] | None = None,
    required_scenarios: set[str] | None = None,
    require_redacted_request: bool = False,
) -> ValidationResult:
    result = ValidationResult(name="recorded_model_adapter")
    paths = _recorded_fixture_paths(fixture_dir)
    if not paths:
        result.skipped = True
        if (
            require
            or required_adapter_counts
            or required_model_counts
            or required_scenarios
            or require_redacted_request
        ):
            result.failures.append(f"no recorded fixtures found in {fixture_dir}")
        return result

    recorder = StreamRecorder()
    for path in paths:
        result.checked += 1
        try:
            recorded = recorder.load_turn(path)
            adapter_kind = str(
                recorded.profile_snapshot.get("adapter_kind", "openai_compat")
                or "openai_compat"
            )
            result.by_adapter_kind[adapter_kind] = (
                result.by_adapter_kind.get(adapter_kind, 0) + 1
            )
            model_name = _recorded_model_name(recorded.profile_snapshot)
            result.by_model[model_name] = result.by_model.get(model_name, 0) + 1
            result.raw_chunks += len(recorded.raw_chunks)
            result.scenarios.update(_recorded_fixture_scenarios(recorded))
            if require_redacted_request:
                redaction_failures = _recorded_request_redaction_failures(
                    recorded.request_body
                )
                if redaction_failures:
                    result.failures.append(
                        f"{path}: request body is not redacted: "
                        + ",".join(redaction_failures)
                    )
            adapter = resolve_adapter(adapter_kind)
            events, _turn_done = recorder.replay_through_adapter(recorded, adapter)
            diffs = recorder.diff_against_legacy(recorded, events)
            if diffs:
                result.failures.append(f"{path}: {'; '.join(diffs)}")
        except Exception as exc:
            result.failures.append(f"{path}: {type(exc).__name__}: {exc}")

    for adapter_kind, minimum in sorted((required_adapter_counts or {}).items()):
        observed = result.by_adapter_kind.get(adapter_kind, 0)
        if observed < minimum:
            result.failures.append(
                f"recorded fixtures require {adapter_kind}>={minimum}, observed {observed}"
            )
    for pattern, minimum in sorted((required_model_counts or {}).items()):
        observed = _matching_model_count(result.by_model, pattern)
        if observed < minimum:
            result.failures.append(
                f"recorded fixtures require model {pattern}>={minimum}, observed {observed}"
            )
    missing_scenarios = sorted((required_scenarios or set()) - result.scenarios)
    if missing_scenarios:
        result.failures.append(
            "recorded fixtures missing required scenarios: "
            + ",".join(missing_scenarios)
        )
    return result


def validate_anthropic_fixtures(
    fixture_dir: Path,
    *,
    require: bool = False,
    require_min_raw_chunks: int = 0,
    required_scenarios: set[str] | None = None,
) -> ValidationResult:
    result = ValidationResult(name="anthropic_native")
    paths = _anthropic_fixture_paths(fixture_dir)
    if not paths:
        result.skipped = True
        if require or require_min_raw_chunks or required_scenarios:
            result.failures.append(f"no Anthropic fixtures found in {fixture_dir}")
        return result

    adapter = AnthropicNativeAdapter()
    for path in paths:
        result.checked += 1
        try:
            fixture = json.loads(path.read_text(encoding="utf-8"))
            result.raw_chunks += _anthropic_raw_chunk_count(fixture)
            result.scenarios.update(_anthropic_fixture_scenarios(fixture))
            _validate_anthropic_request_fixture(path, fixture, adapter, result)
            _validate_anthropic_stream_fixture(path, fixture, adapter, result)
        except Exception as exc:
            result.failures.append(f"{path}: {type(exc).__name__}: {exc}")
    if result.raw_chunks < require_min_raw_chunks:
        result.failures.append(
            "Anthropic fixtures require "
            f"raw_chunks>={require_min_raw_chunks}, observed {result.raw_chunks}"
        )
    missing_scenarios = sorted((required_scenarios or set()) - result.scenarios)
    if missing_scenarios:
        result.failures.append(
            "Anthropic fixtures missing required scenarios: "
            + ",".join(missing_scenarios)
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate recorded model adapter fixtures."
    )
    parser.add_argument(
        "--recorded-dir",
        type=Path,
        default=Path(
            os.getenv(
                "MODEL_ADAPTER_RECORDED_FIXTURES_DIR",
                str(DEFAULT_RECORDED_FIXTURE_DIR),
            )
        ),
        help="Directory containing RecordedTurn *.jsonl(.gz) fixtures.",
    )
    parser.add_argument(
        "--anthropic-dir",
        type=Path,
        default=Path(
            os.getenv(
                "ANTHROPIC_NATIVE_FIXTURES_DIR",
                str(DEFAULT_ANTHROPIC_FIXTURE_DIR),
            )
        ),
        help="Directory containing Anthropic native request/SSE *.json fixtures.",
    )
    parser.add_argument("--skip-recorded", action="store_true")
    parser.add_argument("--skip-anthropic", action="store_true")
    parser.add_argument("--require-recorded", action="store_true")
    parser.add_argument("--require-anthropic", action="store_true")
    parser.add_argument(
        "--require-anthropic-chunks",
        type=int,
        default=0,
        metavar="N",
        help="Require at least N raw Anthropic SSE chunks across fixtures.",
    )
    parser.add_argument(
        "--require-anthropic-scenario",
        action="append",
        default=[],
        metavar="NAME",
        help="Require an Anthropic fixture scenario such as signed_thinking or tool_use.",
    )
    parser.add_argument(
        "--require-recorded-adapter",
        action="append",
        default=[],
        metavar="KIND=N",
        help="Require at least N recorded fixtures for an adapter kind.",
    )
    parser.add_argument(
        "--require-recorded-model",
        action="append",
        default=[],
        metavar="PATTERN=N",
        help="Require at least N recorded fixtures matching a requested/provider model glob.",
    )
    parser.add_argument(
        "--require-recorded-scenario",
        action="append",
        default=[],
        metavar="NAME",
        help="Require a recorded fixture scenario such as tool_use, reasoning, usage, or length.",
    )
    parser.add_argument(
        "--require-recorded-redacted",
        action="store_true",
        help="Require recorded request messages and tool arguments to be redacted.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable JSON validation report to stdout.",
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        help="Write a machine-readable JSON validation report to this path.",
    )
    parser.add_argument(
        "--fail-on-skipped",
        action="store_true",
        help="Fail if any enabled fixture category is skipped.",
    )
    args = parser.parse_args(argv)

    try:
        required_adapter_counts = _parse_required_adapter_counts(
            args.require_recorded_adapter
        )
        required_model_counts = _parse_required_model_counts(
            args.require_recorded_model
        )
    except ValueError as exc:
        parser.error(str(exc))
    if args.require_anthropic_chunks < 0:
        parser.error("--require-anthropic-chunks must be non-negative")
    if args.skip_recorded and args.skip_anthropic:
        parser.error("at least one fixture category must be enabled")

    results: list[ValidationResult] = []
    if not args.skip_recorded:
        results.append(
            validate_recorded_fixtures(
                args.recorded_dir,
                require=args.require_recorded,
                required_adapter_counts=required_adapter_counts,
                required_model_counts=required_model_counts,
                required_scenarios=set(args.require_recorded_scenario),
                require_redacted_request=args.require_recorded_redacted,
            )
        )
    if not args.skip_anthropic:
        results.append(
            validate_anthropic_fixtures(
                args.anthropic_dir,
                require=args.require_anthropic,
                require_min_raw_chunks=args.require_anthropic_chunks,
                required_scenarios=set(args.require_anthropic_scenario),
            )
        )

    if args.fail_on_skipped:
        for result in results:
            if result.skipped:
                result.failures.append(
                    f"{result.name} skipped while --fail-on-skipped is enabled"
                )

    report = _validation_report(results)
    if args.json_report is not None:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        for result in results:
            _print_result(result)

    return 0 if report["ok"] else 1


def _recorded_fixture_paths(fixture_dir: Path) -> list[Path]:
    if not fixture_dir.exists():
        return []
    return sorted([*fixture_dir.glob("*.jsonl"), *fixture_dir.glob("*.jsonl.gz")])


def _anthropic_fixture_paths(fixture_dir: Path) -> list[Path]:
    if not fixture_dir.exists():
        return []
    return sorted(fixture_dir.glob("*.json"))


def _recorded_model_name(profile_snapshot: dict[str, Any]) -> str:
    for key in ("requested_model", "provider_model_name", "provider_model", "model"):
        value = profile_snapshot.get(key)
        if value:
            return str(value)
    return "unknown"


def _recorded_fixture_scenarios(recorded: Any) -> set[str]:
    scenarios: set[str] = set()
    expected_events = recorded.expected_events or []
    legacy_dict = recorded.expected_legacy_dict or {}
    content = legacy_dict.get("content")
    content_blocks = content if isinstance(content, list) else []

    if legacy_dict.get("text_content") or _has_event_type(expected_events, "text"):
        scenarios.add("text")
    if any(
        isinstance(block, dict) and block.get("type") == "text" and block.get("text")
        for block in content_blocks
    ):
        scenarios.add("text")

    if legacy_dict.get("reasoning_text") or _has_event_type(
        expected_events, "reasoning"
    ):
        scenarios.add("reasoning")
    if any(
        isinstance(block, dict) and block.get("type") == "reasoning"
        for block in content_blocks
    ):
        scenarios.add("reasoning")

    if _has_event_type(expected_events, "tool_use"):
        scenarios.add("tool_use")
    if any(
        isinstance(block, dict) and block.get("type") == "tool_use"
        for block in content_blocks
    ):
        scenarios.add("tool_use")

    if any(
        isinstance(block, dict)
        and block.get("type") == "tool_use"
        and block.get("name") == "ask_user"
        for block in content_blocks
    ) or any(
        isinstance(event, dict)
        and event.get("type") == "tool_use"
        and event.get("name") == "ask_user"
        for event in expected_events
    ):
        scenarios.add("ask_user")

    if any(
        isinstance(block, dict) and block.get("input_parse_error")
        for block in content_blocks
    ):
        scenarios.add("tool_args_parse_error")

    usage = legacy_dict.get("usage")
    if isinstance(usage, dict) and bool(usage):
        scenarios.add("usage")

    stop_reason = str(legacy_dict.get("stop_reason") or "").strip()
    if stop_reason:
        scenarios.add("stop_reason")
        scenarios.add(f"stop_reason:{stop_reason}")
        if stop_reason == "length":
            scenarios.add("length")
        elif stop_reason == "length_limit":
            scenarios.add("length_limit")
        elif stop_reason.startswith("loop_break"):
            scenarios.add("loop_break")
    return scenarios


def _has_event_type(events: list[Any], prefix: str) -> bool:
    return any(
        isinstance(event, dict) and str(event.get("type") or "").startswith(prefix)
        for event in events
    )


def _recorded_request_redaction_failures(request_body: dict[str, Any]) -> list[str]:
    messages = request_body.get("messages")
    if not isinstance(messages, list):
        return []

    failures: list[str] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        base_path = f"messages[{index}]"
        if "content" in message:
            failures.extend(
                _content_redaction_failures(
                    message["content"],
                    f"{base_path}.content",
                )
            )
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            for tool_index, tool_call in enumerate(tool_calls):
                if not isinstance(tool_call, dict):
                    continue
                function = tool_call.get("function")
                if not isinstance(function, dict) or "arguments" not in function:
                    continue
                failures.extend(
                    _redacted_scalar_failures(
                        function["arguments"],
                        (
                            f"{base_path}.tool_calls[{tool_index}]"
                            ".function.arguments"
                        ),
                    )
                )
    return failures


def _content_redaction_failures(value: Any, path: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return _redacted_scalar_failures(value, path)
    if isinstance(value, list):
        failures: list[str] = []
        for index, item in enumerate(value):
            failures.extend(_content_redaction_failures(item, f"{path}[{index}]"))
        return failures
    if isinstance(value, dict):
        failures = []
        if "text" in value:
            failures.extend(_redacted_scalar_failures(value["text"], f"{path}.text"))
        if "content" in value:
            failures.extend(
                _content_redaction_failures(value["content"], f"{path}.content")
            )
        if "input" in value:
            failures.extend(_redacted_scalar_failures(value["input"], f"{path}.input"))
        return failures
    return [path]


def _redacted_scalar_failures(value: Any, path: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str) and (not value or value.startswith("[redacted:")):
        return []
    return [path]


def _matching_model_count(by_model: dict[str, int], pattern: str) -> int:
    return sum(
        count
        for model_name, count in by_model.items()
        if fnmatch.fnmatchcase(model_name, pattern)
    )


def _anthropic_raw_chunk_count(fixture: dict[str, Any]) -> int:
    stream_case = fixture.get("stream")
    if not isinstance(stream_case, dict):
        return 0
    raw_chunks = stream_case.get("raw_chunks")
    if not isinstance(raw_chunks, list):
        return 0
    return len(raw_chunks)


def _anthropic_fixture_scenarios(fixture: dict[str, Any]) -> set[str]:
    scenarios: set[str] = set()
    values = list(_walk_values(fixture))

    if any(
        isinstance(value, dict)
        and value.get("type") == "thinking"
        and bool(value.get("signature"))
        for value in values
    ) or any(
        isinstance(value, dict)
        and value.get("type") == "signature_delta"
        and bool(value.get("signature"))
        for value in values
    ):
        scenarios.add("signed_thinking")

    if any(
        isinstance(value, dict)
        and (
            value.get("type") == "redacted_thinking"
            or (value.get("type") == "reasoning" and value.get("redacted") is True)
        )
        for value in values
    ):
        scenarios.add("redacted_thinking")

    if any(
        isinstance(value, dict) and value.get("type") == "tool_use"
        for value in values
    ):
        scenarios.add("tool_use")

    if any(
        isinstance(value, dict) and value.get("type") == "tool_result"
        for value in values
    ):
        scenarios.add("tool_result")

    if any(
        isinstance(value, dict)
        and isinstance(value.get("usage"), dict)
        and bool(value["usage"])
        for value in values
    ):
        scenarios.add("usage")

    if any(
        isinstance(value, dict)
        and (
            bool(value.get("stop_reason"))
            or bool(value.get("raw_stop_reason"))
            or (
                isinstance(value.get("delta"), dict)
                and bool(value["delta"].get("stop_reason"))
            )
        )
        for value in values
    ):
        scenarios.add("stop_reason")

    return scenarios


def _walk_values(value: Any) -> list[Any]:
    values = [value]
    if isinstance(value, dict):
        for item in value.values():
            values.extend(_walk_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_walk_values(item))
    return values


def _parse_required_adapter_counts(values: list[str]) -> dict[str, int]:
    return _parse_required_counts(values, "--require-recorded-adapter")


def _parse_required_model_counts(values: list[str]) -> dict[str, int]:
    return _parse_required_counts(values, "--require-recorded-model")


def _parse_required_counts(values: list[str], option_name: str) -> dict[str, int]:
    requirements: dict[str, int] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"{option_name} must be NAME=N, got {raw!r}")
        name, raw_count = raw.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"{option_name} name is required")
        try:
            count = int(raw_count)
        except ValueError as exc:
            raise ValueError(
                f"{option_name} count must be an integer, got {raw!r}"
            ) from exc
        if count < 0:
            raise ValueError(f"{option_name} count must be non-negative, got {raw!r}")
        requirements[name] = count
    return requirements


def _validate_anthropic_request_fixture(
    path: Path,
    fixture: dict[str, Any],
    adapter: AnthropicNativeAdapter,
    result: ValidationResult,
) -> None:
    request_case = fixture.get("request")
    if not request_case:
        return
    request_body = adapter.build_request(**request_case["input"])
    expected = request_case["expected_body"]
    if request_body != expected:
        result.failures.append(
            f"{path}: request snapshot differs: "
            f"expected={_compact_json(expected)} actual={_compact_json(request_body)}"
        )


def _validate_anthropic_stream_fixture(
    path: Path,
    fixture: dict[str, Any],
    adapter: AnthropicNativeAdapter,
    result: ValidationResult,
) -> None:
    stream_case = fixture.get("stream")
    if not stream_case:
        return
    session = adapter.create_parser_session()
    turn_done: TurnDone | None = None
    for raw_chunk in stream_case["raw_chunks"]:
        for event in session.feed(raw_chunk):
            if isinstance(event, TurnDone):
                turn_done = event
    if turn_done is None:
        for event in session.finalize():
            if isinstance(event, TurnDone):
                turn_done = event

    actual = _turn_done_snapshot(turn_done) if turn_done is not None else None
    expected = stream_case["expected_turn_done"]
    if actual != expected:
        result.failures.append(
            f"{path}: stream snapshot differs: "
            f"expected={_compact_json(expected)} actual={_compact_json(actual)}"
        )


def _turn_done_snapshot(turn_done: TurnDone) -> dict[str, Any]:
    return {
        "stop_reason": turn_done.stop_reason,
        "raw_stop_reason": turn_done.raw_stop_reason,
        "usage": turn_done.usage.to_dict() if turn_done.usage else {},
        "content": [_content_block_snapshot(block) for block in turn_done.content],
        "tool_calls": [
            {
                "id": tool_call.id,
                "name": tool_call.name,
                "input": tool_call.input,
                "encoding": tool_call.encoding,
            }
            for tool_call in turn_done.tool_calls
        ],
        "invalid_tool_calls": [
            _content_block_snapshot(block) for block in turn_done.invalid_tool_calls
        ],
    }


def _content_block_snapshot(block: Any) -> dict[str, Any]:
    if isinstance(block, ReasoningBlock):
        return {
            "type": "reasoning",
            "text": block.text,
            "signature": block.signature,
            "redacted": block.redacted,
            "data": block.data,
        }
    if isinstance(block, TextBlock):
        return {"type": "text", "text": block.text}
    if isinstance(block, ToolUseBlock):
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }
    if isinstance(block, InvalidToolCall):
        return {
            "type": "invalid_tool_call",
            "id": block.id,
            "name": block.name,
            "raw_args": block.raw_args,
            "parse_error": block.parse_error,
            "index": block.index,
            "encoding": block.encoding,
        }
    raise TypeError(f"unsupported content block: {block!r}")


def _compact_json(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(text) > 800:
        return text[:800] + "..."
    return text


def _print_result(result: ValidationResult) -> None:
    status = "ok" if result.ok else "failed"
    if result.skipped and result.ok:
        status = "skipped"
    details = ""
    if result.by_adapter_kind:
        by_adapter = ",".join(
            f"{adapter_kind}:{count}"
            for adapter_kind, count in sorted(result.by_adapter_kind.items())
        )
        details = f" adapters={by_adapter}"
    if result.by_model:
        by_model = ",".join(
            f"{model_name}:{count}"
            for model_name, count in sorted(result.by_model.items())
        )
        details += f" models={by_model}"
    if result.raw_chunks:
        details += f" raw_chunks={result.raw_chunks}"
    if result.scenarios:
        details += " scenarios=" + ",".join(sorted(result.scenarios))
    print(f"{result.name}: {status} checked={result.checked}{details}")
    for failure in result.failures:
        print(f"  - {failure}")


def _validation_report(results: list[ValidationResult]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "ok": all(result.ok for result in results),
        "summary": {
            "categories": len(results),
            "checked": sum(result.checked for result in results),
            "skipped": sum(1 for result in results if result.skipped),
            "failures": sum(len(result.failures) for result in results),
            "raw_chunks": sum(result.raw_chunks for result in results),
        },
        "results": [_result_to_dict(result) for result in results],
    }


def _result_to_dict(result: ValidationResult) -> dict[str, Any]:
    status = "ok" if result.ok else "failed"
    if result.skipped and result.ok:
        status = "skipped"
    return {
        "name": result.name,
        "status": status,
        "ok": result.ok,
        "checked": result.checked,
        "skipped": result.skipped,
        "failures": list(result.failures),
        "by_adapter_kind": dict(sorted(result.by_adapter_kind.items())),
        "by_model": dict(sorted(result.by_model.items())),
        "raw_chunks": result.raw_chunks,
        "scenarios": sorted(result.scenarios),
    }


if __name__ == "__main__":
    raise SystemExit(main())

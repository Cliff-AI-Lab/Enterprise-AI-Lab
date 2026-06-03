"""rd-replay-evals — 录制现有 monolith 事件流为 golden trace，replay 验证 engine 行为不变。"""

from .checks import (
    ReplayMismatch,
    check_event_sequence_match,
    check_stop_reason_match,
    check_tool_call_set_match,
    check_transcript_hash_match,
    check_usage_match,
)
from .dumper import EventRow, dump_event_rows
from .mocks import MockLLMProvider, MockToolExecutor
from .recorder import RecordingEventSink, finalize_to_trace
from .trace_format import GoldenTrace, TraceMeta, read_trace, write_trace

__version__ = "1.0.0"

__all__ = [
    "EventRow",
    "GoldenTrace",
    "MockLLMProvider",
    "MockToolExecutor",
    "RecordingEventSink",
    "ReplayMismatch",
    "TraceMeta",
    "check_event_sequence_match",
    "check_stop_reason_match",
    "check_tool_call_set_match",
    "check_transcript_hash_match",
    "check_usage_match",
    "dump_event_rows",
    "finalize_to_trace",
    "read_trace",
    "write_trace",
]

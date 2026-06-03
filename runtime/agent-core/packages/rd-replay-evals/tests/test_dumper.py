"""验证 dump_events_table_rows 把 codesphere-saas events 行翻译为 GoldenTrace。"""
from rd_replay_evals.dumper import EventRow, dump_event_rows


def test_dump_simple_run():
    rows = [
        EventRow(
            project_id="p1",
            event_type="ai_session",
            content_json=(
                '{"type":"agent_run_state","data":{"event":"agent_run_started",'
                '"run_id":"run_1","turn_id":"turn_1","seq":1,'
                '"timestamp_ms":1714377600000,"payload":{}}}'
            ),
            created_at_ms=1714377600000,
        ),
        EventRow(
            project_id="p1",
            event_type="ai_session",
            content_json=(
                '{"type":"tool_use","data":{"event":"tool_use",'
                '"run_id":"run_1","turn_id":"turn_1","seq":2,'
                '"timestamp_ms":1714377600100,"payload":{"tool_use_id":"tu_1"}}}'
            ),
            created_at_ms=1714377600100,
        ),
    ]
    trace = dump_event_rows(
        rows=rows,
        run_id="run_1",
        category="single_tool",
    )
    assert trace.meta.run_id == "run_1"
    assert len(trace.events) == 2
    assert trace.events[1].payload["tool_use_id"] == "tu_1"

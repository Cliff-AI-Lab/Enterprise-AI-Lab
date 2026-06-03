"""验证 dump_run 的 SQL 行 → EventRow 转换逻辑。"""
from datetime import datetime

from rd_tools.dump_run import row_to_event_row


class _FakeRow:
    """模拟 SQLAlchemy attribute-style row。"""

    def __init__(
        self,
        project_id: str,
        event_type: str,
        content: str,
        created_at: datetime,
    ) -> None:
        self.project_id = project_id
        self.event_type = event_type
        self.content = content
        self.created_at = created_at


def test_row_to_event_row_attribute_style():
    r = _FakeRow(
        project_id="p1",
        event_type="ai_session",
        content='{"type":"x","data":{}}',
        created_at=datetime(2026, 4, 29, 12, 0, 0),
    )
    er = row_to_event_row(r)
    assert er.project_id == "p1"
    assert er.event_type == "ai_session"
    assert er.created_at_ms > 0


def test_row_to_event_row_dict_style():
    """psycopg2 RealDictCursor 返回 dict 风格也支持。"""
    r = {
        "project_id": "p2",
        "event_type": "ai_session",
        "content": '{"type":"y","data":{}}',
        "created_at": datetime(2026, 4, 29, 13, 0, 0),
    }
    er = row_to_event_row(r)
    assert er.project_id == "p2"
    assert er.event_type == "ai_session"
    assert er.content_json == '{"type":"y","data":{}}'

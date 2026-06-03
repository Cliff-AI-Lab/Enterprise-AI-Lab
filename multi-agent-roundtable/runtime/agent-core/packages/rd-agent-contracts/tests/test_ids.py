"""验证 ID 类型 + IdGenerator protocol 行为。"""
import re

from rd_agent_contracts.ids import RunId, UuidIdGenerator


def test_id_types_are_str_subclass():
    """ID 类型必须可以当 str 用，但类型系统能区分。"""
    rid: RunId = RunId("run_123")
    assert isinstance(rid, str)
    assert rid == "run_123"


def test_uuid_id_generator_run_id_format():
    gen = UuidIdGenerator()
    rid = gen.run_id()
    assert isinstance(rid, str)
    # 格式：run_<uuid4>
    assert re.match(r"^run_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", rid)


def test_uuid_id_generator_all_kinds():
    gen = UuidIdGenerator()
    assert gen.turn_id().startswith("turn_")
    assert gen.message_id().startswith("msg_")
    assert gen.action_id().startswith("act_")
    assert gen.tool_use_id().startswith("tu_")
    assert gen.session_id().startswith("sess_")


def test_uuid_id_generator_unique():
    gen = UuidIdGenerator()
    ids = {gen.run_id() for _ in range(1000)}
    assert len(ids) == 1000  # 1000 个全唯一

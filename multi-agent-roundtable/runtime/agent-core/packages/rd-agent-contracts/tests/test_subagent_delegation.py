from __future__ import annotations

import pytest
from rd_agent_contracts import (
    SubagentDelegationContext,
    SubagentDelegationRuleSet,
    decide_subagent_delegation,
)

_PRODUCT_RULES = SubagentDelegationRuleSet(
    frontend_terms=(
        "前端",
        "前后端",
        "frontend",
        "front-end",
        "react",
        "vue",
        "页面",
        "界面",
    ),
    backend_terms=(
        "后端",
        "backend",
        "back-end",
        "fastapi",
        "django",
        "api",
        "接口",
        "数据库",
        "postgres",
        "postgresql",
        "mysql",
        "服务端",
    ),
    complex_product_terms=(
        "完整",
        "系统",
        "平台",
        "应用",
        "智能体",
        "助手",
        "上传",
        "pdf",
        "文档",
        "检索",
        "问答",
        "认证",
        "权限",
        "测试",
        "部署",
    ),
    product_generation_terms=(
        "[appgenerate]",
        "appgenerate",
        "设计",
        "生成",
        "创建",
        "搭建",
        "构建",
        "开发",
        "做一个",
        "实现一个",
        "应用系统",
        "管理系统",
    ),
    product_scope_terms=(
        "系统",
        "平台",
        "应用",
        "项目",
        "模块",
        "大屏",
        "wms",
        "crm",
        "erp",
    ),
    database_terms=(
        "数据库",
        "db",
        "sqlite",
        "postgres",
        "postgresql",
        "mysql",
        "schema",
    ),
)


def test_subagent_delegation_uses_recent_history_for_short_followups():
    decision = decide_subagent_delegation(
        SubagentDelegationContext(
            instruction="确认",
            session_messages=[
                {
                    "role": "user",
                    "content": (
                        "帮我做一个设备检修助手智能体，包含前后端设计及文档PDF上传，"
                        "封装好API接口"
                    ),
                }
            ],
            available_tool_names={"create_subagent_task"},
        ),
        rules=_PRODUCT_RULES,
    )

    assert decision.required is True
    assert decision.reason == "任务同时包含前端和后端/API工作流"


def test_open_subagent_tasks_keep_delegation_gate_closed():
    decision = decide_subagent_delegation(
        SubagentDelegationContext(
            instruction="继续",
            available_tool_names={"create_subagent_task"},
            has_open_subagent_tasks=True,
        )
    )

    assert decision.required is True
    assert (
        decision.reason
        == "已有子 Agent 任务尚未完成，root orchestrator 需要等待或检查子任务状态"
    )


def test_satisfied_subagent_tasks_do_not_force_more_delegation():
    decision = decide_subagent_delegation(
        SubagentDelegationContext(
            instruction="做一个前后端系统",
            available_tool_names={"create_subagent_task"},
            has_satisfied_subagent_tasks=True,
        )
    )

    assert decision.required is False
    assert decision.reason is None


def test_product_backend_database_continuation_requires_delegation():
    decision = decide_subagent_delegation(
        SubagentDelegationContext(
            instruction="执行吧",
            session_messages=[
                {
                    "role": "user",
                    "content": (
                        '设计"仓管家"WMS仓储系统。适用：电商仓库。模块：库存总览大屏、'
                        "出入库操作、库位管理、盘点任务、预警中心。要求：操作高效优先、"
                        "支持PDA扫码、大字体大按钮、状态颜色编码清晰[appGenerate][应用系统]"
                    ),
                },
                {"role": "user", "content": "要有后端和数据库"},
            ],
            available_tool_names={"create_subagent_task"},
        ),
        rules=_PRODUCT_RULES,
    )

    assert decision.required is True
    assert decision.reason == "任务要求后端/数据库且属于产品级应用生成"


def test_simple_followup_does_not_use_history_for_specific_edit():
    decision = decide_subagent_delegation(
        SubagentDelegationContext(
            instruction="把标题改成 Raytone",
            session_messages=[
                {"role": "user", "content": "之前做一个包含前后端和API的系统"}
            ],
            file_count=100,
            available_tool_names={"create_subagent_task"},
        ),
        rules=_PRODUCT_RULES,
    )

    assert decision.required is False
    assert decision.reason is None


def test_subagent_delegation_requires_orchestrator_and_tool():
    assert (
        decide_subagent_delegation(
            SubagentDelegationContext(
                instruction="请并行处理",
                available_tool_names={"create_subagent_task"},
            )
        ).required
        is True
    )
    assert (
        decide_subagent_delegation(
            SubagentDelegationContext(
                instruction="请并行处理",
                agent_kind="subagent",
                available_tool_names={"create_subagent_task"},
            )
        ).required
        is False
    )
    assert (
        decide_subagent_delegation(
            SubagentDelegationContext(
                instruction="请并行处理",
                available_tool_names={"write_file"},
            )
        ).required
        is False
    )


def test_subagent_delegation_default_rules_do_not_encode_product_terms():
    decision = decide_subagent_delegation(
        SubagentDelegationContext(
            instruction="做一个包含前后端 API 和数据库的管理系统",
            available_tool_names={"create_subagent_task"},
        )
    )

    assert decision.required is False
    assert decision.reason is None


def test_subagent_delegation_accepts_host_owned_rule_set():
    decision = decide_subagent_delegation(
        SubagentDelegationContext(
            instruction="please delegate this to another worker",
            available_tool_names={"spawn_child"},
        ),
        rules=SubagentDelegationRuleSet(
            create_task_tool_name="spawn_child",
            explicit_subagent_terms=("delegate",),
        ),
    )

    assert decision.required is True
    assert decision.reason == "用户明确要求子 Agent、多 Agent或并行任务"


def test_subagent_delegation_rule_set_validates_policy_shape():
    with pytest.raises(ValueError, match="create_task_tool_name"):
        SubagentDelegationRuleSet(create_task_tool_name="")

    with pytest.raises(ValueError, match="recent_history_window"):
        SubagentDelegationRuleSet(recent_history_window=0)

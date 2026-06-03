"""横切 ports protocol（共 6 个，加 Clock 在 clock.py 任务）。

Phase A 只定接口。实现：
- EventSink → A1 saas-adapter 包装 EventService（Phase B 起）；H1 OTel exporter（Phase C）
- Meter → A1 包装 billing_service（Phase B 起）；H2 实现（Phase C）
- BudgetGate → A1 包装 budget_controller（Phase B 起）；H2（Phase C）
- PolicyGate → A1 包装 command_policy（Phase B 起）；H3（Phase C）
- CancellationToken → P5 内部 + A1 桥接 NATS（Phase B 起）
- BlobWriter → A1 包装本地文件系统（Phase B 起）；S1 BlobStore；S3 backend（Phase C）
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .events import AgentEvent
from .usage import Usage


@runtime_checkable
class EventSink(Protocol):
    """事件接收器。所有 AgentEvent 通过此接口流出。"""

    async def emit(self, event: AgentEvent) -> None: ...


@runtime_checkable
class Meter(Protocol):
    """计量。Codex：必须支持 idempotency_key 防止 queue reclaim 双计费。"""

    async def record_usage(
        self,
        run_id: str,
        turn_id: str,
        usage: Usage,
        idempotency_key: str,
    ) -> None: ...


@runtime_checkable
class BudgetGate(Protocol):
    """预算前置 / 后置检查。before_turn 返回 False 则 engine 拒绝起 turn。"""

    async def before_turn(self, run_id: str) -> bool: ...
    async def after_turn(self, run_id: str, usage: Usage) -> None: ...


@runtime_checkable
class PolicyGate(Protocol):
    """安全策略 gate。三个挂点：tool 调用前、LLM 调用前、event 流出前。"""

    async def before_tool(
        self, run_id: str, tool_name: str, tool_input: dict[str, Any]
    ) -> bool: ...

    async def before_llm(
        self, run_id: str, messages: list[dict[str, Any]]
    ) -> bool: ...

    async def redact_event(self, event: AgentEvent) -> AgentEvent: ...


@runtime_checkable
class CancellationToken(Protocol):
    """协作式取消令牌。

    P5 engine 在 turn loop 内轮询；P6 tools / P7 runtime 接收 token 后能
    kill process group。
    """

    def is_cancelled(self) -> bool: ...
    def request_cancel(self) -> None: ...


@runtime_checkable
class BlobWriter(Protocol):
    """大对象写入。

    返回 (content_ref, content_sha256)，与 BlobRef 字段对齐。
    """

    async def write_large_payload(
        self, content: bytes, mime_type: str
    ) -> tuple[str, str]: ...

"""LLM 基础层：基于 rd-agent-core OpenAICompatLLMClient 直连 iruidong（OpenAI 兼容）。

满足 PRD 4.1.6：多模型接入（Qwen/DeepSeek 系列）+ 切换/降级 + token 统计。
单个 `generate()` 既服务专家发言，也服务主持人推理（议程/冲突/总结），
区别只在 system_prompt 与 messages，由调用方（Node 编排层）决定。
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

from rd_agent_contracts import Message, ToolExecutionContext
from rd_agent_core import OpenAICompatLLMClient, ProviderClientConfig, TurnRequest
from rd_llm_adapter.events import TextDelta, TurnDone, UsageUpdate

BASE_URL = os.getenv("RUIDONG_BASE_URL", "https://iruidong.com/v1")
API_KEY = os.getenv("RUIDONG_API_KEY", "")
MAX_TOKENS = int(os.getenv("ROUNDTABLE_MAX_TOKENS", "2048"))


def _models_from_env() -> list[str]:
    # 优先国产模型（PRD 6.1 硬约束）。可被 ROUNDTABLE_MODELS 覆盖（逗号分隔）。
    raw = os.getenv("ROUNDTABLE_MODELS", "qwen-plus,deepseek-chat")
    return [m.strip() for m in raw.split(",") if m.strip()]


MODELS = _models_from_env()
DEFAULT_MODEL = os.getenv("ROUNDTABLE_DEFAULT_MODEL") or (MODELS[0] if MODELS else "qwen-plus")

# UI「遍历模型」发现的可用模型(/models/discover 填充),专家可从中任选
DISCOVERED_MODELS: list[str] = []


def set_api_key(key: str) -> None:
    """运行时更新睿动 key(_client 每次调用读模块全局,立即生效)。"""
    global API_KEY
    API_KEY = key


def set_discovered(models: list[str]) -> None:
    global DISCOVERED_MODELS
    DISCOVERED_MODELS = models


def _client(model: str) -> OpenAICompatLLMClient:
    return OpenAICompatLLMClient(
        ProviderClientConfig(model=model, api_key=API_KEY, base_url=BASE_URL, max_tokens=MAX_TOKENS)
    )


async def generate(
    *,
    system_prompt: str,
    messages: list[dict[str, str]],
    model: str | None = None,
    run_id: str = "run",
    turn_id: str = "t1",
) -> AsyncIterator[dict[str, Any]]:
    """流式产出标准事件 dict：
    {type: delta, text} / {type: usage, model, input_tokens, ...} /
    {type: done, model} / {type: degrade, from, error} / {type: error, error}

    降级语义：请求模型失败且**尚未吐出任何文本**时，自动切到下一模型（PRD 切换/降级）。
    已经吐出文本后再失败，则直接报错，不重启避免重复内容。
    """
    requested = model or DEFAULT_MODEL
    chain = [requested] + [m for m in MODELS if m != requested]

    msgs = [
        Message(message_id=f"m{i}", role=m.get("role", "user"), content=m.get("content", ""), turn_id=turn_id)
        for i, m in enumerate(messages)
    ]
    ctx = ToolExecutionContext(project_id="roundtable")

    last_err: Exception | None = None
    for mdl in chain:
        emitted = False
        req = TurnRequest(
            run_id=run_id,
            turn_id=turn_id,
            messages=msgs,
            tool_context=ctx,
            model=mdl,
            system_prompt=system_prompt,
        )
        try:
            async for ev in _client(mdl).stream_turn(req):
                if isinstance(ev, TextDelta):
                    if ev.text:
                        emitted = True
                        yield {"type": "delta", "text": ev.text}
                elif isinstance(ev, UsageUpdate):
                    yield {"type": "usage", "model": mdl, **ev.to_dict()}
                elif isinstance(ev, TurnDone):
                    yield {"type": "done", "model": mdl}
            return
        except Exception as e:  # noqa: BLE001 — 降级链需要兜住任意 provider 异常
            last_err = e
            if emitted:
                yield {"type": "error", "model": mdl, "error": str(e)[:300]}
                return
            yield {"type": "degrade", "from": mdl, "error": str(e)[:200]}
            continue

    yield {"type": "error", "error": str(last_err)[:300] if last_err else "all models failed"}

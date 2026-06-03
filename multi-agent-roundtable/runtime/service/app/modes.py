"""多智能体协作模式扩展(借鉴 TelegramAgent 三房):接龙 / 头脑风暴 / 打磨。

与圆桌共用一套事件协议(meeting.started / moderator.turn / topic.started / turn /
conclusion / meeting.finished),因此 UI 渲染、落库、会议记录回放、纪要导出全部复用。
每位专家依旧带各自的 模型 / skills / 知识。
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from .knowledge import knowledge_context
from .roundtable import HOST_NAME, MODERATOR, _collect, _extract_json
from .skills import skill_guidance


def _sys(expert: dict, task: str, extra: str = "") -> str:
    kn = knowledge_context(expert.get("id", ""), task) if expert.get("knowledge_ids") else ""
    sk = skill_guidance(expert.get("skills") or [])
    return expert["persona"] + f"\n\n协作任务:{task}\n" + (sk + "\n" if sk else "") + (kn + "\n" if kn else "") + extra


def _turn(e: dict, text: str, u: dict, phase: str | None = None) -> dict:
    ev = {"type": "turn", "topic_index": 0, "expert_id": e["id"], "expert_name": e["name"],
          "domain": e["domain"], "model": e.get("model") or "", "text": text, "usage": u}
    if phase:
        ev["phase"] = phase
    return ev


def _started(mode: str, task: str, experts: list[dict]) -> list[dict]:
    return [
        {"type": "meeting.started", "topic": task, "mode": mode,
         "experts": [{"id": e["id"], "name": e["name"], "domain": e["domain"]} for e in experts]},
        {"type": "topic.started", "index": 0, "title": task},
    ]


async def run_relay(*, task: str, experts: list[dict], model: str | None = None,
                    rounds: int = 1) -> AsyncIterator[dict]:
    """接龙:专家依序发言,每人在前面成果基础上推进,最后主持人整合成稿。"""
    for ev in _started("relay", task, experts):
        yield ev
    order = " → ".join(e["name"] for e in experts)
    yield {"type": "moderator.turn", "phase": "opening", "name": HOST_NAME,
           "text": f"接龙协作开始。任务:{task}。发言顺序:{order},共 {rounds} 轮——每人在前一棒基础上实质推进,不重复、不空转。",
           "order": [e["name"] for e in experts]}
    chain: list[tuple[str, str]] = []
    for r in range(rounds):
        for e in experts:
            done = "\n".join(f"{i+1}. {n}:{t}" for i, (n, t) in enumerate(chain)) or "(你是第一棒)"
            text, u = await _collect(
                _sys(e, task, "接龙规则:接住上一棒,在已有成果上推进一步,不重复已有内容。"),
                f"已有接龙成果:\n{done}\n\n轮到你。基于以上推进(3-5 句,结论先行)。",
                e.get("model") or model)
            yield _turn(e, text, u)
            chain.append((e["name"], text))
    cc_text, u = await _collect(
        MODERATOR + " 你在收束一次接龙协作。",
        f"任务:{task}\n接龙记录:\n" + "\n".join(f"- {n}:{t}" for n, t in chain)
        + "\n把接龙成果整合为最终输出(结构化、可直接使用,保留各棒的关键贡献)。",
        model)
    yield {"type": "conclusion", "conclusion": cc_text, "risks": [], "actions": []}
    yield {"type": "meeting.finished", "usage_total": {}}


async def run_brainstorm(*, task: str, experts: list[dict], model: str | None = None,
                         rounds: int = 1) -> AsyncIterator[dict]:
    """头脑风暴:全员并行独立出想法(互不干扰),完成即流出,最后主持人聚类精选。"""
    for ev in _started("brainstorm", task, experts):
        yield ev
    yield {"type": "moderator.turn", "phase": "opening", "name": HOST_NAME,
           "text": f"头脑风暴开始。任务:{task}。各位**并行独立**出想法,互不干扰;我最后做聚类与精选。"}
    ideas: list[tuple[str, str]] = []

    async def one(e: dict) -> tuple[dict, str, dict]:
        text, u = await _collect(
            _sys(e, task, "头脑风暴规则:大胆发散,给出你领域视角下最有价值的想法。"),
            "给出 2-3 个想法,每个一句话点子 + 一句话理由。不许保守复述常识。",
            e.get("model") or model)
        return e, text, u

    tasks = [asyncio.create_task(one(e)) for e in experts]
    for fut in asyncio.as_completed(tasks):
        e, text, u = await fut
        yield _turn(e, text, u)
        ideas.append((e["name"], text))
    agg_raw, u = await _collect(
        MODERATOR + " 你在聚合头脑风暴结果。",
        f"任务:{task}\n各专家想法:\n" + "\n".join(f"- {n}:{t}" for n, t in ideas)
        + '\n去重聚类后精选最有价值的 3-5 个方向。只输出 JSON:'
        '{"conclusion": "2-3 句聚合总结", "actions": ["精选方向,每条一句话(标注来自谁)"]}',
        model)
    agg = _extract_json(agg_raw)
    if not isinstance(agg, dict):
        agg = {"conclusion": agg_raw, "actions": []}
    yield {"type": "conclusion", "conclusion": agg.get("conclusion", ""),
           "risks": [], "actions": agg.get("actions", [])}
    yield {"type": "meeting.finished", "usage_total": {}}


async def run_polish(*, task: str, experts: list[dict], model: str | None = None,
                     rounds: int = 1) -> AsyncIterator[dict]:
    """打磨:第 1 位专家创作初稿,其余专家评审,创作者按意见修订,循环 N 轮。"""
    producer, critics = experts[0], experts[1:]
    for ev in _started("polish", task, experts):
        yield ev
    yield {"type": "moderator.turn", "phase": "opening", "name": HOST_NAME,
           "text": f"打磨协作开始。任务:{task}。由 {producer['name']} 创作初稿,"
                   f"{'、'.join(c['name'] for c in critics)} 担任评审,共 {rounds} 轮「评审→修订」。"}
    draft, u = await _collect(
        _sys(producer, task, "你是本次协作的创作者。"),
        "产出第一版完整成果(可直接使用的成稿,不是提纲)。",
        producer.get("model") or model)
    yield _turn(producer, draft, u, phase=None)
    for r in range(rounds):
        crits: list[tuple[str, str]] = []
        for c in critics:
            ct, u = await _collect(
                _sys(c, task, "你是评审,只提对成果质量真正有影响的意见。"),
                f"当前稿:\n{draft}\n\n给出最关键的修改意见(2-4 条,具体、可执行,指明位置)。",
                c.get("model") or model)
            yield _turn(c, ct, u, phase="followup")
            crits.append((c["name"], ct))
        draft, u = await _collect(
            _sys(producer, task, "你是创作者,正在按评审意见修订。"),
            f"当前稿:\n{draft}\n\n评审意见:\n" + "\n".join(f"- {n}:{t}" for n, t in crits)
            + "\n\n吸收合理意见,输出修订后的完整成稿(不要写修改说明,直接给成稿)。",
            producer.get("model") or model)
        yield _turn(producer, draft, u)
    yield {"type": "conclusion", "conclusion": draft, "risks": [],
           "actions": [f"已完成 {rounds} 轮打磨,可直接采用上述终稿"]}
    yield {"type": "meeting.finished", "usage_total": {}}


MODE_RUNNERS = {"relay": run_relay, "brainstorm": run_brainstorm, "polish": run_polish}
MODE_NAMES = {"relay": "接龙", "brainstorm": "头脑风暴", "polish": "打磨"}

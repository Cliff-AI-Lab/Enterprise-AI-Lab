"""主持人 Agent + 圆桌编排（PRD 4.1.3 智能主持人 / 4.1.4 结论输出）。

流程（参考架构的会议主循环）：
  议程拆解 → 逐议题[ 调度发言(每轮≥2人) → 冲突检测 → (追问) → 阶段总结 ] → 最终结论/风险/行动

主持人是隐藏编排者，所有跨专家信息流经它裁剪后再分发，专家之间不直接对话。
所有 LLM 调用复用 llm.generate()（已接 iruidong 多模型 + 降级）。
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from .llm import generate
from .knowledge import knowledge_context
from .skills import skill_guidance

MODERATOR = (
    "你是企业圆桌会议的主持人 Agent。职责：拆议程、调度发言、识别分歧、聚合观点、阶段总结、生成结论。"
    "你不替专家发表领域观点，只做组织与提炼。输出务必克制、结构化。"
)


async def _collect(system_prompt: str, user: str, model: str | None) -> tuple[str, dict]:
    """跑一次完整 LLM 回合，返回 (文本, usage)。"""
    text = ""
    usage: dict = {}
    async for ev in generate(
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": user}],
        model=model,
    ):
        t = ev.get("type")
        if t == "delta":
            text += ev.get("text", "")
        elif t == "usage":
            usage = {k: ev[k] for k in ("input_tokens", "output_tokens", "total_tokens") if k in ev}
        elif t == "error":
            raise RuntimeError(ev.get("error", "llm error"))
    return text.strip(), usage


def _extract_json(s: str, prefer: str = "obj") -> Any:
    """从模型输出里抠出第一个完整 JSON。prefer 决定先找对象还是数组
    （对象里常嵌数组，若先找 '[' 会误抓内层数组导致解析失败）。"""
    s = s.replace("```json", "```").replace("```", "")
    order = (("{", "}"), ("[", "]")) if prefer == "obj" else (("[", "]"), ("{", "}"))
    for open_c, close_c in order:
        i = s.find(open_c)
        if i == -1:
            continue
        depth = 0
        for j in range(i, len(s)):
            if s[j] == open_c:
                depth += 1
            elif s[j] == close_c:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(s[i : j + 1])
                    except json.JSONDecodeError:
                        break
    return None


def _add_usage(total: dict, u: dict) -> None:
    for k in ("input_tokens", "output_tokens", "total_tokens"):
        total[k] = total.get(k, 0) + int(u.get(k, 0) or 0)


def _context_block(log: list[tuple[str, str, str]], topic: str, limit: int = 6) -> str:
    rel = [(name, text) for (t, name, text) in log if t == topic][-limit:]
    if not rel:
        return ""
    lines = [f"- {name}：{text}" for name, text in rel]
    return "本议题已有发言（供参考，不要重复）：\n" + "\n".join(lines)


async def gen_agenda(*, topic: str, description: str, experts: list[dict],
                     model: str | None = None, usage_acc: dict | None = None) -> list[str]:
    """议程拆解（PRD 4.1.3 AC1：至少 3 个议题）。返回议题标题列表。"""
    names = "、".join(e["name"] for e in experts)
    ag_text, u = await _collect(
        MODERATOR + " 现在只拆解议程。",
        f"会议主题：{topic}\n背景：{description or '（无额外背景）'}\n参会专家：{names}\n"
        "把主题拆成 3-5 个有逻辑顺序、彼此不重叠的讨论议题。只输出 JSON 数组，每个元素是一句议题标题。",
        model,
    )
    if usage_acc is not None:
        _add_usage(usage_acc, u)
    agenda = _extract_json(ag_text, prefer="arr")
    if not isinstance(agenda, list) or not agenda:
        agenda = [topic]
    return [str(x) for x in agenda][:5]


HOST_NAME = "主持人"


async def gen_opening(*, topic: str, description: str, experts: list[dict], agenda: list[str],
                      model: str | None = None, usage_acc: dict | None = None) -> dict:
    """主持人开场白:欢迎、点题、介绍专家阵容、预告议程(让主持人在交互中可见)。"""
    names = "、".join(f"{e['name']}({e['domain']})" for e in experts)
    text, u = await _collect(
        MODERATOR + " 现在做会议开场。",
        f"会议主题:{topic}\n背景:{description or '无'}\n参会专家:{names}\n"
        f"议程:{json.dumps(agenda, ensure_ascii=False)}\n"
        "做一段开场白(3-4 句):点明本次会议要解决的决策问题、介绍参会专家及各自看什么角度、"
        "预告议程推进方式。口吻干练专业,不要客套堆砌。",
        model,
    )
    if usage_acc is not None:
        _add_usage(usage_acc, u)
    return {"type": "moderator.turn", "phase": "opening", "name": HOST_NAME, "text": text}


def _followups_for(cf: dict, experts: list[dict]) -> list[dict]:
    """按主持人给的 involved 宽松匹配出要追问的专家;匹配不上则全员回应(避免空转)。"""
    raw = [str(x) for x in (cf.get("involved") or [])]

    def hit(e: dict) -> bool:
        short = e["name"].split("·")[-1]
        cands = {e["name"], short, e["domain"], e["id"]}
        return any(any(inv == c or inv in c or c in inv for c in cands) for inv in raw)

    matched = [e for e in experts if hit(e)]
    return matched or list(experts)


async def run_topic(*, topic: str, item: str, ti: int, experts: list[dict],
                    prior_log: list[tuple[str, str, str]], model: str | None = None,
                    max_followup: int = 1, intervention: str = "",
                    usage_acc: dict | None = None) -> AsyncIterator[dict]:
    """跑一个议题:发言(每轮≥2人)→冲突检测→(追问)→阶段总结。可独立调用(分步会议)。

    PRD 4.1.3 AC2:每轮调度≥2 名专家、同一专家连续≤2 轮——本设计每位专家每议题发言 1 次、
    至多再追问 1 次(连续≤2),且参会下限 2 人保证每轮≥2 人,天然满足。
    intervention:人类/主持人在本议题的指引,注入发言上下文(P1 干预)。
    """
    def acc(u: dict) -> None:
        if usage_acc is not None:
            _add_usage(usage_acc, u)

    log = list(prior_log)
    yield {"type": "topic.started", "index": ti, "title": item}

    # 主持人引入议题 + 安排发言顺序(组织/调度在交互流中可见)
    names_d = "、".join(f"{e['name']}({e['domain']})" for e in experts)
    host_raw, u0 = await _collect(
        MODERATOR + " 你在主持会议:引入议题并安排本轮发言顺序。",
        f"会议主题:{topic}。现在进入第 {ti+1} 个议题:「{item}」。参会专家:{names_d}。\n"
        + (f"用户刚给出指引:{intervention},安排时要承接它。\n" if intervention else "")
        + "根据议题与各专家领域的相关度决定谁先讲、谁后讲。只输出 JSON:"
        '{"intro": "2-3句:干练引入议题(点明要回答的决策问题)并宣布发言安排(按顺序点名)", '
        '"order": ["按发言先后排列的专家名"]}',
        model,
    )
    acc(u0)
    host = _extract_json(host_raw)
    speak_order = list(experts)
    if isinstance(host, dict):
        # 按主持人给的顺序重排(宽松名字匹配),没排到的专家按原序补在后面
        ordered = []
        for nm in host.get("order") or []:
            nm = str(nm)
            for e in experts:
                if e in ordered:
                    continue
                short = e["name"].split("·")[-1]
                if nm == e["name"] or nm in e["name"] or short in nm or e["domain"] in nm:
                    ordered.append(e)
                    break
        speak_order = ordered + [e for e in experts if e not in ordered]
        intro_text = host.get("intro") or host_raw
    else:
        intro_text = host_raw
    yield {"type": "moderator.turn", "phase": "topic_intro", "topic_index": ti,
           "name": HOST_NAME, "text": intro_text,
           "order": [e["name"] for e in speak_order]}

    intro = f"\n\n会议主题：{topic}。当前讨论议题：{item}。\n"
    if intervention:
        intro += f"【用户/主持人指引,请在发言中优先回应】：{intervention}\n"

    round_points: list[tuple[dict, str]] = []
    for expert in speak_order:
        kn = knowledge_context(expert.get("id", ""), item) if expert.get("knowledge_ids") else ""
        sk = skill_guidance(expert.get("skills") or [])
        sys = (expert["persona"] + intro + (sk + "\n" if sk else "")
               + (kn + "\n" if kn else "") + _context_block(log, item))
        # 每个专家可单独指定模型(睿动多模型),缺省回退会议级模型
        e_model = expert.get("model") or model
        text, u = await _collect(
            sys, f"针对当前议题「{item}」，给出你这个领域最关键的判断（2-4 句，结论先行，不要寒暄）。", e_model)
        acc(u)
        yield {"type": "turn", "topic_index": ti, "expert_id": expert["id"],
               "expert_name": expert["name"], "domain": expert["domain"],
               "model": (u.get("model") if isinstance(u, dict) else None) or e_model or "",
               "text": text, "usage": u}
        round_points.append((expert, text))
        log.append((item, expert["name"], text))

    points_text = "\n".join(f"- {e['name']}（{e['domain']}）：{t}" for e, t in round_points)

    # 冲突检测（AC3）
    cf_text, u = await _collect(
        MODERATOR + " 你在做冲突检测。",
        f"议题：{item}\n各专家观点：\n{points_text}\n"
        "判断专家之间是否存在**值得当场澄清的实质分歧**：即在结论方向、关键假设、"
        "执行路径或优先级排序上出现真实对立或不一致(仅措辞或侧重点不同不算分歧)。"
        "只要存在这类实质分歧就置 has_conflict=true。\n"
        '只输出 JSON：{"has_conflict": true/false, "summary": "分歧概述", '
        '"question": "把分歧逼到决策点的一句追问", "involved": ["涉及分歧的专家名"]}',
        model,
    )
    acc(u)
    cf = _extract_json(cf_text)
    if not isinstance(cf, dict):
        cf = {"has_conflict": False}
    if cf.get("has_conflict") and max_followup > 0:
        followups = _followups_for(cf, experts)
        yield {"type": "conflict", "topic_index": ti, "summary": cf.get("summary", ""),
               "question": cf.get("question", ""), "involved": [e["name"] for e in followups]}
        for expert in followups:
            sys = expert["persona"] + f"\n\n会议议题：{item}。主持人就分歧追问：{cf.get('question', '')}"
            if intervention:
                sys += f"\n另注意用户指引：{intervention}"
            text, u = await _collect(sys, "正面回应追问，表明立场并给理由（2-3 句）。",
                                     expert.get("model") or model)
            acc(u)
            yield {"type": "turn", "topic_index": ti, "phase": "followup", "expert_id": expert["id"],
                   "expert_name": expert["name"], "domain": expert["domain"], "text": text, "usage": u}
            log.append((item, expert["name"], text))

    # 阶段总结（AC4）
    ss_text, u = await _collect(
        MODERATOR + " 你在做阶段总结。",
        f"议题：{item}\n讨论记录：\n{points_text}\n"
        '输出 JSON：{"core": ["各方核心观点"], "consensus": ["共识点"], "divergence": ["分歧点"]}',
        model,
    )
    acc(u)
    ss = _extract_json(ss_text)
    if not isinstance(ss, dict):
        ss = {}
    ss = {"title": item, **{k: ss.get(k, []) for k in ("core", "consensus", "divergence")}}
    yield {"type": "stage_summary", "topic_index": ti, **ss}


async def gen_conclusion(*, topic: str, agenda: list[str], stage_summaries: list[dict],
                         model: str | None = None, usage_acc: dict | None = None) -> dict:
    """最终结论 + 风险清单 + 行动建议（PRD 4.1.4）。"""
    cc_text, u = await _collect(
        MODERATOR + " 你在生成会议最终结论、结构化风险清单与行动建议。",
        f"会议主题：{topic}\n各议题阶段总结：\n{json.dumps(stage_summaries, ensure_ascii=False)}\n"
        '输出 JSON：{"conclusion": "3-5 句最终结论与建议", '
        '"risks": [{"risk": "风险描述", "topic": "涉及议题", "expert_view": "相关专家观点"}], '
        '"actions": ["下一步行动建议"]}',
        model,
    )
    if usage_acc is not None:
        _add_usage(usage_acc, u)
    cc = _extract_json(cc_text)
    if not isinstance(cc, dict):
        cc = {"conclusion": cc_text, "risks": [], "actions": []}
    return {"type": "conclusion", "conclusion": cc.get("conclusion", ""),
            "risks": cc.get("risks", []), "actions": cc.get("actions", []),
            "agenda": agenda, "stage_summaries": stage_summaries}


async def run_meeting(*, topic: str, description: str, experts: list[dict],
                      model: str | None = None, max_followup: int = 1) -> AsyncIterator[dict]:
    """一次性跑完整场会议(快速路径)。分步会议见 main.py 的 /meeting/* 端点,复用同一批构件。"""
    total_usage: dict = {}
    yield {"type": "meeting.started", "topic": topic,
           "experts": [{"id": e["id"], "name": e["name"], "domain": e["domain"]} for e in experts]}
    agenda = await gen_agenda(topic=topic, description=description, experts=experts,
                              model=model, usage_acc=total_usage)
    yield {"type": "agenda", "items": agenda}
    yield await gen_opening(topic=topic, description=description, experts=experts,
                            agenda=agenda, model=model, usage_acc=total_usage)

    log: list[tuple[str, str, str]] = []
    stage_summaries: list[dict] = []
    for ti, item in enumerate(agenda):
        async for ev in run_topic(topic=topic, item=item, ti=ti, experts=experts, prior_log=log,
                                  model=model, max_followup=max_followup, usage_acc=total_usage):
            if ev["type"] == "turn":
                log.append((item, ev["expert_name"], ev["text"]))
            elif ev["type"] == "stage_summary":
                stage_summaries.append({k: ev.get(k, []) for k in ("title", "core", "consensus", "divergence")})
            yield ev

    yield await gen_conclusion(topic=topic, agenda=agenda, stage_summaries=stage_summaries,
                               model=model, usage_acc=total_usage)
    yield {"type": "meeting.finished", "usage_total": total_usage}

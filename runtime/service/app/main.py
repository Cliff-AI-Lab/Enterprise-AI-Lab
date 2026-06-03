"""温氏虚拟圆桌会议 — Python 专家运行时（基础层/智能层 generation kernel）。

Node 编排层（三房 + 会议循环 + 主持人调度）按需调用：
  POST /generate  —— 专家单轮发言 或 主持人推理（议程/冲突/聚合/总结），SSE 流式
  GET  /health    —— 服务 + 多模型配置自检
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

# 在导入 llm（其在模块加载期读取 env）之前装载 .env
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile  # noqa: E402
from fastapi.responses import FileResponse, Response, StreamingResponse  # noqa: E402

from .llm import API_KEY, BASE_URL, DEFAULT_MODEL, MODELS, generate  # noqa: E402
from .experts import PRESET_EXPERTS  # noqa: E402
from .roundtable import gen_agenda, gen_conclusion, gen_opening, run_meeting, run_topic  # noqa: E402
from . import knowledge, store  # noqa: E402

# 分步会议:待消费的人类干预(进程内,下次 advance 注入)
_pending_intervention: dict[str, str] = {}


async def _collect_text(system_prompt: str, user: str, model: str | None = None) -> str:
    """跑一次 LLM 回合,收集纯文本(非流式),供专家起草等内部用途。"""
    text = ""
    async for ev in generate(system_prompt=system_prompt,
                             messages=[{"role": "user", "content": user}], model=model):
        if ev.get("type") == "delta":
            text += ev.get("text", "")
    return text.strip()

app = FastAPI(title="Roundtable Runtime", version="0.1.0")

store.init_db()

_STATIC = Path(__file__).resolve().parent / "static"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "roundtable-runtime",
        "models": MODELS,
        "default_model": DEFAULT_MODEL,
        "base_url": BASE_URL,
        "has_key": bool(API_KEY),
    }


@app.get("/models")
def models() -> dict:
    from . import llm as llm_mod
    return {"models": MODELS, "default": DEFAULT_MODEL, "discovered": llm_mod.DISCOVERED_MODELS}


@app.post("/models/discover")
async def models_discover(req: Request) -> dict:
    """输入睿动 key 遍历可用模型;key 验证通过则热更新运行时 key 并持久到 .env。"""
    import httpx
    from . import llm as llm_mod
    b = await req.json()
    key = (b.get("api_key") or "").strip() or llm_mod.API_KEY
    if not key:
        raise HTTPException(400, "请提供睿动 API key")
    try:
        async with httpx.AsyncClient(timeout=20) as cli:
            r = await cli.get(f"{BASE_URL.rstrip('/')}/models",
                              headers={"Authorization": f"Bearer {key}"})
        if r.status_code >= 400:
            raise HTTPException(400, f"key 无效或无权限:HTTP {r.status_code} — {r.text[:120]}")
        ids = sorted({m.get("id", "") for m in r.json().get("data", []) if m.get("id")})
    except HTTPException:
        raise
    except Exception as ex:  # noqa: BLE001
        raise HTTPException(400, f"遍历失败:{str(ex)[:160]}")
    llm_mod.set_discovered(ids)
    if b.get("api_key"):  # 用户输入了新 key 且已验证可用 → 热更新 + 持久化
        llm_mod.set_api_key(key)
        env_path = Path(__file__).resolve().parent.parent / ".env"
        try:
            lines = env_path.read_text().splitlines()
            lines = [f"RUIDONG_API_KEY={key}" if ln.startswith("RUIDONG_API_KEY=") else ln for ln in lines]
            env_path.write_text("\n".join(lines) + "\n")
        except OSError:
            pass
        store.log("models.key_update", "", "key 已更新并验证")
    store.log("models.discover", "", f"{len(ids)} 个模型")
    return {"ok": True, "models": ids, "count": len(ids)}


@app.post("/models/test")
async def models_test(req: Request) -> dict:
    """对指定模型做联通测试:跑一次最小生成,返回时延与回包。"""
    b = await req.json()
    mdl = (b.get("model") or DEFAULT_MODEL).strip()
    t0 = time.time()
    try:
        reply = await _collect_text("你是连通性探针,只回「连接正常」四个字。", "ping", mdl)
        return {"ok": True, "model": mdl, "latency_s": round(time.time() - t0, 2), "reply": reply[:40]}
    except Exception as ex:  # noqa: BLE001
        return {"ok": False, "model": mdl, "latency_s": round(time.time() - t0, 2), "error": str(ex)[:200]}


@app.get("/experts")
def experts(domain: str | None = None, active_only: bool = False,
            page: int = 1, page_size: int = 100) -> dict:
    rows = store.list_experts(active_only=active_only) or PRESET_EXPERTS
    if domain:
        rows = [e for e in rows if e.get("domain") == domain]
    total = len(rows)
    start = max(0, (page - 1) * page_size)
    return {"experts": rows[start : start + page_size], "total": total,
            "page": page, "page_size": page_size,
            "domains": sorted({e.get("domain", "") for e in (store.list_experts(active_only=False) or PRESET_EXPERTS)})}


@app.get("/skills")
def skills_catalog() -> dict:
    from .skills import SKILLS
    return {"skills": [{k: s[k] for k in ("id", "name", "desc")} for s in SKILLS]}


@app.post("/experts")
async def create_expert(req: Request) -> dict:
    b = await req.json()
    if not (b.get("name") and b.get("domain") and b.get("persona")):
        raise HTTPException(400, "name / domain / persona 必填")
    e = store.create_expert(name=b["name"], domain=b["domain"], persona=b["persona"],
                            specialty=b.get("specialty", ""), skills=b.get("skills") or [],
                            model=b.get("model", ""))
    store.log("expert.create", e["id"], e["name"])
    return e


@app.put("/experts/{eid}")
async def update_expert(eid: str, req: Request) -> dict:
    if not store.get_expert(eid):
        raise HTTPException(404, "专家不存在")
    e = store.update_expert(eid, await req.json())
    store.log("expert.update", eid)
    return e


@app.delete("/experts/{eid}")
def delete_expert(eid: str) -> dict:
    store.delete_expert(eid)
    store.log("expert.delete", eid)
    return {"ok": True}


@app.post("/experts/{eid}/toggle")
def toggle_expert(eid: str) -> dict:
    e = store.get_expert(eid)
    if not e:
        raise HTTPException(404, "专家不存在")
    e2 = store.update_expert(eid, {"active": not e["active"]})
    store.log("expert.toggle", eid, str(e2["active"]))
    return e2


@app.post("/experts/register")
async def register_expert(req: Request) -> dict:
    """注册外部已有专家 Agent(OpenAI-compat)。探活成功才入库(PRD 4.1.1 AC4)。"""
    import httpx
    b = await req.json()
    name, domain, endpoint = b.get("name"), b.get("domain"), b.get("endpoint")
    if not (name and domain and endpoint):
        raise HTTPException(400, "name / domain / endpoint 必填")
    api_key, model = b.get("api_key", ""), b.get("model", "")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {"model": model or "default",
               "messages": [{"role": "user", "content": "ping"}], "max_tokens": 8, "stream": False}
    try:
        async with httpx.AsyncClient(timeout=15) as cli:
            r = await cli.post(endpoint, json=payload, headers=headers)
        if r.status_code >= 400:
            raise HTTPException(400, f"探活失败:HTTP {r.status_code} — {r.text[:160]}")
    except HTTPException:
        raise
    except Exception as ex:  # noqa: BLE001
        raise HTTPException(400, f"探活失败:{str(ex)[:160]}")
    e = store.create_expert(name=name, domain=domain,
                            persona=b.get("persona", f"你是{domain}领域的外部专家 {name}。"),
                            specialty=b.get("specialty", ""), source="registered",
                            kind="external", endpoint=endpoint, api_key=api_key)
    store.log("expert.register", e["id"], endpoint)
    return {"ok": True, "expert": e}


# ---- 知识(知识升级页)----
@app.get("/knowledge")
def list_knowledge(expert_id: str | None = None) -> dict:
    return {"docs": store.list_docs(expert_id=expert_id)}


@app.post("/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...), expert_id: str = Form(default="")) -> dict:
    data = await file.read()
    text = knowledge.extract_text_from_file(file.filename or "doc", data)
    if not text:
        raise HTTPException(400, "未能从文件中抽取到文本")
    d = store.add_doc(title=file.filename or "上传文档", source_type="file",
                      origin=file.filename or "", text=text, expert_id=expert_id or None)
    store.log("knowledge.upload", d["id"], file.filename or "")
    return {"ok": True, "doc": {"id": d["id"], "title": d["title"], "chars": len(text)}}


@app.post("/knowledge/wiki")
async def wiki_knowledge(req: Request) -> dict:
    b = await req.json()
    url = b.get("url")
    if not url:
        raise HTTPException(400, "url 必填")
    try:
        title, text = await knowledge.extract_text_from_url(url)
    except Exception as ex:  # noqa: BLE001
        raise HTTPException(400, f"抓取失败:{str(ex)[:160]}")
    if not text:
        raise HTTPException(400, "未能抽取到正文")
    d = store.add_doc(title=title, source_type="wiki", origin=url,
                      text=text, expert_id=b.get("expert_id") or None)
    store.log("knowledge.wiki", d["id"], url)
    return {"ok": True, "doc": {"id": d["id"], "title": d["title"], "chars": len(text)}}


@app.post("/knowledge/{did}/attach")
async def attach_knowledge(did: str, req: Request) -> dict:
    b = await req.json()
    eid = b.get("expert_id")
    e = store.get_expert(eid) if eid else None
    if not e:
        raise HTTPException(404, "专家不存在")
    ids = list(dict.fromkeys([*e.get("knowledge_ids", []), did]))
    store.update_expert(eid, {"knowledge_ids": ids})
    store.log("knowledge.attach", did, eid)
    return {"ok": True, "knowledge_ids": ids}


@app.delete("/knowledge/{did}")
def delete_knowledge(did: str) -> dict:
    store.delete_doc(did)
    store.log("knowledge.delete", did)
    return {"ok": True}


@app.post("/experts/from_knowledge")
async def expert_from_knowledge(req: Request) -> dict:
    """上传知识 → 快速形成业务专家:LLM 依据知识起草人设,建专家并挂知识。"""
    b = await req.json()
    name, domain = b.get("name"), b.get("domain")
    if not (name and domain):
        raise HTTPException(400, "name / domain 必填")
    doc_ids = b.get("doc_ids") or []
    docs = store.docs_by_ids(doc_ids)
    excerpt = "\n\n".join((d.get("text_content") or "")[:1500] for d in docs)[:6000]
    persona = await _collect_text(
        "你在为企业圆桌会议起草一个领域专家的人设(system prompt)。要求:结论先行、有专业边界、"
        "反 AI 腔、能落到具体动作或数字区间。只输出人设正文,不要解释。",
        f"专家名:{name}\n领域:{domain}\n专长:{b.get('specialty','')}\n"
        f"参考业务资料(据此塑造其专业视角):\n{excerpt or '(无)'}",
        b.get("model"),
    )
    persona = persona or f"你是{domain}领域专家{name},结论先行、只谈对决策有影响的因素。"
    e = store.create_expert(name=name, domain=domain, persona=persona,
                            specialty=b.get("specialty", ""), knowledge_ids=doc_ids, source="from_knowledge")
    store.log("expert.from_knowledge", e["id"], name)
    return {"ok": True, "expert": e}


@app.post("/meeting/run")
async def meeting_run(req: Request) -> StreamingResponse:
    """运行一场圆桌会议（SSE 流式：议程 / 发言 / 冲突 / 阶段总结 / 结论）。

    body: {topic, description?, expert_ids?: [...], model?, max_followup?}
    expert_ids 省略时用全部预置专家；给定时从预置库解析（外部注册专家后续接入）。
    """
    body = await req.json()
    topic = (body.get("topic") or "").strip()
    description = body.get("description", "") or ""
    model = body.get("model")
    max_followup = int(body.get("max_followup", 1))
    all_ids = [e["id"] for e in store.list_experts(active_only=True)] or [e["id"] for e in PRESET_EXPERTS]
    ids = body.get("expert_ids") or all_ids
    chosen = store.get_experts_by_ids(ids)

    async def event_stream():
        if not topic:
            yield f"data: {json.dumps({'type': 'error', 'error': 'topic required'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return
        if len(chosen) < 2:
            yield f"data: {json.dumps({'type': 'error', 'error': '至少需要 2 名专家'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return
        mid = store.create_meeting(topic=topic, description=description,
                                   expert_ids=[e["id"] for e in chosen], model=model,
                                   max_followup=max_followup, status="running")
        store.log("meeting.create", mid, topic)
        yield f"data: {json.dumps({'type': 'meeting.id', 'meeting_id': mid}, ensure_ascii=False)}\n\n"
        seq = 0
        try:
            async for evt in run_meeting(
                topic=topic,
                description=description,
                experts=chosen,
                model=model,
                max_followup=max_followup,
            ):
                store.save_event(mid, seq, evt); seq += 1
                if evt.get("type") == "agenda":
                    store.set_meeting(mid, agenda_json=json.dumps(evt.get("items", []), ensure_ascii=False))
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
            store.set_meeting(mid, status="done", finished_at=time.time())
        except Exception as e:  # noqa: BLE001
            store.set_meeting(mid, status="done")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)[:300]}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ============ 多智能体模式扩展(M9:接龙/头脑风暴/打磨)============
@app.post("/modes/run")
async def modes_run(req: Request) -> StreamingResponse:
    """跑一次协作模式(SSE)。body: {mode, task, expert_ids[≥2], model?, rounds?}
    事件协议与圆桌一致 → 落库/记录/导出全复用。"""
    from .modes import MODE_NAMES, MODE_RUNNERS
    body = await req.json()
    mode = body.get("mode", "")
    task = (body.get("task") or body.get("topic") or "").strip()
    rounds = max(1, min(int(body.get("rounds", 1)), 3))
    model = body.get("model")
    chosen = store.get_experts_by_ids(body.get("expert_ids") or [])

    async def stream():
        if mode not in MODE_RUNNERS:
            yield f"data: {json.dumps({'type':'error','error':'mode 须为 relay/brainstorm/polish'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"; return
        if not task:
            yield f"data: {json.dumps({'type':'error','error':'任务/主题必填'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"; return
        if len(chosen) < 2:
            yield f"data: {json.dumps({'type':'error','error':'至少选择 2 名专家'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"; return
        mid = store.create_meeting(topic=f"[{MODE_NAMES[mode]}] {task}", description="",
                                   expert_ids=[e["id"] for e in chosen], model=model,
                                   mode=mode, status="running")
        store.log("mode.run", mid, f"{mode} · {task[:40]}")
        yield f"data: {json.dumps({'type':'meeting.id','meeting_id':mid}, ensure_ascii=False)}\n\n"
        seq = 0
        try:
            async for ev in MODE_RUNNERS[mode](task=task, experts=chosen, model=model, rounds=rounds):
                store.save_event(mid, seq, ev); seq += 1
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            store.set_meeting(mid, status="done", finished_at=time.time())
        except Exception as e:  # noqa: BLE001
            store.set_meeting(mid, status="done", finished_at=time.time())
            yield f"data: {json.dumps({'type':'error','error':str(e)[:300]}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


# ============ 分步会议(M3 会议管理 + M4 人在环路 + M8 人类参与)============
def _rebuild_state(m: dict) -> tuple[list[tuple[str, str, str]], list[dict]]:
    """从已落库事件重建 (prior_log, stage_summaries),供断点续跑。"""
    agenda = m["agenda"]
    log: list[tuple[str, str, str]] = []
    summaries: list[dict] = []
    for ev in store.get_events(m["id"]):
        t = ev.get("type")
        if t in ("turn", "human.turn"):
            ti = ev.get("topic_index", m["cursor"])
            title = agenda[ti] if 0 <= ti < len(agenda) else ""
            log.append((title, ev.get("expert_name") or ev.get("name", "用户"), ev.get("text", "")))
        elif t == "stage_summary":
            summaries.append({k: ev.get(k, []) for k in ("title", "core", "consensus", "divergence")})
    return log, summaries


def _next_seq(mid: str) -> int:
    return len(store.get_events(mid))


@app.post("/meeting/create")
async def meeting_create(req: Request) -> dict:
    """创建会议(PRD 4.1.2 AC1):多选专家(≥2)→唯一 ID→准备中。"""
    b = await req.json()
    topic = (b.get("topic") or "").strip()
    if not topic:
        raise HTTPException(400, "会议主题必填")
    mode = b.get("mode", "roundtable")
    chosen = store.get_experts_by_ids(b.get("expert_ids") or [])
    if len(chosen) < 2:
        raise HTTPException(400, "至少选择 2 名专家")
    if mode == "1v1" and len(chosen) != 2:
        raise HTTPException(400, "1V1 模式需恰好 2 名专家")
    mid = store.create_meeting(topic=topic, description=b.get("description", ""),
                               expert_ids=[e["id"] for e in chosen], model=b.get("model"),
                               mode=mode, max_followup=int(b.get("max_followup", 1)), status="preparing")
    store.log("meeting.create", mid, topic)
    return {"ok": True, "meeting": store.get_meeting(mid)}


@app.post("/meeting/{mid}/agenda/generate")
async def meeting_agenda_generate(mid: str) -> dict:
    """自动拆解议程(PRD 4.1.3 AC1:至少 3 个议题),供用户确认/调整。"""
    m = store.get_meeting(mid)
    if not m:
        raise HTTPException(404, "会议不存在")
    experts = store.get_experts_by_ids(m["expert_ids"])
    agenda = await gen_agenda(topic=m["topic"], description=m["description"], experts=experts, model=m["model"])
    store.set_meeting(mid, agenda_json=json.dumps(agenda, ensure_ascii=False))
    return {"ok": True, "agenda": agenda}


@app.put("/meeting/{mid}/agenda")
async def meeting_agenda_confirm(mid: str, req: Request) -> dict:
    """用户确认/编辑议程(调整顺序、增删)。"""
    m = store.get_meeting(mid)
    if not m:
        raise HTTPException(404, "会议不存在")
    items = [str(x).strip() for x in (await req.json()).get("items", []) if str(x).strip()]
    if len(items) < 1:
        raise HTTPException(400, "议程不能为空")
    store.set_meeting(mid, agenda_json=json.dumps(items, ensure_ascii=False))
    store.log("meeting.agenda", mid, f"{len(items)} 题")
    return {"ok": True, "agenda": items}


@app.post("/meeting/{mid}/intervene")
async def meeting_intervene(mid: str, req: Request) -> dict:
    """人类干预(P1 4.2):注入一句指引,下次推进生效;同时入转写。"""
    m = store.get_meeting(mid)
    if not m:
        raise HTTPException(404, "会议不存在")
    text = (await req.json()).get("text", "").strip()
    if not text:
        raise HTTPException(400, "指引内容必填")
    _pending_intervention[mid] = (_pending_intervention.get(mid, "") + " " + text).strip()
    store.save_event(mid, _next_seq(mid), {"type": "intervention", "topic_index": m["cursor"], "text": text})
    store.log("meeting.intervene", mid, text[:60])
    return {"ok": True}


@app.post("/meeting/{mid}/speak")
async def meeting_speak(mid: str, req: Request) -> dict:
    """人类以参会者身份发言(P1 4.2 AC1):即时入转写,作为后续上下文与优先回应对象。"""
    m = store.get_meeting(mid)
    if not m:
        raise HTTPException(404, "会议不存在")
    text = (await req.json()).get("text", "").strip()
    if not text:
        raise HTTPException(400, "发言内容必填")
    evt = {"type": "human.turn", "topic_index": m["cursor"], "name": "我(用户)", "text": text}
    store.save_event(mid, _next_seq(mid), evt)
    # 把人类发言作为下一轮的优先回应指引(AC2)
    _pending_intervention[mid] = (_pending_intervention.get(mid, "") + f" 用户发言:{text} 请专家优先回应。").strip()
    return {"ok": True, "event": evt}


@app.post("/meeting/{mid}/advance")
async def meeting_advance(mid: str) -> StreamingResponse:
    """推进一个议题(SSE);全部议题完成后再调一次则生成结论。AC2 调度约束在 run_topic 内保证。"""
    m = store.get_meeting(mid)
    if not m:
        raise HTTPException(404, "会议不存在")
    experts = store.get_experts_by_ids(m["expert_ids"])
    agenda = m["agenda"]

    async def stream():
        nonlocal m
        if not agenda:
            yield f"data: {json.dumps({'type':'error','error':'请先生成并确认议程'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"; return
        if m["status"] == "paused":
            yield f"data: {json.dumps({'type':'error','error':'会议已被管理员暂停,恢复后才能推进'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"; return
        if m["status"] == "done":
            yield f"data: {json.dumps({'type':'error','error':'会议已结束'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"; return
        cursor = m["cursor"]
        seq = _next_seq(mid)
        started_yet = any(ev.get("type") == "meeting.started" for ev in store.get_events(mid))
        try:
            if not started_yet:
                started = {"type": "meeting.started", "topic": m["topic"],
                           "experts": [{"id": e["id"], "name": e["name"], "domain": e["domain"]} for e in experts]}
                store.save_event(mid, seq, started); seq += 1
                yield f"data: {json.dumps(started, ensure_ascii=False)}\n\n"
                ag = {"type": "agenda", "items": agenda}
                store.save_event(mid, seq, ag); seq += 1
                yield f"data: {json.dumps(ag, ensure_ascii=False)}\n\n"
                opening = await gen_opening(topic=m["topic"], description=m["description"],
                                            experts=experts, agenda=agenda, model=m["model"])
                store.save_event(mid, seq, opening); seq += 1
                yield f"data: {json.dumps(opening, ensure_ascii=False)}\n\n"
            if cursor < len(agenda):
                store.set_meeting(mid, status="running")
                prior_log, _ = _rebuild_state(m)
                interv = _pending_intervention.pop(mid, "")
                async for ev in run_topic(topic=m["topic"], item=agenda[cursor], ti=cursor,
                                          experts=experts, prior_log=prior_log, model=m["model"],
                                          max_followup=m["max_followup"], intervention=interv):
                    store.save_event(mid, seq, ev); seq += 1
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                store.set_meeting(mid, cursor=cursor + 1)
                done_topics = cursor + 1
                yield f"data: {json.dumps({'type':'topic.done','index':cursor,'remaining':len(agenda)-done_topics}, ensure_ascii=False)}\n\n"
            else:
                m2 = store.get_meeting(mid)
                _, summaries = _rebuild_state(m2)
                concl = await gen_conclusion(topic=m["topic"], agenda=agenda,
                                             stage_summaries=summaries, model=m["model"])
                store.save_event(mid, seq, concl); seq += 1
                yield f"data: {json.dumps(concl, ensure_ascii=False)}\n\n"
                fin = {"type": "meeting.finished", "usage_total": {}}
                store.save_event(mid, seq, fin)
                store.set_meeting(mid, status="done", finished_at=time.time())
                yield f"data: {json.dumps(fin, ensure_ascii=False)}\n\n"
        except Exception as e:  # noqa: BLE001
            yield f"data: {json.dumps({'type':'error','error':str(e)[:300]}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/meeting/{mid}/control")
async def meeting_control(mid: str, req: Request) -> dict:
    """人工接管(PRD 4.1.5 AC5):pause / resume / stop。"""
    m = store.get_meeting(mid)
    if not m:
        raise HTTPException(404, "会议不存在")
    action = (await req.json()).get("action")
    if action not in ("pause", "resume", "stop", "takeover"):
        raise HTTPException(400, "action 须为 pause/resume/stop/takeover")
    if action in ("pause", "takeover"):
        store.set_meeting(mid, status="paused")
    elif action == "resume":
        store.set_meeting(mid, status="running")
    else:
        store.set_meeting(mid, status="done", finished_at=time.time())
        store.save_event(mid, _next_seq(mid), {"type": "meeting.stopped", "by": "admin"})
    store.log("meeting.control", mid, action, actor="admin")
    return {"ok": True, "status": store.get_meeting(mid)["status"]}


SLOW_TURN_S = float(os.getenv("ROUNDTABLE_SLOW_TURN_S", "90"))


@app.get("/dashboard")
def dashboard(days: int = 7) -> dict:
    """会议监控(PRD 4.1.5):实时状态 / 专家响应时长 / 告警 / 运营统计。"""
    now = time.time()
    since = now - days * 86400
    all_meetings = store.list_meetings(limit=500)
    recent = [m for m in all_meetings if (m["created_at"] or 0) >= since]
    active = [m for m in all_meetings if m["status"] in ("preparing", "running", "paused")]

    active_detail, alerts = [], []
    expert_stat: dict[str, dict] = {}
    for m in recent:
        evts = store.get_events_ts(m["id"])
        prev_t = None
        turns = 0
        for ev, ts in evts:
            t = ev.get("type")
            if t == "turn":
                turns += 1
                dur = (ts - prev_t) if prev_t else None
                name = ev.get("expert_name", "?")
                st = expert_stat.setdefault(name, {"turns": 0, "total_s": 0.0, "max_s": 0.0, "slow": 0})
                st["turns"] += 1
                if dur is not None:
                    st["total_s"] += dur
                    st["max_s"] = max(st["max_s"], dur)
                    if dur > SLOW_TURN_S:
                        st["slow"] += 1
                        alerts.append({"time": ts, "kind": "slow_turn",
                                       "detail": f"{name} 响应 {dur:.0f}s 超阈值({SLOW_TURN_S:.0f}s) · 会议「{m['topic'][:24]}」"})
            elif t == "error":
                alerts.append({"time": ts, "kind": "api_fail",
                               "detail": f"会议「{m['topic'][:24]}」出错:{str(ev.get('error',''))[:80]}"})
            prev_t = ts
        if m["status"] in ("preparing", "running", "paused"):
            full = store.get_meeting(m["id"])
            active_detail.append({"id": m["id"], "topic": m["topic"], "status": m["status"],
                                  "experts": len(full["expert_ids"]),
                                  "expert_ids": full["expert_ids"], "turns": turns,
                                  "progress": f"{full['cursor']}/{len(full['agenda']) or '?'}"})
    experts_out = [
        {"name": k, "turns": v["turns"],
         "avg_s": round(v["total_s"] / v["turns"], 1) if v["turns"] else 0,
         "max_s": round(v["max_s"], 1), "slow": v["slow"]}
        for k, v in sorted(expert_stat.items(), key=lambda kv: -kv[1]["turns"])
    ]
    done = [m for m in recent if m["status"] == "done" and m.get("finished_at")]
    avg_min = round(sum(m["finished_at"] - m["created_at"] for m in done) / len(done) / 60, 1) if done else 0
    alerts.sort(key=lambda a: -a["time"])
    # 正在讨论的专家(去重,跨所有进行中会议)
    discussing_ids: list[str] = []
    for ad in active_detail:
        for eid in ad.pop("expert_ids"):
            if eid not in discussing_ids:
                discussing_ids.append(eid)
    discussing = [e["name"] for e in store.get_experts_by_ids(discussing_ids)]
    return {"active_count": len(active), "active": active_detail,
            "experts_discussing": discussing, "minutes_total": store.minutes_count(),
            "experts": experts_out, "alerts": alerts[:20],
            "stats": {"days": days, "meetings": len(recent), "done": len(done),
                      "avg_duration_min": avg_min,
                      "total_turns": sum(v["turns"] for v in expert_stat.values())},
            "slow_threshold_s": SLOW_TURN_S,
            "audit": store.recent_audit(12)}


@app.get("/meetings")
def meetings_list(status: str | None = None) -> dict:
    rows = store.list_meetings()
    if status:
        rows = [r for r in rows if r["status"] == status]
    return {"meetings": rows}


@app.get("/meeting/{mid}/export")
def meeting_export(mid: str, format: str = "md") -> Response:
    """导出会议纪要 MD / DOCX / PDF(PRD 4.1.4 AC4)。"""
    from . import export as exp
    if not store.get_meeting(mid):
        raise HTTPException(404, "会议不存在")
    s = exp.build_struct(mid)
    topic = (s["meeting"]["topic"] or "meeting")[:40]
    fn = f"会议纪要-{topic}"
    if format == "md":
        data = exp.to_markdown(s).encode("utf-8"); ct = "text/markdown; charset=utf-8"; ext = "md"
    elif format == "docx":
        data = exp.to_docx(s); ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"; ext = "docx"
    elif format == "pdf":
        data = exp.to_pdf(s); ct = "application/pdf"; ext = "pdf"
    else:
        raise HTTPException(400, "format 须为 md/docx/pdf")
    store.log("meeting.export", mid, format)
    from urllib.parse import quote
    cd = f"attachment; filename*=UTF-8''{quote(fn + '.' + ext)}"
    return Response(content=data, media_type=ct, headers={"Content-Disposition": cd})


@app.get("/meeting/{mid}")
def meeting_detail(mid: str) -> dict:
    m = store.get_meeting(mid)
    if not m:
        raise HTTPException(404, "会议不存在")
    experts = store.get_experts_by_ids(m["expert_ids"])
    return {"meeting": m, "experts": experts, "events": store.get_events(mid)}


@app.post("/generate")
async def generate_endpoint(req: Request) -> StreamingResponse:
    body = await req.json()
    system_prompt = body.get("system_prompt", "") or ""
    messages = body.get("messages", []) or []
    model = body.get("model")
    run_id = body.get("run_id", "run")
    turn_id = body.get("turn_id", "t1")

    async def event_stream():
        try:
            async for evt in generate(
                system_prompt=system_prompt,
                messages=messages,
                model=model,
                run_id=run_id,
                turn_id=turn_id,
            ):
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except Exception as e:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)[:300]}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

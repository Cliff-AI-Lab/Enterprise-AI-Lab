"""持久化层(标准库 sqlite3)——专家 / 知识 / 会议 / 转写 / 演化补丁。

设计取舍:
- 每次操作开一个短连接(WAL 模式),避免 async + 单连接的线程问题;sqlite 本地够快。
- 首次初始化时把 experts.PRESET_EXPERTS 灌入 experts 表,于是预置专家也可编辑、可持久。
- JSON 字段(skills / knowledge_ids / expert_ids / agenda / payload)统一存 TEXT。
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from .experts import PRESET_EXPERTS

DB_PATH = Path(os.getenv("ROUNDTABLE_DB", Path(__file__).resolve().parent / "data" / "roundtable.db"))


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


_SCHEMA = """
CREATE TABLE IF NOT EXISTS experts (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  domain TEXT NOT NULL,
  specialty TEXT DEFAULT '',
  persona TEXT NOT NULL,
  skills_json TEXT DEFAULT '[]',
  knowledge_ids_json TEXT DEFAULT '[]',
  source TEXT DEFAULT 'custom',
  model TEXT DEFAULT '',
  kind TEXT DEFAULT 'local',
  endpoint TEXT DEFAULT '',
  api_key TEXT DEFAULT '',
  active INTEGER DEFAULT 1,
  created_at REAL,
  updated_at REAL
);
CREATE TABLE IF NOT EXISTS knowledge_docs (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  source_type TEXT NOT NULL,
  origin TEXT DEFAULT '',
  text_content TEXT DEFAULT '',
  expert_id TEXT,
  created_at REAL
);
CREATE TABLE IF NOT EXISTS meetings (
  id TEXT PRIMARY KEY,
  topic TEXT NOT NULL,
  description TEXT DEFAULT '',
  expert_ids_json TEXT DEFAULT '[]',
  model TEXT,
  mode TEXT DEFAULT 'roundtable',
  status TEXT DEFAULT 'preparing',
  agenda_json TEXT DEFAULT '[]',
  cursor INTEGER DEFAULT 0,
  max_followup INTEGER DEFAULT 1,
  created_at REAL,
  finished_at REAL
);
CREATE TABLE IF NOT EXISTS meeting_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  meeting_id TEXT NOT NULL,
  seq INTEGER NOT NULL,
  type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at REAL
);
CREATE INDEX IF NOT EXISTS idx_events_meeting ON meeting_events(meeting_id, seq);
CREATE TABLE IF NOT EXISTS evolution_patches (
  id TEXT PRIMARY KEY,
  meeting_id TEXT,
  expert_id TEXT,
  proposal_md TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  created_at REAL,
  decided_at REAL
);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT DEFAULT 'system',
  action TEXT NOT NULL,
  target TEXT DEFAULT '',
  detail TEXT DEFAULT '',
  created_at REAL
);
"""


def init_db() -> None:
    c = _conn()
    try:
        c.executescript(_SCHEMA)
        # 轻量迁移:为已存在的旧表补列
        cols = {r[1] for r in c.execute("PRAGMA table_info(experts)")}
        for col, ddl in {"model": "model TEXT DEFAULT ''", "kind": "kind TEXT DEFAULT 'local'",
                         "endpoint": "endpoint TEXT DEFAULT ''", "api_key": "api_key TEXT DEFAULT ''"}.items():
            if col not in cols:
                c.execute(f"ALTER TABLE experts ADD COLUMN {ddl}")
        c.commit()
        n = c.execute("SELECT COUNT(*) FROM experts").fetchone()[0]
        if n == 0:
            now = time.time()
            for e in PRESET_EXPERTS:
                c.execute(
                    "INSERT INTO experts(id,name,domain,specialty,persona,skills_json,"
                    "knowledge_ids_json,source,active,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,1,?,?)",
                    (e["id"], e["name"], e["domain"], e.get("specialty", ""), e["persona"],
                     "[]", "[]", "preset", now, now),
                )
            c.commit()
    finally:
        c.close()


def _expert_row(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"], "name": r["name"], "domain": r["domain"],
        "specialty": r["specialty"], "persona": r["persona"],
        "skills": json.loads(r["skills_json"] or "[]"),
        "knowledge_ids": json.loads(r["knowledge_ids_json"] or "[]"),
        "source": r["source"], "model": r["model"] or "",
        "kind": r["kind"], "endpoint": r["endpoint"],
        "active": bool(r["active"]),
    }


def log(action: str, target: str = "", detail: str = "", actor: str = "system") -> None:
    """关键操作审计(PRD 5.2)。"""
    c = _conn()
    try:
        c.execute(
            "INSERT INTO audit_log(actor,action,target,detail,created_at) VALUES(?,?,?,?,?)",
            (actor, action, target, detail, time.time()),
        )
        c.commit()
    finally:
        c.close()


# ---- experts ----
def list_experts(active_only: bool = True) -> list[dict]:
    c = _conn()
    try:
        q = "SELECT * FROM experts" + (" WHERE active=1" if active_only else "") + " ORDER BY created_at"
        return [_expert_row(r) for r in c.execute(q).fetchall()]
    finally:
        c.close()


def get_expert(eid: str) -> dict | None:
    c = _conn()
    try:
        r = c.execute("SELECT * FROM experts WHERE id=?", (eid,)).fetchone()
        return _expert_row(r) if r else None
    finally:
        c.close()


def get_experts_by_ids(ids: list[str]) -> list[dict]:
    """按给定 id 顺序返回存在的专家。"""
    by_id = {e["id"]: e for e in list_experts(active_only=False)}
    return [by_id[i] for i in ids if i in by_id]


def create_expert(*, name: str, domain: str, persona: str, specialty: str = "",
                  skills: list | None = None, knowledge_ids: list | None = None,
                  eid: str | None = None, source: str = "custom", model: str = "",
                  kind: str = "local", endpoint: str = "", api_key: str = "") -> dict:
    eid = eid or f"x_{uuid.uuid4().hex[:8]}"
    now = time.time()
    c = _conn()
    try:
        c.execute(
            "INSERT INTO experts(id,name,domain,specialty,persona,skills_json,"
            "knowledge_ids_json,source,model,kind,endpoint,api_key,active,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)",
            (eid, name, domain, specialty, persona,
             json.dumps(skills or [], ensure_ascii=False),
             json.dumps(knowledge_ids or [], ensure_ascii=False),
             source, model, kind, endpoint, api_key, now, now),
        )
        c.commit()
    finally:
        c.close()
    return get_expert(eid)  # type: ignore[return-value]


def update_expert(eid: str, fields: dict) -> dict | None:
    allowed = {"name", "domain", "specialty", "persona", "active", "model"}
    sets, vals = [], []
    for k in allowed & fields.keys():
        sets.append(f"{k}=?")
        vals.append(int(fields[k]) if k == "active" else fields[k])
    if "skills" in fields:
        sets.append("skills_json=?"); vals.append(json.dumps(fields["skills"], ensure_ascii=False))
    if "knowledge_ids" in fields:
        sets.append("knowledge_ids_json=?"); vals.append(json.dumps(fields["knowledge_ids"], ensure_ascii=False))
    if not sets:
        return get_expert(eid)
    sets.append("updated_at=?"); vals.append(time.time())
    vals.append(eid)
    c = _conn()
    try:
        c.execute(f"UPDATE experts SET {','.join(sets)} WHERE id=?", vals)
        c.commit()
    finally:
        c.close()
    return get_expert(eid)


def delete_expert(eid: str) -> None:
    c = _conn()
    try:
        c.execute("DELETE FROM experts WHERE id=?", (eid,))
        c.commit()
    finally:
        c.close()


# ---- knowledge ----
def add_doc(*, title: str, source_type: str, origin: str = "", text: str = "",
            expert_id: str | None = None) -> dict:
    did = f"k_{uuid.uuid4().hex[:8]}"
    c = _conn()
    try:
        c.execute(
            "INSERT INTO knowledge_docs(id,title,source_type,origin,text_content,expert_id,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (did, title, source_type, origin, text, expert_id, time.time()),
        )
        c.commit()
    finally:
        c.close()
    return get_doc(did)  # type: ignore[return-value]


def get_doc(did: str) -> dict | None:
    c = _conn()
    try:
        r = c.execute("SELECT * FROM knowledge_docs WHERE id=?", (did,)).fetchone()
        return dict(r) if r else None
    finally:
        c.close()


def list_docs(expert_id: str | None = None, with_text: bool = False) -> list[dict]:
    c = _conn()
    try:
        if expert_id:
            rows = c.execute("SELECT * FROM knowledge_docs WHERE expert_id=? ORDER BY created_at DESC",
                             (expert_id,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM knowledge_docs ORDER BY created_at DESC").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            if not with_text:
                d["chars"] = len(d.pop("text_content") or "")
            out.append(d)
        return out
    finally:
        c.close()


def docs_by_ids(ids: list[str]) -> list[dict]:
    if not ids:
        return []
    c = _conn()
    try:
        ph = ",".join("?" * len(ids))
        rows = c.execute(f"SELECT * FROM knowledge_docs WHERE id IN ({ph})", ids).fetchall()
        return [dict(r) for r in rows]
    finally:
        c.close()


def delete_doc(did: str) -> None:
    c = _conn()
    try:
        c.execute("DELETE FROM knowledge_docs WHERE id=?", (did,))
        c.commit()
    finally:
        c.close()


# ---- meetings & events ----
def create_meeting(*, topic: str, description: str, expert_ids: list[str],
                   model: str | None, mode: str = "roundtable",
                   max_followup: int = 1, status: str = "running") -> str:
    mid = f"m_{uuid.uuid4().hex[:10]}"
    c = _conn()
    try:
        c.execute(
            "INSERT INTO meetings(id,topic,description,expert_ids_json,model,mode,status,"
            "agenda_json,cursor,max_followup,created_at) VALUES(?,?,?,?,?,?,?,?,0,?,?)",
            (mid, topic, description, json.dumps(expert_ids, ensure_ascii=False),
             model, mode, status, "[]", max_followup, time.time()),
        )
        c.commit()
    finally:
        c.close()
    return mid


def set_meeting(mid: str, **fields: Any) -> None:
    cols = {"status", "agenda_json", "cursor", "finished_at"}
    sets, vals = [], []
    for k in cols & fields.keys():
        sets.append(f"{k}=?"); vals.append(fields[k])
    if not sets:
        return
    vals.append(mid)
    c = _conn()
    try:
        c.execute(f"UPDATE meetings SET {','.join(sets)} WHERE id=?", vals)
        c.commit()
    finally:
        c.close()


def get_meeting(mid: str) -> dict | None:
    c = _conn()
    try:
        r = c.execute("SELECT * FROM meetings WHERE id=?", (mid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["expert_ids"] = json.loads(d.pop("expert_ids_json") or "[]")
        d["agenda"] = json.loads(d.pop("agenda_json") or "[]")
        return d
    finally:
        c.close()


def list_meetings(limit: int = 50) -> list[dict]:
    c = _conn()
    try:
        rows = c.execute(
            "SELECT id,topic,status,model,created_at,finished_at FROM meetings "
            "ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        c.close()


def save_event(mid: str, seq: int, evt: dict) -> None:
    c = _conn()
    try:
        c.execute(
            "INSERT INTO meeting_events(meeting_id,seq,type,payload_json,created_at) VALUES(?,?,?,?,?)",
            (mid, seq, evt.get("type", ""), json.dumps(evt, ensure_ascii=False), time.time()),
        )
        c.commit()
    finally:
        c.close()


def get_events(mid: str) -> list[dict]:
    c = _conn()
    try:
        rows = c.execute(
            "SELECT payload_json FROM meeting_events WHERE meeting_id=? ORDER BY seq", (mid,)).fetchall()
        return [json.loads(r["payload_json"]) for r in rows]
    finally:
        c.close()


def get_events_ts(mid: str) -> list[tuple[dict, float]]:
    """事件 + 落库时间戳(仪表盘算响应时长用)。"""
    c = _conn()
    try:
        rows = c.execute(
            "SELECT payload_json, created_at FROM meeting_events WHERE meeting_id=? ORDER BY seq",
            (mid,)).fetchall()
        return [(json.loads(r["payload_json"]), r["created_at"]) for r in rows]
    finally:
        c.close()


def minutes_count() -> int:
    """已形成会议纪要的会议数(产出过 conclusion 事件即纪要已形成)。"""
    c = _conn()
    try:
        return c.execute(
            "SELECT COUNT(DISTINCT meeting_id) FROM meeting_events WHERE type='conclusion'"
        ).fetchone()[0]
    finally:
        c.close()


def recent_audit(limit: int = 50) -> list[dict]:
    c = _conn()
    try:
        rows = c.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        c.close()

import { DatabaseSync } from "node:sqlite";
import { mkdirSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";

const dbPath = resolve(process.env.TELEGRAM_AGENT_DB ?? "./data/telegram-agent.sqlite");
if (!existsSync(dirname(dbPath))) mkdirSync(dirname(dbPath), { recursive: true });

export const db = new DatabaseSync(dbPath);
db.exec("PRAGMA journal_mode = WAL");
db.exec("PRAGMA foreign_keys = ON");

db.exec(`
CREATE TABLE IF NOT EXISTS users (
  id            TEXT PRIMARY KEY,
  display_name  TEXT NOT NULL,
  created_at    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_profiles (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  role        TEXT NOT NULL,
  profile     TEXT NOT NULL,
  model       TEXT NOT NULL,
  hidden      INTEGER NOT NULL DEFAULT 0,
  emoji       TEXT,
  color       TEXT NOT NULL DEFAULT '#2563eb',
  initials    TEXT NOT NULL,
  best_for    TEXT,
  updated_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rooms (
  id          TEXT PRIMARY KEY,
  kind        TEXT NOT NULL CHECK (kind IN ('agent','room')),
  title       TEXT NOT NULL,
  agent_id    TEXT,
  member_ids  TEXT NOT NULL DEFAULT '[]',
  run_mode    TEXT,
  created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id          TEXT PRIMARY KEY,
  room_id     TEXT NOT NULL REFERENCES rooms(id),
  sender      TEXT NOT NULL CHECK (sender IN ('human','agent','system')),
  agent_id    TEXT,
  body        TEXT NOT NULL,
  created_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_room_time ON messages(room_id, created_at);

CREATE TABLE IF NOT EXISTS posts (
  id          TEXT PRIMARY KEY,
  agent_id    TEXT NOT NULL REFERENCES agent_profiles(id),
  body        TEXT NOT NULL,
  media_paths TEXT,                       -- JSON array of relative filenames under backend/data/posts/
  created_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_posts_agent_time ON posts(agent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_posts_time ON posts(created_at);
`);

// Migration: add media_paths to existing messages tables. JSON array of relative file names
// under backend/data/media/, e.g. ["msg_abc-0.png"]. NULL/empty for messages without media.
const messagesCols = db.prepare("PRAGMA table_info(messages)").all() as Array<{ name: string }>;
if (!messagesCols.some((c) => c.name === "media_paths")) {
  db.exec("ALTER TABLE messages ADD COLUMN media_paths TEXT");
}

// Migration: add run_mode to rooms. NULL = fall back to hardcoded table or "sequential".
const roomsCols = db.prepare("PRAGMA table_info(rooms)").all() as Array<{ name: string }>;
if (!roomsCols.some((c) => c.name === "run_mode")) {
  db.exec("ALTER TABLE rooms ADD COLUMN run_mode TEXT");
}

// Migration: add best_for to agent_profiles. JSON-encoded string[] of agent capability tags,
// parsed from personas/<id>/IDENTITY.md "- bestFor: A, B, C" 一行。NULL/[] = no claim.
const agentCols = db.prepare("PRAGMA table_info(agent_profiles)").all() as Array<{ name: string }>;
if (!agentCols.some((c) => c.name === "best_for")) {
  db.exec("ALTER TABLE agent_profiles ADD COLUMN best_for TEXT");
}

const now = () => Date.now();

db.prepare(`INSERT OR IGNORE INTO users (id, display_name, created_at) VALUES (?, ?, ?)`)
  .run("me", "Ricky", now());

export function upsertAgent(a: {
  id: string;
  name: string;
  role: string;
  profile: string;
  model: string;
  hidden: boolean;
  emoji?: string;
  color: string;
  initials: string;
  bestFor?: string[];
}): void {
  const bestForJson = a.bestFor && a.bestFor.length > 0 ? JSON.stringify(a.bestFor) : null;
  db.prepare(
    `INSERT INTO agent_profiles (id, name, role, profile, model, hidden, emoji, color, initials, best_for, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(id) DO UPDATE SET
       name=excluded.name, role=excluded.role, profile=excluded.profile,
       model=excluded.model, hidden=excluded.hidden, emoji=excluded.emoji,
       color=excluded.color, initials=excluded.initials,
       best_for=excluded.best_for, updated_at=excluded.updated_at`,
  ).run(a.id, a.name, a.role, a.profile, a.model, a.hidden ? 1 : 0, a.emoji ?? null, a.color, a.initials, bestForJson, now());
}

interface AgentRow {
  id: string;
  name: string;
  role: string;
  profile: string;
  model: string;
  hidden: number;
  emoji: string | null;
  color: string;
  initials: string;
  best_for: string | null;
}

function parseBestFor(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const arr = JSON.parse(raw) as unknown;
    if (Array.isArray(arr)) return arr.filter((x): x is string => typeof x === "string");
  } catch {
    // 旧行可能不是 JSON，忽略
  }
  return [];
}

export function listAgents(includeHidden = false): Array<Omit<AgentRow, "hidden" | "best_for"> & { hidden: boolean; bestFor: string[]; lastSeenAt: number | null }> {
  const baseSelect = `
    SELECT a.id, a.name, a.role, a.profile, a.model, a.hidden, a.emoji, a.color, a.initials, a.best_for,
           (SELECT MAX(m.created_at) FROM messages m WHERE m.agent_id = a.id) AS last_seen_at
    FROM agent_profiles a`;
  const rows = (includeHidden
    ? db.prepare(`${baseSelect} ORDER BY a.id`).all()
    : db.prepare(`${baseSelect} WHERE a.hidden = 0 ORDER BY a.id`).all()
  ) as unknown as Array<AgentRow & { last_seen_at: number | null }>;
  return rows.map((r) => ({
    id: r.id,
    name: r.name,
    role: r.role,
    profile: r.profile,
    model: r.model,
    hidden: r.hidden === 1,
    emoji: r.emoji,
    color: r.color,
    initials: r.initials,
    bestFor: parseBestFor(r.best_for),
    lastSeenAt: r.last_seen_at,
  }));
}

export function ensureDirectRoom(agentId: string, title: string): void {
  db.prepare(
    `INSERT OR IGNORE INTO rooms (id, kind, title, agent_id, member_ids, created_at)
     VALUES (?, 'agent', ?, ?, ?, ?)`,
  ).run(agentId, title, agentId, JSON.stringify([agentId]), now());
}

export type RoomRunMode = "sequential" | "parallel" | "loop";

export function ensureCollaborationRoom(room: {
  id: string;
  title: string;
  memberIds: string[];
  runMode?: RoomRunMode;
}): void {
  db.prepare(
    `INSERT OR IGNORE INTO rooms (id, kind, title, agent_id, member_ids, run_mode, created_at)
     VALUES (?, 'room', ?, NULL, ?, ?, ?)`,
  ).run(room.id, room.title, JSON.stringify(room.memberIds), room.runMode ?? null, now());
}

export function createCollaborationRoom(room: {
  id: string;
  title: string;
  memberIds: string[];
  runMode?: RoomRunMode;
}): void {
  db.prepare(
    `INSERT INTO rooms (id, kind, title, agent_id, member_ids, run_mode, created_at)
     VALUES (?, 'room', ?, NULL, ?, ?, ?)`,
  ).run(room.id, room.title, JSON.stringify(room.memberIds), room.runMode ?? null, now());
}

interface RoomRow {
  id: string;
  kind: "agent" | "room";
  title: string;
  agent_id: string | null;
  member_ids: string;
  run_mode: string | null;
  last_message: string | null;
  last_activity_at: number | null;
}

export function listRooms(): Array<{
  id: string;
  kind: "agent" | "room";
  title: string;
  agentId: string | null;
  memberIds: string[];
  runMode: RoomRunMode | null;
  lastMessage: string | null;
  lastActivityAt: number | null;
}> {
  const rows = db.prepare(
    `SELECT r.id, r.kind, r.title, r.agent_id, r.member_ids, r.run_mode,
            (SELECT body FROM messages WHERE room_id = r.id ORDER BY created_at DESC LIMIT 1) AS last_message,
            (SELECT created_at FROM messages WHERE room_id = r.id ORDER BY created_at DESC LIMIT 1) AS last_activity_at
     FROM rooms r
     LEFT JOIN agent_profiles a ON r.agent_id = a.id
     WHERE r.kind != 'agent' OR COALESCE(a.hidden, 0) = 0
     ORDER BY r.created_at`,
  ).all() as unknown as RoomRow[];
  return rows.map((r) => ({
    id: r.id,
    kind: r.kind,
    title: r.title,
    agentId: r.agent_id,
    memberIds: JSON.parse(r.member_ids) as string[],
    runMode: (r.run_mode === "sequential" || r.run_mode === "parallel" || r.run_mode === "loop") ? r.run_mode : null,
    lastMessage: r.last_message,
    lastActivityAt: r.last_activity_at,
  }));
}

interface MessageRow {
  id: string;
  roomId: string;
  sender: "human" | "agent" | "system";
  agentId: string | null;
  body: string;
  createdAt: number;
  mediaPaths: string[];
}

interface RawMessageRow {
  id: string;
  roomId: string;
  sender: "human" | "agent" | "system";
  agentId: string | null;
  body: string;
  createdAt: number;
  mediaPaths: string | null;
}

function parseMediaPaths(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((p): p is string => typeof p === "string") : [];
  } catch {
    return [];
  }
}

export function listMessages(roomId: string, limit = 200): MessageRow[] {
  // 取最新 N 条然后反转，保证长对话 UI 看到的是最近上下文而不是"最早 200 条"
  const rows = db.prepare(
    `SELECT id, room_id AS roomId, sender, agent_id AS agentId, body, created_at AS createdAt, media_paths AS mediaPaths
     FROM messages WHERE room_id = ? ORDER BY created_at DESC LIMIT ?`,
  ).all(roomId, limit) as unknown as RawMessageRow[];
  return rows.reverse().map((r) => ({ ...r, mediaPaths: parseMediaPaths(r.mediaPaths) }));
}

export function insertMessage(m: {
  id: string;
  roomId: string;
  sender: "human" | "agent" | "system";
  agentId?: string;
  body: string;
  mediaPaths?: string[];
}): void {
  db.prepare(
    `INSERT INTO messages (id, room_id, sender, agent_id, body, created_at, media_paths)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
  ).run(
    m.id,
    m.roomId,
    m.sender,
    m.agentId ?? null,
    m.body,
    now(),
    m.mediaPaths && m.mediaPaths.length > 0 ? JSON.stringify(m.mediaPaths) : null,
  );
}

export interface PostRow {
  id: string;
  agentId: string;
  body: string;
  mediaPaths: string[];
  createdAt: number;
}

interface RawPostRow {
  id: string;
  agentId: string;
  body: string;
  mediaPaths: string | null;
  createdAt: number;
}

export function insertPost(p: { id: string; agentId: string; body: string; mediaPaths?: string[] }): void {
  db.prepare(
    `INSERT INTO posts (id, agent_id, body, media_paths, created_at) VALUES (?, ?, ?, ?, ?)`,
  ).run(
    p.id,
    p.agentId,
    p.body,
    p.mediaPaths && p.mediaPaths.length > 0 ? JSON.stringify(p.mediaPaths) : null,
    now(),
  );
}

export function listPosts(opts: { agentId?: string; limit?: number } = {}): PostRow[] {
  const limit = opts.limit ?? 100;
  const rows = (opts.agentId
    ? db.prepare(
        `SELECT id, agent_id AS agentId, body, media_paths AS mediaPaths, created_at AS createdAt
         FROM posts WHERE agent_id = ? ORDER BY created_at DESC LIMIT ?`,
      ).all(opts.agentId, limit)
    : db.prepare(
        `SELECT id, agent_id AS agentId, body, media_paths AS mediaPaths, created_at AS createdAt
         FROM posts ORDER BY created_at DESC LIMIT ?`,
      ).all(limit)) as unknown as RawPostRow[];
  return rows.map((r) => ({ ...r, mediaPaths: parseMediaPaths(r.mediaPaths) }));
}

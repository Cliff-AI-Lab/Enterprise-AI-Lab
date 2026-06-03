#!/usr/bin/env node
// 验证 listMessages 在消息 >200 条时返回的是"最新 200 条"而不是"最早 200 条"。
// 用一个 throwaway room 注入 250 条，调 API，回收。

import { DatabaseSync } from "node:sqlite";
import { dirname, resolve } from "node:path";
import { mkdirSync, existsSync } from "node:fs";

const dbPath = resolve(process.env.TELEGRAM_AGENT_DB ?? "./backend/data/telegram-agent.sqlite");
if (!existsSync(dirname(dbPath))) mkdirSync(dirname(dbPath), { recursive: true });

const db = new DatabaseSync(dbPath);
const ROOM = "_pagination_test_room";
const TOTAL = 250;

console.log(`db=${dbPath}`);

let pass = false;
try {
  // clean up if rerun
  db.prepare(`DELETE FROM messages WHERE room_id = ?`).run(ROOM);
  db.prepare(`DELETE FROM rooms WHERE id = ?`).run(ROOM);

  db.prepare(
    `INSERT INTO rooms (id, kind, title, agent_id, member_ids, created_at) VALUES (?, 'agent', 'pagination test', NULL, '[]', ?)`,
  ).run(ROOM, Date.now());

  const insert = db.prepare(
    `INSERT INTO messages (id, room_id, sender, body, created_at) VALUES (?, ?, 'human', ?, ?)`,
  );
  const t0 = Date.now() - TOTAL * 1000;
  for (let i = 0; i < TOTAL; i++) {
    insert.run(`pag_${i}`, ROOM, `msg-${i}`, t0 + i * 1000);
  }
  console.log(`inserted ${TOTAL} messages into room=${ROOM}`);

  const res = await fetch(`http://127.0.0.1:18791/api/rooms/${ROOM}/messages`);
  if (!res.ok) {
    console.error(`✗ HTTP ${res.status}`);
  } else {
    const { messages } = await res.json();
    console.log(`got ${messages.length} messages back`);

    const first = messages[0].body;
    const last = messages[messages.length - 1].body;
    console.log(`first=${first}, last=${last}`);

    // expected (with fix): latest 200 → msg-50 ... msg-249, returned in ASC order
    // pre-fix bug behavior: earliest 200 → msg-0 ... msg-199
    const expectFirst = `msg-${TOTAL - 200}`; // msg-50
    const expectLast = `msg-${TOTAL - 1}`;    // msg-249

    let ok = true;
    if (messages.length !== 200) {
      console.error(`✗ expected 200 messages, got ${messages.length}`);
      ok = false;
    }
    if (first !== expectFirst) {
      console.error(`✗ first message should be ${expectFirst}, got ${first}`);
      ok = false;
    }
    if (last !== expectLast) {
      console.error(`✗ last message should be ${expectLast}, got ${last}`);
      ok = false;
    }
    if (ok) {
      console.log(`✓ pagination returns latest 200 in ASC order`);
    }
    pass = ok;
  }
} finally {
  // cleanup 必须无条件跑：后端 500、网络挂、断言失败都不能留下测试 room。
  try {
    db.prepare(`DELETE FROM messages WHERE room_id = ?`).run(ROOM);
    db.prepare(`DELETE FROM rooms WHERE id = ?`).run(ROOM);
    console.log(`cleanup done`);
  } catch (e) {
    console.error(`✗ cleanup failed: ${e.message}`);
  }
  db.close();
}

process.exit(pass ? 0 : 1);

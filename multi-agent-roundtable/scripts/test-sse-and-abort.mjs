#!/usr/bin/env node
// 验证：
// 1) SSE 流正常工作（POST → text.delta → run.finished）
// 2) 客户端 abort / 切房间后，后端 run 继续完成并落库（避免切换房间丢输出）

import { randomUUID } from "node:crypto";

const BE = process.env.BACKEND_BASE ?? "http://127.0.0.1:18791";
const ROOM = "sarah";

// ── case 1: 正常流 ─────────────────────────────────────────────
async function caseHappyPath() {
  console.log("──── case 1: SSE happy path ────");
  const runId = `run_${randomUUID()}`;
  const res = await fetch(`${BE}/api/rooms/${ROOM}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: "用一句话告诉我，写文案最常见的毛病是什么。", runId }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const eventTypes = [];
  let deltaCount = 0;
  let firstDeltaAt = null;
  const t0 = Date.now();

  outer: while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let nl;
    while ((nl = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, nl);
      buffer = buffer.slice(nl + 1);
      if (!line.startsWith("data:")) continue;
      const data = line.slice(5).trim();
      if (!data) continue;
      try {
        const evt = JSON.parse(data);
        eventTypes.push(evt.type);
        if (evt.type === "text.delta") {
          deltaCount++;
          if (firstDeltaAt === null) firstDeltaAt = Date.now() - t0;
        }
        if (evt.type === "run.finished") break outer;
        if (evt.type === "run.error") {
          console.error(`✗ got run.error: ${JSON.stringify(evt.payload)}`);
          return false;
        }
      } catch (e) {
        console.error(`  malformed event: ${data.slice(0, 80)}`);
      }
    }
  }

  const dt = Date.now() - t0;
  const summary = Object.fromEntries(
    [...new Set(eventTypes)].map((t) => [t, eventTypes.filter((x) => x === t).length]),
  );
  console.log(`  events:`, summary, `total dt=${dt}ms first-delta=${firstDeltaAt}ms deltas=${deltaCount}`);

  const ok =
    eventTypes.includes("run.started") &&
    eventTypes.includes("text.started") &&
    deltaCount > 0 &&
    eventTypes.includes("text.finished") &&
    eventTypes.includes("run.finished");
  console.log(ok ? "  ✓ full SSE protocol observed" : "  ✗ missing expected events");
  return ok;
}

// ── case 2: abort 仍持久化后台 run ───────────────────────────────
// 关键判定：abort 后轮询 /messages。修复后应看到新的 agent 消息最终出现。
async function caseAbortStillPersistsRun() {
  console.log("──── case 2: abort keeps backend run alive and persisted ────");

  const before = await fetch(`${BE}/api/rooms/${ROOM}/messages`).then((r) => r.json());
  const beforeAgentCount = before.messages.filter((m) => m.sender === "agent").length;
  console.log(`  agent-msg count before: ${beforeAgentCount}`);

  const ctrl = new AbortController();
  const runId = `run_${randomUUID()}`;
  const userText = "请用两句话解释一下，为什么切换房间时后台任务仍然要继续完成。";

  const reqPromise = fetch(`${BE}/api/rooms/${ROOM}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: userText, runId }),
    signal: ctrl.signal,
  });

  // 等首批 delta 飞过来再 abort（确认流真开起来了）
  let firstDeltaSeen = false;
  reqPromise
    .then(async (res) => {
      if (!res.ok || !res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { value, done } = await reader.read().catch(() => ({ done: true }));
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        if (!firstDeltaSeen && buf.includes("text.delta")) {
          firstDeltaSeen = true;
          break;
        }
      }
    })
    .catch(() => {});

  // 轮询等 first delta，最多 8s
  const tStart = Date.now();
  while (!firstDeltaSeen && Date.now() - tStart < 8000) {
    await new Promise((r) => setTimeout(r, 100));
  }
  if (!firstDeltaSeen) {
    console.error("  ✗ never saw first delta within 8s; cannot test abort");
    return false;
  }
  const tFirstDelta = Date.now() - tStart;
  console.log(`  first delta after ${tFirstDelta}ms → aborting now`);
  ctrl.abort();

  console.log("  polling up to 30s for persisted agent message...");
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 1000));
    const after = await fetch(`${BE}/api/rooms/${ROOM}/messages`).then((r) => r.json());
    const afterAgents = after.messages.filter((m) => m.sender === "agent");
    const afterAgentCount = afterAgents.length;
    const delta = afterAgentCount - beforeAgentCount;
    if (delta > 0) {
      const lastAgent = afterAgents.at(-1);
      const body = lastAgent?.body ?? "";
      console.log(`  agent-msg count after: ${afterAgentCount} (+${delta})`);
      console.log(`  ✓ run persisted after client abort (body="${body.slice(0, 80)}"...)`);
      return true;
    }
  }

  const after = await fetch(`${BE}/api/rooms/${ROOM}/messages`).then((r) => r.json());
  const afterAgentCount = after.messages.filter((m) => m.sender === "agent").length;
  console.error(`  ✗ no persisted agent message after abort; before=${beforeAgentCount}, after=${afterAgentCount}`);
  return false;
}

let pass = 0;
let total = 0;
total++; if (await caseHappyPath()) pass++;
console.log();
total++; if (await caseAbortStillPersistsRun()) pass++;

console.log(`\n━━━ ${pass}/${total} passed ━━━`);
process.exit(pass === total ? 0 : 1);

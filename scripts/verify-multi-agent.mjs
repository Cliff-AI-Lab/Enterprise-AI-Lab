#!/usr/bin/env node
// 多 agent 共存 + 跨 agent session 隔离验证。
// 前提：openclaw.json 含 main / sarah / alex / kai 四个 agent，Gateway 已 restart。
//
// 跑：
//   OPENCLAW_GATEWAY_TOKEN=... node scripts/verify-multi-agent.mjs

const GATEWAY = process.env.OPENCLAW_GATEWAY_URL || process.env.OPENCLAW_BASE_URL || "http://127.0.0.1:18789";
const TOKEN = process.env.OPENCLAW_GATEWAY_TOKEN;
if (!TOKEN) {
  console.error("✗ Missing OPENCLAW_GATEWAY_TOKEN");
  process.exit(1);
}

async function ask(agent, userMessage, sessionUser) {
  const t0 = Date.now();
  const r = await fetch(`${GATEWAY}/v1/chat/completions`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: `openclaw/${agent}`,
      messages: [{ role: "user", content: userMessage }],
      user: sessionUser,
      stream: false,
    }),
  });
  const dt = Date.now() - t0;
  if (!r.ok) {
    const body = await r.text().catch(() => "<no body>");
    throw new Error(`HTTP ${r.status}: ${body.slice(0, 200)}`);
  }
  const j = await r.json();
  return { reply: j?.choices?.[0]?.message?.content ?? "<empty>", dt };
}

let pass = 0;
let total = 0;

async function check(name, fn) {
  total++;
  console.log(`\n──── ${name} ────`);
  try {
    const ok = await fn();
    if (ok) { pass++; console.log("  ✓ PASS"); }
    else console.log("  ✗ FAIL");
  } catch (e) {
    console.error(`  ✗ ERROR: ${e.message}`);
  }
}

// ─── Test 1: 三个 visible agent 身份差异化 ───
await check("身份差异化 (sarah / alex / kai 各自答自己)", async () => {
  const q = "你好，你是谁？做什么的？一句话。";
  const [s, a, k] = await Promise.all([
    ask("sarah", q, "verify-identity-sarah"),
    ask("alex",  q, "verify-identity-alex"),
    ask("kai",   q, "verify-identity-kai"),
  ]);
  console.log(`  sarah (${s.dt}ms): ${s.reply}`);
  console.log(`  alex  (${a.dt}ms): ${a.reply}`);
  console.log(`  kai   (${k.dt}ms): ${k.reply}`);
  return (
    s.reply.includes("Sarah") && s.reply.includes("文案") &&
    a.reply.includes("Alex")  && (a.reply.includes("PM") || a.reply.includes("产品")) &&
    k.reply.includes("Kai")   && (k.reply.includes("工程") || k.reply.includes("Engineer"))
  );
});

// ─── Test 2: cross-agent isolation (用同一 user key 发给不同 agent) ───
await check("跨 agent session 隔离 (同 user 发给 sarah 后, alex 应无记忆)", async () => {
  const sessionUser = "verify-iso-test";
  const turn1 = await ask("sarah", "记一下：我手头有一个叫 BlueDragon 的项目代号。", sessionUser);
  console.log(`  sarah turn 1 (${turn1.dt}ms): ${turn1.reply.slice(0, 120)}`);
  const turn2 = await ask("alex", "我刚才告诉过你一个项目代号叫什么？", sessionUser);
  console.log(`  alex  turn 2 (${turn2.dt}ms): ${turn2.reply.slice(0, 200)}`);
  // Alex 不应该知道 BlueDragon（如果泄露说明 session 没按 agent 隔离）
  const leaked = turn2.reply.includes("BlueDragon");
  if (leaked) console.log("    🚨 LEAK: alex knew BlueDragon, session not isolated by agentId!");
  return !leaked;
});

// ─── Test 3: same-agent session 持续 (同 sessionUser, 同 agent, 跨 turn 应连续) ───
await check("同 agent 同 session 跨 turn 连续 (sarah 应记得自己说过什么)", async () => {
  const sessionUser = `verify-cont-${Date.now()}`;
  const turn1 = await ask("sarah", "我接下来要写一个针对程序员的 App 落地页。第一段先写一句 hook。", sessionUser);
  console.log(`  turn 1 (${turn1.dt}ms): ${turn1.reply.slice(0, 200)}`);
  const turn2 = await ask("sarah", "我上一条问你写什么受众的什么内容？", sessionUser);
  console.log(`  turn 2 (${turn2.dt}ms): ${turn2.reply.slice(0, 200)}`);
  // sarah 应记得"程序员" + "落地页"
  return turn2.reply.includes("程序员") && (turn2.reply.includes("落地页") || turn2.reply.includes("App"));
});

// ─── Test 4: 同 agent 不同 sessionUser 应不连续 ───
await check("同 agent 不同 sessionUser 应独立 (不串记忆)", async () => {
  await ask("sarah", "记一下：我的猫叫毛球。", "verify-cat-A");
  const r = await ask("sarah", "我之前提到过我的猫叫什么？", "verify-cat-B");
  console.log(`  sarah turn (sessionUser=B): ${r.reply.slice(0, 200)}`);
  const leaked = r.reply.includes("毛球");
  if (leaked) console.log("    🚨 LEAK: sarah leaked context across sessionUsers!");
  return !leaked;
});

// ─── Test 5: 人格区别 — 同一需求, 三个 agent 各自风格 ───
await check("人格区别 (同需求 sarah/alex/kai 给出风格鲜明不同的回应)", async () => {
  const q = "我想做一个本地 AI 写作助手 App。给点建议。";
  const [s, a, k] = await Promise.all([
    ask("sarah", q, "verify-style-s"),
    ask("alex",  q, "verify-style-a"),
    ask("kai",   q, "verify-style-k"),
  ]);
  console.log(`\n  ── sarah (文案视角, ${s.dt}ms) ──\n${s.reply}`);
  console.log(`\n  ── alex (PM 视角, ${a.dt}ms) ──\n${a.reply}`);
  console.log(`\n  ── kai (工程视角, ${k.dt}ms) ──\n${k.reply}`);
  // 简单标志词检查 — 各自视角应触发不同关键词
  const sarahFocus = s.reply.match(/(文案|tone|读者|表达|落地页)/);
  const alexFocus = a.reply.match(/(用户|优先级|metric|指标|RICE|MoSCoW|画像|痛点|场景|衡量)/);
  const kaiFocus = k.reply.match(/(技术|栈|trade|风险|本地|存储|架构|实现|root cause|可逆)/i);
  console.log(`\n  sarah 视角关键词命中: ${sarahFocus ? "✓ " + sarahFocus[0] : "✗"}`);
  console.log(`  alex  视角关键词命中: ${alexFocus ? "✓ " + alexFocus[0] : "✗"}`);
  console.log(`  kai   视角关键词命中: ${kaiFocus ? "✓ " + kaiFocus[0] : "✗"}`);
  return sarahFocus && alexFocus && kaiFocus;
});

console.log(`\n━━━ ${pass}/${total} cases passed ━━━`);
process.exit(pass === total ? 0 : 1);

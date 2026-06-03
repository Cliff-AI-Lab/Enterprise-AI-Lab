#!/usr/bin/env node
// Path C 验证脚本：通过 OpenAI-compat HTTP 端点调 sarah agent，
// 检查 workspace bootstrap files (SOUL/IDENTITY/AGENTS/USER) 是否真的注入了 system prompt。
//
// 前置：
//   1. openclaw onboard --install-daemon       (装 Gateway daemon)
//   2. 按 RUN_FOR_TESTERS.md 生成 ~/.openclaw/openclaw.json；不要直接 cp 项目副本，
//      因为项目副本里有 ${RUIDONG_API_KEY} 占位符和本机 workspace 绝对路径。
//   3. openclaw gateway restart
//   4. export OPENCLAW_GATEWAY_TOKEN=<你的 token>
//
// 运行：
//   node scripts/verify-openclaw.mjs
//   node scripts/verify-openclaw.mjs --case identity      # 验证身份
//   node scripts/verify-openclaw.mjs --case style         # 验证文风
//   node scripts/verify-openclaw.mjs --case all           # 跑全部

const GATEWAY = process.env.OPENCLAW_GATEWAY_URL || process.env.OPENCLAW_BASE_URL || "http://127.0.0.1:18789";
const TOKEN = process.env.OPENCLAW_GATEWAY_TOKEN;
const AGENT = process.env.OPENCLAW_AGENT_ID || "sarah";

if (!TOKEN) {
  console.error("✗ Missing OPENCLAW_GATEWAY_TOKEN env var");
  console.error("  Get it from: openclaw gateway status   (or your onboard output)");
  process.exit(1);
}

const argCase = process.argv.find(a => a.startsWith("--case="))?.split("=")[1]
              ?? (process.argv.includes("--case") ? process.argv[process.argv.indexOf("--case") + 1] : null)
              ?? "identity";

const CASES = {
  identity: {
    label: "Identity check (SOUL.md + IDENTITY.md 是否注入)",
    user: "你好，你是谁？做什么的？一句话。",
    expectHints: ["Sarah", "文案"],
  },
  style: {
    label: "Style check (SOUL.md tone 是否生效)",
    user: "帮我写一句产品 banner：一站式赋能极致打造的智能写作平台。",
    expectHints: ["Sarah"],
    notExpectHints: ["一站式", "赋能", "极致打造"],
  },
  unknown: {
    label: "Unknown-info honesty (TOOLS.md 边界是否生效)",
    user: "帮我查一下 Notion 最新版的定价是多少？",
    expectHints: ["没有", "工具"],
  },
};

async function runCase(name) {
  const c = CASES[name];
  if (!c) {
    console.error(`✗ Unknown case: ${name}. Available: ${Object.keys(CASES).join(", ")}`);
    process.exit(2);
  }
  console.log(`\n━━━ ${name}: ${c.label} ━━━`);
  console.log(`> user: ${c.user}`);

  const t0 = Date.now();
  let r;
  try {
    r = await fetch(`${GATEWAY}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: `openclaw/${AGENT}`,
        messages: [{ role: "user", content: c.user }],
        user: `verify-${name}`,    // 稳定 sessionKey 派生
        stream: false,
      }),
    });
  } catch (e) {
    console.error(`✗ Network/Gateway error: ${e.message}`);
    console.error("  Check: openclaw gateway status");
    return false;
  }

  if (!r.ok) {
    const body = await r.text().catch(() => "<no body>");
    console.error(`✗ HTTP ${r.status} ${r.statusText}`);
    console.error(`  Body: ${body.slice(0, 500)}`);
    return false;
  }

  const j = await r.json();
  const reply = j?.choices?.[0]?.message?.content ?? "<no content>";
  const dt = Date.now() - t0;
  console.log(`< sarah (${dt}ms): ${reply}`);

  const hits = (c.expectHints ?? []).filter(h => reply.includes(h));
  const leaks = (c.notExpectHints ?? []).filter(h => reply.includes(h));

  const okHits = hits.length === (c.expectHints ?? []).length;
  const okLeaks = leaks.length === 0;

  if (okHits) console.log(`  ✓ expected hints found: [${hits.join(", ")}]`);
  else console.log(`  ✗ missing hints: [${(c.expectHints ?? []).filter(h => !hits.includes(h)).join(", ")}]`);

  if (c.notExpectHints) {
    if (okLeaks) console.log(`  ✓ no banned phrases leaked`);
    else console.log(`  ✗ banned phrases leaked: [${leaks.join(", ")}]`);
  }

  return okHits && okLeaks;
}

const cases = argCase === "all" ? Object.keys(CASES) : [argCase];
let pass = 0;
for (const name of cases) {
  if (await runCase(name)) pass++;
}
console.log(`\n━━━ ${pass}/${cases.length} cases passed ━━━`);
process.exit(pass === cases.length ? 0 : 1);

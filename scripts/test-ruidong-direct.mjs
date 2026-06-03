#!/usr/bin/env node
// 绕过 OpenClaw 的直测：手动把 sarah workspace 的 bootstrap 文件
// 拼成 system prompt，发给 ruidong，看模型扮演 Sarah 是否合格。
//
// 目的：在配 Gateway 之前先验证「模型 + persona 文件」这个组合本身可行。
// 如果直测都不像 Sarah，配 OpenClaw 也是同样的问题——先解决 prompt 工程。

import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PERSONA_DIR = join(__dirname, "..", "personas", "sarah-writer");

const RUIDONG_BASE = "https://iruidong.com/v1";
const RUIDONG_KEY = process.env.RUIDONG_API_KEY;
const MODEL = process.env.RUIDONG_MODEL || "ruidong-std";

if (!RUIDONG_KEY) {
  console.error("✗ RUIDONG_API_KEY 未设置。先 source backend/.env 再跑：");
  console.error("  export $(grep -v '^#' backend/.env | xargs) && node scripts/test-ruidong-direct.mjs");
  process.exit(2);
}

// 模拟 OpenClaw normal session 注入：所有 bootstrap 文件按顺序拼成 system prompt
const BOOTSTRAP_FILES = ["SOUL.md", "IDENTITY.md", "AGENTS.md", "TOOLS.md", "USER.md"];

async function buildSystemPrompt() {
  const parts = [];
  for (const f of BOOTSTRAP_FILES) {
    const path = join(PERSONA_DIR, f);
    try {
      const body = await readFile(path, "utf8");
      parts.push(`## ${f}\n\n${body.trim()}`);
    } catch (e) {
      console.error(`✗ Failed to read ${path}: ${e.message}`);
      process.exit(2);
    }
  }
  return parts.join("\n\n---\n\n");
}

const CASES = [
  {
    name: "identity",
    label: "身份注入：SOUL.md + IDENTITY.md 是否生效",
    user: "你好，你是谁？做什么的？一句话。",
    expect: ["Sarah", "文案"],
  },
  {
    name: "style",
    label: "文风约束：SOUL.md 的 banned phrases 是否生效",
    user: "帮我写一句产品 banner：一站式赋能极致打造的智能写作平台。",
    notExpect: ["一站式", "赋能", "极致打造"],
  },
  {
    name: "honesty",
    label: "工具边界：TOOLS.md 是否生效（应承认没工具，不假装查）",
    user: "帮我查一下 Notion 最新版的定价是多少？",
    expect: ["没有"],
  },
  {
    name: "ask-first",
    label: "AGENTS.md 工作协议：需求不明应反问而非硬写",
    user: "帮我写一句广告语。",
    expect: ["?", "？"],
    expectAny: true,
  },
];

async function callRuidong(systemPrompt, userMessage) {
  const t0 = Date.now();
  const r = await fetch(`${RUIDONG_BASE}/chat/completions`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${RUIDONG_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: MODEL,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userMessage },
      ],
      max_tokens: 400,
      temperature: 0.7,
    }),
  });
  const dt = Date.now() - t0;
  if (!r.ok) {
    const body = await r.text().catch(() => "<no body>");
    throw new Error(`HTTP ${r.status}: ${body.slice(0, 400)}`);
  }
  const j = await r.json();
  return { reply: j?.choices?.[0]?.message?.content ?? "<no content>", backend: j?.model, dt };
}

const systemPrompt = await buildSystemPrompt();
console.log(`━━━ Persona system prompt: ${systemPrompt.length} chars (含 ${BOOTSTRAP_FILES.length} files) ━━━`);
console.log(`━━━ Model: ${MODEL} ━━━\n`);

let pass = 0;
for (const c of CASES) {
  console.log(`──── ${c.name}: ${c.label} ────`);
  console.log(`> user: ${c.user}`);
  try {
    const { reply, backend, dt } = await callRuidong(systemPrompt, c.user);
    console.log(`< sarah [${backend} ${dt}ms]:\n${reply}\n`);

    const hits = (c.expect ?? []).filter(h => reply.includes(h));
    const leaks = (c.notExpect ?? []).filter(h => reply.includes(h));

    const okHits = c.expectAny
      ? hits.length > 0
      : hits.length === (c.expect ?? []).length;
    const okLeaks = leaks.length === 0;

    if (c.expect) {
      const missing = (c.expect ?? []).filter(h => !hits.includes(h));
      if (c.expectAny) {
        console.log(okHits ? `  ✓ found any of: [${(c.expect ?? []).join(", ")}]` : `  ✗ none of expected: [${(c.expect ?? []).join(", ")}]`);
      } else {
        console.log(missing.length === 0 ? `  ✓ all hints present: [${hits.join(", ")}]` : `  ✗ missing: [${missing.join(", ")}]`);
      }
    }
    if (c.notExpect) {
      console.log(okLeaks ? `  ✓ no banned phrases` : `  ✗ leaked: [${leaks.join(", ")}]`);
    }
    if (okHits && okLeaks) pass++;
  } catch (e) {
    console.error(`  ✗ Error: ${e.message}\n`);
  }
}

console.log(`\n━━━ ${pass}/${CASES.length} cases passed ━━━`);
process.exit(pass === CASES.length ? 0 : 1);

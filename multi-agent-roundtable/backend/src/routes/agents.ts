import { Hono } from "hono";
import { existsSync, statSync, createReadStream, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve, join, dirname } from "node:path";
import { listAgents } from "../db.js";
import { getAgentWorkspace } from "../agentSync.js";

export const agentsRoute = new Hono();

type Presence = "online" | "idle" | "offline";

let gatewayProbeCache: { up: boolean; at: number } | null = null;
const PROBE_TTL_MS = 30_000;

async function probeGateway(): Promise<boolean> {
  if (gatewayProbeCache && Date.now() - gatewayProbeCache.at < PROBE_TTL_MS) {
    return gatewayProbeCache.up;
  }
  const baseUrl = (process.env.OPENCLAW_BASE_URL ?? "http://127.0.0.1:18789").replace(/\/+$/, "");
  try {
    const res = await fetch(baseUrl, { signal: AbortSignal.timeout(2000) });
    const up = res.status < 500;
    gatewayProbeCache = { up, at: Date.now() };
    return up;
  } catch {
    gatewayProbeCache = { up: false, at: Date.now() };
    return false;
  }
}

function computePresence(lastSeenAt: number | null, gatewayUp: boolean): Presence {
  if (!gatewayUp) return "offline";
  if (lastSeenAt === null) return "idle";
  const ageMs = Date.now() - lastSeenAt;
  if (ageMs < 5 * 60 * 1000) return "online";
  if (ageMs < 60 * 60 * 1000) return "idle";
  return "idle";
}

// agentId 必须是纯短形式（main / sarah / maruko），不能含 / 或 ..。
// 读写都走 agentSync 注册的 workspace（openclaw.json agents.list[].workspace），
// 保证 GET 路径 == PUT 路径。老的"personas/<id>/avatar.png"硬编码会让
// sarah-writer / alex-pm / kai-engineer 这种目录后缀不一致的 agent 上传成功后读不到。
function avatarPath(agentId: string): string | null {
  if (!/^[a-z0-9_-]+$/i.test(agentId)) return null;
  const ws = getAgentWorkspace(agentId);
  if (!ws) return null;
  const p = resolve(ws, "avatar.png");
  return existsSync(p) ? p : null;
}

function avatarUrl(agentId: string): string | null {
  const p = avatarPath(agentId);
  if (!p) return null;
  return `/api/agents/${agentId}/avatar?v=${statSync(p).mtimeMs.toFixed(0)}`;
}

agentsRoute.get("/", async (c) => {
  const gatewayUp = await probeGateway();
  const agents = listAgents(false).map((a) => {
    const versionedAvatarUrl = avatarUrl(a.id);
    return {
      ...a,
      presence: computePresence(a.lastSeenAt, gatewayUp),
      ...(versionedAvatarUrl ? { avatarUrl: versionedAvatarUrl } : {}),
    };
  });
  return c.json({ agents, gatewayUp });
});

agentsRoute.get("/:id/avatar", (c) => {
  const id = c.req.param("id");
  const p = avatarPath(id);
  if (!p) return c.notFound();
  const stat = statSync(p);
  c.header("Content-Type", "image/png");
  c.header("Content-Length", String(stat.size));
  c.header("Cache-Control", "public, max-age=300");
  return c.body(createReadStream(p) as unknown as ReadableStream);
});

// ── 编辑接口 (writes persona files in workspace) ────────────────────────────

const VALID_AGENT_ID = /^[a-z0-9_-]+$/i;

// 通过 openclaw.json workspace 找 agent 的 persona 目录。
// 没注册过的 agent 拒绝（防 traversal + 防写入野路径）。
function resolveWorkspaceFile(agentId: string, filename: "SOUL.md" | "avatar.png"): string | undefined {
  if (!VALID_AGENT_ID.test(agentId)) return undefined;
  const ws = getAgentWorkspace(agentId);
  if (!ws) return undefined;
  // 不允许 .. 之类 — getAgentWorkspace 返回 absolute path，join + 固定 filename 安全
  return join(ws, filename);
}

agentsRoute.get("/:id/soul", (c) => {
  const id = c.req.param("id");
  const p = resolveWorkspaceFile(id, "SOUL.md");
  if (!p || !existsSync(p)) return c.notFound();
  const markdown = readFileSync(p, "utf8");
  return c.json({ agentId: id, markdown });
});

agentsRoute.put("/:id/soul", async (c) => {
  const id = c.req.param("id");
  const p = resolveWorkspaceFile(id, "SOUL.md");
  if (!p) return c.json({ error: "agent not found" }, 404);
  const body = (await c.req.json().catch(() => null)) as { markdown?: string } | null;
  if (!body || typeof body.markdown !== "string") return c.json({ error: "markdown required" }, 400);
  if (body.markdown.length > 200_000) return c.json({ error: "markdown too large" }, 413);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, body.markdown, "utf8");
  return c.json({
    ok: true,
    agentId: id,
    path: p,
    restartRequired: true,
    hint: "OpenClaw 启动时一次性 load SOUL.md，热重载不生效——改动需要 openclaw gateway restart 才会被 agent 感知。",
  });
});

agentsRoute.put("/:id/avatar", async (c) => {
  const id = c.req.param("id");
  const p = resolveWorkspaceFile(id, "avatar.png");
  if (!p) return c.json({ error: "agent not found" }, 404);
  const body = (await c.req.json().catch(() => null)) as { dataUrl?: string } | null;
  if (!body || typeof body.dataUrl !== "string") return c.json({ error: "dataUrl required" }, 400);
  // data:image/png;base64,XXXX
  const m = body.dataUrl.match(/^data:image\/png;base64,([A-Za-z0-9+/=]+)$/);
  if (!m) return c.json({ error: "only data:image/png;base64,... accepted" }, 400);
  const buf = Buffer.from(m[1]!, "base64");
  if (buf.length === 0) return c.json({ error: "empty image" }, 400);
  if (buf.length > 5_000_000) return c.json({ error: "image too large (>5MB)" }, 413);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, buf);
  return c.json({
    ok: true,
    agentId: id,
    path: p,
    bytes: buf.length,
    hint: "刷新前端 contact list 头像即刻更新。无需重启 Gateway。",
  });
});

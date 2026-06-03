import cron from "node-cron";
import { db } from "./db.js";

// Moments 定时调度——每个 agent 有自己的节奏（人设相关，小丸子最活跃）
// cron 表达式说明（5 字段，UTC 还是 local 看 node-cron 配置——这里用系统 local time）
// "M H DoM Mo DoW"
//
// 错时间 + 错星期，避免堆在同一时间触发 Ruidong API
const SCHEDULES: Array<{ agentId: string; cron: string; description: string }> = [
  // 小丸子：每天 22:30（最活跃，二次元人设需要持续追番感）
  { agentId: "maruko", cron: "30 22 * * *", description: "每天 22:30" },
  // alex：每周一/三/五 10:05（约每 2 天，PM 工作日早上观察 trend）
  { agentId: "alex", cron: "5 10 * * 1,3,5", description: "周一/三/五 10:05" },
  // sarah：每周二/四/六 14:07（约每 2 天，文案下午灵感）
  { agentId: "sarah", cron: "7 14 * * 2,4,6", description: "周二/四/六 14:07" },
  // kai：每周一/四 21:13（约每 3 天，工程深夜观察）
  { agentId: "kai", cron: "13 21 * * 1,4", description: "周一/四 21:13" },
  // iris：每天 9:23（工作日早上扫一篇 Agent Harness / Multi-Agent 一手文章。
  // 主题约束 + "不输出工具调用过程" 的纪律写在 personas/iris-researcher/SOUL.md
  // 里，trigger 仍用默认的 MOMENTS_TRIGGER_PROMPT，跟其他 agent 一致。）
  { agentId: "iris", cron: "23 9 * * *", description: "每天 9:23" },
];

// 错过补跑窗口：只补"过去 24h 内本应 fire 但没 fire"的——
// 避免 Mac 关机几天后重启时把陈年旧账一次性翻出来打 Ruidong。
// maruko 每天那次错过能覆盖；隔 2~3 天 schedule 错过的就让它自然下次再来。
const CATCHUP_WINDOW_MS = 24 * 60 * 60 * 1000;

async function generateMomentForAgent(agentId: string, backendPort: number): Promise<void> {
  const endpoint = `http://127.0.0.1:${backendPort}/api/agents/${encodeURIComponent(agentId)}/posts/generate`;
  const t0 = Date.now();
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(180_000), // 3 分钟兜底
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status}: ${body.slice(0, 200)}`);
    }
    const data = (await res.json()) as { post?: { id?: string } };
    const dt = Date.now() - t0;
    console.log(`[cron] ${agentId} → moment ${data.post?.id ?? "?"} in ${dt}ms`);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.warn(`[cron] ${agentId} failed after ${Date.now() - t0}ms: ${msg}`);
    // 不抛——保持 cron 继续跑，下次 schedule 再试
  }
}

// 简化版 cron 解析：只处理 "M H * * DoW(s)" 这种格式（当前 SCHEDULES 都是）
// 返回 before 之前最近一次该 fire 的本地时间；不支持 step / range / DoM / Month。
function lastExpectedFire(cronExpr: string, before: Date): Date | null {
  const parts = cronExpr.trim().split(/\s+/);
  if (parts.length !== 5) return null;
  const [mStr, hStr, dom, mon, dowStr] = parts as [string, string, string, string, string];
  if (dom !== "*" || mon !== "*") return null;
  const minute = Number(mStr);
  const hour = Number(hStr);
  if (!Number.isInteger(minute) || !Number.isInteger(hour)) return null;
  const allowedDows: Set<number> | null = dowStr === "*"
    ? null
    : new Set(
        dowStr
          .split(",")
          .map((s) => Number(s))
          .filter((n) => Number.isInteger(n) && n >= 0 && n <= 6),
      );

  // 从 before 当天倒退最多 8 天，找第一个 (DoW 匹配 && 当天 H:M <= before)
  for (let i = 0; i < 8; i++) {
    const d = new Date(before);
    d.setDate(d.getDate() - i);
    d.setHours(hour, minute, 0, 0);
    if (d.getTime() > before.getTime()) continue; // 当天的 H:M 还没到
    const dow = d.getDay();
    if (allowedDows && !allowedDows.has(dow)) continue;
    return d;
  }
  return null;
}

function lastPostTime(agentId: string): number | null {
  const row = db
    .prepare(`SELECT MAX(created_at) AS t FROM posts WHERE agent_id = ?`)
    .get(agentId) as { t: number | null } | undefined;
  return row?.t ?? null;
}

async function catchUpMissedFires(backendPort: number): Promise<void> {
  const now = new Date();
  const queue: Array<{ agentId: string; expected: Date }> = [];
  for (const s of SCHEDULES) {
    const expected = lastExpectedFire(s.cron, now);
    if (!expected) {
      console.warn(`[cron] catch-up: cannot parse ${s.cron} for ${s.agentId}, skip`);
      continue;
    }
    const ageMs = now.getTime() - expected.getTime();
    if (ageMs > CATCHUP_WINDOW_MS) continue; // 太久远，跳过
    const last = lastPostTime(s.agentId);
    if (last !== null && last >= expected.getTime()) continue; // 已经在那之后 post 过
    queue.push({ agentId: s.agentId, expected });
  }
  if (queue.length === 0) {
    console.log("[cron] catch-up: nothing to backfill");
    return;
  }
  console.log(`[cron] catch-up queue: ${queue.map((q) => q.agentId).join(", ")}`);
  // 串行——避免同时打 Ruidong
  for (const { agentId, expected } of queue) {
    console.log(`[cron] catch-up ${agentId} (missed ${expected.toLocaleString()})`);
    await generateMomentForAgent(agentId, backendPort);
  }
}

export function startMomentsCron(backendPort: number): void {
  if (process.env.TELEGRAM_AGENT_MOMENTS_CRON === "0") {
    console.log("[cron] TELEGRAM_AGENT_MOMENTS_CRON=0 → 跳过 Moments 定时");
    return;
  }
  for (const s of SCHEDULES) {
    if (!cron.validate(s.cron)) {
      console.warn(`[cron] invalid expression for ${s.agentId}: ${s.cron}`);
      continue;
    }
    cron.schedule(s.cron, () => {
      void generateMomentForAgent(s.agentId, backendPort);
    });
    console.log(`[cron] scheduled ${s.agentId} → ${s.description} (${s.cron})`);
  }
  // 启动后延迟 5s 跑 catch-up，给 server / OpenClaw Gateway 留余裕
  setTimeout(() => {
    void catchUpMissedFires(backendPort);
  }, 5000);
}

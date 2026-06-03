import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { cors } from "hono/cors";
import { syncAgentsFromOpenClaw } from "./agentSync.js";
import { agentsRoute } from "./routes/agents.js";
import { roomsRoute } from "./routes/rooms.js";
import { messagesRoute } from "./routes/messages.js";
import { mediaRoute } from "./routes/media.js";
import { postsRoute } from "./routes/posts.js";
import { startMomentsCron } from "./momentsCron.js";

// 兜底：undici 内部 SSE / fetch body 的 close race —— 客户端断开 / Gateway 重启 / tsx watch
// reload 时，ReadableStream 被 cancel + 自然 EOF 双关闭，抛 ERR_INVALID_STATE。
// 两条路径都得堵：microtask 里冒泡时走 unhandledRejection，从 undici 内部 sync throw
// 走 uncaughtException。后者只对 ERR_INVALID_STATE 白名单，其他真 bug（启动期 sqlite locked、
// 模块加载错误）原样退出让 tsx watch 重启。
process.on("unhandledRejection", (reason) => {
  const msg = reason instanceof Error ? `${reason.name}: ${reason.message}` : String(reason);
  console.warn(`[server] unhandledRejection (suppressed): ${msg}`);
});
process.on("uncaughtException", (err) => {
  if ((err as NodeJS.ErrnoException).code === "ERR_INVALID_STATE") {
    console.warn(`[server] uncaughtException (suppressed undici stream race): ${err.message}`);
    return;
  }
  console.error(`[server] uncaughtException (fatal): ${err.stack ?? err.message}`);
  process.exit(1);
});

syncAgentsFromOpenClaw();

const app = new Hono();

app.use("*", cors({ origin: ["http://127.0.0.1:5183", "http://localhost:5183"] }));

app.get("/api/health", (c) => c.json({ ok: true, ts: Date.now() }));
app.route("/api/agents", agentsRoute);
app.route("/api/rooms", roomsRoute);
app.route("/api/rooms", messagesRoute);
app.route("/api/messages", mediaRoute);
app.route("/api", postsRoute);

const port = Number(process.env.PORT ?? 18791);
serve({ fetch: app.fetch, port, hostname: "127.0.0.1" }, (info) => {
  console.log(`[server] http://127.0.0.1:${info.port}`);
  startMomentsCron(info.port);
});

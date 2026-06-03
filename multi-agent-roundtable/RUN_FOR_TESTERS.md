# TelegramAgent 同事测试运行指南

这份包只包含 TelegramAgent 源码、persona workspace、配置模板和测试脚本，不包含 OpenClaw、本地 `node_modules`、`backend/.env`、SQLite 历史数据或已生成媒体文件。

官方 OpenClaw 文档：
- Install: https://docs.openclaw.ai/install/index
- Getting started: https://docs.openclaw.ai/start/getting-started
- Gateway: https://docs.openclaw.ai/cli/gateway

## 1. 环境要求

- Node.js 22.19+；Node 24 更推荐。
- pnpm。没有的话先跑 `corepack enable`。
- OpenClaw CLI/Gateway。本项目只通过 OpenAI-compatible HTTP 调 OpenClaw，不需要安装 `@openclaw/sdk`。
- 一个可用的 `RUIDONG_API_KEY`。
- 可选：`ffmpeg` / `ffprobe`。音乐能生成时会尝试裁静音，没有也能落文件，只是不会做裁剪。

默认端口：
- OpenClaw Gateway: `127.0.0.1:18789`
- Backend: `127.0.0.1:18791`
- Frontend: `127.0.0.1:5183`

## 2. 安装 OpenClaw

官方推荐安装脚本：

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
openclaw onboard --install-daemon
openclaw gateway status
```

如果你已经自己管理 Node，也可以用 npm：

```bash
npm install -g openclaw@latest
openclaw onboard --install-daemon
openclaw gateway status
```

`openclaw gateway status` 应该显示 Gateway 正在 `18789` 监听。Windows 建议用 WSL2 跑完整体验。

## 3. 解压并安装项目依赖

```bash
tar -xzf TelegramAgent-test-*.tar.gz
cd TelegramAgent

corepack enable

cd backend
pnpm install

cd ../frontend
pnpm install
```

## 4. 配置后端环境变量

```bash
cd ../backend
cp .env.example .env
```

编辑 `backend/.env`：

```bash
OPENCLAW_BASE_URL=http://127.0.0.1:18789
OPENCLAW_GATEWAY_TOKEN=<填你的 OpenClaw Gateway token>
RUIDONG_API_KEY=<填你的 ruidong key>
TELEGRAM_AGENT_DB=./data/telegram-agent.sqlite
PROJECT_ROOT=<你的 TelegramAgent 解压后的绝对路径>
PORT=18791

TELEGRAM_AGENT_TZ=Asia/Shanghai
TELEGRAM_AGENT_MOMENTS_CRON=0
TELEGRAM_AGENT_MEDIA_DIR=./data/media
TELEGRAM_AGENT_POSTS_MEDIA_DIR=./data/posts
```

`TELEGRAM_AGENT_MOMENTS_CRON=0` 建议保留。否则后端启动 5 秒后会补跑 Moments 定时任务，测试聊天时容易误打 Ruidong。

如果 onboarding 没给你现成 token，可以先生成一个本地 token，并同时写进 `backend/.env`：

```bash
node -e "console.log(require('node:crypto').randomBytes(24).toString('hex'))"
```

## 5. 生成本机 OpenClaw 配置

不要直接把项目里的 `openclaw.json` 复制到 `~/.openclaw/openclaw.json`。项目副本里有两类不能原样给 Gateway 使用的内容：
- `${RUIDONG_API_KEY}` 占位符。
- 相对 workspace 路径；Gateway 配置最好写成你本机的绝对路径。

在项目根目录执行下面脚本，它会生成适配你本机路径的 `~/.openclaw/openclaw.json`：

```bash
cd <你的 TelegramAgent 解压目录>
set -a
source backend/.env
set +a

mkdir -p "$HOME/.openclaw"
cp "$HOME/.openclaw/openclaw.json" "$HOME/.openclaw/openclaw.json.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true

node <<'NODE'
const fs = require("node:fs");
const path = require("node:path");

const root = process.cwd();
const cfg = JSON.parse(fs.readFileSync("openclaw.json", "utf8"));
const apiKey = process.env.RUIDONG_API_KEY;
const token = process.env.OPENCLAW_GATEWAY_TOKEN;

if (!apiKey || apiKey.startsWith("<")) throw new Error("RUIDONG_API_KEY is not configured");
if (!token || token.startsWith("<")) throw new Error("OPENCLAW_GATEWAY_TOKEN is not configured");

const workspaceById = {
  main: "main",
  sarah: "sarah-writer",
  alex: "alex-pm",
  kai: "kai-engineer",
  architect: "architect",
  mira: "mira-designer",
  lin: "lin-qa",
  iris: "iris-researcher",
  maruko: "maruko",
};

cfg.gateway.mode = "local";
cfg.gateway.auth = { ...(cfg.gateway.auth ?? {}), mode: "token", token };
cfg.models.providers.ruidong.apiKey = apiKey;
cfg.agents.defaults.memorySearch.remote.apiKey = apiKey;

for (const agent of cfg.agents.list) {
  const dir = workspaceById[agent.id] ?? agent.id;
  agent.workspace = path.join(root, "personas", dir);
}

fs.writeFileSync(
  path.join(process.env.HOME, ".openclaw", "openclaw.json"),
  `${JSON.stringify(cfg, null, 2)}\n`,
);
console.log("wrote ~/.openclaw/openclaw.json");
NODE

openclaw gateway restart
openclaw gateway status
```

如果 Gateway 报某些 skill 找不到，先不用阻塞聊天测试。可以在 `~/.openclaw/openclaw.json` 里临时删掉对应 agent 的 `skills` 项，或安装你本机缺的 skill 后再 `openclaw gateway restart`。Sarah 和 Maruko 的部分 workspace skills 已随包带在 `personas/` 内。

## 6. 启动项目

开三个终端。

终端 1，确认 OpenClaw：

```bash
openclaw gateway status
```

终端 2，启动后端：

```bash
cd <TelegramAgent>/backend
pnpm dev
```

终端 3，启动前端：

```bash
cd <TelegramAgent>/frontend
pnpm dev
```

浏览器打开：

```text
http://127.0.0.1:5183/
```

## 7. 冒烟测试

后端健康检查：

```bash
curl http://127.0.0.1:18791/api/health
curl http://127.0.0.1:18791/api/agents
```

OpenClaw 单 agent 检查：

```bash
cd <TelegramAgent>
set -a
source backend/.env
set +a
node scripts/verify-openclaw.mjs --case identity
```

UI 检查：
- 打开 Sarah / Alex / Kai 任意单聊，发一句短消息。
- 打开“头脑风暴房”，发一句“大家各自给一个方向”，确认多个 Agent 都能输出。
- 切到其它房间再切回来，正在跑的群聊最终结果应仍然落库显示。

如需验证“切换/断开后仍持久化”：

```bash
cd <TelegramAgent>
set -a
source backend/.env
set +a
node scripts/test-sse-and-abort.mjs
```

## 8. 常见问题

`agents` 全部 offline：
检查 `openclaw gateway status`、`OPENCLAW_BASE_URL`、`OPENCLAW_GATEWAY_TOKEN` 是否一致。

OpenClaw 返回 401/unauthorized：
后端 `.env` 里的 `OPENCLAW_GATEWAY_TOKEN` 和 `~/.openclaw/openclaw.json` 里的 `gateway.auth.token` 不一致。改一致后 `openclaw gateway restart`。

OpenClaw 启动后 agent 还是旧人格：
OpenClaw 启动时一次性读取 persona 文件；改 `SOUL.md` / `IDENTITY.md` / `openclaw.json` 后必须 `openclaw gateway restart`。

端口被占用：
本项目默认写死前端 `5183` strict port，后端默认 `18791`。先停旧进程再启动。

图片/音乐生成失败：
通常是 `RUIDONG_API_KEY` 没配或额度/模型不可用。基础聊天只需要 OpenClaw 能用 ruidong chat model。

SQLite/Node 提示 experimental warning：
当前后端用 `node:sqlite` 的 `DatabaseSync`，这个 warning 不影响本地测试。

# 遗留问题清单

> 当前 phase = MVP / Phase 1。单聊跑通后的开放面记在这里，按优先级排。
> 设计依据多数在 `temp_design.md`，方括号引用具体小节。

---

## 高优先级（影响当前体验）

### OpenClaw 不热重载 workspace 文件
- **现象**：改 `personas/<id>/SOUL.md`、`IDENTITY.md`、`openclaw.json` 等 OpenClaw 不会自动重读，行为依然是旧的
- **机制**：OpenClaw Gateway 启动时一次性把 workspace 加载到 system prompt 缓存
- **workaround**：`kill $(lsof -ti:18789); openclaw gateway --port 18789 > /tmp/openclaw-gateway.log 2>&1 &`
- **长期**：调研 OpenClaw 是否有 `agent:bootstrap` hook 或 SIGHUP-reload；写脚本 `scripts/reload-personas.sh` 封装

### openclaw.json 两份不同步
- **现状**：`~/.openclaw/openclaw.json`（Gateway 实际读）和项目内 `./openclaw.json`（git 可追溯参考副本）**内容不一致**，手动维护
- **风险**：改了项目里那份以为生效了，其实 Gateway 还在用 home 那份；反之亦然
- **方向**：要么 symlink 一边到另一边（要先剥离 `gateway.auth.token` 防止泄露），要么写脚本把两份的 agents.list / models / skills allowlist 同步
- **临时方案**：CLAUDE.md "关键约定" 段已点明两份关系，改时记得**主改 home 那份**再同步项目副本

### Anti-AI-tone 现在复制三份在 SOUL.md
- **现状**：`personas/{sarah,alex,kai}/SOUL.md` 各有一段同样的「别这样说话」（不用"作为 X"开头 / 不复述问题 / 不写"希望对你有帮助"等）
- **问题**：一处改、三处忘
- **方向**：profile-agnostic 规则提到 `backend/src/envBlock.ts`（注入到所有 agent 的 system prompt），SOUL.md 只留 agent-specific（Alex 反对功能堆叠 / Sarah 拒绝"赋能/打造" / Kai 怀疑式优先）

---

## 中优先级（功能缺失，但有设计）

### Visible persona repo 权限边界过宽（测试阶段先记录，不修）
- **现象**：`architect`/Atlas 等用户可见 persona 当前配置了 `tools.profile: "coding"`，实际可获得 `read/write/edit/exec/process` 等工具；一次群聊中 Atlas 已通过 `exec`/`read` 读取项目文件（如 `docs/00_README.md`、`docs/14_AGENT_COMMUNICATION_PROTOCOL.md`、`backend/src/openclaw.ts`）后给出架构判断。
- **为什么不理想**：读的是本项目 repo 也属于产品内部实现状态。Visible persona 直接读 repo 容易把文件路径、源码结构、DB schema、OpenClaw 配置、内部调度细节带进普通聊天，相当于对用户“露底”。`SOUL.md`/`TOOLS.md` 保密提示只能降低输出概率，不能阻止它先知道。
- **当前不修**：MVP 测试阶段先保留现状，便于快速验证多 agent 能力；上线前必须收紧。
- **后续方向**：
  1. 日常聊天：Atlas/Sarah/Alex/Mira/Lin/Iris 默认不拿 `coding` profile，不直接读 repo。
  2. Main/Admin 或 Kai 才默认拥有 repo 访问权；由它们生成脱敏 ContextPack/架构摘要再交给可见 persona。
  3. 若 Atlas 需要代码/架构 review，不直接把 workspace 指向 repo 根目录；改用临时 review pack，例如 `.agent-workspaces/architect-review/`，只放 `ARCHITECTURE_SUMMARY.md`、`DIFF_SUMMARY.md`、必要代码片段和风险说明。
  4. 对 review 型 Atlas 使用 `profile: "minimal" + alsoAllow: ["read"] + fs.workspaceOnly: true`，并显式 deny `write/edit/apply_patch/exec/process`。
  5. `workspace` 只作为默认上下文目录，不是天然 ACL；必须配 `tools.fs.workspaceOnly: true` 才能限制文件工具只读 workspace 内文件。
- **提示词补充**：可在 `envBlock` 或 persona `TOOLS.md` 加“内部实现不披露”规则，但它是软约束，不能替代工具权限。
- **来源**：2026-06-01 Atlas 群聊架构判断暴露出 repo 读取权限问题。

### Group room 协议后续债务
- **现状**：接龙房 / 头脑风暴房 / 打磨房 已接 OpenClaw；后端按 `sequential | parallel | loop` 三种 mode 分流；P0 的硬约束提升和前序输出压缩已做。
- **P1**：头脑风暴房还没有 Merger artifact。Merger 应从 room member 中选，不让 Main 作为普通聊天发言。
- **P1**：打磨房 `VERDICT: escalate` 目前只表现为 critic 可见输出 + `run.finished`，UI 没有专门的 escalated 状态。
- **P2**：还没有 `context_pack_snapshots` / `audit_events`，上下文省略只在 prompt 文本中 inline 标注。
- **P3**：打磨房 3+ 成员语义未定；当前只取前两位作为 producer / critic。
- **P3**：头脑风暴房并发 abort 路径未专门压测。
- **设计**：`docs/14_AGENT_COMMUNICATION_PROTOCOL.md`

### Audit Panel 未实现
- **现状**：前端有 context panel 占位但没接事件源；DB 没有 `audit_events` 表
- **要做**：DB schema → 后端事件写入 → 前端 SSE 订阅 → UI 展开
- **设计**：`temp_design.md §5.46`

### Permission Gateway 未实现
- **现状**：没有三级风险 / approve prompt
- **要做**：DB `permission_grants` 表 + 中间件
- **设计**：`temp_design.md §5.47`

### Evolution / reflector loop 未实现
- **现状**：用户偏好自动提取 / SOUL 改进 patch 还没开始
- **要做**：reflector loop（后台周期任务）→ 提 diff 写 `evolution.md` → 人审 → patch SOUL.md
- **设计**：`temp_design.md §5.5.5`

### SQLite schema 还在 `db.ts` 内联
- **现状**：DDL 直接写在 `backend/src/db.ts`，只 4 表（users / agent_profiles / rooms / messages）
- **temp_design §5.4.3** 还设计了 runs / artifacts / audit_events / permission_grants / context_pack_snapshots / user_facts / main_agent_state
- **方向**：按需扩；不必一次铺完。新表先加到 `db.ts`，等表多了再分到 `schema.sql`
- **来源**：`temp_design.md §6 任务 A`

---

## 低优先级 / 后续

### Memory 写入触发器
- **现状**：`personas/<id>/memory/*.md` 要人工写 + `openclaw memory index --force` 才能召回
- **bge-m3 embedding 已配通**（`openclaw memory status --deep` 显示 ready，第 13 轮实证）
- **方向**：后端 reflector loop 自动提取偏好写文件
- **来源**：`temp_design.md §6 任务 K`

### tools.profile 调整
- **现状**：`openclaw.json` 默认 "coding" profile，过滤掉 5 个工具（agents_list / gateway / message / nodes / tts）；对 sarah/alex 不合适
- **方向**：per-agent profile 或自定义 profile
- **来源**：`temp_design.md §6 任务 L`

### App.tsx 是 monolith（3700 行）
- 来源是 vite-tar 包就这样
- 不紧急，按需要拆分（拆 RoomHeader / Composer / Sidebar 是合理切割点）

### SOUL.md 篇幅 & 软/硬约束的边界
- **现状**：persona SOUL 行数差异大 —— architect/mira/lin 33-42、sarah/alex/kai 105-120、maruko 183、iris 现在 ~60。chat 部分 (Voice/原则/边界/Tone) 普遍精炼，差异主要在 Moments 段
- **风险**：长 SOUL.md 占 system prompt context；多重约束 + 辩证语言（"X 但 Y"）让 LLM 拘谨且容易钻口子
- **教训（来自 iris 这次）**：
  1. **思考独白红线**：自带工具的 agent (web_search/web_fetch) 发 Moments 时，必须有"工具调用过程不写进正文"约束 + 1 完整 few-shot 例子。这是 LLM 默认会犯的特有错（流式输出 thinking phase）。光写"不要开场白"不够，必须列出反例 ❌
  2. **引用规则去辩证**：iris SOUL 起初写"引用具体事实带链接，综合判断可不带"，LLM 利用"综合判断"口子点名却不带链接。改成硬规则"输出里出现任何具体名字必须带链接，带不了就不点名"才稳。**辩证语言 = 给 LLM 留钻空子的口子**
  3. **配图禁令必须 backend 硬挡**：SOUL 写"不输出 `<image_prompt>`"也没用——默认 `MOMENTS_TRIGGER_PROMPT` (user message) 写了"可以配 1 张图"，先验更强，LLM 仍偶发输出 image_prompt。最终在 `backend/src/routes/posts.ts` 加 `NO_MOMENTS_IMAGE_AGENTS = new Set(["iris"])`，硬丢 prompts。新研究类 agent 需禁图就加 ID
- **软 vs 硬约束分工**：
  | 类型 | 在哪一层 |
  |---|---|
  | 风格 / 语气 / 内容方向 | SOUL.md（prompt 软约束，LLM 大概率遵守）|
  | 高频出现的特有 anti-pattern（如思考独白）| SOUL.md 红线段 + 反例 + few-shot |
  | 必须 100% 不能出现的内容禁令（如 iris 配图）| **backend 硬挡**，不依赖 LLM 服从度 |
- **方向**：
  - 已稳定运行的 sarah/alex/kai/maruko 不主动重写（按"改 A 别动 B"）
  - architect/mira/lin **接 Moments cron 时**才按 iris 瘦身版补一段（≤ 25 行：红线 + 长度 + 1 完整例子），不要 copy sarah/alex/kai 的 60 行重版本
  - 后续新增 persona 走精简档：chat 部分 3-5 条核心约束一行一刀，Moments 段（如果接 cron）≤ 25 行
  - 任何"100% 不能出现"的内容（图、特定 tag、危险关键词）走 backend 硬挡，不堆 SOUL prompt
- **来源**：2026-05-31 iris 调研 Moment 系列事故复盘（思考独白 → 配图诱导 → 链接缺失三轮调试）

### 音乐生成质量调优（ace-step）
- **现象**（2026-06-01 接通当晚观察）：
  1. **节奏 repeat**：生成的曲子整段反复同一节奏型 / loop 感强，缺乏段落起伏（**待修**）
  2. ~~**尾部哑掉**：请求 `seconds="30"` 实际有声音段只到 ~27 秒，最后 2-3 秒静音~~ → **已缓解 2026-06-01**：默认改成 `seconds="auto"`（musicGen.ts、SOUL.md、SKILL.md），让 ace-step 自己决定时长，audio player 拿到真实 duration。只有用户明确说"30 秒 / 1 分钟"才显式写 `seconds`。
- **节奏 repeat 的可能方向**（按猜测顺序，待实测确认）：
  1. **Prompt 太单维**：默认走 `[Instrumental]` 一个段落，模型无段落 cue → 容易产平铺循环。试在 lyrics 里塞 `[Intro] / [Build] / [Drop] / [Breakdown] / [Outro]` 时间分段，给模型起伏 anchor
  2. **bpm 太低**：当前默认 78-100 bpm = 一段也填不满 → 模型 loop 凑数。试更高 bpm / 更短小节
  3. **模型本身**：`ace-step-v15`（响应叫 `-turbo`）是蒸馏 8-step 版，本来就在牺牲 detail 换速度。SKILL.md 说还有 `sft` / `xl` 变体——确认 ruidong 是否也提供
- **不动**：现在的 SOUL.md `<music_prompt>` 协议和 backend 通路是 work 的，**只是产出质量需要 prompt/参数调优**，不是协议 bug
- **入手点**：`personas/maruko/SOUL.md` "## 配音乐" 段的协议范例（让小丸子默认写更结构化的 lyrics），或 `~/.agents/skills/music-gen/SKILL.md` 详细 prompt 写法段
- **来源**：2026-06-01 接通验证

### Path A 切换（可选）
- 现在用 Path C（OpenAI-compat HTTP）
- Phase 2 候选：切 Path A（`@openclaw/sdk` workspace 安装），才能用 `oc.tools.invoke` / `oc.artifacts` / `oc.approvals` / 显式 `agentToAgent`
- **设计**：`temp_design.md §5.4.5.4`

---

## 已完成（本批次，2026-05-30）

- ✅ 后端注入当前时间到 OpenClaw（`buildEnvBlock()`）—— 日期错乱修复
- ✅ Anti-AI-tone 加到 sarah/alex/kai SOUL.md（暂时复制三份，待 envBlock 化）
- ✅ Status dot 真实化：online / idle / offline 基于 Gateway probe + lastSeenAt
- ✅ Emoji 从 RoomHeader 去掉
- ✅ Group room 改名匹配设计（接龙房 / 头脑风暴房 / 打磨房）
- ✅ 头像 gender 修正 + 显示比例加大（44px / center 18% / size 145%）
- ✅ 表情 placeholder Chinese 化（"皱了皱眉" / "盯着 stacktrace" 类）
- ✅ 给 4 个 persona 配 OpenClaw skill：main=1 / sarah=2 (ClawHub) / alex=2 / kai=3；用 `agents.list[].skills` allowlist 收窄；Gateway 重启生效
- ✅ Gateway 重启（PID 63004），上面所有 SOUL.md anti-AI-tone 改动 + skill allowlist 同步生效

## 已完成（本批次，2026-05-31）

- ✅ Group room LLM 路径接通：接龙房 sequential、头脑风暴房 parallel fanout、打磨房 producer/critic loop。
- ✅ room-scoped sessionUser：`me:<roomId>:<agentId>`，避免同一 agent 的单聊/群聊上下文串线。
- ✅ 群聊成员动态化：mention 表和建群成员来自 agent 列表，不再硬编码 4 个 agent。
- ✅ P0 constraints hardening：从用户请求抽硬约束，放到 prompt 顶部和末尾；“每人一句话”派生为最多 40 中文字符、不要姓名前缀。
- ✅ P0 input 粒度阈值：前序输出总量超过 1500 字时按 head/tail 压缩并标注 omitted 字数。
- ✅ 复测约束稀释：relay 同 prompt `多 Agent 验证：请每个人只回复一句话。`，输出长度 Sarah 31 / Alex 36 / Kai 38，均低于 50 字。

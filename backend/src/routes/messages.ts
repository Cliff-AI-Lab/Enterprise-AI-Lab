import { Hono } from "hono";
import { streamSSE } from "hono/streaming";
import { randomUUID } from "node:crypto";
import { db, insertMessage } from "../db.js";
import { streamOpenClaw } from "../openclaw.js";
import { generateImage } from "../imageGen.js";
import { generateMusic, normalizeMusicSeconds, type MusicFormat, type MusicSeconds } from "../musicGen.js";

export const messagesRoute = new Hono();

interface PostBody {
  text?: string;
  prompt?: string;
  agentId?: string;
  agentIds?: string[];
  memberIds?: string[];
  mode?: string;
  sessionUser?: string;
  runId?: string;
}

interface AgentProfileLite {
  id: string;
  name: string;
  role: string;
}

type RoomRunMode = "direct" | "sequential" | "parallel" | "loop";
type PolishVerdict = "approved" | "revise" | "escalate";

interface AgentTurnOutput {
  agent: AgentProfileLite;
  body: string;
}

// Hide <image_prompt>...</image_prompt> blocks from the streamed SSE so the user
// never sees raw tags flowing by. Buffer enough trailing chars to recognize a
// partial "<image_prompt" prefix across delta boundaries.
class ImagePromptStreamFilter {
  private buf = "";

  push(delta: string): FilterResult {
    this.buf += delta;
    let emit = "";
    const prompts: ParsedImagePrompt[] = [];
    const OPEN = "<image_prompt";
    const CLOSE = "</image_prompt>";
    while (this.buf.length > 0) {
      const openIdx = this.buf.indexOf(OPEN);
      if (openIdx === -1) {
        // No tag open in buffer. Emit all but the last (OPEN.length - 1) chars,
        // in case a partial OPEN is forming across deltas.
        const safe = this.buf.length - (OPEN.length - 1);
        if (safe > 0) {
          emit += this.buf.slice(0, safe);
          this.buf = this.buf.slice(safe);
        }
        break;
      }
      // Emit text up to the tag open.
      emit += this.buf.slice(0, openIdx);
      this.buf = this.buf.slice(openIdx);
      const closeIdx = this.buf.indexOf(CLOSE);
      if (closeIdx === -1) {
        // Tag not yet closed; hold everything until next delta.
        break;
      }
      const tag = this.buf.slice(0, closeIdx + CLOSE.length);
      const prompt = parseImagePromptTag(tag);
      if (prompt) {
        prompts.push(prompt);
      }
      // Drop the whole tag (open through close).
      this.buf = this.buf.slice(closeIdx + CLOSE.length);
    }
    return { text: emit, prompts };
  }

  flush(): string {
    // If the buffer still contains an unclosed <image_prompt, drop it
    // (the agent never finished writing the tag). Otherwise emit residual.
    if (this.buf.includes("<image_prompt")) {
      this.buf = "";
      return "";
    }
    const out = this.buf;
    this.buf = "";
    return out;
  }
}

interface ParsedImagePrompt {
  alt: string;
  prompt: string;
}

interface FilterResult {
  text: string;
  prompts: ParsedImagePrompt[];
}

interface MediaTaskResult {
  idx: number;
  alt: string;
  filename?: string;
  mdLine?: string;
}

function parseImagePromptTag(tag: string): ParsedImagePrompt | undefined {
  const m = tag.match(/^<image_prompt(?:\s+alt=["']([^"']*)["'])?\s*>([\s\S]*?)<\/image_prompt>$/);
  const prompt = (m?.[2] ?? "").trim();
  if (!m || prompt.length === 0) {
    return undefined;
  }
  return {
    alt: (m[1] ?? "图").trim() || "图",
    prompt,
  };
}

// 仿 ImagePromptStreamFilter：截取 <music_prompt ...>...</music_prompt> tag，body 隐藏不发给前端。
interface ParsedMusicPrompt {
  alt: string;
  prompt: string;
  lyrics?: string;
  instrumental?: boolean;
  seconds?: MusicSeconds;
  format?: MusicFormat;
  bpm?: number;
  keyscale?: string;
  seed?: number;
}

interface MusicFilterResult {
  text: string;
  prompts: ParsedMusicPrompt[];
}

class MusicPromptStreamFilter {
  private buf = "";

  push(delta: string): MusicFilterResult {
    this.buf += delta;
    let emit = "";
    const prompts: ParsedMusicPrompt[] = [];
    const OPEN = "<music_prompt";
    const CLOSE = "</music_prompt>";
    while (this.buf.length > 0) {
      const openIdx = this.buf.indexOf(OPEN);
      if (openIdx === -1) {
        const safe = this.buf.length - (OPEN.length - 1);
        if (safe > 0) {
          emit += this.buf.slice(0, safe);
          this.buf = this.buf.slice(safe);
        }
        break;
      }
      emit += this.buf.slice(0, openIdx);
      this.buf = this.buf.slice(openIdx);
      const closeIdx = this.buf.indexOf(CLOSE);
      if (closeIdx === -1) break;
      const tag = this.buf.slice(0, closeIdx + CLOSE.length);
      const parsed = parseMusicPromptTag(tag);
      if (parsed) prompts.push(parsed);
      this.buf = this.buf.slice(closeIdx + CLOSE.length);
    }
    return { text: emit, prompts };
  }

  flush(): string {
    if (this.buf.includes("<music_prompt")) {
      this.buf = "";
      return "";
    }
    const out = this.buf;
    this.buf = "";
    return out;
  }
}

const MUSIC_VALID_FORMATS = new Set<MusicFormat>(["mp3", "wav", "flac"]);
const EMPTY_AGENT_OUTPUT_ERROR = "Agent returned no visible output.";

function parseMusicPromptTag(tag: string): ParsedMusicPrompt | undefined {
  // 解析 open tag + body。Body 用 `\n---\n` 分隔 prompt 和 lyrics（lyrics 可选）。
  const m = tag.match(/^<music_prompt((?:\s+\w+=["'][^"']*["'])*)\s*>([\s\S]*?)<\/music_prompt>$/);
  if (!m) return undefined;
  const attrsRaw = m[1] ?? "";
  const body = (m[2] ?? "").trim();
  if (body.length === 0) return undefined;

  const attrs: Record<string, string> = {};
  for (const am of attrsRaw.matchAll(/(\w+)=["']([^"']*)["']/g)) {
    const key = am[1];
    const val = am[2];
    if (key && val !== undefined) attrs[key.toLowerCase()] = val;
  }

  // 拆 prompt / lyrics
  const sepIdx = body.indexOf("\n---\n");
  let prompt: string;
  let lyrics: string | undefined;
  if (sepIdx !== -1) {
    prompt = body.slice(0, sepIdx).trim();
    lyrics = body.slice(sepIdx + 5).trim();
    if (lyrics.length === 0) lyrics = undefined;
  } else {
    prompt = body;
  }
  if (prompt.length === 0) return undefined;

  // 截断到 API 限制，避免无效请求
  if (prompt.length > 512) prompt = prompt.slice(0, 512);
  if (lyrics && lyrics.length > 4096) lyrics = lyrics.slice(0, 4096);

  const format = (attrs.format ?? "").toLowerCase().trim();
  const bpmRaw = Number.parseInt(attrs.bpm ?? "", 10);
  const seedRaw = Number.parseInt(attrs.seed ?? "", 10);
  const instrumentalStr = (attrs.instrumental ?? "").toLowerCase();

  return {
    alt: (attrs.alt ?? "音乐").trim() || "音乐",
    prompt,
    lyrics,
    instrumental: instrumentalStr === "true" ? true : instrumentalStr === "false" ? false : undefined,
    seconds: normalizeMusicSeconds(attrs.seconds),
    format: MUSIC_VALID_FORMATS.has(format as MusicFormat) ? (format as MusicFormat) : undefined,
    bpm: Number.isFinite(bpmRaw) && bpmRaw >= 30 && bpmRaw <= 300 ? bpmRaw : undefined,
    keyscale: attrs.keyscale ? attrs.keyscale.trim() : undefined,
    seed: Number.isFinite(seedRaw) ? seedRaw : undefined,
  };
}

function escapeMarkdownAlt(alt: string): string {
  return alt.replace(/[\]\\]/g, "\\$&");
}

function parseMemberIds(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === "string") : [];
  } catch {
    return [];
  }
}

function requestMemberIds(value: unknown, fallback: string[]): string[] {
  if (!Array.isArray(value)) {
    return fallback;
  }

  const ids = value.filter((id): id is string => typeof id === "string" && /^[a-z0-9_-]+$/i.test(id));
  return ids.length > 0 ? [...new Set(ids)] : fallback;
}

function requestAgentIds(body: PostBody, fallback: string[]): string[] {
  if (Array.isArray(body.agentIds)) {
    const ids = body.agentIds.filter((id): id is string => typeof id === "string" && /^[a-z0-9_-]+$/i.test(id));
    if (ids.length > 0) {
      return [...new Set(ids)];
    }
  }

  return body.agentId ? [body.agentId] : fallback;
}

const roomModeById: Record<string, RoomRunMode> = {
  relay: "sequential",
  brainstorm: "parallel",
  polish: "loop",
  "template-relay": "sequential",
  "template-brainstorm": "parallel",
  "template-polish": "loop",
};
const CONTEXT_TOTAL_CHAR_LIMIT = 1500;
const MIN_CONTEXT_ITEM_CHAR_LIMIT = 350;

function isRoomRunMode(value: unknown): value is RoomRunMode {
  return value === "direct" || value === "sequential" || value === "parallel" || value === "loop";
}

function resolveRoomRunMode(
  room: { id: string; agent_id: string | null; run_mode: string | null },
  body: PostBody,
): RoomRunMode {
  if (room.agent_id) {
    return "direct";
  }

  if (room.run_mode === "sequential" || room.run_mode === "parallel" || room.run_mode === "loop") {
    return room.run_mode;
  }

  if (isRoomRunMode(body.mode) && body.mode !== "direct") {
    return body.mode;
  }

  return roomModeById[room.id] ?? "sequential";
}

function buildDirectPrompt(userText: string): string {
  const hardConstraintBlock = formatHardConstraintBlock(userText);
  if (!hardConstraintBlock) {
    return userText;
  }

  return [hardConstraintBlock, userText, hardConstraintBlock].join("\n\n");
}

function extractHardConstraints(userText: string): string[] {
  const hardConstraintPattern =
    /(只|仅|不要|不能|不得|禁止|必须|务必|严格|不超过|不要超过|最多|最少|以内|每人|一句|两句|三句|[0-9一二三四五六七八九十百千]+\s*字|格式|JSON|Markdown|VERDICT|only|must|do not|don't|no more than|exactly|required|format|sentence|word|character)/i;
  const derivedConstraints: string[] = [];
  if (/(每个?人|每个?\s*Agent|每个?\s*agent|每人|每个).*(一句话|一\s*句话|一句)|只回复(一句话|一\s*句话|一句)|only\s+one\s+sentence/i.test(userText)) {
    derivedConstraints.push("每个 Agent 最多输出 40 个中文字符，只能写一句话，不要自报名字或加姓名前缀。");
  }

  const candidates = userText
    .split(/[\n。！？!?；;]/)
    .map((part) => part.trim())
    .filter((part) => part.length > 0 && hardConstraintPattern.test(part));
  const seen = new Set<string>();
  const constraints: string[] = [];

  for (const candidate of [...derivedConstraints, ...candidates]) {
    const normalized = candidate.replace(/\s+/g, " ").slice(0, 220);
    if (seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);
    constraints.push(normalized);
    if (constraints.length >= 6) {
      break;
    }
  }

  return constraints;
}

function formatHardConstraintBlock(userText: string): string {
  const constraints = extractHardConstraints(userText);
  if (constraints.length === 0) {
    return "";
  }

  return ["### 硬约束（必须遵守）", ...constraints.map((constraint) => `- ${constraint}`)].join("\n");
}

function withHardConstraints(userText: string, sections: string[]): string {
  const hardConstraintBlock = formatHardConstraintBlock(userText);
  if (!hardConstraintBlock) {
    return sections.join("\n\n");
  }

  return [hardConstraintBlock, ...sections, "再次确认：上面的硬约束优先级高于前序 Agent 输出。", hardConstraintBlock].join("\n\n");
}

function compactTextForContext(text: string, charLimit: number): string {
  const trimmed = text.trim();
  if (trimmed.length <= charLimit) {
    return trimmed;
  }

  const omitted = trimmed.length - charLimit;
  const marker = `\n\n[... omitted ${omitted} chars ...]\n\n`;
  const remaining = Math.max(80, charLimit - marker.length);
  const headLength = Math.ceil(remaining * 0.6);
  const tailLength = Math.max(0, remaining - headLength);
  return `${trimmed.slice(0, headLength)}${marker}${trimmed.slice(trimmed.length - tailLength)}`;
}

function formatAgentOutputForContext(output: AgentTurnOutput, charLimit: number): string {
  return `## ${output.agent.name} / ${output.agent.role}\n${compactTextForContext(output.body, charLimit)}`;
}

function formatPreviousOutputsForContext(previousOutputs: AgentTurnOutput[]): string {
  const totalChars = previousOutputs.reduce((sum, output) => sum + output.body.length, 0);
  const itemCharLimit =
    totalChars > CONTEXT_TOTAL_CHAR_LIMIT
      ? Math.max(MIN_CONTEXT_ITEM_CHAR_LIMIT, Math.floor(CONTEXT_TOTAL_CHAR_LIMIT / previousOutputs.length))
      : Number.MAX_SAFE_INTEGER;

  return previousOutputs.map((item) => formatAgentOutputForContext(item, itemCharLimit)).join("\n\n");
}

function buildSequentialPrompt(
  userText: string,
  previousOutputs: AgentTurnOutput[],
): string {
  if (previousOutputs.length === 0) {
    return withHardConstraints(userText, [
      "你在一个多 Agent 群聊接龙中发言，这是第一棒。",
      `用户原始需求：\n${userText}`,
      "请只完成你这个角色最有价值的一步，不要替后续 Agent 总结。",
    ]);
  }

  const context = formatPreviousOutputsForContext(previousOutputs);
  return withHardConstraints(userText, [
    "你在一个多 Agent 群聊接龙中发言。",
    `用户原始需求：\n${userText}`,
    `前序 Agent 输出：\n${context}`,
    "请基于前序输出继续推进，只补充你这个角色最有价值的判断、修改或执行建议。不要重复寒暄。",
  ]);
}

function buildParallelPrompt(userText: string): string {
  return withHardConstraints(userText, [
    "你在一个多 Agent 头脑风暴房中发言。",
    "房间模式：parallel fanout。你这一轮看不到其他 Agent 的输出，也不要假设他们说了什么。",
    `用户原始需求：\n${userText}`,
    "请只给出你这个角色的独立判断、方案或风险。不要做最终合并；不要要求等待其他人；不要重复寒暄。",
  ]);
}

function buildPolishProducerPrompt(params: {
  userText: string;
  round: number;
  previousDraft?: string;
  criticFeedback?: string;
}): string {
  if (!params.previousDraft || !params.criticFeedback) {
    return withHardConstraints(params.userText, [
      "你在打磨房中担任 producer。",
      "任务：先产出一个可被 critic 审查的初稿，不要自我评审。",
      `用户原始需求：\n${params.userText}`,
    ]);
  }

  return withHardConstraints(params.userText, [
    "你在打磨房中担任 producer。",
    `这是第 ${params.round} 轮修订。请基于 critic 反馈改稿，只输出修订后的版本和必要说明。`,
    `用户原始需求：\n${params.userText}`,
    `上一版初稿：\n${compactTextForContext(params.previousDraft, CONTEXT_TOTAL_CHAR_LIMIT)}`,
    `critic 反馈：\n${compactTextForContext(params.criticFeedback, CONTEXT_TOTAL_CHAR_LIMIT)}`,
  ]);
}

function buildPolishCriticPrompt(params: {
  userText: string;
  draftAgent: AgentProfileLite;
  draft: string;
  round: number;
}): string {
  return withHardConstraints(params.userText, [
    "你在打磨房中担任 critic。",
    "任务：审查 producer 的输出是否满足用户原始需求。先给具体修改意见，再用最后一行给 verdict。",
    "最后一行必须严格写成：VERDICT: approved 或 VERDICT: revise 或 VERDICT: escalate",
    "approved = 可交付；revise = producer 应该再改一轮；escalate = 缺少用户输入或目标冲突。",
    `用户原始需求：\n${params.userText}`,
    `producer (${params.draftAgent.name} / ${params.draftAgent.role}) 第 ${params.round} 轮输出：\n${compactTextForContext(params.draft, CONTEXT_TOTAL_CHAR_LIMIT)}`,
  ]);
}

function parsePolishVerdict(text: string): PolishVerdict | undefined {
  const match = text.match(/VERDICT:\s*(approved|revise|escalate)\s*$/im);
  return match?.[1] as PolishVerdict | undefined;
}

messagesRoute.post("/:roomId/messages", async (c) => {
  const roomId = c.req.param("roomId");
  const body = (await c.req.json()) as PostBody;

  const room = db.prepare(`SELECT id, agent_id, member_ids, run_mode FROM rooms WHERE id = ?`).get(roomId) as
    | { id: string; agent_id: string | null; member_ids: string | null; run_mode: string | null }
    | undefined;
  if (!room) return c.json({ error: "room not found" }, 404);

  const storedMemberIds = parseMemberIds(room.member_ids);
  const memberIds = room.agent_id ? storedMemberIds : requestMemberIds(body.memberIds, storedMemberIds);
  const targetAgentIds = room.agent_id ? [room.agent_id] : requestAgentIds(body, memberIds);
  if (targetAgentIds.length === 0) return c.json({ error: "agentId required for room messages" }, 400);
  if (!room.agent_id && targetAgentIds.some((agentId) => !memberIds.includes(agentId))) {
    return c.json({ error: "agent is not a member of this room" }, 400);
  }

  const targetAgents: AgentProfileLite[] = [];
  for (const agentId of targetAgentIds) {
    const agent = db.prepare(`SELECT id, name, role FROM agent_profiles WHERE id = ?`).get(agentId) as
      | AgentProfileLite
      | undefined;
    if (!agent) return c.json({ error: `agent not found: ${agentId}` }, 404);
    targetAgents.push(agent);
  }
  const runMode = resolveRoomRunMode(room, body);

  const userText = (body.text ?? body.prompt ?? "").trim();
  if (!userText) return c.json({ error: "text or prompt required" }, 400);
  const runId = body.runId ?? `run_${randomUUID()}`;
  const threadId = roomId;

  insertMessage({
    id: `msg_${randomUUID()}`,
    roomId,
    sender: "human",
    body: userText,
  });

  return streamSSE(c, async (stream) => {
    let seq = 1;
    const ts = () => Date.now();
    const upstream = new AbortController();
    // 客户端断开只代表当前 UI 不再接收 SSE；后台 run 仍要跑完并入库。
    // 切换房间会断开当前流，如果这里取消上游，未完成的 agent 输出和 media 会丢。
    let clientAborted = false;
    stream.onAbort(() => {
      clientAborted = true;
    });
    const canStream = () => !clientAborted && !stream.aborted;
    let emitChain = Promise.resolve();

    const emit = async (type: string, payload: unknown, extra: Record<string, unknown> = {}) => {
      if (!canStream()) return;
      const evt = {
        id: `evt_${randomUUID()}`,
        runId,
        threadId,
        seq: seq++,
        ts: ts(),
        visibility: "user" as const,
        type,
        payload,
        ...extra,
      };
      const write = () => canStream() ? stream.writeSSE({ event: "agentux", data: JSON.stringify(evt) }) : Promise.resolve();
      const next = emitChain.then(write, write);
      emitChain = next.catch(() => {});
      try {
        await next;
      } catch {
        clientAborted = true;
      }
    };

    const runAgentTurn = async (agent: AgentProfileLite, agentPrompt: string): Promise<AgentTurnOutput | undefined> => {
      if (upstream.signal.aborted) return undefined;

      const agentId = agent.id;
      const sessionUser = body.sessionUser ?? `me:${roomId}:${agentId}`;
      const messageId = `msg_${randomUUID()}`;
      const textId = `txt_${randomUUID()}`;
      const textMetadata = { agentId, roomId };
      await emit("text.started", { textId, agentId, metadata: textMetadata }, { messageId });

      const filter = new ImagePromptStreamFilter();
      const musicFilter = new MusicPromptStreamFilter();
      let visibleBuffer = ""; // 用户看到的部分（不含 tag）
      const mediaTasks: Promise<MediaTaskResult>[] = [];

      const startImageTask = ({ alt, prompt }: ParsedImagePrompt) => {
        const idx = mediaTasks.length;
        const mediaUrl = `/api/messages/${messageId}/media/${idx}`;
        const task = (async (): Promise<MediaTaskResult> => {
          try {
            if (canStream()) {
              await emit("media.started", { messageId, idx, alt, kind: "image" }, { messageId });
            }
            const { filename } = await generateImage({
              messageId,
              idx,
              prompt,
              signal: upstream.signal,
            });
            if (canStream()) {
              await emit("media.ready", { messageId, idx, alt, mediaUrl, kind: "image" }, { messageId });
            }
            return {
              idx,
              alt,
              filename,
              mdLine: `\n\n![${escapeMarkdownAlt(alt)}](${mediaUrl})\n\n`,
            };
          } catch (err) {
            if (!upstream.signal.aborted) {
              const reason = err instanceof Error ? err.message : String(err);
              console.warn(`[messages] image gen failed for ${messageId}#${idx}: ${reason}`);
              try {
                if (canStream()) {
                  await emit("media.failed", { messageId, idx, alt, reason, kind: "image" }, { messageId });
                }
              } catch {
                /* stream closed */
              }
            }
            return { idx, alt };
          }
        })();
        mediaTasks.push(task);
      };

      const startMusicTask = (p: ParsedMusicPrompt) => {
        const idx = mediaTasks.length;
        const format = p.format ?? "mp3";
        const mediaUrl = `/api/messages/${messageId}/media/${idx}.${format}`;
        const task = (async (): Promise<MediaTaskResult> => {
          try {
            if (canStream()) {
              await emit("media.started", { messageId, idx, alt: p.alt, kind: "audio" }, { messageId });
            }
            const { filename } = await generateMusic({
              messageId,
              idx,
              prompt: p.prompt,
              lyrics: p.lyrics,
              instrumental: p.instrumental,
              seconds: p.seconds,
              format,
              bpm: p.bpm,
              keyscale: p.keyscale,
              seed: p.seed,
              signal: upstream.signal,
            });
            if (canStream()) {
              await emit("media.ready", { messageId, idx, alt: p.alt, mediaUrl, kind: "audio" }, { messageId });
            }
            return {
              idx,
              alt: p.alt,
              filename,
              mdLine: `\n\n![${escapeMarkdownAlt(p.alt)}](${mediaUrl})\n\n`,
            };
          } catch (err) {
            if (!upstream.signal.aborted) {
              const reason = err instanceof Error ? err.message : String(err);
              console.warn(`[messages] music gen failed for ${messageId}#${idx}: ${reason}`);
              try {
                if (canStream()) {
                  await emit("media.failed", { messageId, idx, alt: p.alt, reason, kind: "audio" }, { messageId });
                }
              } catch {
                /* stream closed */
              }
            }
            return { idx, alt: p.alt };
          }
        })();
        mediaTasks.push(task);
      };

      for await (const event of streamOpenClaw({ agentId, userText: agentPrompt, sessionUser, signal: upstream.signal })) {
        if ("delta" in event) {
          const { text: afterImage, prompts: imagePrompts } = filter.push(event.delta);
          imagePrompts.forEach(startImageTask);
          const { text, prompts: musicPrompts } = musicFilter.push(afterImage);
          musicPrompts.forEach(startMusicTask);
          if (text.length > 0) {
            visibleBuffer += text;
            await emit("text.delta", { textId, delta: text, metadata: textMetadata }, { messageId });
          }
        }
      }

      const tail = filter.flush();
      if (tail.length > 0) {
        const { text: tailText, prompts: tailMusic } = musicFilter.push(tail);
        tailMusic.forEach(startMusicTask);
        if (tailText.length > 0) {
          visibleBuffer += tailText;
          await emit("text.delta", { textId, delta: tailText, metadata: textMetadata }, { messageId });
        }
      }
      const musicTail = musicFilter.flush();
      if (musicTail.length > 0) {
        visibleBuffer += musicTail;
        await emit("text.delta", { textId, delta: musicTail, metadata: textMetadata }, { messageId });
      }

      const mediaFilenames: string[] = [];
      const mediaResults = (await Promise.all(mediaTasks)).sort((left, right) => left.idx - right.idx);
      for (const result of mediaResults) {
        if (!result.filename || !result.mdLine) {
          continue;
        }
        mediaFilenames.push(result.filename);
        visibleBuffer += result.mdLine;
        // 实时渲染会在 run.finished 前跳过 markdown 图片，避免和 media card 重影。
        try {
          if (canStream()) {
            await emit("text.delta", { textId, delta: result.mdLine, metadata: textMetadata }, { messageId });
          }
        } catch {
          /* stream closed */
        }
      }

      if (visibleBuffer.trim().length === 0 && mediaTasks.length === 0) {
        throw new Error(EMPTY_AGENT_OUTPUT_ERROR);
      }

      try {
        if (canStream()) {
          await emit("text.finished", { textId, text: visibleBuffer, metadata: textMetadata }, { messageId });
        }
      } catch {
        /* stream closed */
      }

      if (visibleBuffer.length > 0) {
        insertMessage({
          id: messageId,
          roomId,
          sender: "agent",
          agentId,
          body: visibleBuffer,
          mediaPaths: mediaFilenames,
        });
      }

      return { agent, body: visibleBuffer };
    };

    const runSequential = async () => {
      const previousOutputs: AgentTurnOutput[] = [];
      for (const agent of targetAgents) {
        const prompt = runMode === "direct" ? buildDirectPrompt(userText) : buildSequentialPrompt(userText, previousOutputs);
        const output = await runAgentTurn(agent, prompt);
        if (output?.body) {
          previousOutputs.push(output);
        }
      }
    };

    const runParallel = async () => {
      await Promise.all(targetAgents.map((agent) => runAgentTurn(agent, buildParallelPrompt(userText))));
    };

    const runLoop = async () => {
      const [producer, critic] = targetAgents;
      if (!producer) {
        return;
      }
      if (!critic) {
        await runAgentTurn(producer, buildDirectPrompt(userText));
        return;
      }

      const firstDraft = await runAgentTurn(producer, buildPolishProducerPrompt({ userText, round: 1 }));
      if (upstream.signal.aborted || !firstDraft?.body) {
        return;
      }

      const firstCritique = await runAgentTurn(
        critic,
        buildPolishCriticPrompt({
          userText,
          draftAgent: producer,
          draft: firstDraft.body,
          round: 1,
        }),
      );
      if (upstream.signal.aborted || !firstCritique?.body) {
        return;
      }

      if (parsePolishVerdict(firstCritique.body) !== "revise") {
        return;
      }

      await runAgentTurn(
        producer,
        buildPolishProducerPrompt({
          userText,
          round: 2,
          previousDraft: firstDraft.body,
          criticFeedback: firstCritique.body,
        }),
      );
    };

    try {
      await emit("run.started", { agentIds: targetAgentIds, mode: runMode });

      if (runMode === "parallel") {
        await runParallel();
      } else if (runMode === "loop") {
        await runLoop();
      } else {
        await runSequential();
      }

      try {
        if (canStream()) {
          await emit("run.finished", { agentIds: targetAgentIds, mode: runMode });
        }
      } catch {
        /* stream closed */
      }
    } catch (err) {
      if (upstream.signal.aborted) return;
      const message = err instanceof Error ? err.message : String(err);
      const userMessage =
        message === EMPTY_AGENT_OUTPUT_ERROR
          ? "这次没有生成出可显示的内容，可以重新发一次。"
          : "这次回复没有发出去，可以检查本地模型连接后再试。";
      try {
        await emit("run.error", { error: message, userMessage });
      } catch {
        /* stream closed */
      }
    }
  });
});

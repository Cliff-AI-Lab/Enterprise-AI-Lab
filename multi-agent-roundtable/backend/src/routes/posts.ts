import { Hono } from "hono";
import { randomUUID } from "node:crypto";
import { existsSync, statSync, createReadStream } from "node:fs";
import { db, insertPost, listPosts } from "../db.js";
import { streamOpenClaw } from "../openclaw.js";
import { generatePostImage, postMediaLocalPath } from "../imageGen.js";
import { generateMusic, normalizeMusicSeconds, POSTS_MUSIC_DIR, type MusicFormat, type MusicSeconds } from "../musicGen.js";

export const postsRoute = new Hono();

const MOMENTS_TRIGGER_PROMPT = `[Moments 朋友圈] 现在请发一条新动态。

要求：
- 直接给出 post 正文，不要"好的，我来发一条"这种开场白
- 第一人称、口语、有具体内容（一个场景 / 一段感受 / 一帧画面）
- 长度 40-180 字
- 可以配 1 张图：用 <image_prompt alt="中文简短">英文画面描述</image_prompt> 嵌在正文里
- 配图描述要具体到画面（人物 / 场景 / 风格 / 光线），不要泛词
- 不配图就纯文字也行，**不要为了配图凑画面**
- 如果你的 SOUL 教过 <music_prompt> 协议，也可以配 1 段音乐——和图二选一或都配，自己判断要不要
- 不要在末尾问用户问题（这是单向发布，不是聊天）`;

interface ParsedImagePrompt {
  alt: string;
  prompt: string;
}

function parseImagePrompts(text: string): ParsedImagePrompt[] {
  const re = /<image_prompt(?:\s+alt=["']([^"']*)["'])?\s*>([\s\S]*?)<\/image_prompt>/g;
  const out: ParsedImagePrompt[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    const alt = (m[1] ?? "图").trim() || "图";
    const prompt = (m[2] ?? "").trim();
    if (prompt.length === 0) continue;
    out.push({ alt, prompt });
  }
  return out;
}

function stripImagePrompts(text: string): string {
  return text.replace(/<image_prompt[^>]*>[\s\S]*?<\/image_prompt>/g, "").trim();
}

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

const MUSIC_VALID_FORMATS = new Set<MusicFormat>(["mp3", "wav", "flac"]);

function parseMusicPrompts(text: string): ParsedMusicPrompt[] {
  const re = /<music_prompt((?:\s+\w+=["'][^"']*["'])*)\s*>([\s\S]*?)<\/music_prompt>/g;
  const out: ParsedMusicPrompt[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    const attrsRaw = m[1] ?? "";
    const body = (m[2] ?? "").trim();
    if (body.length === 0) continue;

    const attrs: Record<string, string> = {};
    for (const am of attrsRaw.matchAll(/(\w+)=["']([^"']*)["']/g)) {
      const key = am[1];
      const val = am[2];
      if (key && val !== undefined) attrs[key.toLowerCase()] = val;
    }

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
    if (prompt.length === 0) continue;
    if (prompt.length > 512) prompt = prompt.slice(0, 512);
    if (lyrics && lyrics.length > 4096) lyrics = lyrics.slice(0, 4096);

    const format = (attrs.format ?? "").toLowerCase().trim();
    const bpmRaw = Number.parseInt(attrs.bpm ?? "", 10);
    const seedRaw = Number.parseInt(attrs.seed ?? "", 10);
    const instrumentalStr = (attrs.instrumental ?? "").toLowerCase();

    out.push({
      alt: (attrs.alt ?? "音乐").trim() || "音乐",
      prompt,
      lyrics,
      instrumental: instrumentalStr === "true" ? true : instrumentalStr === "false" ? false : undefined,
      seconds: normalizeMusicSeconds(attrs.seconds),
      format: MUSIC_VALID_FORMATS.has(format as MusicFormat) ? (format as MusicFormat) : undefined,
      bpm: Number.isFinite(bpmRaw) && bpmRaw >= 30 && bpmRaw <= 300 ? bpmRaw : undefined,
      keyscale: attrs.keyscale ? attrs.keyscale.trim() : undefined,
      seed: Number.isFinite(seedRaw) ? seedRaw : undefined,
    });
  }
  return out;
}

function stripMusicPrompts(text: string): string {
  return text.replace(/<music_prompt[^>]*>[\s\S]*?<\/music_prompt>/g, "").trim();
}

function escapeMarkdownAlt(alt: string): string {
  return alt.replace(/[\]\\]/g, "\\$&");
}

// POST /api/agents/:id/posts/generate
// 同步：~5-40s（取决于是否生图）。前端 button 显 spinner 等。
postsRoute.post("/agents/:id/posts/generate", async (c) => {
  const agentId = c.req.param("id");
  const agent = db.prepare(`SELECT id FROM agent_profiles WHERE id = ?`).get(agentId) as
    | { id: string }
    | undefined;
  if (!agent) return c.json({ error: "agent not found" }, 404);

  const postId = `post_${randomUUID()}`;
  // sessionUser 用 :moments 后缀隔离 Moments 会话，不污染 chat 上下文
  const sessionUser = `me:${agentId}:moments`;

  let rawReply = "";
  try {
    for await (const event of streamOpenClaw({ agentId, userText: MOMENTS_TRIGGER_PROMPT, sessionUser })) {
      if ("delta" in event) rawReply += event.delta;
    }
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err);
    return c.json({ error: `agent run failed: ${reason}` }, 502);
  }

  if (!rawReply.trim()) {
    return c.json({ error: "agent returned empty reply" }, 502);
  }

  const imagePrompts = parseImagePrompts(rawReply);
  const musicPrompts = parseMusicPrompts(rawReply);
  let body = stripMusicPrompts(stripImagePrompts(rawReply));
  const mediaFilenames: string[] = [];

  // 研究类 agent 强制不配图：SOUL.md 写了"不配图"但 LLM 受默认 trigger 里
  // "可以配 1 张图"诱导仍会偶发输出 <image_prompt>。这里做硬挡，确保 Moment
  // 不带图——研究内容文字驱动，配图反而减分。
  const NO_MOMENTS_IMAGE_AGENTS = new Set(["iris"]);
  // Moments 限 1 张图、1 段音乐（SOUL.md 也教了），多余的忽略
  const cappedImagePrompts = NO_MOMENTS_IMAGE_AGENTS.has(agentId) ? [] : imagePrompts.slice(0, 1);
  const cappedMusicPrompts = musicPrompts.slice(0, 1);
  let mediaIdx = 0;
  for (const item of cappedImagePrompts) {
    const i = mediaIdx++;
    try {
      const { filename } = await generatePostImage({
        postId,
        idx: i,
        prompt: item.prompt,
      });
      mediaFilenames.push(filename);
      body += `\n\n![${escapeMarkdownAlt(item.alt)}](/api/posts/${postId}/media/${i})\n\n`;
    } catch (err) {
      const reason = err instanceof Error ? err.message : String(err);
      console.warn(`[posts] image gen failed for ${postId}#${i}: ${reason}`);
      // 失败不阻塞——post 仅保留文字
    }
  }
  for (const item of cappedMusicPrompts) {
    const i = mediaIdx++;
    const format = item.format ?? "mp3";
    try {
      const { filename } = await generateMusic({
        messageId: postId, // musicGen 用 messageId 拼文件名；这里给 postId 复用
        idx: i,
        prompt: item.prompt,
        lyrics: item.lyrics,
        instrumental: item.instrumental,
        seconds: item.seconds,
        format,
        bpm: item.bpm,
        keyscale: item.keyscale,
        seed: item.seed,
        outputDir: POSTS_MUSIC_DIR,
      });
      mediaFilenames.push(filename);
      body += `\n\n![${escapeMarkdownAlt(item.alt)}](/api/posts/${postId}/media/${i}.${format})\n\n`;
    } catch (err) {
      const reason = err instanceof Error ? err.message : String(err);
      console.warn(`[posts] music gen failed for ${postId}#${i}: ${reason}`);
    }
  }

  body = body.trim();
  if (body.length === 0) {
    return c.json({ error: "agent reply collapsed to empty after parsing" }, 502);
  }

  insertPost({ id: postId, agentId, body, mediaPaths: mediaFilenames });

  const fresh = listPosts({ agentId, limit: 1 })[0];
  return c.json({ post: fresh });
});

// GET /api/posts?agentId=...&limit=...
postsRoute.get("/posts", (c) => {
  const agentId = c.req.query("agentId") || undefined;
  const limitParam = c.req.query("limit");
  const limit = limitParam ? Math.min(Math.max(parseInt(limitParam, 10) || 50, 1), 200) : 50;
  return c.json({ posts: listPosts({ agentId, limit }) });
});

// GET /api/posts/:id/media/:idx — 安全 stream，扩展名可选：无 = .png（图片旧格式），mp3/wav/flac = 音频
const POSTS_CONTENT_TYPES: Record<string, string> = {
  png: "image/png",
  mp3: "audio/mpeg",
  wav: "audio/wav",
  flac: "audio/flac",
};
postsRoute.get("/posts/:id/media/:idx", (c) => {
  const id = c.req.param("id");
  const idxParam = c.req.param("idx");
  if (!/^post_[a-z0-9-]+$/i.test(id)) return c.notFound();
  const m = idxParam.match(/^(\d+)(?:\.([a-z0-9]+))?$/i);
  if (!m) return c.notFound();
  const idx = m[1];
  const reqExt = (m[2] ?? "").toLowerCase();
  const ext = reqExt || "png";
  const p = postMediaLocalPath(`${id}-${idx}.${ext}`);
  if (!existsSync(p)) return c.notFound();
  const stat = statSync(p);
  const contentType = POSTS_CONTENT_TYPES[ext] ?? "application/octet-stream";
  const cacheControl = /^(mp3|wav|flac)$/.test(ext) ? "no-cache" : "public, max-age=86400";
  const range = c.req.header("range");
  if (range) {
    const mRange = range.match(/^bytes=(\d*)-(\d*)$/);
    if (!mRange || (!mRange[1] && !mRange[2])) {
      c.header("Content-Range", `bytes */${stat.size}`);
      return c.body(null, 416);
    }
    const requestedStart = mRange[1] ? Number.parseInt(mRange[1], 10) : undefined;
    const requestedEnd = mRange[2] ? Number.parseInt(mRange[2], 10) : undefined;
    const suffixLength = requestedStart === undefined ? requestedEnd : undefined;
    const start = suffixLength !== undefined ? Math.max(stat.size - suffixLength, 0) : requestedStart!;
    const end = suffixLength !== undefined ? stat.size - 1 : requestedEnd !== undefined ? Math.min(requestedEnd, stat.size - 1) : stat.size - 1;
    if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end < start || start >= stat.size) {
      c.header("Content-Range", `bytes */${stat.size}`);
      return c.body(null, 416);
    }
    c.status(206);
    c.header("Content-Type", contentType);
    c.header("Content-Length", String(end - start + 1));
    c.header("Content-Range", `bytes ${start}-${end}/${stat.size}`);
    c.header("Cache-Control", cacheControl);
    c.header("Accept-Ranges", "bytes");
    return c.body(createReadStream(p, { start, end }) as unknown as ReadableStream);
  }

  c.header("Content-Type", contentType);
  c.header("Content-Length", String(stat.size));
  c.header("Cache-Control", cacheControl);
  c.header("Accept-Ranges", "bytes");
  return c.body(createReadStream(p) as unknown as ReadableStream);
});

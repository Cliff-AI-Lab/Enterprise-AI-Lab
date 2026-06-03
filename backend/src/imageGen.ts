import { mkdirSync, existsSync, createWriteStream } from "node:fs";
import { resolve } from "node:path";
import { pipeline } from "node:stream/promises";
import { Readable } from "node:stream";

// 同步调 ruidong z-image-turbo（~10s 阻塞），fetch 返回的 URL，落到 backend/data/media/<id>.png。
// 返回相对文件名（如 "msg_abc-0.png"），不返回绝对路径——上层用 GET /api/messages/:id/media/:idx 拼。

const MEDIA_DIR = resolve(process.env.TELEGRAM_AGENT_MEDIA_DIR ?? "./data/media");
const POSTS_MEDIA_DIR = resolve(process.env.TELEGRAM_AGENT_POSTS_MEDIA_DIR ?? "./data/posts");
const RUIDONG_BASE = "https://iruidong.com/v1";
const IMAGE_MODEL = process.env.RUIDONG_IMAGE_MODEL ?? "z-image-turbo";
const IMAGE_TIMEOUT_MS = 60_000;

function ensureDir(dir: string): void {
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

function ensureMediaDir(): void { ensureDir(MEDIA_DIR); }
function ensurePostsDir(): void { ensureDir(POSTS_MEDIA_DIR); }

export interface ImageGenResult {
  filename: string;
  costTokens: number | null;
}

export async function generateImage(params: {
  messageId: string;
  idx: number;
  prompt: string;
  signal?: AbortSignal;
}): Promise<ImageGenResult> {
  const apiKey = process.env.RUIDONG_API_KEY;
  if (!apiKey) throw new Error("RUIDONG_API_KEY not set");

  ensureMediaDir();

  const ctrl = new AbortController();
  const timeoutHandle = setTimeout(() => ctrl.abort(), IMAGE_TIMEOUT_MS);
  // 串联外部 abort：上游 SSE 客户端断开 → 取消 image gen 也取消
  const onParentAbort = () => ctrl.abort();
  if (params.signal) params.signal.addEventListener("abort", onParentAbort, { once: true });

  try {
    const genRes = await fetch(`${RUIDONG_BASE}/images/generations`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: IMAGE_MODEL,
        prompt: params.prompt,
        n: 1,
        size: "1024x1024",
      }),
      signal: ctrl.signal,
    });

    if (!genRes.ok) {
      const body = await genRes.text().catch(() => "");
      throw new Error(`image gen HTTP ${genRes.status}: ${body.slice(0, 300)}`);
    }

    const payload = (await genRes.json()) as {
      data?: Array<{ url?: string }>;
      usage?: { total_tokens?: number };
    };
    const url = payload.data?.[0]?.url;
    if (!url) throw new Error("image gen returned no url");

    const imgRes = await fetch(url, { signal: ctrl.signal });
    if (!imgRes.ok || !imgRes.body) {
      throw new Error(`image fetch HTTP ${imgRes.status}`);
    }

    const filename = `${params.messageId}-${params.idx}.png`;
    const localPath = resolve(MEDIA_DIR, filename);
    await pipeline(Readable.fromWeb(imgRes.body as never), createWriteStream(localPath));

    return { filename, costTokens: payload.usage?.total_tokens ?? null };
  } finally {
    clearTimeout(timeoutHandle);
    if (params.signal) params.signal.removeEventListener("abort", onParentAbort);
  }
}

export function mediaLocalPath(filename: string): string {
  ensureMediaDir();
  return resolve(MEDIA_DIR, filename);
}

// Moments posts 用独立目录 backend/data/posts/<postId>-<idx>.png，不和 chat messages media 混。
export async function generatePostImage(params: {
  postId: string;
  idx: number;
  prompt: string;
  signal?: AbortSignal;
}): Promise<ImageGenResult> {
  const apiKey = process.env.RUIDONG_API_KEY;
  if (!apiKey) throw new Error("RUIDONG_API_KEY not set");
  ensurePostsDir();

  const ctrl = new AbortController();
  const timeoutHandle = setTimeout(() => ctrl.abort(), IMAGE_TIMEOUT_MS);
  const onParentAbort = () => ctrl.abort();
  if (params.signal) params.signal.addEventListener("abort", onParentAbort, { once: true });

  try {
    const genRes = await fetch(`${RUIDONG_BASE}/images/generations`, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model: IMAGE_MODEL, prompt: params.prompt, n: 1, size: "1024x1024" }),
      signal: ctrl.signal,
    });
    if (!genRes.ok) {
      const body = await genRes.text().catch(() => "");
      throw new Error(`image gen HTTP ${genRes.status}: ${body.slice(0, 300)}`);
    }
    const payload = (await genRes.json()) as { data?: Array<{ url?: string }>; usage?: { total_tokens?: number } };
    const url = payload.data?.[0]?.url;
    if (!url) throw new Error("image gen returned no url");

    const imgRes = await fetch(url, { signal: ctrl.signal });
    if (!imgRes.ok || !imgRes.body) throw new Error(`image fetch HTTP ${imgRes.status}`);

    const filename = `${params.postId}-${params.idx}.png`;
    const localPath = resolve(POSTS_MEDIA_DIR, filename);
    await pipeline(Readable.fromWeb(imgRes.body as never), createWriteStream(localPath));

    return { filename, costTokens: payload.usage?.total_tokens ?? null };
  } finally {
    clearTimeout(timeoutHandle);
    if (params.signal) params.signal.removeEventListener("abort", onParentAbort);
  }
}

export function postMediaLocalPath(filename: string): string {
  ensurePostsDir();
  return resolve(POSTS_MEDIA_DIR, filename);
}

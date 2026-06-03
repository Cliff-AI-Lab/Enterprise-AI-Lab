import { Hono } from "hono";
import { existsSync, statSync, createReadStream } from "node:fs";
import { mediaLocalPath } from "../imageGen.js";

export const mediaRoute = new Hono();

// 前端 MarkdownText 白名单：URL 必须精确匹配 ^/api/(messages|posts)/[a-z0-9_-]+/media/\d+(\.\w+)?$
// 这里 msgId 限 msg_<uuid-ish>，idx 限纯数字，扩展名可选（图片旧消息没扩展名，音频/未来格式带扩展名）。
const CONTENT_TYPES: Record<string, string> = {
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  webp: "image/webp",
  mp3: "audio/mpeg",
  wav: "audio/wav",
  flac: "audio/flac",
  ogg: "audio/ogg",
  m4a: "audio/mp4",
  mp4: "video/mp4",
  webm: "video/webm",
};

mediaRoute.get("/:msgId/media/:idx", (c) => {
  const msgId = c.req.param("msgId");
  const idxParam = c.req.param("idx");
  if (!/^msg_[a-z0-9-]+$/i.test(msgId)) return c.notFound();

  // idx 可带扩展名：'0' 或 '0.mp3'
  const m = idxParam.match(/^(\d+)(?:\.([a-z0-9]+))?$/i);
  if (!m) return c.notFound();
  const idx = m[1];
  const reqExt = (m[2] ?? "").toLowerCase();

  // 显式扩展名 → 直接读对应文件；否则回退到 .png（图片旧消息）。
  const candidateExt = reqExt || "png";
  const filename = `${msgId}-${idx}.${candidateExt}`;
  const p = mediaLocalPath(filename);
  if (!existsSync(p)) return c.notFound();

  const stat = statSync(p);
  const contentType = CONTENT_TYPES[candidateExt] ?? "application/octet-stream";
  const cacheControl = /^(mp3|wav|flac|ogg|m4a|mp4|webm)$/.test(candidateExt)
    ? "no-cache"
    : "public, max-age=86400";
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

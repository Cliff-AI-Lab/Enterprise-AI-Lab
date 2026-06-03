import { spawnSync } from "node:child_process";
import { mkdirSync, existsSync, createWriteStream, renameSync, unlinkSync } from "node:fs";
import { resolve } from "node:path";
import { pipeline } from "node:stream/promises";
import { Readable } from "node:stream";

// ruidong ACE-Step：异步生成。POST /v1/videos → poll GET /v1/videos/{id} → GET /v1/videos/{id}/content。
// 落到 backend/data/media/<messageId>-<idx>.<ext>，<ext> = mp3 | wav | flac。
// 注意：下载端点的 Content-Type 是 video/mp4 但 bytes 是真音频；按 format 落 ext，别看 header。

const MEDIA_DIR = resolve(process.env.TELEGRAM_AGENT_MEDIA_DIR ?? "./data/media");
export const POSTS_MUSIC_DIR = resolve(process.env.TELEGRAM_AGENT_POSTS_MEDIA_DIR ?? "./data/posts");
const RUIDONG_BASE = "https://iruidong.com/v1";
const MUSIC_MODEL = process.env.RUIDONG_MUSIC_MODEL ?? "ace-step-v15";
const MUSIC_TIMEOUT_MS = 180_000;
const POLL_INTERVAL_MS = 4_000;

function ensureDir(dir: string): void {
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

export type MusicFormat = "mp3" | "wav" | "flac";
export type MusicSeconds = "auto" | `${number}`;

export interface MusicGenParams {
  messageId: string;
  idx: number;
  prompt: string;
  lyrics?: string;
  instrumental?: boolean;
  seconds?: MusicSeconds;
  format?: MusicFormat;
  bpm?: number;
  keyscale?: string;
  seed?: number;
  signal?: AbortSignal;
  /** 落地目录。chat messages 用默认（data/media），Moments posts 传 POSTS_MEDIA_DIR。 */
  outputDir?: string;
}

export interface MusicGenResult {
  filename: string;
  format: MusicFormat;
  durationSeconds: number | null;
}

export function normalizeMusicSeconds(value: string | undefined): MusicSeconds | undefined {
  const trimmed = value?.trim().toLowerCase();
  if (!trimmed) return undefined;
  if (trimmed === "auto") return "auto";

  const seconds = Number(trimmed);
  if (!Number.isInteger(seconds) || seconds < 5 || seconds > 240) {
    return undefined;
  }
  return String(seconds) as MusicSeconds;
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((res, rej) => {
    const t = setTimeout(res, ms);
    if (signal) {
      const onAbort = () => {
        clearTimeout(t);
        rej(new DOMException("aborted", "AbortError"));
      };
      signal.addEventListener("abort", onAbort, { once: true });
    }
  });
}

function probeAudioDurationSeconds(localPath: string): number | null {
  const res = spawnSync(
    "ffprobe",
    ["-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", localPath],
    { encoding: "utf8" },
  );
  if (res.status !== 0) return null;
  const duration = Number.parseFloat(res.stdout.trim());
  return Number.isFinite(duration) && duration > 0 ? duration : null;
}

function trimTrailingSilence(localPath: string, format: MusicFormat, fallbackDuration: number | null): number | null {
  const beforeDuration = probeAudioDurationSeconds(localPath) ?? fallbackDuration;
  const trimmedPath = `${localPath}.trim.${format}`;
  const codecArgs = format === "mp3" ? ["-codec:a", "libmp3lame", "-b:a", "128k"] : [];
  const res = spawnSync(
    "ffmpeg",
    [
      "-y",
      "-hide_banner",
      "-nostdin",
      "-i",
      localPath,
      "-af",
      "silenceremove=start_periods=0:stop_periods=1:stop_duration=0.45:stop_threshold=-45dB",
      ...codecArgs,
      trimmedPath,
    ],
    { encoding: "utf8" },
  );

  if (res.status !== 0 || !existsSync(trimmedPath)) {
    if (existsSync(trimmedPath)) unlinkSync(trimmedPath);
    return beforeDuration ?? fallbackDuration;
  }

  const afterDuration = probeAudioDurationSeconds(trimmedPath);
  const trimmedEnough =
    beforeDuration !== null
    && afterDuration !== null
    && beforeDuration - afterDuration >= 0.3
    && afterDuration >= 1
    && afterDuration >= beforeDuration * 0.65;
  if (!trimmedEnough) {
    unlinkSync(trimmedPath);
    return beforeDuration ?? fallbackDuration;
  }

  renameSync(trimmedPath, localPath);
  return afterDuration;
}

export async function generateMusic(params: MusicGenParams): Promise<MusicGenResult> {
  const apiKey = process.env.RUIDONG_API_KEY;
  if (!apiKey) throw new Error("RUIDONG_API_KEY not set");

  const outputDir = params.outputDir ?? MEDIA_DIR;
  ensureDir(outputDir);

  const format: MusicFormat = params.format ?? "mp3";
  const ctrl = new AbortController();
  const timeoutHandle = setTimeout(() => ctrl.abort(), MUSIC_TIMEOUT_MS);
  const onParentAbort = () => ctrl.abort();
  if (params.signal) params.signal.addEventListener("abort", onParentAbort, { once: true });

  try {
    const body: Record<string, unknown> = {
      model: MUSIC_MODEL,
      prompt: params.prompt,
      // 默认 "auto" 让 ACE-Step 自己决定时长；固定时长偶发静音尾巴，下载后再裁掉。
      seconds: params.seconds ?? "auto",
      format,
    };
    if (params.lyrics) body.lyrics = params.lyrics;
    if (params.instrumental !== undefined) body.instrumental = params.instrumental;
    if (params.bpm !== undefined) body.bpm = params.bpm;
    if (params.keyscale) body.keyscale = params.keyscale;
    if (params.seed !== undefined) body.seed = params.seed;

    const createRes = await fetch(`${RUIDONG_BASE}/videos`, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    });
    if (!createRes.ok) {
      const txt = await createRes.text().catch(() => "");
      throw new Error(`music create HTTP ${createRes.status}: ${txt.slice(0, 300)}`);
    }
    const createJson = (await createRes.json()) as { id?: string; status?: string; error?: unknown };
    const id = createJson.id;
    if (!id) throw new Error(`music create returned no id: ${JSON.stringify(createJson).slice(0, 200)}`);

    let durationSeconds: number | null = null;
    while (true) {
      await sleep(POLL_INTERVAL_MS, ctrl.signal);
      const stRes = await fetch(`${RUIDONG_BASE}/videos/${encodeURIComponent(id)}`, {
        headers: { Authorization: `Bearer ${apiKey}` },
        signal: ctrl.signal,
      });
      if (!stRes.ok) {
        const txt = await stRes.text().catch(() => "");
        throw new Error(`music poll HTTP ${stRes.status}: ${txt.slice(0, 300)}`);
      }
      const st = (await stRes.json()) as {
        status?: string;
        error?: { message?: string } | null;
        usage?: { duration_seconds?: number };
      };
      durationSeconds = st.usage?.duration_seconds ?? durationSeconds;
      if (st.status === "completed") break;
      if (st.status === "failed") {
        const msg = st.error?.message ?? "unknown failure";
        throw new Error(`music failed: ${msg}`);
      }
    }

    const dlRes = await fetch(`${RUIDONG_BASE}/videos/${encodeURIComponent(id)}/content`, {
      headers: { Authorization: `Bearer ${apiKey}` },
      signal: ctrl.signal,
      redirect: "follow",
    });
    if (!dlRes.ok || !dlRes.body) {
      throw new Error(`music download HTTP ${dlRes.status}`);
    }

    const filename = `${params.messageId}-${params.idx}.${format}`;
    const localPath = resolve(outputDir, filename);
    await pipeline(Readable.fromWeb(dlRes.body as never), createWriteStream(localPath));
    durationSeconds = trimTrailingSilence(localPath, format, durationSeconds);

    return { filename, format, durationSeconds };
  } finally {
    clearTimeout(timeoutHandle);
    if (params.signal) params.signal.removeEventListener("abort", onParentAbort);
  }
}

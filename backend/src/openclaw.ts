import { buildEnvBlock } from "./envBlock.js";

interface OpenClawChunk {
  choices?: Array<{
    delta?: { content?: string };
    finish_reason?: string | null;
  }>;
}

export async function* streamOpenClaw(params: {
  agentId: string;
  userText: string;
  sessionUser: string;
  signal?: AbortSignal;
}): AsyncGenerator<{ delta: string } | { finish: string }, void, void> {
  const baseUrl = (process.env.OPENCLAW_BASE_URL ?? "http://127.0.0.1:18789").replace(/\/+$/, "");
  const token = process.env.OPENCLAW_GATEWAY_TOKEN ?? "";

  const res = await fetch(`${baseUrl}/v1/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      model: `openclaw/${params.agentId}`,
      messages: [
        { role: "system", content: buildEnvBlock() },
        { role: "user", content: params.userText },
      ],
      stream: true,
      user: params.sessionUser,
    }),
    signal: params.signal,
  });

  if (!res.ok || !res.body) {
    const errText = await res.text().catch(() => "(no body)");
    throw new Error(`OpenClaw ${res.status}: ${errText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      if (params.signal?.aborted) {
        await reader.cancel().catch(() => {});
        return;
      }
      // reader.read() 在 abort / body 提前 close 时可能抛 ERR_INVALID_STATE。
      // 包 try/catch 让 generator 静默退出，避免错误冒到 microtask 变 unhandled rejection。
      let chunk: Awaited<ReturnType<typeof reader.read>>;
      try {
        chunk = await reader.read();
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        if (!params.signal?.aborted) {
          console.warn(`[openclaw] reader.read aborted: ${msg}`);
        }
        return;
      }
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });

      let nlIdx: number;
      while ((nlIdx = buffer.indexOf("\n")) !== -1) {
        const line = buffer.slice(0, nlIdx).trim();
        buffer = buffer.slice(nlIdx + 1);
        if (!line.startsWith("data:")) continue;
        const data = line.slice(5).trim();
        if (data === "[DONE]") return;
        try {
          const parsed = JSON.parse(data) as OpenClawChunk;
          const choice = parsed.choices?.[0];
          if (!choice) continue;
          if (choice.delta?.content) yield { delta: choice.delta.content };
          if (choice.finish_reason) yield { finish: choice.finish_reason };
        } catch {
          // ignore malformed line
        }
      }
    }
  } finally {
    // 确保 generator 提前退出（break / return / throw）时 reader 也释放，避免 body 悬挂。
    await reader.cancel().catch(() => {});
  }
}

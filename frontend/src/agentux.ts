export type AgentUXVisibility = "user" | "developer";

type AgentUXEventBase = {
  id: string;
  runId: string;
  threadId: string;
  seq: number;
  ts: number;
  visibility: AgentUXVisibility;
  messageId?: string;
};

type AgentUXEventPayload = Record<string, any>;

type AgentUXEventPayloads = {
  "run.started": AgentUXEventPayload;
  "run.finished": AgentUXEventPayload;
  "run.error": AgentUXEventPayload;
  "run.awaiting_input": AgentUXEventPayload;
  "reasoning.status": AgentUXEventPayload;
  "text.started": AgentUXEventPayload;
  "text.delta": AgentUXEventPayload;
  "text.finished": AgentUXEventPayload;
  "media.started": AgentUXEventPayload;
  "media.ready": AgentUXEventPayload;
  "media.failed": AgentUXEventPayload;
  "artifact.created": AgentUXEventPayload;
  "artifact.delta": AgentUXEventPayload;
  "artifact.finished": AgentUXEventPayload;
  "state.patch": AgentUXEventPayload;
};

export type AgentUXEventType = keyof AgentUXEventPayloads;

export type AgentUXEvent<T extends AgentUXEventType = AgentUXEventType> = AgentUXEventBase & {
  [K in T]: {
    type: K;
    payload: AgentUXEventPayloads[K];
  };
}[T];

type EventMeta = AgentUXEventBase;

function event<T extends AgentUXEventType>(
  meta: EventMeta,
  type: T,
  payload: AgentUXEventPayloads[T],
): AgentUXEvent<T> {
  return {
    ...meta,
    type,
    payload,
  };
}

export const agentUXEventBuilders = {
  runStarted: (meta: EventMeta, payload: Record<string, any>) => event(meta, "run.started", payload),
  runFinished: (meta: EventMeta, payload: Record<string, any>) => event(meta, "run.finished", payload),
  runError: (meta: EventMeta, payload: Record<string, any>) => event(meta, "run.error", payload),
  runAwaitingInput: (meta: EventMeta, payload: Record<string, any>) => event(meta, "run.awaiting_input", payload),
  reasoningStatus: (meta: EventMeta, payload: Record<string, any>) => event(meta, "reasoning.status", payload),
  textStarted: (meta: EventMeta, payload: Record<string, any>) => event(meta, "text.started", payload),
  textDelta: (meta: EventMeta, payload: Record<string, any>) => event(meta, "text.delta", payload),
  textFinished: (meta: EventMeta, payload: Record<string, any>) => event(meta, "text.finished", payload),
  mediaStarted: (meta: EventMeta, payload: Record<string, any>) => event(meta, "media.started", payload),
  mediaReady: (meta: EventMeta, payload: Record<string, any>) => event(meta, "media.ready", payload),
  mediaFailed: (meta: EventMeta, payload: Record<string, any>) => event(meta, "media.failed", payload),
  artifactCreated: (meta: EventMeta, payload: Record<string, any>) => event(meta, "artifact.created", payload),
  artifactDelta: (meta: EventMeta, payload: Record<string, any>) => event(meta, "artifact.delta", payload),
  artifactFinished: (meta: EventMeta, payload: Record<string, any>) => event(meta, "artifact.finished", payload),
  statePatch: (meta: EventMeta, payload: Record<string, any>) => event(meta, "state.patch", payload),
};

export type AgentUXSSERecord =
  | {
      kind: "event";
      event: AgentUXEvent;
    }
  | {
      kind: "error";
      error: Error;
    };

export class AgentUXSSEDecoder {
  private buffer = "";

  decode(chunk?: string): AgentUXSSERecord[] {
    if (chunk) this.buffer += chunk;
    const records: AgentUXSSERecord[] = [];

    while (true) {
      const sepIdx = this.findBlockEnd(this.buffer);
      if (sepIdx < 0) break;
      const block = this.buffer.slice(0, sepIdx);
      this.buffer = this.buffer.slice(sepIdx + 2);
      this.parseBlock(block, records);
    }

    return records;
  }

  flush(): AgentUXSSERecord[] {
    const records: AgentUXSSERecord[] = [];
    if (this.buffer.trim().length > 0) {
      this.parseBlock(this.buffer, records);
      this.buffer = "";
    }
    return records;
  }

  private findBlockEnd(s: string): number {
    const i1 = s.indexOf("\n\n");
    const i2 = s.indexOf("\r\n\r\n");
    if (i1 < 0) return i2;
    if (i2 < 0) return i1;
    return Math.min(i1, i2);
  }

  private parseBlock(block: string, out: AgentUXSSERecord[]): void {
    let eventType = "message";
    const dataParts: string[] = [];
    for (const raw of block.split(/\r?\n/)) {
      if (!raw) continue;
      if (raw.startsWith(":")) continue;
      if (raw.startsWith("event:")) {
        eventType = raw.slice(6).trim();
      } else if (raw.startsWith("data:")) {
        dataParts.push(raw.slice(5).trimStart());
      }
    }
    if (eventType !== "agentux" || dataParts.length === 0) return;
    const data = dataParts.join("\n");
    try {
      const event = JSON.parse(data) as AgentUXEvent;
      out.push({ kind: "event", event });
    } catch (err) {
      out.push({ kind: "error", error: err instanceof Error ? err : new Error(String(err)) });
    }
  }
}

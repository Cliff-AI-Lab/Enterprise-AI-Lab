import type { AgentUXEvent } from "./agentux";

export function runStatusForRun(
  events: readonly AgentUXEvent[],
  runId: string | undefined,
): string {
  if (!runId) {
    return "idle";
  }

  const latestLifecycleEvent = events
    .filter((event) =>
      event.runId === runId
      && (event.type === "run.error"
        || event.type === "run.awaiting_input"
        || event.type === "run.finished"
        || event.type === "run.started"),
    )
    .sort((left, right) => left.seq - right.seq)
    .at(-1);

  if (latestLifecycleEvent?.type === "run.error") {
    return "error";
  }

  if (latestLifecycleEvent?.type === "run.awaiting_input") {
    return "awaiting_input";
  }

  if (latestLifecycleEvent?.type === "run.finished") {
    return "finished";
  }

  if (hasCompletedVisibleText(events, runId)) {
    return "finished";
  }

  return latestLifecycleEvent?.type === "run.started" ? "running" : "idle";
}

function hasCompletedVisibleText(events: readonly AgentUXEvent[], runId: string): boolean {
  const startedTextIds = new Set<string>();
  const finishedTextIds = new Set<string>();

  for (const event of events) {
    if (event.runId !== runId) {
      continue;
    }
    if (event.type === "text.started") {
      startedTextIds.add(event.payload.textId);
    }
    if (event.type === "text.finished") {
      finishedTextIds.add(event.payload.textId);
    }
  }

  return startedTextIds.size > 0 && [...startedTextIds].every((textId) => finishedTextIds.has(textId));
}

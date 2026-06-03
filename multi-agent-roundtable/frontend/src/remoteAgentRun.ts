// Path C: 后端 /api/rooms/:roomId/messages 只读 { prompt, runId }。
// 其余 agent / history / settings 由后端从 DB + OpenClaw 自取，不再跨边界传。

export type RemoteHistoryMessage = {
  sender: "human" | "agent" | "system";
  agentId?: string;
  body: string;
};

export type RemoteAgentRunMode = "direct" | "sequential" | "parallel" | "loop";

export type RemoteAgentRunPayload = {
  runId: string;
  prompt: string;
  mode?: RemoteAgentRunMode;
  agentId?: string;
  agentIds?: string[];
  memberIds?: string[];
};

export function buildRemoteAgentRunPayload({
  agentId,
  agentIds,
  memberIds,
  mode,
  runId,
  prompt,
}: {
  agentId?: string;
  agentIds?: string[];
  memberIds?: string[];
  mode?: RemoteAgentRunMode;
  runId: string;
  prompt: string;
}): RemoteAgentRunPayload {
  return { agentId, agentIds, memberIds, mode, runId, prompt };
}

export type RemoteRunTaskResumePayload = {
  responseText: string;
};

export function buildRemoteRunTaskResumePayload({
  responseText,
}: {
  responseText: string;
}): RemoteRunTaskResumePayload {
  return {
    responseText: responseText.trim() || "Continue.",
  };
}

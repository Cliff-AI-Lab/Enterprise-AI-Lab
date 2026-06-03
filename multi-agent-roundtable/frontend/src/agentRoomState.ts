export type AgentRunTrigger = "direct" | "mention" | "convene";

export type RoomIdentity = {
  id: string;
  kind: "room" | "agent" | "group";
  agentId?: string;
  memberIds?: string[];
  template?: boolean;
};

export type RoomRunIndex = Record<string, string[] | undefined>;

export type AgentRunTarget = {
  trigger: Extract<AgentRunTrigger, "direct" | "mention">;
  agentIds: string[];
};

export type MentionableAgent = {
  id: string;
  name: string;
};

export type ArtifactPointer = {
  id: string;
  roomId: string;
  sourceAgentId: string;
  updatedAt: number;
};

export function resolveAgentRunTarget(
  room: RoomIdentity,
  text: string,
  mentionableAgents: readonly MentionableAgent[],
): AgentRunTarget | undefined {
  // DM 房（kind === "agent"）任何 agentId 都走 direct。
  // 这里以前用 knownAgentIds 硬编码白名单，新 agent 加进来 UI silent fail。
  if (room.kind === "agent" && room.agentId) {
    return {
      trigger: "direct",
      agentIds: [room.agentId],
    };
  }

  const agentIds = filterMentionedAgentIdsForRoom(detectMentionedAgentIds(text, mentionableAgents), room);
  if (agentIds.length > 0) {
    return { trigger: "mention", agentIds };
  }

  const memberIds = room.memberIds ?? [];
  const knownAgentIds = new Set(mentionableAgents.map((agent) => agent.id));
  const roomAgentIds = memberIds.filter((agentId) => knownAgentIds.has(agentId));
  return roomAgentIds.length > 0 ? { trigger: "mention", agentIds: roomAgentIds } : undefined;
}

export function detectMentionedAgentIds(text: string, mentionableAgents: readonly MentionableAgent[]): string[] {
  const knownAgentNameToId = new Map<string, string>();
  for (const agent of mentionableAgents) {
    knownAgentNameToId.set(agent.id.toLowerCase(), agent.id);
    knownAgentNameToId.set(agent.name.toLowerCase(), agent.id);
  }

  const mentions = new Set<string>();
  for (const match of text.matchAll(/@([^\s@,.;:!?，。！？、]+)/g)) {
    const mention = match[1];
    if (!mention) continue;
    const agentId = knownAgentNameToId.get(mention.toLowerCase());
    if (agentId) {
      mentions.add(agentId);
    }
  }

  return [...mentions];
}

function filterMentionedAgentIdsForRoom(agentIds: string[], room: RoomIdentity): string[] {
  if (room.kind === "agent" || !room.memberIds) {
    return agentIds;
  }

  const roomMemberIds = new Set(room.memberIds);
  if (roomMemberIds.size === 0 && room.template) {
    return agentIds;
  }
  return agentIds.filter((agentId) => roomMemberIds.has(agentId));
}

export function chooseConveneAgentIds(
  turn: number,
  roomMemberIds: readonly string[],
  routingPool: readonly string[],
): string[] {
  const roomMemberIdSet = new Set(roomMemberIds);
  const candidates = [...new Set(routingPool)].filter((agentId) => roomMemberIdSet.has(agentId));
  if (candidates.length === 0) {
    return [];
  }

  const count = Math.min(turn % 2 === 0 ? 2 : 1, candidates.length);
  const start = turn % candidates.length;
  return Array.from({ length: count }, (_item, index) => candidates[(start + index) % candidates.length]);
}

export function assignRoomRun(index: RoomRunIndex, roomId: string, runId: string): RoomRunIndex {
  const currentRunIds = index[roomId] ?? [];
  if (currentRunIds.includes(runId)) {
    return index;
  }

  return {
    ...index,
    [roomId]: [...currentRunIds, runId],
  };
}

export function runIdForRoom(index: RoomRunIndex, roomId: string): string | undefined {
  return index[roomId]?.at(-1);
}

export function runIdsForRoom(index: RoomRunIndex, roomId: string): string[] {
  return index[roomId] ?? [];
}

export function artifactsForAgentRoom<T extends ArtifactPointer>(room: RoomIdentity, artifacts: readonly T[]): T[] {
  if (room.kind !== "agent" || !room.agentId) {
    return [...artifacts].filter((artifact) => artifact.roomId === room.id).sort(sortNewestFirst);
  }

  return [...artifacts]
    .filter((artifact) => artifact.roomId === room.id && artifact.sourceAgentId === room.agentId)
    .sort(sortNewestFirst);
}

function sortNewestFirst(left: ArtifactPointer, right: ArtifactPointer): number {
  return right.updatedAt - left.updatedAt;
}

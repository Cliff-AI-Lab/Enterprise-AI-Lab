export type MentionRoom = {
  id?: string;
  kind: "room" | "agent" | "group";
  agentId?: string;
  memberIds: string[];
};

export function mentionCandidateIdsForRoom(room: MentionRoom, fallbackAgentIds: readonly string[]): string[] {
  const candidateIds = room.kind === "agent" && room.agentId ? [room.agentId] : room.memberIds;
  const knownAgentIds = new Set(fallbackAgentIds);
  const uniqueCandidateIds = [...new Set(candidateIds)].filter((agentId) => knownAgentIds.has(agentId));
  return uniqueCandidateIds.length > 0 ? uniqueCandidateIds : [...fallbackAgentIds];
}

export function draftWithMentionMarker(draft: string): string {
  return draft.length === 0 || draft.endsWith(" ") ? `${draft}@` : `${draft} @`;
}

export function draftWithSelectedMention(draft: string, agentName: string): string {
  const mention = `@${agentName} `;
  if (/@[^\s@]*$/.test(draft)) {
    return draft.replace(/@[^\s@]*$/, mention);
  }
  return draft.length === 0 || draft.endsWith(" ") ? `${draft}${mention}` : `${draft} ${mention}`;
}

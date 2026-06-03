import type { AgentUXEvent } from "./agentux";

export type MemoryApprovalStorage = Pick<Storage, "getItem" | "setItem">;
export type MemoryProposalCategory = "facts" | "preferences" | "decisions" | "rejected";
export type MemoryProposalStatus = "pending" | "approved" | "rejected";

export type MemoryProposalRecord = {
  id: string;
  runId: string;
  eventId: string;
  agentId: string;
  roomId: string;
  sourceAgent?: string;
  sourceAgentId?: string;
  category: MemoryProposalCategory;
  text: string;
  evidence?: string;
  confidence: number;
  reason?: string;
  status: MemoryProposalStatus;
  createdAt: number;
  decidedAt?: number;
};

export type VersionedMemoryValue = {
  summary: string;
  revision: number;
  updatedAt: number;
};

export type MemoryApprovalState = {
  version: 1;
  proposals: Record<string, MemoryProposalRecord>;
  agentMemoryById: Record<string, VersionedMemoryValue>;
  roomMemoryById: Record<string, VersionedMemoryValue>;
};

type MemoryProposalItem = {
  text: string;
  evidence?: string;
  confidence?: number;
  reason?: string;
};

export const memoryApprovalStorageKey = "agentelegram_memory_approvals";

export function emptyMemoryApprovalState(): MemoryApprovalState {
  return {
    version: 1,
    proposals: {},
    agentMemoryById: {},
    roomMemoryById: {},
  };
}

export function readMemoryApprovalState(
  storage: MemoryApprovalStorage | undefined = browserStorage(),
): MemoryApprovalState {
  if (!storage) {
    return emptyMemoryApprovalState();
  }

  const raw = storage.getItem(memoryApprovalStorageKey);
  if (!raw) {
    return emptyMemoryApprovalState();
  }

  try {
    return normalizeMemoryApprovalState(JSON.parse(raw));
  } catch {
    return emptyMemoryApprovalState();
  }
}

export function writeMemoryApprovalState(
  storage: MemoryApprovalStorage | undefined = browserStorage(),
  state: MemoryApprovalState,
): MemoryApprovalState {
  const normalized = normalizeMemoryApprovalState(state);
  storage?.setItem(memoryApprovalStorageKey, JSON.stringify(normalized));
  return normalized;
}

export function captureMemoryProposalEvent(
  state: MemoryApprovalState,
  event: AgentUXEvent,
): MemoryApprovalState {
  const records = memoryProposalRecordsFromEvent(event);
  if (records.length === 0) {
    return state;
  }

  const proposals = { ...state.proposals };
  let changed = false;
  for (const record of records) {
    if (!proposals[record.id]) {
      proposals[record.id] = record;
      changed = true;
    }
  }

  return changed ? { ...state, proposals } : state;
}

export function approveMemoryProposal(
  state: MemoryApprovalState,
  proposalId: string,
  now: number = Date.now(),
): MemoryApprovalState {
  const proposal = state.proposals[proposalId];
  if (!proposal || proposal.status !== "pending") {
    return state;
  }

  const approvedProposal: MemoryProposalRecord = {
    ...proposal,
    status: "approved",
    decidedAt: now,
  };
  const proposals = { ...state.proposals, [proposalId]: approvedProposal };
  const line = memoryLineForProposal(proposal);

  if (proposal.category === "preferences") {
    return {
      ...state,
      proposals,
      agentMemoryById: {
        ...state.agentMemoryById,
        [proposal.agentId]: appendVersionedMemory(state.agentMemoryById[proposal.agentId], line, now),
      },
    };
  }

  return {
    ...state,
    proposals,
    roomMemoryById: {
      ...state.roomMemoryById,
      [proposal.roomId]: appendVersionedMemory(state.roomMemoryById[proposal.roomId], line, now),
    },
  };
}

export function rejectMemoryProposal(
  state: MemoryApprovalState,
  proposalId: string,
  now: number = Date.now(),
): MemoryApprovalState {
  const proposal = state.proposals[proposalId];
  if (!proposal || proposal.status !== "pending") {
    return state;
  }

  return {
    ...state,
    proposals: {
      ...state.proposals,
      [proposalId]: {
        ...proposal,
        status: "rejected",
        decidedAt: now,
      },
    },
  };
}

export function pendingMemoryProposalsForRoom(
  state: MemoryApprovalState,
  roomId: string,
  agentId?: string,
): MemoryProposalRecord[] {
  return Object.values(state.proposals)
    .filter(
      (proposal) =>
        proposal.status === "pending" &&
        proposal.roomId === roomId &&
        (!agentId || proposal.agentId === agentId),
    )
    .sort((left, right) => right.confidence - left.confidence || right.createdAt - left.createdAt)
    .slice(0, 3);
}

export function applyApprovedAgentMemory<T extends { id: string; privateMemorySummary?: string }>(
  agents: readonly T[],
  state: MemoryApprovalState,
): Array<T & { privateMemorySummary?: string }> {
  return agents.map((agent) => {
    const memory = state.agentMemoryById[agent.id]?.summary;
    return memory ? { ...agent, privateMemorySummary: mergeMemoryText(agent.privateMemorySummary, memory) } : agent;
  });
}

export function applyApprovedRoomMemory<T extends { id: string; summary?: string }>(
  rooms: readonly T[],
  state: MemoryApprovalState,
): Array<T & { summary?: string }> {
  return rooms.map((room) => {
    const memory = state.roomMemoryById[room.id]?.summary;
    return memory ? { ...room, summary: mergeMemoryText(room.summary, memory) } : room;
  });
}

function memoryProposalRecordsFromEvent(event: AgentUXEvent): MemoryProposalRecord[] {
  if (event.type !== "state.patch" || event.visibility !== "developer") {
    return [];
  }

  const metadata = isRecord(event.payload.metadata) ? event.payload.metadata : {};
  if (metadata.kind !== "memory_proposal") {
    return [];
  }

  const patch = isRecord(event.payload.patch) ? event.payload.patch : undefined;
  const target = isRecord(patch?.target) ? patch.target : undefined;
  const proposal = isRecord(patch?.proposal) ? patch.proposal : undefined;
  if (patch?.type !== "memory_proposal" || !target || !proposal) {
    return [];
  }

  const agentId = stringValue(target.agentId) ?? stringValue(metadata.agentId);
  const roomId = stringValue(target.roomId) ?? stringValue(metadata.roomId);
  if (!agentId || !roomId) {
    return [];
  }

  return (["facts", "preferences", "decisions"] as MemoryProposalCategory[]).flatMap((category) => {
    const items = Array.isArray(proposal[category]) ? proposal[category] : [];
    return items.flatMap((item, index): MemoryProposalRecord[] => {
      const normalized = memoryProposalItemValue(item);
      if (!normalized) {
        return [];
      }

      return [
        {
          id: `${event.id}:${category}:${index}`,
          runId: event.runId,
          eventId: event.id,
          agentId,
          roomId,
          sourceAgent: stringValue(metadata.sourceAgent),
          sourceAgentId: stringValue(metadata.sourceAgentId),
          category,
          text: normalized.text,
          evidence: normalized.evidence,
          confidence: normalized.confidence ?? 0,
          reason: normalized.reason,
          status: "pending",
          createdAt: event.ts,
        },
      ];
    });
  });
}

function normalizeMemoryApprovalState(value: unknown): MemoryApprovalState {
  if (!isRecord(value) || value.version !== 1) {
    return emptyMemoryApprovalState();
  }

  return {
    version: 1,
    proposals: normalizeProposalRecords(value.proposals),
    agentMemoryById: normalizeVersionedMemoryById(value.agentMemoryById),
    roomMemoryById: normalizeVersionedMemoryById(value.roomMemoryById),
  };
}

function normalizeProposalRecords(value: unknown): Record<string, MemoryProposalRecord> {
  if (!isRecord(value)) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(value).flatMap(([proposalId, candidate]) => {
      if (!isRecord(candidate)) {
        return [];
      }

      const record = proposalRecordValue(proposalId, candidate);
      return record ? [[record.id, record]] : [];
    }),
  );
}

function proposalRecordValue(id: string, value: Record<string, unknown>): MemoryProposalRecord | undefined {
  const runId = stringValue(value.runId);
  const eventId = stringValue(value.eventId);
  const agentId = stringValue(value.agentId);
  const roomId = stringValue(value.roomId);
  const category = proposalCategoryValue(value.category);
  const text = stringValue(value.text);
  const status = proposalStatusValue(value.status);
  const createdAt = numberValue(value.createdAt);
  if (!runId || !eventId || !agentId || !roomId || !category || !text || !status || createdAt === undefined) {
    return undefined;
  }

  return {
    id,
    runId,
    eventId,
    agentId,
    roomId,
    sourceAgent: stringValue(value.sourceAgent),
    sourceAgentId: stringValue(value.sourceAgentId),
    category,
    text,
    evidence: stringValue(value.evidence),
    confidence: numberValue(value.confidence) ?? 0,
    reason: stringValue(value.reason),
    status,
    createdAt,
    decidedAt: numberValue(value.decidedAt),
  };
}

function normalizeVersionedMemoryById(value: unknown): Record<string, VersionedMemoryValue> {
  if (!isRecord(value)) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(value).flatMap(([id, candidate]) => {
      if (!isRecord(candidate)) {
        return [];
      }

      const summary = stringValue(candidate.summary);
      const revision = numberValue(candidate.revision);
      const updatedAt = numberValue(candidate.updatedAt);
      return summary && revision !== undefined && updatedAt !== undefined
        ? [[id, { summary, revision, updatedAt }]]
        : [];
    }),
  );
}

function memoryProposalItemValue(value: unknown): MemoryProposalItem | undefined {
  if (!isRecord(value)) {
    return undefined;
  }

  const text = stringValue(value.text);
  if (!text) {
    return undefined;
  }

  return {
    text,
    evidence: stringValue(value.evidence),
    confidence: numberValue(value.confidence),
    reason: stringValue(value.reason),
  };
}

function appendVersionedMemory(
  current: VersionedMemoryValue | undefined,
  line: string,
  now: number,
): VersionedMemoryValue {
  const summary = appendUniqueLine(current?.summary, line);
  return {
    summary,
    revision: (current?.revision ?? 0) + (summary === current?.summary ? 0 : 1),
    updatedAt: now,
  };
}

function appendUniqueLine(current: string | undefined, line: string): string {
  const existing = current?.trim();
  if (!existing) {
    return line;
  }
  return existing.split("\n").includes(line) ? existing : `${existing}\n${line}`;
}

function mergeMemoryText(base: string | undefined, approved: string): string {
  return [base?.trim(), approved.trim()].filter(Boolean).join("\n");
}

function memoryLineForProposal(proposal: MemoryProposalRecord): string {
  return `- ${proposalCategoryLabel(proposal.category)}: ${proposal.text}`;
}

function proposalCategoryLabel(category: MemoryProposalCategory): string {
  return {
    facts: "Fact",
    preferences: "Preference",
    decisions: "Decision",
    rejected: "Rejected",
  }[category];
}

function proposalCategoryValue(value: unknown): MemoryProposalCategory | undefined {
  return value === "facts" || value === "preferences" || value === "decisions" || value === "rejected"
    ? value
    : undefined;
}

function proposalStatusValue(value: unknown): MemoryProposalStatus | undefined {
  return value === "pending" || value === "approved" || value === "rejected" ? value : undefined;
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : undefined;
}

function numberValue(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function browserStorage(): MemoryApprovalStorage | undefined {
  return typeof window === "undefined" ? undefined : window.localStorage;
}

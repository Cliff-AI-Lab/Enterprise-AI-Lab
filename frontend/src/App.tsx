import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, KeyboardEvent, MutableRefObject, ReactNode } from "react";
import { createPortal } from "react-dom";
import {
  Archive,
  AtSign,
  Bell,
  Bot,
  Camera,
  Check,
  ChevronDown,
  CircleDot,
  Copy,
  FileCode2,
  FileText,
  Hash,
  ImageOff,
  Loader2,
  Menu,
  MessageCircle,
  Mic,
  MoreHorizontal,
  Music2,
  Paperclip,
  Pencil,
  Pin,
  Plus,
  RefreshCw,
  Search,
  Send,
  Settings,
  Smile,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { AgentUXSSEDecoder, agentUXEventBuilders, type AgentUXEvent } from "./agentux";
import { AudioPlayer } from "./AudioPlayer";
import {
  artifactsForAgentRoom,
  assignRoomRun,
  chooseConveneAgentIds,
  resolveAgentRunTarget,
  runIdForRoom,
  runIdsForRoom,
  type AgentRunTrigger,
  type RoomRunIndex,
} from "./agentRoomState";
import {
  getActiveProviderRuntime,
  readAgentRunSettings,
  switchAgentRunProvider,
  updateProviderRuntimeSettings,
  writeAgentRunSettings,
  type AgentRunProvider,
  type AgentRunSettings,
} from "./agentSettings";
import { activityCueTextForExpression, pickAgentExpression, type AgentExpression } from "./agentExpressions";
import {
  MODEL_PROVIDERS,
  filterProviderModels,
  getProviderConfig,
  mergeProviderModels,
  type ModelOption,
} from "./modelProviders";
import {
  canTestProviderSettings,
  fetchProviderModelOptions,
  providerRuntimeSignature,
  providerUsesServerApiKey,
  testProviderSettings,
} from "./providerRequests";
import {
  buildRemoteAgentRunPayload,
  buildRemoteRunTaskResumePayload,
  type RemoteAgentRunMode,
} from "./remoteAgentRun";
import { agentRunDisplayState } from "./agentRunDisplay";
import { agentSoulTemplates, buildAgentSoulMarkdown, type AgentSoul } from "./agentSouls";
import { runStatusForRun } from "./agentRunLifecycle";
import { clearComposerDraftAfterSend, initialComposerDraft } from "./composerDraft";
import { draftWithMentionMarker, draftWithSelectedMention, mentionCandidateIdsForRoom } from "./composerMention";
import { contextPanelFocusSections, shouldExposeContextPanel } from "./contextPanelFocus";
import { MarkdownText, type MarkdownImage } from "./markdownText";
import {
  AGENT_SKILLS,
  WORKSPACE_PROVIDER_MODEL_ID,
  applyAgentConfigOverrides,
  defaultAgentPermissions,
  permissionLabels,
  permissionModes,
  providerProfileOptions,
  readAgentConfigOverrides,
  skillPolicyOptions,
  writeAgentConfigOverrides,
  type AgentConfigOverridesById,
  type AgentPermissionKey,
  type AgentPermissionSet,
  type AgentSkillPolicy,
} from "./agentConfigs";
import {
  applyApprovedAgentMemory,
  applyApprovedRoomMemory,
  approveMemoryProposal,
  captureMemoryProposalEvent,
  pendingMemoryProposalsForRoom,
  readMemoryApprovalState,
  rejectMemoryProposal,
  writeMemoryApprovalState,
  type MemoryProposalRecord,
} from "./memoryApprovals";
import {
  APP_THEMES,
  getAppTheme,
  readAppThemeId,
  writeAppThemeId,
  type AppTheme,
  type AppThemeId,
} from "./appTheme";

type Mode = "chat" | "convene" | "review";
type AgentStatus = "observing" | "thinking" | "working" | "idle" | "done";

type AgentPresence = "online" | "idle" | "offline";

type Agent = {
  id: string;
  name: string;
  role: string;
  profile: string;
  soul: AgentSoul;
  soulMarkdown?: string;
  privateMemorySummary?: string;
  capabilities: string[];
  // 从 personas/<id>/IDENTITY.md `- bestFor: ...` 解析；用作 Contacts tagline + profile BEST FOR 区。
  bestFor: string[];
  enabledSkillIds: string[];
  skillPolicy: AgentSkillPolicy;
  permissions: AgentPermissionSet;
  providerProfile?: string;
  color: string;
  initials: string;
  status: AgentStatus;
  model: string;
  emoji?: string;
  presence?: AgentPresence;
  avatarUrl?: string;
};

type AgentLookup = ReadonlyMap<string, Agent>;

type Room = {
  id: string;
  title: string;
  goal: string;
  summary?: string;
  lastMessage: string;
  lastActivityAt?: number;
  time: string;
  unread?: number;
  pinned?: boolean;
  template?: boolean;
  runMode?: Exclude<RemoteAgentRunMode, "direct">;
  kind: "room" | "agent" | "group";
  agentId?: string;
  memberIds: string[];
};

type TemplateRoom = Room & {
  template: true;
  runMode: Exclude<RemoteAgentRunMode, "direct">;
};

type ChatMessage = {
  id: string;
  sender: "human" | "agent" | "system";
  agentId?: string;
  author: string;
  time: string;
  body: string;
  createdAt?: number;
  mediaPaths?: string[];
  compact?: boolean;
};

type ArtifactRecord = {
  id: string;
  roomId: string;
  title: string;
  kind: string;
  sourceAgentId: string;
  source: string;
  version: string;
  status: string;
  content: string;
  origin: "seed" | "agentux";
  updatedAt: number;
};

type TimedAgentUXEvent = {
  event: AgentUXEvent;
  delay: number;
};

type FakeRunScript = {
  runId: string;
  roomId: string;
  title: string;
  trigger: AgentRunTrigger;
  agentIds: string[];
  events: TimedAgentUXEvent[];
};

type RunDescriptor = Pick<FakeRunScript, "runId" | "roomId" | "title" | "trigger" | "agentIds"> & {
  startedAt: number;
  anchorMessageId: string;
};

type TimelineRunMessage = {
  id: string;
  runId: string;
  agentId: string;
  text: string;
  media: TimelineRunMedia[];
  streaming: boolean;
  status: string;
  expression: AgentExpression;
};

type TimelineRunMedia = {
  idx: number;
  alt: string;
  status: "started" | "ready" | "failed";
  kind: "image" | "audio";
  mediaUrl?: string;
  reason?: string;
};

type ImagePreview = MarkdownImage;

type AgentProfileAnchor = {
  agentId: string;
  top: number;
  left: number;
};

type OpenAgentProfile = (agentId: string, anchor: HTMLElement) => void;

export const defaultWorkspaceAgents: Agent[] = [
  {
    id: "main",
    name: "Main",
    role: "Orchestrator",
    profile: "Hidden router. Sees every room, decides who answers, never speaks unless asked directly.",
    soul: agentSoulTemplates.main,
    capabilities: ["Routing", "Scope guard", "Decision capture"],
    bestFor: [],
    enabledSkillIds: ["project-scope"],
    skillPolicy: "ask_first",
    permissions: defaultAgentPermissions,
    color: "#42a5f5",
    initials: "M",
    status: "observing",
    model: "ruidong-std",
  },
  {
    id: "kai",
    name: "Kai",
    role: "Engineer",
    profile: "工程实用主义。Root cause first，最小可工作的改动，不堆抽象。",
    soul: agentSoulTemplates.kai,
    capabilities: ["Implementation", "Debugging", "Code review"],
    bestFor: [],
    enabledSkillIds: ["code-patch", "test-triage"],
    skillPolicy: "ask_first",
    permissions: { ...defaultAgentPermissions, codeEdit: "allow", fileRead: "allow", fileWrite: "ask", shell: "ask" },
    color: "#7c5cff",
    initials: "K",
    status: "observing",
    model: "ruidong-plus",
  },
  {
    id: "sarah",
    name: "Sarah",
    role: "Copywriter",
    profile: "冷静、节制、爱砍掉废话。先给判断维度再给版本，不写空话。",
    soul: agentSoulTemplates.sarah,
    capabilities: ["Copy", "Naming", "Microcopy"],
    bestFor: [],
    enabledSkillIds: ["copy-review"],
    skillPolicy: "ask_first",
    permissions: { ...defaultAgentPermissions, webAccess: "allow", fileRead: "ask", fileWrite: "off", shell: "off" },
    color: "#17b890",
    initials: "S",
    status: "observing",
    model: "ruidong-std",
  },
  {
    id: "alex",
    name: "Alex",
    role: "Product Manager",
    profile: "量化思维。Framework-first（RICE/MoSCoW）。反对功能堆叠。",
    soul: agentSoulTemplates.alex,
    capabilities: ["PRD", "Prioritization", "Decision memo"],
    bestFor: [],
    enabledSkillIds: ["prd-skeleton", "prioritize"],
    skillPolicy: "ask_first",
    permissions: { ...defaultAgentPermissions, webAccess: "off", fileWrite: "off", shell: "off", codeEdit: "off" },
    color: "#ff8a65",
    initials: "A",
    status: "observing",
    model: "ruidong-std",
  },
];

const agents = defaultWorkspaceAgents;
const agentById = new Map(agents.map((agent) => [agent.id, agent]));

const rooms: Room[] = [
  {
    id: "relay",
    title: "接龙房",
    goal: "一个干完下一个干（写 → 审 → 改）",
    summary: "Sequential。链上每个 agent 接上一个的产出继续往前推。例：sarah 写初稿 → alex 审优先级 → kai 落实现。链上最后一位负责对外回话。",
    lastMessage: "等待你发起任务。",
    time: "—",
    pinned: true,
    kind: "room",
    memberIds: ["sarah", "alex", "kai"],
  },
  {
    id: "brainstorm",
    title: "头脑风暴房",
    goal: "同时上，各自独立给观点",
    summary: "Parallel。多 agent 同时给意见，互不看彼此输出；MVP 先不做 Merger 合并。",
    lastMessage: "等待你抛出一个题目。",
    time: "—",
    kind: "room",
    memberIds: ["sarah", "alex", "kai"],
  },
  {
    id: "polish",
    title: "打磨房",
    goal: "反复改到达标（producer + critic loop）",
    summary: "Loop。第一位成员做 producer，第二位做 critic；critic 给 verdict，必要时 producer 再改一轮。",
    lastMessage: "等待你发起打磨任务。",
    time: "—",
    kind: "room",
    memberIds: ["sarah", "alex"],
  },
  {
    id: "template-relay",
    title: "接力工作",
    goal: "一个干完下一个干（写 → 审 → 改）",
    summary: "适合有明确上下游依赖的任务：前一个 Agent 的输出，会成为下一个 Agent 的输入。",
    lastMessage: "空模板 · 接龙流程",
    time: "—",
    kind: "room",
    memberIds: [],
    template: true,
    runMode: "sequential",
  },
  {
    id: "template-brainstorm",
    title: "并行探索",
    goal: "同时上，各自独立给观点",
    summary: "适合互不依赖的任务：多个 Agent 同时从不同角度探索，最后回到同一个群聊里汇总判断。",
    lastMessage: "空模板 · 并行流程",
    time: "—",
    kind: "room",
    memberIds: [],
    template: true,
    runMode: "parallel",
  },
  {
    id: "template-polish",
    title: "迭代打磨",
    goal: "反复改到达标（producer + critic loop）",
    summary: "适合需要反复改进的任务：一个 Agent 产出，另一个 Agent 评审，不达标就继续修改。",
    lastMessage: "空模板 · 循环流程",
    time: "—",
    kind: "room",
    memberIds: [],
    template: true,
    runMode: "loop",
  },
  {
    id: "sarah",
    title: "Sarah",
    goal: "Direct copywriter chat",
    lastMessage: "Send here when you want copy reviewed or rewritten.",
    time: "Mon",
    kind: "agent",
    agentId: "sarah",
    memberIds: ["sarah"],
  },
  {
    id: "alex",
    title: "Alex",
    goal: "Direct PM chat",
    lastMessage: "Send here when you want prioritization or a PRD skeleton.",
    time: "Mon",
    kind: "agent",
    agentId: "alex",
    memberIds: ["alex"],
  },
  {
    id: "kai",
    title: "Kai",
    goal: "Direct engineer chat",
    summary: "Direct Kai room summary: implementation-focused chats; root cause first.",
    lastMessage: "Send here when you want a scoped implementation ask.",
    time: "Mon",
    kind: "agent",
    agentId: "kai",
    memberIds: ["kai"],
  },
  {
    id: "maruko",
    title: "小丸子",
    goal: "Direct chat with maruko",
    summary: "二次元高二女生；闲聊 / 看番 / 吐槽。工作类话题她会 punt 给 sarah/alex/kai。",
    lastMessage: "聊点轻松的——番剧 / 吐槽 / 周末干嘛都行。",
    time: "—",
    kind: "agent",
    agentId: "maruko",
    memberIds: ["maruko"],
  },
];

const roomIconById: Partial<Record<string, string>> = {
  relay: "/room-icons/relay.svg",
  brainstorm: "/room-icons/brainstorm.svg",
  polish: "/room-icons/polish.svg",
  "template-relay": "/room-icons/relay.svg",
  "template-brainstorm": "/room-icons/brainstorm.svg",
  "template-polish": "/room-icons/polish.svg",
};

// Contacts/Agents 视图副标题：role 简称 · bestFor 关键词。
// 数据源：personas/<id>/IDENTITY.md `- bestFor: ...` → backend agent_profiles.best_for → API。
// "产品文案 / Copywriter" 这种 "中文 / English" 格式 role 只取中文段，避免 tagline 过长。
function shortRole(role: string): string {
  const head = role.split("/")[0]?.trim() ?? role;
  return head.length > 0 ? head : role;
}

function buildContactTagline(role: string, bestFor: readonly string[]): string {
  const cleanRole = shortRole(role);
  const items = bestFor.slice(0, 4);
  if (items.length === 0) return cleanRole;
  return `${cleanRole} · ${items.join(" / ")}`;
}

const seedMessagesByRoom: Record<string, ChatMessage[]> = {
  launch: [
    {
      id: "launch-m1",
      sender: "human",
      author: "Ricky",
      time: "10:31",
      body: "We need the first screen to feel like Telegram Desktop, but the room has to show contacts, current work, and saved notes.",
    },
    {
      id: "launch-m2",
      sender: "agent",
      agentId: "main",
      author: "Main",
      time: "10:33",
      body: "I will keep this room governed: one visible owner by default, explicit Convene for bounded team passes, and durable notes for decisions that should not vanish into chat history.",
    },
    {
      id: "launch-m3",
      sender: "system",
      author: "Room update",
      time: "10:35",
      body: "Room theme set: Main hosts, Kai implements, Sarah verifies; Alex is not in this room unless the design review room is opened.",
      compact: true,
    },
  ],
  design: [
    {
      id: "design-m1",
      sender: "agent",
      agentId: "alex",
      author: "Alex",
      time: "09:58",
      body: "This room should be used when the UI needs critique, not as the default build lane. Keep density, selected states, and room-member clarity under review.",
    },
  ],
  research: [
    {
      id: "research-m1",
      sender: "agent",
      agentId: "sarah",
      author: "Sarah",
      time: "Yesterday",
      body: "I will keep references, assumptions, and verification notes separate from room decisions so Main can route from evidence instead of memory.",
    },
  ],
  main: [
    {
      id: "main-m1",
      sender: "agent",
      agentId: "main",
      author: "Main",
      time: "Mon",
      body: "Send a message here and I will reply in this thread.",
    },
  ],
  kai: [
    {
      id: "kai-m1",
      sender: "agent",
      agentId: "kai",
      author: "Kai",
      time: "Mon",
      body: "Send me a scoped implementation ask here and I will keep the answer close to the code.",
    },
  ],
  sarah: [
    {
      id: "sarah-m1",
      sender: "agent",
      agentId: "sarah",
      author: "Sarah",
      time: "Mon",
      body: "Send here when the room needs assumptions, references, or verification notes.",
    },
  ],
  alex: [
    {
      id: "alex-m1",
      sender: "agent",
      agentId: "alex",
      author: "Alex",
      time: "Mon",
      body: "Send here when you want density, spacing, or saved-note readability reviewed.",
    },
  ],
};

const staticArtifacts: ArtifactRecord[] = [
  {
    id: "seed-brief",
    roomId: "launch",
    title: "Room operating contract",
    kind: "Decision log",
    sourceAgentId: "main",
    source: "Main",
    version: "v1",
    status: "selected",
    content: "Default to one visible owner. Use Convene only for brainstorming, review, debugging, or high-uncertainty decisions. Keep long work in notes or artifacts.",
    origin: "seed",
    updatedAt: 1,
  },
  {
    id: "seed-ui-direction",
    roomId: "launch",
    title: "UI direction notes",
    kind: "Design direction",
    sourceAgentId: "alex",
    source: "Alex",
    version: "v1",
    status: "draft",
    content: "Soft blue-white surfaces, compact rows, rounded Telegram-like bubbles. Alex belongs in Interface review, not the default Workspace control room.",
    origin: "seed",
    updatedAt: 2,
  },
  {
    id: "seed-design-density",
    roomId: "design",
    title: "Density review",
    kind: "Review",
    sourceAgentId: "alex",
    source: "Alex",
    version: "v1",
    status: "draft",
    content: "Keep room rows scan-first; avoid a marketing-style first screen.",
    origin: "seed",
    updatedAt: 1,
  },
  {
    id: "seed-research-patterns",
    roomId: "research",
    title: "Reference patterns",
    kind: "Research",
    sourceAgentId: "sarah",
    source: "Sarah",
    version: "v1",
    status: "selected",
    content: "Pinned context and stable right-side details reduce room-history hunting.",
    origin: "seed",
    updatedAt: 1,
  },
];

const remoteRunTaskEndpoint = "";
const providerTestEndpoint = "";
const providerModelsEndpoint = "";

export function App() {
  const [activeRoomId, setActiveRoomId] = useState("sarah");
  const [messagesByRoom, setMessagesByRoom] = useState<Record<string, ChatMessage[]>>(() =>
    Object.fromEntries(rooms.map((room) => [room.id, seedMessagesByRoom[room.id] ?? []])),
  );
  const [draft, setDraft] = useState(initialComposerDraft);
  const [mode, setMode] = useState<Mode>("chat");
  const [visibleEvents, setVisibleEvents] = useState<AgentUXEvent[]>([]);
  const [runIdsByRoom, setRunIdsByRoom] = useState<RoomRunIndex>({});
  const [runRegistry, setRunRegistry] = useState<Record<string, RunDescriptor>>({});
  const [selectedArtifactId, setSelectedArtifactId] = useState<string>();
  const [agentRunSettings, setAgentRunSettings] = useState<AgentRunSettings>(() => readAgentRunSettings());
  const [appThemeId, setAppThemeId] = useState<AppThemeId>(() => readAppThemeId());
  const [agentConfigOverrides, setAgentConfigOverrides] = useState<AgentConfigOverridesById>(() =>
    readAgentConfigOverrides(),
  );
  const [memoryApprovalState, setMemoryApprovalState] = useState(() => readMemoryApprovalState());
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [contextPanelOpen, setContextPanelOpen] = useState(false);
  const [agentProfileAnchor, setAgentProfileAnchor] = useState<AgentProfileAnchor>();
  const [copiedSoulAgentId, setCopiedSoulAgentId] = useState<string>();
  const [serverAgents, setServerAgents] = useState<ServerAgentPayload[] | null>(null);
  const [imagePreview, setImagePreview] = useState<ImagePreview>();
  const [view, setView] = useState<WorkspaceView>("chats");
  const [momentsInitialFilter, setMomentsInitialFilter] = useState<string | undefined>();
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>();
  const [createdRooms, setCreatedRooms] = useState<Room[]>([]);
  const [serverRooms, setServerRooms] = useState<ServerRoomPayload[] | null>(null);
  const [roomMemberOverrides, setRoomMemberOverrides] = useState<Record<string, string[]>>({});
  const runIndexRef = useRef(1);
  const conveneTurnRef = useRef(0);
  const timersRef = useRef<number[]>([]);
  const chatScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    const refresh = () => {
      fetch("/api/agents")
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
        .then((data: { agents: ServerAgentPayload[] }) => {
          if (!cancelled) setServerAgents(data.agents);
        })
        .catch((err) => console.warn("[fetch agents]", err));
    };
    refresh();
    const t = window.setInterval(refresh, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/rooms")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data: { rooms: ServerRoomPayload[] }) => {
        if (!cancelled) setServerRooms(data.rooms);
      })
      .catch((err) => console.warn("[fetch rooms]", err));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/rooms/${activeRoomId}/messages`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data: { messages: ServerMessagePayload[] }) => {
        if (cancelled) return;
        const converted = data.messages.map((s) => serverMessageToChatMessage(s));
        setMessagesByRoom((current) => ({ ...current, [activeRoomId]: converted }));
        // 不要在这里清 visibleEvents / runRegistry / runIdsByRoom——切窗口属于 UI 行为，
        // 不该 nuke 其他房间还在跑的 SSE run。这三个 state 都按 runId/roomId 索引，
        // 渲染时自然按 activeRoom 过滤。早期粗暴清空导致"切走再切回，流到一半的消息消失"。
      })
      .catch((err) => console.warn(`[fetch messages ${activeRoomId}]`, err));
    return () => {
      cancelled = true;
    };
  }, [activeRoomId]);

  const liveAgents = useMemo(
    () => (serverAgents ? mergeServerAgents(serverAgents, agents) : agents),
    [serverAgents],
  );

  const appTheme = useMemo(() => getAppTheme(appThemeId), [appThemeId]);
  const configuredAgents = useMemo(
    () => applyAgentConfigOverrides(agentsForTheme(appTheme, liveAgents), agentConfigOverrides),
    [agentConfigOverrides, appTheme, liveAgents],
  );
  const themedAgents = useMemo(
    () => applyApprovedAgentMemory(configuredAgents, memoryApprovalState),
    [configuredAgents, memoryApprovalState],
  );
  const themedAgentById = useMemo(() => new Map(themedAgents.map((agent) => [agent.id, agent])), [themedAgents]);
  const availableRoomAgents = useMemo(() => themedAgents.filter((agent) => agent.id !== "main"), [themedAgents]);
  const visibleAgentIds = useMemo(() => new Set(availableRoomAgents.map((agent) => agent.id)), [availableRoomAgents]);
  const persistedCreatedRooms = useMemo(
    () => serverRoomsToCreatedRooms(serverRooms ?? [], rooms),
    [serverRooms],
  );
  const generatedAgentRooms = useMemo(
    () => directRoomsForAgents(availableRoomAgents, [...rooms, ...createdRooms, ...persistedCreatedRooms], serverRooms ?? []),
    [availableRoomAgents, createdRooms, persistedCreatedRooms, serverRooms],
  );
  const workspaceRooms = useMemo(() => {
    const createdIds = new Set(createdRooms.map((room) => room.id));
    const serverRoomById = new Map((serverRooms ?? []).map((room) => [room.id, room]));
    return [
      ...rooms,
      ...createdRooms,
      ...persistedCreatedRooms.filter((room) => !createdIds.has(room.id)),
      ...generatedAgentRooms,
    ].map((room) => {
      const serverRoom = serverRoomById.get(room.id);
      if (!serverRoom) return room;
      return {
        ...room,
        lastMessage: serverRoom.lastMessage ?? room.lastMessage,
        lastActivityAt: serverRoom.lastActivityAt ?? room.lastActivityAt,
      };
    });
  }, [createdRooms, generatedAgentRooms, persistedCreatedRooms, serverRooms]);
  const memoryRooms = useMemo(() => applyApprovedRoomMemory(workspaceRooms, memoryApprovalState), [memoryApprovalState, workspaceRooms]);
  const memberAdjustedRooms = useMemo(
    () =>
      memoryRooms.map((room) => {
        const memberIds = room.kind === "agent" ? room.memberIds : roomMemberOverrides[room.id] ?? room.memberIds;
        return { ...room, memberIds };
      }),
    [memoryRooms, roomMemberOverrides],
  );
  const themedRooms = useMemo(() => roomsForAgents(memberAdjustedRooms, themedAgentById), [memberAdjustedRooms, themedAgentById]);
  const activeRoom = themedRooms.find((room) => room.id === activeRoomId) ?? themedRooms[0];
  const activeRoomRunId = runIdForRoom(runIdsByRoom, activeRoom.id);
  const activeRoomRunIds = runIdsForRoom(runIdsByRoom, activeRoom.id);
  const activeRun = activeRoomRunId ? runRegistry[activeRoomRunId] : undefined;
  const activeRunStatus = runStatusForRun(visibleEvents, activeRoomRunId);
  const activeRoomMessages = messagesByRoom[activeRoom.id] ?? [];
  const activeAgentStatuses = useMemo(
    () => deriveAllAgentStatuses(visibleEvents, runRegistry),
    [runRegistry, visibleEvents],
  );
  const activeDirectAgent = activeRoom.agentId ? getAgentFrom(themedAgentById, activeRoom.agentId) : undefined;
  const profileAgent = agentProfileAnchor ? getAgentFrom(themedAgentById, agentProfileAnchor.agentId) : undefined;
  const activeMemoryProposals = useMemo(
    () => pendingMemoryProposalsForRoom(memoryApprovalState, activeRoom.id, activeDirectAgent?.id),
    [activeDirectAgent?.id, activeRoom.id, memoryApprovalState],
  );

  const sdkArtifacts = useMemo(() => deriveAgentUXArtifacts(visibleEvents), [visibleEvents]);
  const allArtifacts = useMemo(
    () => [...sdkArtifacts, ...staticArtifacts].sort((left, right) => right.updatedAt - left.updatedAt),
    [sdkArtifacts],
  );
  const roomArtifacts = useMemo(
    () => artifactsForAgentRoom(activeRoom, allArtifacts),
    [activeRoom, allArtifacts],
  );
  const artifactKey = roomArtifacts.map((artifact) => `${artifact.id}:${artifact.status}:${artifact.updatedAt}`).join("|");
  const runMessagesByAnchor = useMemo(
    () => deriveTimelineRunMessages(visibleEvents, runRegistry, activeRoomRunIds),
    [activeRoomRunIds, runRegistry, visibleEvents],
  );
  const activeRunPrimaryMessage = activeRun ? runMessagesByAnchor[activeRun.anchorMessageId]?.[0] : undefined;
  const activeRunExpression = activeRunPrimaryMessage?.expression ?? pickAgentExpression({
    agentId: activeRun?.agentIds[0] ?? activeDirectAgent?.id ?? "main",
    runId: activeRun?.runId,
    trigger: activeRun?.trigger,
    runStatus: activeRun ? activeRunStatus : "idle",
    streaming: activeRunStatus === "running",
    hasText: false,
  });
  const activePanelRunStatus = activeRun?.roomId === activeRoom.id ? activeRunStatus : "idle";
  const approvedAgentMemory = activeDirectAgent ? memoryApprovalState.agentMemoryById[activeDirectAgent.id]?.summary : undefined;
  const approvedRoomMemory = memoryApprovalState.roomMemoryById[activeRoom.id]?.summary;
  const contextPanelInput = {
    artifactCount: roomArtifacts.length,
    hasApprovedMemory: Boolean(approvedAgentMemory || approvedRoomMemory),
    memoryProposalCount: activeMemoryProposals.length,
    runStatus: activePanelRunStatus,
  };
  const contextPanelAvailable = shouldExposeContextPanel(contextPanelInput);
  const contextPanelVisible = contextPanelOpen && contextPanelAvailable;
  const timelineRunKey = Object.values(runMessagesByAnchor)
    .flat()
    .map((message) => {
      const mediaKey = message.media.map((item) => `${item.idx}:${item.status}:${item.mediaUrl ?? ""}`).join(",");
      return `${message.id}:${message.text}:${message.streaming}:${message.status}:${mediaKey}`;
    })
    .join("|");

  useEffect(() => {
    return () => {
      timersRef.current.forEach(window.clearTimeout);
      timersRef.current = [];
    };
  }, []);

  useEffect(() => {
    const newestAgentUXArtifact = roomArtifacts.find((artifact) => artifact.origin === "agentux");
    if (newestAgentUXArtifact) {
      setSelectedArtifactId(newestAgentUXArtifact.id);
      return;
    }

    if (!roomArtifacts.some((artifact) => artifact.id === selectedArtifactId)) {
      setSelectedArtifactId(roomArtifacts[0]?.id);
    }
  }, [activeRoom.id, artifactKey, roomArtifacts, selectedArtifactId]);

  useEffect(() => {
    chatScrollRef.current?.scrollTo({
      top: chatScrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [activeRoom.id, activeRoomMessages.length, timelineRunKey, mode]);

  useEffect(() => {
    setContextPanelOpen(false);
  }, [activeRoom.id]);

  useEffect(() => {
    if (!contextPanelAvailable && contextPanelOpen) {
      setContextPanelOpen(false);
    }
  }, [contextPanelAvailable, contextPanelOpen]);

  useEffect(() => {
    if (!agentProfileAnchor) {
      return undefined;
    }

    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        setAgentProfileAnchor(undefined);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [agentProfileAnchor]);

  useEffect(() => {
    if (!imagePreview) {
      return undefined;
    }

    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        setImagePreview(undefined);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [imagePreview]);

  const openAgentProfile = useCallback<OpenAgentProfile>((agentId, anchor) => {
    setAgentProfileAnchor(positionAgentProfileCard(agentId, anchor.getBoundingClientRect()));
  }, []);

  const closeAgentProfile = useCallback(() => {
    setAgentProfileAnchor(undefined);
  }, []);

  const openImagePreview = useCallback((image: ImagePreview) => {
    setImagePreview(image);
  }, []);

  const closeImagePreview = useCallback(() => {
    setImagePreview(undefined);
  }, []);

  const openDirectAgentRoom = useCallback((agentId: string) => {
    setActiveRoomId(agentId);
    setView("chats");
    setAgentProfileAnchor(undefined);
  }, []);

  const openMomentsFromAgentCard = useCallback((agentId?: string) => {
    setView("moments");
    setMomentsInitialFilter(agentId);
    setAgentProfileAnchor(undefined);
  }, []);

  const createRoomFromTemplate = useCallback(async (template: TemplateRoom, memberIds: string[]) => {
    const id = `${template.id.replace(/^template-/, "group-")}-${crypto.randomUUID()}`;
    const room: Room = {
      id,
      title: template.title,
      goal: template.goal,
      summary: template.summary,
      lastMessage: "等待你发起任务。",
      time: "—",
      kind: "room",
      memberIds,
      runMode: template.runMode,
    };

    const res = await fetch("/api/rooms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, title: room.title, memberIds, mode: template.runMode }),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status}: ${text.slice(0, 160)}`);
    }

    setCreatedRooms((current) => [room, ...current]);
    setMessagesByRoom((current) => ({ ...current, [id]: [] }));
    setSelectedTemplateId(undefined);
    setActiveRoomId(id);
    setView("chats");
  }, []);

  const copyAgentSoul = useCallback((agent: Agent) => {
    const soulMarkdown = buildAgentSoulMarkdown(agent);
    void copyTextToClipboard(soulMarkdown).then((copied) => {
      if (!copied) {
        return;
      }

      setCopiedSoulAgentId(agent.id);
      window.setTimeout(() => {
        setCopiedSoulAgentId((current) => (current === agent.id ? undefined : current));
      }, 1200);
    });
  }, []);

  const appendVisibleEvent = useCallback((event: AgentUXEvent) => {
    setVisibleEvents((current) => (current.some((item) => item.id === event.id) ? current : [...current, event]));
    setMemoryApprovalState((current) => {
      const next = captureMemoryProposalEvent(current, event);
      return next === current ? current : writeMemoryApprovalState(undefined, next);
    });
  }, []);

  const approveMemoryProposalById = useCallback((proposalId: string) => {
    setMemoryApprovalState((current) => writeMemoryApprovalState(undefined, approveMemoryProposal(current, proposalId)));
  }, []);

  const rejectMemoryProposalById = useCallback((proposalId: string) => {
    setMemoryApprovalState((current) => writeMemoryApprovalState(undefined, rejectMemoryProposal(current, proposalId)));
  }, []);

  const registerRun = useCallback((descriptor: RunDescriptor) => {
    setRunRegistry((current) => ({
      ...current,
      [descriptor.runId]: descriptor,
    }));
    setRunIdsByRoom((current) => assignRoomRun(current, descriptor.roomId, descriptor.runId));
  }, []);

  const startFakeRun = useCallback((script: FakeRunScript, anchorMessageId: string) => {
    registerRun({
      runId: script.runId,
      roomId: script.roomId,
      title: script.title,
      trigger: script.trigger,
      agentIds: script.agentIds,
      startedAt: Date.now(),
      anchorMessageId,
    });

    script.events.forEach(({ event, delay }) => {
      const timer = window.setTimeout(() => {
        appendVisibleEvent(event);
      }, delay);
      timersRef.current.push(timer);
    });
  }, [appendVisibleEvent, registerRun]);

  const startRemoteRun = useCallback((
    descriptor: Pick<RunDescriptor, "runId" | "roomId" | "title" | "trigger" | "agentIds" | "anchorMessageId">,
    prompt: string,
    memberIds: string[],
    runMode: RemoteAgentRunMode,
  ) => {
    registerRun({
      ...descriptor,
      startedAt: Date.now(),
    });

    void streamRemoteAgentRunEvents({
      endpoint: `/api/rooms/${descriptor.roomId}/messages`,
      payload: buildRemoteAgentRunPayload({
        agentId: descriptor.agentIds[0],
        agentIds: descriptor.agentIds,
        memberIds,
        mode: runMode,
        runId: descriptor.runId,
        prompt,
      }),
      onEvent: appendVisibleEvent,
      onError: (error) => {
        appendVisibleEvent(createClientRunErrorEvent(descriptor, error));
      },
    });
  }, [appendVisibleEvent, registerRun]);

  const startRemoteRunTaskResume = useCallback((
    descriptor: Pick<RunDescriptor, "runId" | "roomId">,
    responseText: string,
  ) => {
    void streamRemoteAgentRunEvents({
      endpoint: `${remoteRunTaskEndpoint}/${descriptor.runId}/resume`,
      payload: buildRemoteRunTaskResumePayload({ responseText }),
      onEvent: appendVisibleEvent,
      onError: (error) => {
        appendVisibleEvent(createClientRunErrorEvent(descriptor, error));
      },
    });
  }, [appendVisibleEvent]);

  const handleSend = useCallback(() => {
    const body = draft.trim();
    if (!body) {
      return;
    }
    const createdAt = Date.now();

    const message: ChatMessage = {
      id: `human-${createdAt}`,
      sender: "human",
      author: "Ricky",
      time: "Now",
      body,
      createdAt,
    };

    setMessagesByRoom((current) => ({
      ...current,
      [activeRoom.id]: [...(current[activeRoom.id] ?? []), message],
    }));
    clearComposerDraftAfterSend(setDraft);

    if (activeRun && activeRunStatus === "awaiting_input") {
      startRemoteRunTaskResume(activeRun, body);
      return;
    }

    const runTarget = resolveAgentRunTarget(activeRoom, body, availableRoomAgents);
    if (runTarget) {
      const runId = nextRunId(runTarget.trigger, runIndexRef);
      const agent = getAgentFrom(themedAgentById, runTarget.agentIds[0]);
      const agentNames = runTarget.agentIds.map((agentId) => getAgentFrom(themedAgentById, agentId).name).join(" + ");
      const title = activeRoom.kind === "agent" ? `${agent.name} direct chat` : `${agentNames} in ${activeRoom.title}`;
      const memberIds = activeRoom.memberIds.length > 0 ? activeRoom.memberIds : runTarget.agentIds;
      startRemoteRun(
        {
          runId,
          roomId: activeRoom.id,
          title,
          trigger: runTarget.trigger,
          agentIds: runTarget.agentIds,
          anchorMessageId: message.id,
        },
        body,
        memberIds,
        roomRunMode(activeRoom),
      );
    }
  }, [
    activeRoom,
    activeRun,
    activeRunStatus,
    availableRoomAgents,
    draft,
    startRemoteRun,
    startRemoteRunTaskResume,
    themedAgentById,
  ]);

  const handleSaveSettings = useCallback(async (
    nextSettings: AgentRunSettings,
    nextThemeId: AppThemeId,
    nextAgentConfigOverrides: AgentConfigOverridesById,
    providerRuntimeValidated: boolean,
  ): Promise<{ ok: boolean; message?: string }> => {
    void providerRuntimeValidated;
    setAgentRunSettings(writeAgentRunSettings(undefined, nextSettings));
    setAppThemeId(writeAppThemeId(undefined, nextThemeId));
    setAgentConfigOverrides(writeAgentConfigOverrides(undefined, nextAgentConfigOverrides));
    setSettingsOpen(false);
    return { ok: true };
  }, []);

  const handleToggleRoomMember = useCallback((roomId: string, agentId: string) => {
    if (!availableRoomAgents.some((agent) => agent.id === agentId)) {
      return;
    }
    const room = themedRooms.find((item) => item.id === roomId);
    if (!room || room.kind === "agent") {
      return;
    }

    setRoomMemberOverrides((current) => {
      const currentMemberIds = current[roomId] ?? room.memberIds;
      const hasAgent = currentMemberIds.includes(agentId);
      if (hasAgent && currentMemberIds.length <= 1) {
        return current;
      }
      const nextMemberIds = hasAgent
        ? currentMemberIds.filter((id) => id !== agentId)
        : [...currentMemberIds, agentId];
      return { ...current, [roomId]: nextMemberIds };
    });
  }, [availableRoomAgents, themedRooms]);

  const handleConvene = useCallback(() => {
    const turn = conveneTurnRef.current;
    conveneTurnRef.current += 1;
    const hostName = getAgentFrom(themedAgentById, "main").name;
    const runId = nextRunId("convene", runIndexRef);
    const anchorMessageId = `system-convene-${runId}`;
    const selectedAgents = chooseConveneAgentIds(turn, activeRoom.memberIds, activeRoom.memberIds);
    const selectedNames = selectedAgents.map((agentId) => getAgentFrom(themedAgentById, agentId).name).join(" + ");
    const convenePrompt = convenePromptForRoom(activeRoom);

    setMode("convene");
    setMessagesByRoom((current) => ({
      ...current,
      [activeRoom.id]: [
        ...(current[activeRoom.id] ?? []),
        {
          id: anchorMessageId,
          sender: "system",
          author: "Room update",
          time: "Now",
          body: selectedNames
            ? `${hostName} convened the room and routed this pass to ${selectedNames}.`
            : `${hostName} convened the room and kept this pass with the host.`,
          compact: true,
        },
      ],
    }));

    startFakeRun(
      createConveneRunScript({
        runId,
        roomId: activeRoom.id,
        prompt: convenePrompt,
        selectedAgentIds: selectedAgents,
        agentLookup: themedAgentById,
      }),
      anchorMessageId,
    );
  }, [
    activeRoom,
    startFakeRun,
    themedAgentById,
  ]);

  const conversationRows = useMemo(
    () =>
      themedRooms.map((room) => {
        const roomRunId = runIdForRoom(runIdsByRoom, room.id);
        const roomRun = roomRunId ? runRegistry[roomRunId] : undefined;
        const roomRunStatus = runStatusForRun(visibleEvents, roomRunId);

        return {
          ...room,
          lastMessage: roomPreview(room, messagesByRoom[room.id], roomRun, roomRunStatus, themedAgentById),
          time: roomTime(room, messagesByRoom[room.id], roomRun),
        };
      }),
    [messagesByRoom, runIdsByRoom, runRegistry, themedAgentById, themedRooms, visibleEvents],
  );

  const recentAgentRoomIds = useMemo(
    () => recentDirectRoomIds(serverRooms ?? [], messagesByRoom),
    [messagesByRoom, serverRooms],
  );
  const chatRows = useMemo(
    () =>
      [...conversationRows.filter((row) => !row.template && (row.kind !== "agent" || recentAgentRoomIds.has(row.id)))]
        .sort((left, right) => {
          const leftRunId = runIdForRoom(runIdsByRoom, left.id);
          const rightRunId = runIdForRoom(runIdsByRoom, right.id);
          return (
            roomLastActivityAt(right, messagesByRoom[right.id], rightRunId ? runRegistry[rightRunId] : undefined)
            - roomLastActivityAt(left, messagesByRoom[left.id], leftRunId ? runRegistry[leftRunId] : undefined)
          );
        }),
    [conversationRows, messagesByRoom, recentAgentRoomIds, runIdsByRoom, runRegistry],
  );
  const contactRows = useMemo(
    () => conversationRows.filter((row) => row.template || (row.kind === "agent" && row.agentId && visibleAgentIds.has(row.agentId))),
    [conversationRows, visibleAgentIds],
  );
  const selectedTemplate = useMemo(
    () => themedRooms.find((room) => room.id === selectedTemplateId && room.template === true && Boolean(room.runMode)) as TemplateRoom | undefined,
    [selectedTemplateId, themedRooms],
  );

  return (
    <main className={`app-shell ${appTheme.className} ${contextPanelVisible ? "context-open" : ""} ${view === "moments" ? "view-moments" : view === "notifications" ? "view-notifications" : ""}`}>
      <WorkspaceRail
        view={view}
        onChangeView={(next) => {
          setView(next);
          if (next !== "agents") setSelectedTemplateId(undefined);
          // 从 rail 点 Moments 进入 → 全 feed。避免用户上次 deep-link 的 filter 残留。
          if (next === "moments") setMomentsInitialFilter(undefined);
        }}
      />
      {view === "moments" ? (
        <MomentsView
          agents={themedAgents}
          agentLookup={themedAgentById}
          initialFilter={momentsInitialFilter}
          onClearFilter={() => setMomentsInitialFilter(undefined)}
          onImagePreview={openImagePreview}
          onOpenAgentProfile={openAgentProfile}
        />
      ) : view === "notifications" ? (
        <EmptyWorkspaceState
          icon={<Bell size={28} />}
          title="还没有通知"
          message="Agent 之间的动态、群聊新消息、需要审批的内容会出现在这里。"
        />
      ) : view === "agents" ? (
        <>
          <ConversationList
            rooms={contactRows}
            activeRoomId={selectedTemplate?.id ?? activeRoom.id}
            agentLookup={themedAgentById}
            agentStatuses={activeAgentStatuses}
            variant="agents"
            onOpenAgentProfile={openAgentProfile}
            onSelectRoom={(roomId) => {
              const room = themedRooms.find((item) => item.id === roomId);
              if (room?.template) {
                setSelectedTemplateId(room.id);
                return;
              }
              setSelectedTemplateId(undefined);
              setActiveRoomId(roomId);
            }}
          />
          {selectedTemplate ? (
            <TemplateRoomPanel
              agents={availableRoomAgents}
              template={selectedTemplate}
              onCreateRoom={createRoomFromTemplate}
            />
          ) : (
            <AgentProfilePanel
              agent={activeDirectAgent}
              presence={activeDirectAgent ? activeAgentStatuses[activeDirectAgent.id] : undefined}
              onMessage={() => {
                if (activeDirectAgent) {
                  setView("chats");
                  setActiveRoomId(activeDirectAgent.id);
                }
              }}
              onMoments={() => openMomentsFromAgentCard(activeDirectAgent?.id)}
              onAvatarUpdated={() => {
                // backend GET /:id/avatar uses a short versioned cache; give the
                // write a moment to land, then reload this MVP shell.
                // 再 reload 一次让 contact list / profile 头像换成新图。粗暴但 MVP 可接受。
                window.setTimeout(() => window.location.reload(), 600);
              }}
            />
          )}
	        </>
	      ) : (
	        <>
	          <ConversationList
	            rooms={chatRows}
	            activeRoomId={activeRoom.id}
	            agentLookup={themedAgentById}
	            agentStatuses={activeAgentStatuses}
	            variant="chats"
	            onOpenAgentProfile={openAgentProfile}
	            onSelectRoom={(roomId) => {
	              setSelectedTemplateId(undefined);
	              setActiveRoomId(roomId);
	            }}
	          />
	          <section className="room">
	            <RoomHeader
	              room={activeRoom}
	              agentLookup={themedAgentById}
	              availableAgents={availableRoomAgents}
	              members={membersForRoom(activeRoom, themedAgentById)}
	              onToggleRoomMember={handleToggleRoomMember}
	              contextAvailable={contextPanelAvailable}
	              contextOpen={contextPanelVisible}
	              onOpenAgentProfile={openAgentProfile}
	              onToggleContext={() => {
	                if (contextPanelAvailable) {
	                  setContextPanelOpen((current) => !current);
	                }
	              }}
	            />
	            <div className="chat-scroll" aria-label={`${activeRoom.title} chat`} ref={chatScrollRef}>
	              {activeRoomMessages.length > 0 || mode === "review" ? <DayDivider label="Today" /> : null}
	              {activeRoomMessages.map((message) => (
	                <Fragment key={message.id}>
	                  <MessageBubble
	                    agentLookup={themedAgentById}
	                    message={message}
	                    onImagePreview={openImagePreview}
	                    onOpenAgentProfile={openAgentProfile}
	                  />
	                  {(runMessagesByAnchor[message.id] ?? []).map((runMessage) => {
	                    return (
	                      <AgentRunBubble
	                        agent={getAgentFrom(themedAgentById, runMessage.agentId)}
	                        expression={runMessage.expression}
	                        key={runMessage.id}
	                        media={runMessage.media}
	                        onImagePreview={openImagePreview}
	                        onOpenAgentProfile={openAgentProfile}
	                        text={runMessage.text}
	                        streaming={runMessage.streaming}
	                        status={runMessage.status}
	                      />
	                    );
	                  })}
	                </Fragment>
	              ))}
	              {mode === "review" ? <ReviewModePanel artifacts={roomArtifacts} room={activeRoom} /> : null}
	            </div>
	            <Composer
	              agents={availableRoomAgents}
	              agentLookup={themedAgentById}
	              draft={draft}
	              mode={mode}
	              room={activeRoom}
	              setDraft={setDraft}
	              onSend={handleSend}
	            />
	          </section>
	        </>
	      )}
      {contextPanelVisible ? (
        <>
          <button className="context-scrim" aria-label="Hide room context" onClick={() => setContextPanelOpen(false)} />
          <div className="context-drawer">
            <ContextPanel
              agentLookup={themedAgentById}
              room={activeRoom}
              activeExpression={activeRunExpression}
              runStatus={activePanelRunStatus}
              activeRunTitle={activeRun?.roomId === activeRoom.id ? activeRun.title : undefined}
              artifacts={roomArtifacts}
              approvedAgentMemory={approvedAgentMemory}
              approvedRoomMemory={approvedRoomMemory}
              memoryProposals={activeMemoryProposals}
              selectedArtifactId={selectedArtifactId}
              onApproveMemoryProposal={approveMemoryProposalById}
              onRejectMemoryProposal={rejectMemoryProposalById}
              onSelectArtifact={setSelectedArtifactId}
              onClose={() => setContextPanelOpen(false)}
            />
          </div>
        </>
      ) : null}
      {profileAgent && agentProfileAnchor ? (
        <>
          <button className="profile-popover-backdrop" aria-label="Close agent profile" onClick={closeAgentProfile} />
          <AgentProfilePopover
            agent={profileAgent}
            copied={copiedSoulAgentId === profileAgent.id}
            onClose={closeAgentProfile}
            onCopySoul={copyAgentSoul}
            onMessage={openDirectAgentRoom}
            onMoments={() => openMomentsFromAgentCard(profileAgent.id)}
            position={agentProfileAnchor}
            presence={profileAgent.presence ?? activeAgentStatuses[profileAgent.id] ?? profileAgent.status}
          />
        </>
      ) : null}
      {settingsOpen ? (
        <AgentSettingsModal
          agentConfigOverrides={agentConfigOverrides}
          agents={themedAgents}
          onClose={() => setSettingsOpen(false)}
          onSave={handleSaveSettings}
          settings={agentRunSettings}
          themeId={appThemeId}
        />
      ) : null}
      {imagePreview ? <ImagePreviewModal image={imagePreview} onClose={closeImagePreview} /> : null}
    </main>
  );
}

function themePreviewStyle(theme: AppTheme): CSSProperties {
  const preview = theme.preview;
  return {
    "--theme-preview-bg": preview.background,
    "--theme-preview-rail": preview.rail,
    "--theme-preview-surface": preview.surface,
    "--theme-preview-selected-row": preview.selectedRow,
    "--theme-preview-human-bubble": preview.humanBubble,
    "--theme-preview-agent-bubble": preview.agentBubble,
    "--theme-preview-composer": preview.composer,
    "--theme-preview-accent": preview.accent,
    "--theme-preview-accent-strong": preview.accentStrong,
    "--theme-preview-text": preview.text,
    "--theme-preview-muted": preview.muted,
    "--theme-preview-line": preview.line,
    "--theme-preview-status": preview.status,
  } as CSSProperties;
}

function agentModelOptions(
  models: readonly ModelOption[],
  workspaceModel: string,
  providerName: string,
): ModelOption[] {
  return [
    {
      id: WORKSPACE_PROVIDER_MODEL_ID,
      name: `Workspace default (${workspaceModel})`,
      provider: providerName,
      contextLength: 0,
      maxOutputTokens: 0,
      defaultTemperature: 0.7,
    },
    ...models,
  ];
}

function positionAgentProfileCard(agentId: string, rect: DOMRect): AgentProfileAnchor {
  const gap = 12;
  const margin = 12;
  const cardWidth = Math.min(360, window.innerWidth - margin * 2);
  const cardHeight = window.innerHeight - margin * 2;
  const fitsRight = rect.right + gap + cardWidth <= window.innerWidth - margin;
  const rawLeft = fitsRight ? rect.right + gap : rect.left - gap - cardWidth;
  const rawTop = rect.top - 18;

  return {
    agentId,
    left: clamp(rawLeft, margin, window.innerWidth - cardWidth - margin),
    top: clamp(rawTop, margin, window.innerHeight - cardHeight - margin),
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

async function copyTextToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Fall through to the synchronous copy path for non-secure preview hosts.
  }

  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.setAttribute("readonly", "true");
  textArea.style.position = "fixed";
  textArea.style.left = "-9999px";
  textArea.style.top = "0";
  textArea.style.opacity = "0";
  document.body.appendChild(textArea);
  const activeElement = document.activeElement instanceof HTMLElement ? document.activeElement : undefined;
  textArea.focus({ preventScroll: true });
  textArea.select();
  textArea.setSelectionRange(0, text.length);

  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    document.body.removeChild(textArea);
    activeElement?.focus({ preventScroll: true });
  }
}

function ProviderModelPicker({
  disabled,
  models,
  onChange,
  value,
}: {
  disabled: boolean;
  models: readonly ModelOption[];
  onChange: (model: string) => void;
  value: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim();
  const filteredModels = useMemo(() => filterProviderModels(models, normalizedQuery, 60), [models, normalizedQuery]);
  const selectedModel = models.find((model) => model.id === value);
  const exactQueryMatch = normalizedQuery
    ? models.find((model) => model.id.toLowerCase() === normalizedQuery.toLowerCase())
    : undefined;
  const looksLikeModelSlug = /[/.:]/.test(normalizedQuery);
  const canUseCustomModel = Boolean(normalizedQuery && !exactQueryMatch && (filteredModels.length === 0 || looksLikeModelSlug));

  useEffect(() => {
    if (!open) {
      setQuery("");
    }
  }, [open, value]);

  const chooseModel = (modelId: string) => {
    onChange(modelId);
    setQuery("");
    setOpen(false);
  };

  const chooseCustomModel = () => {
    if (!normalizedQuery) {
      return;
    }
    chooseModel(normalizedQuery);
  };

  const openChoices = () => {
    setQuery("");
    setOpen(true);
  };

  const handleInputKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      openChoices();
    }
    if (event.key === "Escape") {
      setOpen(false);
    }
    if (event.key === "Enter" && open) {
      event.preventDefault();
      if (exactQueryMatch) {
        chooseModel(exactQueryMatch.id);
        return;
      }
      if (filteredModels[0]) {
        chooseModel(filteredModels[0].id);
        return;
      }
      chooseCustomModel();
    }
  };

  return (
    <div className={`model-picker ${disabled ? "disabled" : ""}`}>
      <div className="model-picker-input-row">
        <input
          aria-autocomplete="list"
          aria-expanded={open}
          aria-label="Model"
          disabled={disabled}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={openChoices}
          onKeyDown={handleInputKeyDown}
          placeholder={open ? "Search models..." : "Search or paste model slug"}
          role="combobox"
          value={open ? query : value}
        />
        <button
          aria-label="Show model choices"
          disabled={disabled}
          onClick={() => (open ? setOpen(false) : openChoices())}
          onMouseDown={(event) => event.preventDefault()}
          type="button"
        >
          <ChevronDown size={16} />
        </button>
      </div>
      <div className="model-picker-meta">
        {open ? (
          <span className="model-picker-count">
            {filteredModels.length} / {models.length} models
          </span>
        ) : selectedModel ? (
          <>
            <strong>{selectedModel.name}</strong>
            <span>{selectedModel.provider}</span>
          </>
        ) : (
          <span>Custom model slug</span>
        )}
      </div>
      {!disabled && open ? (
        <div className="model-picker-menu" role="listbox">
          {canUseCustomModel ? (
            <button
              className="model-picker-option model-picker-custom-option"
              onClick={chooseCustomModel}
              onMouseDown={(event) => event.preventDefault()}
              type="button"
            >
              <span>
                <strong>Use custom model slug</strong>
                <small>{normalizedQuery}</small>
              </span>
              <span className="model-picker-provider">Custom</span>
            </button>
          ) : null}
          {filteredModels.length > 0 ? (
            filteredModels.map((model) => (
              <button
                aria-selected={model.id === value}
                className="model-picker-option"
                key={model.id}
                onClick={() => chooseModel(model.id)}
                onMouseDown={(event) => event.preventDefault()}
                role="option"
                type="button"
              >
                <span>
                  <strong>{model.name}</strong>
                  <small>{model.id}</small>
                </span>
                <span className="model-picker-provider">{model.provider}</span>
                {model.id === value ? <Check size={15} /> : null}
              </button>
            ))
          ) : (
            <div className="model-picker-empty">No catalog match</div>
          )}
        </div>
      ) : null}
    </div>
  );
}

function AgentSettingsModal({
  agentConfigOverrides,
  agents: configuredAgents,
  settings,
  themeId,
  onClose,
  onSave,
}: {
  agentConfigOverrides: AgentConfigOverridesById;
  agents: Agent[];
  settings: AgentRunSettings;
  themeId: AppThemeId;
  onClose: () => void;
  onSave: (
    settings: AgentRunSettings,
    themeId: AppThemeId,
    agentConfigOverrides: AgentConfigOverridesById,
    providerRuntimeValidated: boolean,
  ) => Promise<{ ok: boolean; message?: string }>;
}) {
  const [activeSection, setActiveSection] = useState<"appearance" | "providers" | "agents">("appearance");
  const [activeAgentId, setActiveAgentId] = useState(configuredAgents[0]?.id ?? "main");
  const [draftSettings, setDraftSettings] = useState(settings);
  const [draftThemeId, setDraftThemeId] = useState<AppThemeId>(themeId);
  const [draftAgentConfigOverrides, setDraftAgentConfigOverrides] =
    useState<AgentConfigOverridesById>(agentConfigOverrides);
  const [editingSoulAgentIds, setEditingSoulAgentIds] = useState<Record<string, boolean>>({});
  const [testState, setTestState] = useState<"idle" | "testing" | "ok" | "error">("idle");
  const [testMessage, setTestMessage] = useState("");
  const [validatedProviderSignature, setValidatedProviderSignature] = useState<string | undefined>();
  const [modelFetchState, setModelFetchState] = useState<"idle" | "fetching" | "ok" | "error">("idle");
  const [saveState, setSaveState] = useState<"idle" | "saving" | "error">("idle");
  const [saveMessage, setSaveMessage] = useState("");
  const [fetchedModelsByProvider, setFetchedModelsByProvider] =
    useState<Partial<Record<AgentRunProvider, ModelOption[]>>>({});
  const activeProvider = getProviderConfig(draftSettings.provider);
  const activeRuntime = getActiveProviderRuntime(draftSettings);
  const activeProviderModels = fetchedModelsByProvider[draftSettings.provider] ?? activeProvider.models;
  const activeAgentModelOptions = useMemo(
    () => agentModelOptions(activeProviderModels, activeRuntime.model, activeProvider.name),
    [activeProvider.name, activeProviderModels, activeRuntime.model],
  );
  const activeProviderSignature = providerRuntimeSignature(draftSettings);
  const providerRuntimeValidated = testState === "ok" && validatedProviderSignature === activeProviderSignature;
  const activeTheme = getAppTheme(draftThemeId);
  const draftAgents = useMemo(
    () => applyAgentConfigOverrides(agentsForTheme(activeTheme), draftAgentConfigOverrides),
    [activeTheme, draftAgentConfigOverrides],
  );
  const activeAgent = draftAgents.find((agent) => agent.id === activeAgentId) ?? draftAgents[0];
  const providerIsFake = activeProvider.transport === "fake";
  const usingServerApiKey = providerUsesServerApiKey(draftSettings);
  const testDisabled = testState === "testing" || !canTestProviderSettings(draftSettings);
  const modelFetchDisabled =
    providerIsFake ||
    modelFetchState === "fetching" ||
    !providerRuntimeValidated;

  const resetTest = () => {
    setTestState("idle");
    setTestMessage("");
    setSaveState("idle");
    setSaveMessage("");
    setValidatedProviderSignature(undefined);
  };

  const resetModelFetch = () => {
    setModelFetchState("idle");
  };

  const selectProvider = (provider: AgentRunProvider) => {
    setDraftSettings((current) => switchAgentRunProvider(current, provider));
    resetTest();
    resetModelFetch();
  };

  const updateRuntime = (patch: Parameters<typeof updateProviderRuntimeSettings>[2]) => {
    const provider = draftSettings.provider;
    const connectionChanged = "baseUrl" in patch || "apiKey" in patch;
    setDraftSettings((current) => updateProviderRuntimeSettings(current, current.provider, patch));
    if (connectionChanged) {
      setFetchedModelsByProvider((current) => {
        const next = { ...current };
        delete next[provider];
        return next;
      });
      resetTest();
      resetModelFetch();
    }
  };

  const updateAgentOverride = (agentId: string, patch: AgentConfigOverridesById[string]) => {
    setDraftAgentConfigOverrides((current) => ({
      ...current,
      [agentId]: {
        ...(current[agentId] ?? {}),
        ...patch,
        soul: patch.soul ? { ...(current[agentId]?.soul ?? {}), ...patch.soul } : current[agentId]?.soul,
        permissions: patch.permissions
          ? { ...(current[agentId]?.permissions ?? {}), ...patch.permissions }
          : current[agentId]?.permissions,
      },
    }));
  };

  const toggleAgentSkill = (agent: Agent, skillId: string) => {
    const enabled = new Set(agent.enabledSkillIds);
    if (enabled.has(skillId)) {
      enabled.delete(skillId);
    } else {
      enabled.add(skillId);
    }
    updateAgentOverride(agent.id, { enabledSkillIds: [...enabled] });
  };

  const toggleSoulEditor = (agentId: string) => {
    setEditingSoulAgentIds((current) => ({ ...current, [agentId]: !current[agentId] }));
  };

  const handleTest = async () => {
    const signature = providerRuntimeSignature(draftSettings);
    setTestState("testing");
    setTestMessage("");
    resetModelFetch();
    const result = await testProviderSettings(draftSettings, { endpoint: providerTestEndpoint });
    setTestState(result.ok ? "ok" : "error");
    setValidatedProviderSignature(result.ok ? signature : undefined);
    setTestMessage(result.message);
  };

  const handleFetchModels = async () => {
    const provider = draftSettings.provider;
    setModelFetchState("fetching");
    const result = await fetchProviderModelOptions(draftSettings, { endpoint: providerModelsEndpoint });
    setModelFetchState(result.ok ? "ok" : "idle");
    if (result.ok) {
      setFetchedModelsByProvider((current) => ({
        ...current,
        [provider]: mergeProviderModels(getProviderConfig(provider).models, result.models),
      }));
    }
  };

  const handleSave = async () => {
    setSaveState("saving");
    setSaveMessage("");
    const result = await onSave(draftSettings, draftThemeId, draftAgentConfigOverrides, providerRuntimeValidated);
    if (!result.ok) {
      setSaveState("error");
      setSaveMessage(result.message ?? "Could not save settings.");
      return;
    }
    setSaveState("idle");
  };

  return (
    <div className="settings-backdrop" role="presentation">
      <section aria-label="Chat settings" className="settings-modal">
        <header className="settings-modal-head">
          <div>
            <span className="panel-label">Workspace settings</span>
            <h2>
              {activeSection === "appearance"
                ? "Appearance"
                : activeSection === "agents"
                  ? "Agents"
                  : "Model provider"}
            </h2>
          </div>
          <button aria-label="Close settings" onClick={onClose}>
            <ChevronDown size={18} />
          </button>
        </header>

        <div className={`settings-grid ${activeSection === "agents" ? "agents-active" : ""}`}>
          <aside className="settings-provider-list settings-nav">
            <button
              aria-pressed={activeSection === "appearance"}
              className={activeSection === "appearance" ? "selected" : ""}
              onClick={() => setActiveSection("appearance")}
            >
              <Sparkles size={16} />
              <span>
                <strong>Appearance</strong>
                <small>Theme colors and agent portraits</small>
              </span>
            </button>
            <button
              aria-pressed={activeSection === "agents"}
              className={activeSection === "agents" ? "selected" : ""}
              onClick={() => setActiveSection("agents")}
            >
              <Users size={16} />
              <span>
                <strong>Agents</strong>
                <small>Profile, soul, skills, and permissions</small>
              </span>
            </button>
            <button
              aria-pressed={activeSection === "providers"}
              className={activeSection === "providers" ? "selected" : ""}
              onClick={() => setActiveSection("providers")}
            >
              <CircleDot size={16} />
              <span>
                <strong>Providers</strong>
                <small>Model runtime and API settings</small>
              </span>
            </button>
            {activeSection === "providers" ? (
              <div className="settings-provider-stack">
                {MODEL_PROVIDERS.map((provider) => (
                  <button
                    aria-pressed={draftSettings.provider === provider.id}
                    className={draftSettings.provider === provider.id ? "selected nested" : "nested"}
                    key={provider.id}
                    onClick={() => selectProvider(provider.id)}
                  >
                    {provider.transport === "fake" ? <Sparkles size={16} /> : <CircleDot size={16} />}
                    <span>
                      <strong>{provider.name}</strong>
                      <small>{provider.description}</small>
                    </span>
                  </button>
                ))}
              </div>
            ) : null}
          </aside>

          {activeSection === "agents" ? (
            <aside aria-label="Agent picker" className="settings-agent-rail">
              {draftAgents.map((agent) => (
                <button
                  aria-label={`${agent.name}, ${agent.role}, ${agent.enabledSkillIds.length} skills`}
                  aria-pressed={activeAgentId === agent.id}
                  className={activeAgentId === agent.id ? "selected" : ""}
                  key={agent.id}
                  onClick={() => setActiveAgentId(agent.id)}
                  title={`${agent.name} · ${agent.enabledSkillIds.length} skills`}
                  type="button"
                >
                  <Avatar agent={agent} small />
                  <span>{agent.name}</span>
                </button>
              ))}
            </aside>
          ) : null}

          <div className={`settings-form ${activeSection === "agents" ? "agent-settings-form" : ""}`}>
            {activeSection === "appearance" ? (
              <>
                <div className="settings-provider-summary theme-summary">
                  <div>
                    <strong>{activeTheme.name}</strong>
                    <span>{activeTheme.description}</span>
                  </div>
                  <small>{activeTheme.nameZh}</small>
                </div>

                <div className="theme-card-grid" aria-label="Theme choices">
                  {APP_THEMES.map((theme) => (
                    <button
                      aria-pressed={draftThemeId === theme.id}
                      className={`theme-choice ${draftThemeId === theme.id ? "selected" : ""}`}
                      key={theme.id}
                      onClick={() => setDraftThemeId(theme.id)}
                      type="button"
                    >
                      <span className="theme-choice-preview" style={themePreviewStyle(theme)}>
                        <span className="theme-mini-shell">
                          <span className="theme-mini-rail">
                            <span />
                            <span />
                          </span>
                          <span className="theme-mini-list">
                            <span className="theme-mini-search" />
                            <span className="theme-mini-row active">
                              <span className="theme-mini-dot" />
                              <span className="theme-mini-lines">
                                <span />
                                <span />
                              </span>
                            </span>
                            <span className="theme-mini-row">
                              <span className="theme-mini-dot muted" />
                              <span className="theme-mini-lines">
                                <span />
                                <span />
                              </span>
                            </span>
                          </span>
                          <span className="theme-mini-chat">
                            <span className="theme-mini-header" />
                            <span className="theme-mini-bubble agent" />
                            <span className="theme-mini-bubble human" />
                            <span className="theme-mini-composer" />
                          </span>
                        </span>
                        <span className="theme-preview-foot">
                          <span className="theme-swatch-row">
                            {theme.swatches.map((color) => (
                              <span className="theme-swatch" key={color} style={{ background: color }} />
                            ))}
                          </span>
                          <span className="theme-avatar-preview">
                            {agents.map((agent) => {
                              const avatar = theme.agentAvatars[agent.id];
                              const persona = theme.agentPersonas[agent.id];
                              return avatar ? (
                                <img alt="" key={agent.id} src={avatar} title={persona?.name ?? agent.name} />
                              ) : (
                                <span key={agent.id} style={{ background: agent.color }}>
                                  {persona?.initials ?? agent.initials}
                                </span>
                              );
                            })}
                          </span>
                        </span>
                      </span>
                      <span className="theme-choice-copy">
                        <strong>{theme.nameZh}</strong>
                        <span>{theme.name}</span>
                      </span>
                      {draftThemeId === theme.id ? <Check size={17} /> : null}
                    </button>
                  ))}
                </div>
              </>
            ) : activeSection === "providers" ? (
              <>
                <div className="settings-provider-summary">
                  <div>
                    <strong>{activeProvider.name}</strong>
                    <span>{activeProvider.description}</span>
                  </div>
                  <small>{providerIsFake ? "Local preview" : "OpenAI-compatible"}</small>
                </div>

                <label>
                  <span>Base URL</span>
                  <input
                    disabled={providerIsFake}
                    onChange={(event) => updateRuntime({ baseUrl: event.target.value })}
                    value={activeRuntime.baseUrl}
                  />
                </label>
                <label>
                  <span>API key {activeProvider.requiresApiKey ? "(saved after a passing Test)" : "(optional)"}</span>
                  <input
                    autoComplete="new-password"
                    disabled={providerIsFake}
                    onChange={(event) => updateRuntime({ apiKey: event.target.value })}
                    placeholder={
                      activeProvider.requiresApiKey
                        ? "Paste once, Test, then Save to Keychain"
                        : "Optional for local providers"
                    }
                    type="password"
                    value={activeRuntime.apiKey}
                  />
                  {activeProvider.keyLink ? (
                    <a className="settings-key-link" href={activeProvider.keyLink} rel="noreferrer" target="_blank">
                      Get provider key
                    </a>
                  ) : null}
                  {usingServerApiKey ? <small className="settings-key-hint">Blank uses saved Keychain/env key.</small> : null}
                </label>
                <div className="settings-field">
                  <span className="settings-field-label">Model</span>
                  <ProviderModelPicker
                    disabled={providerIsFake}
                    models={activeProviderModels}
                    onChange={(model) => updateRuntime({ model })}
                    value={activeRuntime.model}
                  />
                </div>

                <div className="settings-test-row">
                  <button disabled={testDisabled} onClick={handleTest}>
                    {testState === "testing" ? "Testing" : "Test"}
                  </button>
                  <button
                    className="model-fetch-button"
                    disabled={modelFetchDisabled}
                    onClick={handleFetchModels}
                    title={providerRuntimeValidated ? "Fetch provider models" : "Run Test successfully first"}
                    type="button"
                  >
                    <RefreshCw size={14} />
                    {modelFetchState === "fetching" ? "Fetching" : "Fetch models"}
                  </button>
                  {testMessage ? <span className={`settings-test-message ${testState}`}>{testMessage}</span> : null}
                </div>
              </>
            ) : activeAgent ? (
              <AgentConfigEditor
                agent={activeAgent}
                editingSoul={Boolean(editingSoulAgentIds[activeAgent.id])}
                modelOptions={activeAgentModelOptions}
                modelPickerDisabled={providerIsFake}
                onChange={updateAgentOverride}
                onSoulMarkdownChange={(agentId, soulMarkdown) => updateAgentOverride(agentId, { soulMarkdown })}
                onToggleSoulEditing={toggleSoulEditor}
                onToggleSkill={toggleAgentSkill}
              />
            ) : null}

            <footer className="settings-actions">
              <button onClick={onClose}>Cancel</button>
              {saveMessage ? <span className={`settings-save-message ${saveState}`}>{saveMessage}</span> : null}
              <button className="primary" disabled={saveState === "saving"} onClick={handleSave}>
                {saveState === "saving" ? "Saving" : "Save"}
              </button>
            </footer>
          </div>
        </div>
      </section>
    </div>
  );
}

function AgentConfigEditor({
  agent,
  editingSoul,
  modelOptions,
  modelPickerDisabled,
  onChange,
  onSoulMarkdownChange,
  onToggleSoulEditing,
  onToggleSkill,
}: {
  agent: Agent;
  editingSoul: boolean;
  modelOptions: readonly ModelOption[];
  modelPickerDisabled: boolean;
  onChange: (agentId: string, patch: AgentConfigOverridesById[string]) => void;
  onSoulMarkdownChange: (agentId: string, soulMarkdown: string) => void;
  onToggleSoulEditing: (agentId: string) => void;
  onToggleSkill: (agent: Agent, skillId: string) => void;
}) {
  const soulMarkdown = buildAgentSoulMarkdown(agent);

  return (
    <>
      <div className="settings-provider-summary agent-settings-summary">
        <Avatar agent={agent} />
        <div className="agent-settings-summary-copy">
          <strong>{agent.name}</strong>
          <span>{agent.soul.identity}</span>
        </div>
        <small>{agent.skillPolicy.replaceAll("_", " ")}</small>
      </div>

      <section className="settings-subsection">
        <div className="settings-subsection-title">
          <span>Profile</span>
          <Bot size={16} />
        </div>
        <div className="agent-settings-two-column">
          <label>
            <span>Name</span>
            <input onChange={(event) => onChange(agent.id, { name: event.target.value })} value={agent.name} />
          </label>
          <label>
            <span>Role</span>
            <input onChange={(event) => onChange(agent.id, { role: event.target.value })} value={agent.role} />
          </label>
        </div>
          <label>
            <span>Short bio</span>
            <textarea
            onChange={(event) => onChange(agent.id, { profile: event.target.value })}
            rows={2}
            value={agent.profile}
          />
        </label>
        <div className="agent-settings-two-column">
          <div className="settings-field">
            <span className="settings-field-label">Model</span>
            <ProviderModelPicker
              disabled={modelPickerDisabled}
              models={modelOptions}
              onChange={(model) => onChange(agent.id, { model })}
              value={agent.model || WORKSPACE_PROVIDER_MODEL_ID}
            />
          </div>
          <label>
            <span>Skill policy</span>
            <select
              onChange={(event) => onChange(agent.id, { skillPolicy: event.target.value as AgentSkillPolicy })}
              value={agent.skillPolicy}
            >
              {skillPolicyOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Runtime profile</span>
            <select
              onChange={(event) => onChange(agent.id, { providerProfile: event.target.value || undefined })}
              value={agent.providerProfile ?? ""}
            >
              {providerProfileOptions.map((option) => (
                <option key={option.value || "workspace"} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <section className="settings-subsection">
        <div className="settings-subsection-title">
          <span>soul.md</span>
          <button className="settings-inline-action" onClick={() => onToggleSoulEditing(agent.id)} type="button">
            {editingSoul ? <Check size={15} /> : <Pencil size={15} />}
            <span>{editingSoul ? "Done" : "Edit"}</span>
          </button>
        </div>
        {editingSoul ? (
          <textarea
            aria-label={`${agent.name} soul.md editor`}
            className="soul-markdown-input"
            onChange={(event) => onSoulMarkdownChange(agent.id, event.target.value)}
            rows={14}
            spellCheck={false}
            value={soulMarkdown}
          />
        ) : (
          <pre className="soul-markdown-preview">{soulMarkdown}</pre>
        )}
      </section>

      <section className="settings-subsection">
        <div className="settings-subsection-title">
          <span>Skills</span>
          <FileCode2 size={16} />
        </div>
        <div className="skill-toggle-grid">
          {AGENT_SKILLS.map((skill) => {
            const enabled = agent.enabledSkillIds.includes(skill.id);
            return (
              <button
                aria-pressed={enabled}
                className={`skill-toggle ${enabled ? "selected" : ""}`}
                key={skill.id}
                onClick={() => onToggleSkill(agent, skill.id)}
                type="button"
              >
                <strong>{skill.name}</strong>
                <span>{skill.description}</span>
                <small>{skill.category}</small>
              </button>
            );
          })}
        </div>
      </section>

      <section className="settings-subsection">
        <div className="settings-subsection-title">
          <span>Permissions</span>
          <Settings size={16} />
        </div>
        <div className="permission-grid">
          {(Object.keys(permissionLabels) as AgentPermissionKey[]).map((permission) => (
            <label className="permission-row" key={permission}>
              <span>{permissionLabels[permission]}</span>
              <select
                onChange={(event) =>
                  onChange(agent.id, { permissions: { [permission]: event.target.value as AgentPermissionSet[typeof permission] } })
                }
                value={agent.permissions[permission]}
              >
                {permissionModes.map((mode) => (
                  <option key={mode.value} value={mode.value}>
                    {mode.label}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
      </section>
    </>
  );
}

type WorkspaceView = "chats" | "agents" | "moments" | "notifications";

function WorkspaceRail({
  view,
  onChangeView,
}: {
  view: WorkspaceView;
  onChangeView: (view: WorkspaceView) => void;
}) {
  const items: Array<{ id: WorkspaceView; label: string; icon: ReactNode }> = [
    { id: "chats", label: "Chats", icon: <MessageCircle size={20} /> },
    { id: "agents", label: "Agents", icon: <Users size={20} /> },
    { id: "moments", label: "Moments", icon: <Camera size={20} /> },
    { id: "notifications", label: "Notifications", icon: <Bell size={20} /> },
  ];
  return (
    <aside className="rail" aria-label="Workspace navigation">
      <button className="rail-menu" aria-label="Main menu">
        <Menu size={20} />
      </button>
      <div className="workspace-mark">TA</div>
      <nav className="rail-stack">
        {items.map((item) => (
          <button
            aria-current={view === item.id ? "page" : undefined}
            aria-label={item.label}
            className={`rail-item ${view === item.id ? "active" : ""}`}
            key={item.id}
            onClick={() => onChangeView(item.id)}
            type="button"
          >
            {item.icon}
          </button>
        ))}
      </nav>
      {/* TODO: settings UI hidden in PoC; provider/agent/theme config lives in openclaw.json for now.
          To re-enable: render <button className="rail-item bottom" onClick={onOpenSettings}>...</button> */}
    </aside>
  );
}

function ConversationList({
  rooms,
  activeRoomId,
  agentLookup,
  agentStatuses,
  variant,
  onOpenAgentProfile,
  onSelectRoom,
}: {
  rooms: Room[];
  activeRoomId: string;
  agentLookup: AgentLookup;
  agentStatuses: Record<string, AgentStatus>;
  variant: "chats" | "agents";
  onOpenAgentProfile: OpenAgentProfile;
  onSelectRoom: (roomId: string) => void;
}) {
  const chatRooms = rooms.filter((room) => room.kind !== "agent");
  const agentRooms = rooms.filter((room) => room.kind === "agent");
  const sectionCopy =
    variant === "agents"
      ? {
          searchPlaceholder: "Search templates or agents",
          chatSectionLabel: "Templates",
          agentSectionLabel: "Agents",
        }
      : {
          searchPlaceholder: "Search chats or contacts",
          chatSectionLabel: "Groups",
          agentSectionLabel: "Chats",
        };
  const renderRoomRow = (room: Room) => {
    const directAgent = room.agentId ? getOptionalAgentFrom(agentLookup, room.agentId) : undefined;
    const roomIcon = roomIconById[room.id];
    // Contacts/Agents 视图把 agent 行的副标题换成能力 tagline；其它视图/群聊/模板维持原样。
    // tagline 从 directAgent.role + directAgent.bestFor 派生，缺 bestFor 时退化为 lastMessage。
    const tagline =
      variant === "agents" && room.kind === "agent" && directAgent && directAgent.bestFor.length > 0
        ? buildContactTagline(directAgent.role, directAgent.bestFor)
        : null;
    const previewText = tagline ?? room.lastMessage;
    return (
      <button
        aria-pressed={room.id === activeRoomId}
        className={`room-row ${room.id === activeRoomId ? "active" : ""}`}
        key={room.id}
        onClick={(event) => {
          const avatar = directAgent ? (event.target as HTMLElement).closest(".room-icon.agent") : null;
          if (directAgent && avatar instanceof HTMLElement) {
            onOpenAgentProfile(directAgent.id, avatar);
            return;
          }

          onSelectRoom(room.id);
        }}
      >
        <div
          className={`room-icon ${room.kind === "room" ? "room-kind" : room.kind} ${roomIcon ? "custom-room-icon" : ""}`}
          data-agent-id={directAgent?.id}
          style={
            directAgent
              ? ({
                  "--room-agent-color": directAgent.color,
                  // 和 Avatar 组件一致：persona 目录自带 avatar 时走 inline background。
                  // 没图就回退到既有 CSS 主题头像（sarah/kai/alex/main）或 initials。
                  ...(directAgent.avatarUrl
                    ? {
                        backgroundImage: `url("${directAgent.avatarUrl}")`,
                        backgroundSize: "145%",
                        backgroundPosition: "center 18%",
                      }
                    : {}),
                } as CSSProperties)
              : undefined
          }
        >
          {directAgent ? (
            <span className="avatar-initials">{directAgent.initials}</span>
          ) : roomIcon ? (
            <img alt="" className="room-type-icon" src={roomIcon} />
          ) : room.kind === "agent" ? (
            <Bot size={18} />
          ) : (
            <Hash size={18} />
          )}
        </div>
        <span className="room-copy">
          <span className="room-title-line">
            <strong>{room.title}</strong>
            <time>{room.time}</time>
          </span>
          <span className="room-preview">{previewText}</span>
        </span>
        <span className="room-trailing">
          {directAgent ? (
            <span className={`status-dot ${directAgent.presence ?? agentStatuses[directAgent.id] ?? directAgent.status}`} />
          ) : null}
          {room.unread && room.id !== activeRoomId ? <span className="unread">{room.unread}</span> : null}
        </span>
      </button>
    );
  };

  return (
    <aside className="conversation-panel">
      <div className="conversation-top">
        <h1>TelegramAgent</h1>
        <button aria-label="New room">
          <Plus size={18} />
        </button>
      </div>
      <label className="search-box">
        <Search size={16} />
        <input placeholder={sectionCopy.searchPlaceholder} />
      </label>
      <div className="filters" aria-label="Conversation filters">
        {["All", "Unread", "Contacts", "Groups"].map((filter, index) => (
          <button className={index === 0 ? "selected" : ""} key={filter}>
            {filter}
          </button>
        ))}
      </div>
      <div className="conversation-scroll">
        <section className="conversation-section">
          <div className="conversation-section-head">
            <span>{sectionCopy.chatSectionLabel}</span>
            <small>{chatRooms.length}</small>
          </div>
          <div className="room-list">{chatRooms.map(renderRoomRow)}</div>
        </section>
        <section className="conversation-section agent-section">
          <div className="conversation-section-head">
            <span>{sectionCopy.agentSectionLabel}</span>
            <small>{agentRooms.length}</small>
          </div>
          <div className="room-list">{agentRooms.map(renderRoomRow)}</div>
        </section>
      </div>
    </aside>
  );
}

function RoomHeader({
  room,
  agentLookup,
  availableAgents,
  members,
  onToggleRoomMember,
  contextAvailable,
  contextOpen,
  onOpenAgentProfile,
  onToggleContext,
}: {
  room: Room;
  agentLookup: AgentLookup;
  availableAgents: Agent[];
  members: Agent[];
  onToggleRoomMember: (roomId: string, agentId: string) => void;
  contextAvailable: boolean;
  contextOpen: boolean;
  onOpenAgentProfile: OpenAgentProfile;
  onToggleContext: () => void;
}) {
  const [memberMenuOpen, setMemberMenuOpen] = useState(false);
  const memberMenuRef = useRef<HTMLDivElement>(null);
  const directAgent = room.agentId ? getAgentFrom(agentLookup, room.agentId) : undefined;
  const memberIdSet = new Set(members.map((agent) => agent.id));

  useEffect(() => {
    setMemberMenuOpen(false);
  }, [room.id]);

  useEffect(() => {
    if (!memberMenuOpen) {
      return undefined;
    }

    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target;
      if (target instanceof Node && memberMenuRef.current?.contains(target)) {
        return;
      }
      setMemberMenuOpen(false);
    };

    window.addEventListener("pointerdown", handlePointerDown);
    return () => window.removeEventListener("pointerdown", handlePointerDown);
  }, [memberMenuOpen]);

  return (
    <header className="room-header">
      <div className="room-header-main">
        <div className="room-title">
          {directAgent ? (
            <Avatar agent={directAgent} onOpenProfile={onOpenAgentProfile} />
          ) : (
            <div className="room-avatar-cluster" ref={memberMenuRef}>
              <div className="room-avatar-stack" aria-label="Room members">
                {members.slice(0, 4).map((agent) => (
                  <Avatar key={agent.id} agent={agent} onOpenProfile={onOpenAgentProfile} small />
                ))}
              </div>
              <button
                aria-expanded={memberMenuOpen}
                aria-haspopup="listbox"
                aria-label="Add or remove room agents"
                className="room-add-member"
                onClick={() => setMemberMenuOpen((current) => !current)}
                type="button"
              >
                <Plus size={16} />
              </button>
              {memberMenuOpen ? (
                <div className="room-member-menu" role="listbox">
                  {availableAgents.map((agent) => {
                    const selected = memberIdSet.has(agent.id);
                    return (
                      <button
                        aria-selected={selected}
                        className={`room-member-menu-option ${selected ? "selected" : ""}`}
                        key={agent.id}
                        onClick={() => onToggleRoomMember(room.id, agent.id)}
                        role="option"
                        type="button"
                      >
                        <Avatar agent={agent} small />
                        <span>
                          <strong>{agent.name}</strong>
                          <small>{agent.role}</small>
                        </span>
                        {selected ? <Check size={16} /> : <Plus size={15} />}
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
          )}
          <div>
            <h2>{room.title}</h2>
            <p>{directAgent ? `${directAgent.role} · ${directAgent.model} · direct chat` : `Goal: ${room.goal}`}</p>
          </div>
        </div>
        <div className="header-actions">
          <button aria-label="Search room" className="header-icon">
            <Search size={18} />
          </button>
          {contextAvailable ? (
            <button
              aria-label={contextOpen ? "Hide room context" : "Show room context"}
              className={`header-icon context-toggle ${contextOpen ? "selected" : ""}`}
              onClick={onToggleContext}
            >
              <Pin size={18} />
            </button>
          ) : null}
          <button aria-label="More actions" className="header-icon">
            <MoreHorizontal size={19} />
          </button>
        </div>
      </div>
    </header>
  );
}

function DayDivider({ label }: { label: string }) {
  return (
    <div className="day-divider">
      <span>{label}</span>
    </div>
  );
}

function MessageBubble({
  agentLookup,
  message,
  onImagePreview,
  onOpenAgentProfile,
}: {
  agentLookup: AgentLookup;
  message: ChatMessage;
  onImagePreview: (image: ImagePreview) => void;
  onOpenAgentProfile: OpenAgentProfile;
}) {
  if (message.sender === "system") {
    return <div className="system-message">{themeAgentNames(message.body, agentLookup)}</div>;
  }

  const agent = message.agentId ? getAgentFrom(agentLookup, message.agentId) : undefined;
  const media = mediaItemsForMessage(message);
  const displayBody = themeAgentNames(message.body, agentLookup);
  const copyText = displayBody.trim();

  return (
    <article className={`message-row ${message.sender}`}>
      {agent ? <Avatar agent={agent} onOpenProfile={onOpenAgentProfile} /> : <div className="human-avatar">R</div>}
      <div className="message-body">
        <div className="message-meta">
          <strong>{agent ? agent.name : message.author}</strong>
          {agent ? <span>{agent.role}</span> : null}
          <time>{message.time}</time>
        </div>
        <div className="message-content-row">
          <div className="bubble">
            {agent ? (
              <>
                <MarkdownText onImageClick={onImagePreview} skipImages={media.length > 0}>
                  {displayBody}
                </MarkdownText>
                {media.length > 0 ? <GeneratedMediaList media={media} onImagePreview={onImagePreview} /> : null}
              </>
            ) : (
              displayBody
            )}
          </div>
          {copyText ? <MessageCopyButton text={copyText} /> : null}
        </div>
      </div>
    </article>
  );
}

function MessageCopyButton({ text }: { text: string }) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    if (copyState === "idle") {
      return;
    }
    const timer = window.setTimeout(() => setCopyState("idle"), 1200);
    return () => window.clearTimeout(timer);
  }, [copyState]);

  const handleCopy = async () => {
    const ok = await copyTextToClipboard(text);
    setCopyState(ok ? "copied" : "failed");
  };

  const copied = copyState === "copied";

  return (
    <button
      aria-label={copied ? "已复制消息" : "复制消息"}
      className={`message-copy-button ${copied ? "copied" : ""} ${copyState === "failed" ? "failed" : ""}`}
      onClick={handleCopy}
      title={copied ? "已复制" : copyState === "failed" ? "复制失败" : "复制"}
      type="button"
    >
      {copied ? <Check size={13} strokeWidth={2.4} /> : <Copy size={13} strokeWidth={2.1} />}
    </button>
  );
}

function AgentRunBubble({
  agent,
  expression,
  media,
  onImagePreview,
  onOpenAgentProfile,
  text,
  streaming,
  status,
}: {
  agent: Agent;
  expression: AgentExpression;
  media: TimelineRunMedia[];
  onImagePreview: (image: ImagePreview) => void;
  onOpenAgentProfile: OpenAgentProfile;
  text: string;
  streaming: boolean;
  status: string;
}) {
  const hasText = text.trim().length > 0;
  const hasReplyContent = hasText || media.length > 0;
  const activityCue = activityCueTextForExpression(expression);
  const display = agentRunDisplayState({
    expression,
    hasText: hasReplyContent,
    status,
    activityCueLength: activityCue.length,
  });

  return (
    <article className={`message-row agent active-run expression-${expression.phase}`}>
      <div className={`agent-avatar-motion ${display.avatarMotionClass}`}>
        <Avatar agent={agent} onOpenProfile={onOpenAgentProfile} />
      </div>
      <div className="message-body">
        <div className="message-meta">
          <strong>{agent.name}</strong>
          <span>{agent.role}</span>
          <time>{status === "running" ? "now" : "sent"}</time>
        </div>
        {display.showActivityCue || display.showTypingWait ? (
          <div
            className="pre-reply-status"
            key={`${agent.id}-${expression.phase}-${activityCue}`}
            style={
              {
                "--cue-characters": activityCue.length,
                "--cue-duration": `${display.cueDurationMs}ms`,
                "--typing-delay": `${display.typingDelayMs}ms`,
              } as CSSProperties
            }
          >
            {display.showActivityCue ? (
              <div aria-label={activityCue} className={`activity-cue ${expression.tone}`}>
                <span className="mood-pulse" />
                <span className="activity-cue-copy">{activityCue}</span>
                <span className="activity-cue-spark" aria-hidden="true" />
              </div>
            ) : null}
            {display.showTypingWait ? (
              <div aria-label={`${agent.name} is typing`} className="typing-wait">
                <span className="typing-wait-dots" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                </span>
                <span>typing</span>
              </div>
            ) : null}
          </div>
        ) : null}
        {display.showReplyBubble ? (
          <div className="message-content-row">
            <div className="bubble agent-bubble">
              <MarkdownText onImageClick={onImagePreview} skipImages={status === "running"}>
                {text}
              </MarkdownText>
              {status === "running" && media.length > 0 ? <GeneratedMediaList media={media} onImagePreview={onImagePreview} /> : null}
              {streaming ? <span className="typing-caret" /> : null}
            </div>
            {hasText ? <MessageCopyButton text={text.trim()} /> : null}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function GeneratedMediaList({
  media,
  onImagePreview,
}: {
  media: TimelineRunMedia[];
  onImagePreview: (image: ImagePreview) => void;
}) {
  return (
    <div className="generated-media-list" aria-label="Generated media">
      {media.map((item) => (
        <GeneratedMediaCard key={item.idx} media={item} onImagePreview={onImagePreview} />
      ))}
    </div>
  );
}

function GeneratedMediaCard({
  media,
  onImagePreview,
}: {
  media: TimelineRunMedia;
  onImagePreview: (image: ImagePreview) => void;
}) {
  const isAudio = media.kind === "audio";

  if (media.status === "ready" && media.mediaUrl) {
    if (isAudio) {
      return (
        <div className="generated-media-card audio ready" role="group" aria-label={media.alt}>
          <div className="audio-card-head">
            <span className="audio-card-icon" aria-hidden="true">
              <Music2 size={14} strokeWidth={2.2} />
            </span>
            <span className="generated-media-audio-label">{media.alt}</span>
          </div>
          <AudioPlayer src={media.mediaUrl} label={media.alt} className="generated-media-audio" />
        </div>
      );
    }
    return (
      <button
        aria-label={media.alt ? `查看图片：${media.alt}` : "查看图片"}
        className="generated-media-image-button"
        onClick={() => onImagePreview({ src: media.mediaUrl!, alt: media.alt })}
        type="button"
      >
        <img alt={media.alt} className="generated-media-image" src={media.mediaUrl} />
      </button>
    );
  }

  if (media.status === "failed") {
    return (
      <div className={`generated-media-card failed ${isAudio ? "audio" : ""}`} role="status" title={media.reason}>
        {isAudio ? <Music2 size={20} aria-hidden="true" /> : <ImageOff size={20} aria-hidden="true" />}
        <strong>{isAudio ? "音乐生成失败" : "图片生成失败"}</strong>
        <span>这次没有生成出来，可以换个说法再试。</span>
      </div>
    );
  }

  if (isAudio) {
    return (
      <div aria-label={`${media.alt} 生成中`} className="generated-media-card audio generating" role="status">
        <span className="generated-media-notes" aria-hidden="true">
          <span className="note note-1">♪</span>
          <span className="note note-2">♫</span>
          <span className="note note-3">♩</span>
          <span className="note note-4">♬</span>
        </span>
        <div className="generated-media-audio-meta">
          <span className="generated-media-audio-title">{media.alt}</span>
          <span className="generated-media-audio-sub">正在作曲中…</span>
        </div>
      </div>
    );
  }

  return (
    <div aria-label={`${media.alt} 生成中`} className="generated-media-card generating" role="status">
      <span className="generated-media-shimmer" aria-hidden="true" />
      <span>生成图片中</span>
    </div>
  );
}

function TemplateRoomPanel({
  agents,
  template,
  onCreateRoom,
}: {
  agents: Agent[];
  template: TemplateRoom;
  onCreateRoom: (template: TemplateRoom, memberIds: string[]) => Promise<void>;
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [selectedAgentIds, setSelectedAgentIds] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string>();
  const flow = templateFlowCopy(template.runMode);

  useEffect(() => {
    setPickerOpen(false);
    setSelectedAgentIds([]);
    setError(undefined);
    setCreating(false);
  }, [template.id]);

  const toggleAgent = (agentId: string) => {
    setSelectedAgentIds((current) =>
      current.includes(agentId) ? current.filter((id) => id !== agentId) : [...current, agentId],
    );
  };

  const create = async () => {
    if (selectedAgentIds.length === 0) {
      setError("至少选择一个 Agent。");
      return;
    }
    setCreating(true);
    setError(undefined);
    try {
      await onCreateRoom(template, selectedAgentIds);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setCreating(false);
    }
  };

  return (
    <section className="template-room-panel" aria-label={`${template.title} template`}>
      <div className="template-room-scroll">
        <div className="template-room-hero">
          <div className={`template-room-visual ${template.runMode}`}>
            <div className="template-room-mode-icon" aria-hidden="true">
              {template.runMode === "parallel" ? <Users size={30} /> : template.runMode === "loop" ? <RefreshCw size={30} /> : <Sparkles size={30} />}
            </div>
            <div className="template-room-diagram" aria-hidden="true">
              {flow.diagram.map((row, rowIndex) => (
                <div className={`template-room-diagram-row ${row.kind}`} key={`${row.kind}-${rowIndex}`}>
                  {row.items.map((item, index) => (
                    <Fragment key={`${item}-${index}`}>
                      <span>{item}</span>
                      {index < row.items.length - 1 ? <em>{row.connector}</em> : null}
                    </Fragment>
                  ))}
                </div>
              ))}
            </div>
          </div>
          <div className="template-room-copy">
            <span className="template-room-kicker">{flow.kicker}</span>
            <h1>{template.title}</h1>
            <strong>{flow.relation}</strong>
            <p>{template.summary ?? template.goal}</p>
          </div>
        </div>

        <div className="template-room-story">
          {flow.steps.map((step, index) => (
            <div key={step}>
              <CircleDot size={18} aria-hidden="true" />
              <strong>{step}</strong>
              <span>{flow.details[index]}</span>
            </div>
          ))}
        </div>

        <div className="template-room-use-cases">
          <h2>适合这类工作</h2>
          <div>
            {flow.useCases.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </div>

        <div className="template-room-actions">
          <button className="template-room-create" onClick={() => setPickerOpen(true)} type="button">
            <Plus size={18} />
            <span>创建</span>
          </button>
          <p>创建后会跳到 Chats，新 Group 会出现在聊天列表里。</p>
        </div>

        {pickerOpen ? (
          <div className="template-agent-picker" role="dialog" aria-label="选择 Agents">
            <div className="template-agent-picker-head">
              <h2>选择 Agents</h2>
              <button aria-label="Close picker" onClick={() => setPickerOpen(false)} type="button">
                <X size={18} />
              </button>
            </div>
            <div className="template-agent-options">
              {agents.map((agent) => {
                const selected = selectedAgentIds.includes(agent.id);
                return (
                  <button
                    aria-pressed={selected}
                    className={`template-agent-option ${selected ? "selected" : ""}`}
                    key={agent.id}
                    onClick={() => toggleAgent(agent.id)}
                    type="button"
                  >
                    <Avatar agent={agent} small />
                    <span>
                      <strong>{agent.name}</strong>
                      <small>{agent.role}</small>
                    </span>
                    {selected ? <Check size={17} /> : <Plus size={16} />}
                  </button>
                );
              })}
            </div>
            {error ? <p className="template-agent-error">{error}</p> : null}
            <button
              className="template-agent-confirm"
              disabled={creating || selectedAgentIds.length === 0}
              onClick={() => void create()}
              type="button"
            >
              {creating ? <Loader2 size={17} className="spin" /> : <MessageCircle size={17} />}
              <span>{creating ? "创建中…" : `创建 Group${selectedAgentIds.length ? ` (${selectedAgentIds.length})` : ""}`}</span>
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function AgentProfilePanel({
  agent,
  presence,
  onMessage,
  onMoments,
  onAvatarUpdated,
}: {
  agent: Agent | undefined;
  presence: AgentStatus | undefined;
  onMessage: () => void;
  onMoments: () => void;
  onAvatarUpdated: () => void;
}) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [soulEditing, setSoulEditing] = useState(false);
  const [soulText, setSoulText] = useState<string>("");
  const [soulLoading, setSoulLoading] = useState(false);
  const [soulSaving, setSoulSaving] = useState(false);
  const [soulMessage, setSoulMessage] = useState<string | undefined>();
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarMessage, setAvatarMessage] = useState<string | undefined>();
  const [latestPost, setLatestPost] = useState<MomentsPost | null>(null);
  const [latestLoading, setLatestLoading] = useState(false);
  const avatarFileInputRef = useRef<HTMLInputElement>(null);

  // reset edit state when switching agent
  useEffect(() => {
    setSoulEditing(false);
    setSoulText("");
    setSoulMessage(undefined);
    setAvatarMessage(undefined);
  }, [agent?.id]);

  // 拉 agent 的最新一条 Moment（Advanced 上方的小卡片）
  useEffect(() => {
    if (!agent) {
      setLatestPost(null);
      return;
    }
    let cancelled = false;
    setLatestLoading(true);
    fetch(`/api/posts?agentId=${encodeURIComponent(agent.id)}&limit=1`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data: { posts: MomentsPost[] }) => {
        if (cancelled) return;
        setLatestPost(data.posts[0] ?? null);
      })
      .catch(() => {
        if (!cancelled) setLatestPost(null);
      })
      .finally(() => {
        if (!cancelled) setLatestLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [agent?.id]);

  const startEditingSoul = useCallback(async () => {
    if (!agent) return;
    setSoulLoading(true);
    setSoulMessage(undefined);
    try {
      const res = await fetch(`/api/agents/${encodeURIComponent(agent.id)}/soul`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { markdown: string };
      setSoulText(data.markdown);
      setSoulEditing(true);
    } catch (err) {
      setSoulMessage(`读取失败: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSoulLoading(false);
    }
  }, [agent]);

  const saveSoul = useCallback(async () => {
    if (!agent) return;
    setSoulSaving(true);
    setSoulMessage(undefined);
    try {
      const res = await fetch(`/api/agents/${encodeURIComponent(agent.id)}/soul`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ markdown: soulText }),
      });
      if (!res.ok) {
        const t = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status}: ${t.slice(0, 200)}`);
      }
      setSoulMessage("已保存。重启 OpenClaw Gateway 后生效。");
    } catch (err) {
      setSoulMessage(`保存失败: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSoulSaving(false);
    }
  }, [agent, soulText]);

  const handleAvatarFile = useCallback(async (file: File) => {
    if (!agent) return;
    setAvatarUploading(true);
    setAvatarMessage(undefined);
    try {
      if (file.type !== "image/png") throw new Error("只支持 PNG (导出时选 PNG 格式)");
      if (file.size > 5_000_000) throw new Error("图片不能超过 5MB");
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = () => reject(new Error("读取文件失败"));
        reader.readAsDataURL(file);
      });
      const res = await fetch(`/api/agents/${encodeURIComponent(agent.id)}/avatar`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataUrl }),
      });
      if (!res.ok) {
        const t = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status}: ${t.slice(0, 200)}`);
      }
      setAvatarMessage("已上传。刷新页面看新头像。");
      onAvatarUpdated();
    } catch (err) {
      setAvatarMessage(`上传失败: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setAvatarUploading(false);
    }
  }, [agent, onAvatarUpdated]);

  if (!agent) {
    return (
      <section className="agent-profile-panel empty" aria-label="Agent profile">
        <p>从左侧选一个 Agent 查看资料。</p>
      </section>
    );
  }

  const presenceInfo = presenceLabelZh(agent.presence ?? presence);
  const skillsList = agent.enabledSkillIds ?? [];
  const soul = agent.soul;

  return (
    <section className="agent-profile-panel" aria-label={`${agent.name} profile`}>
      <div className="agent-profile-scroll">
        <header className="agent-profile-hero">
          <div className="agent-profile-avatar">
            <Avatar agent={agent} />
          </div>
          <div className="agent-profile-head-text">
            <h1>{agent.name}</h1>
            <p className="agent-profile-handle">@{agent.id}</p>
            <p className="agent-profile-role">{agent.role}</p>
            {agent.profile ? <p className="agent-profile-bio">{agent.profile}</p> : null}
          </div>
        </header>

        <div className="agent-profile-actions">
          <button className="agent-profile-action primary" onClick={onMessage} type="button">
            <MessageCircle size={18} />
            <span>Message</span>
          </button>
          <button className="agent-profile-action" onClick={onMoments} type="button">
            <Camera size={18} />
            <span>Moments</span>
          </button>
        </div>

        {/* SOUL 主信息：四个 sections，从 popover 搬过来的内容 */}
        <div className="agent-profile-sections">
          {soul.personality ? (
            <div className="agent-profile-section">
              <h3>Personality</h3>
              <p>{soul.personality}</p>
            </div>
          ) : null}
          {agent.bestFor.length > 0 ? (
            <div className="agent-profile-section">
              <h3>Best for</h3>
              <ul>
                {agent.bestFor.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          ) : null}
          {soul.workingStyle.length > 0 ? (
            <div className="agent-profile-section">
              <h3>Working style</h3>
              <ul>
                {soul.workingStyle.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          ) : null}
          {soul.boundaries.length > 0 ? (
            <div className="agent-profile-section">
              <h3>Boundaries</h3>
              <ul>
                {soul.boundaries.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          ) : null}
          {agent.capabilities.length > 0 ? (
            <div className="agent-profile-section">
              <h3>Capabilities</h3>
              <div className="agent-profile-chips">
                {agent.capabilities.map((cap) => <span key={cap}>{cap}</span>)}
              </div>
            </div>
          ) : null}
        </div>

        {/* Latest Moment 摘要 — Advanced 上方 */}
        <div className="agent-latest-moment">
          <div className="agent-latest-moment-head">
            <h3>Latest Moment</h3>
            {latestPost ? <time>{formatMomentTime(latestPost.createdAt)}</time> : null}
          </div>
          {latestLoading ? (
            <p className="agent-latest-moment-placeholder">加载中…</p>
          ) : latestPost ? (
            <button
              className="agent-latest-moment-card"
              onClick={onMoments}
              type="button"
              aria-label="跳转到 Moments"
            >
              <p className="agent-latest-moment-body">{stripMomentMarkdown(latestPost.body)}</p>
              {latestPost.mediaPaths.length > 0 ? (
                <span className="agent-latest-moment-media-hint">
                  <Camera size={13} aria-hidden="true" />
                  含图片
                </span>
              ) : null}
            </button>
          ) : (
            <p className="agent-latest-moment-placeholder">
              {agent.name} 还没发过 Moments。
            </p>
          )}
        </div>

        <button
          aria-expanded={advancedOpen}
          className={`agent-advanced-toggle ${advancedOpen ? "open" : ""}`}
          onClick={() => setAdvancedOpen((v) => !v)}
          type="button"
        >
          <span>Advanced</span>
          <ChevronDown size={16} className="agent-advanced-chevron" />
        </button>

        {advancedOpen ? (
          <div className="agent-advanced-body">
            <dl className="agent-advanced-grid">
              <dt>状态</dt>
              <dd>
                <span className={`status-dot ${presenceInfo.key}`} aria-hidden="true" />
                <span>{presenceInfo.label}</span>
              </dd>
              <dt>Color</dt>
              <dd>
                <span className="agent-advanced-swatch" style={{ background: agent.color }} />
                <code>{agent.color}</code>
              </dd>
              <dt>Emoji</dt>
              <dd>{agent.emoji ?? "—"}</dd>
            </dl>

            {/* (1) Avatar — 可编辑 */}
            <div className="agent-advanced-editor">
              <div className="agent-advanced-editor-head">
                <h4>Avatar</h4>
                <button
                  className="agent-advanced-edit-btn"
                  disabled={avatarUploading}
                  onClick={() => avatarFileInputRef.current?.click()}
                  type="button"
                >
                  {avatarUploading ? <Loader2 size={14} className="spin" /> : <Pencil size={14} />}
                  <span>{avatarUploading ? "上传中…" : "Change avatar"}</span>
                </button>
                <input
                  ref={avatarFileInputRef}
                  type="file"
                  accept="image/png"
                  style={{ display: "none" }}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) void handleAvatarFile(file);
                    e.target.value = "";
                  }}
                />
              </div>
              <div className="agent-advanced-avatar-row">
                {agent.avatarUrl ? (
                  <img alt="" className="agent-advanced-avatar-img" src={agent.avatarUrl} />
                ) : (
                  <span className="agent-advanced-hint-inline">使用 initials fallback</span>
                )}
                <span className="agent-advanced-hint-inline">PNG, ≤ 5MB, 1:1 推荐 1024×1024</span>
              </div>
              {avatarMessage ? <p className="agent-advanced-status">{avatarMessage}</p> : null}
            </div>

            {/* (2) SOUL.md — 可编辑 */}
            <div className="agent-advanced-editor">
              <div className="agent-advanced-editor-head">
                <h4>SOUL.md</h4>
                {!soulEditing ? (
                  <button
                    className="agent-advanced-edit-btn"
                    disabled={soulLoading}
                    onClick={() => void startEditingSoul()}
                    type="button"
                  >
                    {soulLoading ? <Loader2 size={14} className="spin" /> : <Pencil size={14} />}
                    <span>{soulLoading ? "加载中…" : "Edit SOUL"}</span>
                  </button>
                ) : null}
              </div>
              {soulEditing ? (
                <>
                  <textarea
                    className="agent-advanced-soul-textarea"
                    value={soulText}
                    onChange={(e) => setSoulText(e.target.value)}
                    disabled={soulSaving}
                    spellCheck={false}
                    rows={18}
                  />
                  <div className="agent-advanced-editor-actions">
                    <button
                      className="agent-advanced-edit-btn primary"
                      disabled={soulSaving}
                      onClick={() => void saveSoul()}
                      type="button"
                    >
                      {soulSaving ? <Loader2 size={14} className="spin" /> : <Check size={14} />}
                      <span>{soulSaving ? "保存中…" : "保存"}</span>
                    </button>
                    <button
                      className="agent-advanced-edit-btn"
                      onClick={() => { setSoulEditing(false); setSoulMessage(undefined); }}
                      type="button"
                    >
                      <span>取消</span>
                    </button>
                  </div>
                </>
              ) : (
                <p className="agent-advanced-hint-inline">写入 personas/{agent.id}/SOUL.md。需要重启 Gateway 后被 agent 感知。</p>
              )}
              {soulMessage ? <p className="agent-advanced-status">{soulMessage}</p> : null}
            </div>

            {/* (3) Skills allowlist — 占位 */}
            <div className="agent-advanced-editor disabled">
              <div className="agent-advanced-editor-head">
                <h4>Skills</h4>
                <span className="agent-advanced-soon">Coming soon</span>
              </div>
              {skillsList.length === 0 ? (
                <span className="agent-advanced-hint-inline">当前 allowlist 为空</span>
              ) : (
                <ul className="agent-advanced-skills">
                  {skillsList.map((s) => <li key={s}><code>{s}</code></li>)}
                </ul>
              )}
              <p className="agent-advanced-hint-inline">UI 编辑待实现。改 <code>~/.openclaw/openclaw.json</code> 的 <code>agents.list[].skills</code> + 重启 Gateway。</p>
            </div>

            {/* (4) Model — 占位 */}
            <div className="agent-advanced-editor disabled">
              <div className="agent-advanced-editor-head">
                <h4>Model</h4>
                <span className="agent-advanced-soon">Coming soon</span>
              </div>
              <p className="agent-advanced-hint-inline">当前：<code>{agent.model}</code></p>
              <p className="agent-advanced-hint-inline">UI 切换待实现。改 <code>~/.openclaw/openclaw.json</code> 的 <code>agents.list[].model.primary</code> + 重启 Gateway。</p>
            </div>

            <details className="agent-advanced-soul">
              <summary>SOUL 模板预览（agentSouls.ts 内）</summary>
              <pre>{agent.soulMarkdown ?? buildAgentSoulMarkdown(agent)}</pre>
            </details>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function EmptyWorkspaceState({ icon, title, message }: { icon: ReactNode; title: string; message: string }) {
  return (
    <section className="empty-workspace-state" role="status">
      <div className="empty-workspace-icon" aria-hidden="true">{icon}</div>
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}

interface MomentsPost {
  id: string;
  agentId: string;
  body: string;
  mediaPaths: string[];
  createdAt: number;
}

function MomentsView({
  agents,
  agentLookup,
  initialFilter,
  onClearFilter,
  onImagePreview,
  onOpenAgentProfile,
}: {
  agents: readonly Agent[];
  agentLookup: AgentLookup;
  initialFilter?: string;
  onClearFilter: () => void;
  onImagePreview: (image: ImagePreview) => void;
  onOpenAgentProfile: OpenAgentProfile;
}) {
  const visibleAgents = useMemo(() => agents.filter((a) => !a.id.startsWith("_") && a.id !== "main"), [agents]);
  const [filterAgentId, setFilterAgentId] = useState<string | undefined>(initialFilter);
  const [posts, setPosts] = useState<MomentsPost[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [composeAgentId, setComposeAgentId] = useState<string>(initialFilter ?? visibleAgents[0]?.id ?? "maruko");
  const [composerOpen, setComposerOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);

  // 默认显示前 10 条（约 2 屏），多余的折叠让用户点开。避免 feed 长了之后渲染慢、滚动卡。
  const INITIAL_VISIBLE = 10;
  const visiblePosts = showAll ? posts : posts.slice(0, INITIAL_VISIBLE);
  const hiddenCount = posts.length - visiblePosts.length;

  // filter 变了重置 showAll（filter 后 post 数变少，无需折叠）
  useEffect(() => {
    setShowAll(false);
  }, [filterAgentId]);

  // 外部传入的 initialFilter 变化（用户从不同 agent profile 跳过来）→ 重置 filter
  useEffect(() => {
    setFilterAgentId(initialFilter);
    if (initialFilter) setComposeAgentId(initialFilter);
  }, [initialFilter]);

  useEffect(() => {
    if (visibleAgents.length === 0) return;
    if (!visibleAgents.some((a) => a.id === composeAgentId)) {
      setComposeAgentId(visibleAgents[0]!.id);
    }
  }, [visibleAgents, composeAgentId]);

  const refreshPosts = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const qs = filterAgentId ? `?agentId=${encodeURIComponent(filterAgentId)}` : "";
      const res = await fetch(`/api/posts${qs}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { posts: MomentsPost[] };
      setPosts(data.posts);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [filterAgentId]);

  useEffect(() => {
    void refreshPosts();
  }, [refreshPosts]);

  const filterAgent = filterAgentId ? agentLookup.get(filterAgentId) : undefined;

  const handleGenerate = useCallback(async () => {
    // filter active 时强制让 filter agent 发；select 已经 disabled，但 composeAgentId state 可能是 stale
    const targetAgentId = filterAgentId ?? composeAgentId;
    setGenerating(true);
    setError(undefined);
    try {
      const res = await fetch(`/api/agents/${encodeURIComponent(targetAgentId)}/posts/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status}: ${body.slice(0, 200)}`);
      }
      setComposerOpen(false);
      await refreshPosts();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setGenerating(false);
    }
  }, [composeAgentId, filterAgentId, refreshPosts]);

  return (
    <section className="moments-main">
      <header className="moments-header">
        <div>
          <h1>Moments</h1>
          <p>
            {filterAgent
              ? `${filterAgent.name} 的动态 · ${posts.length} 条`
              : posts.length > 0 ? `${posts.length} 条动态` : "还没有动态"}
          </p>
        </div>
        <button
          aria-label="发一条 Moment"
          className="moments-compose-trigger"
          onClick={() => setComposerOpen((v) => !v)}
          type="button"
        >
          <Camera size={18} />
        </button>
        {composerOpen ? (
          <div className="moments-composer-popover" role="dialog" aria-label="Compose a moment">
            <label className="moments-composer-label">
              <span>让谁发</span>
              <select
                className="moments-compose-select"
                value={filterAgent ? filterAgent.id : composeAgentId}
                onChange={(event) => setComposeAgentId(event.target.value)}
                disabled={generating || Boolean(filterAgent)}
                aria-disabled={Boolean(filterAgent)}
                title={filterAgent ? "已筛选这个 agent；切换前请先清除筛选" : undefined}
              >
                {visibleAgents.map((agent) => (
                  <option key={agent.id} value={agent.id}>{agent.name}</option>
                ))}
              </select>
              {filterAgent ? (
                <small className="moments-composer-locked-hint">
                  已锁定 — 当前正在筛选 {filterAgent.name}。换人请先「查看全部」。
                </small>
              ) : null}
            </label>
            <button
              className="moments-compose-button"
              disabled={generating || visibleAgents.length === 0}
              onClick={handleGenerate}
              type="button"
            >
              {generating ? <Loader2 size={16} className="spin" /> : <Sparkles size={16} />}
              <span>{generating ? "生成中…（最多约 30s）" : "让 TA 发一条"}</span>
            </button>
          </div>
        ) : null}
      </header>
      {filterAgent ? (
        <div className="moments-filter-banner" role="status">
          <Avatar agent={filterAgent} small />
          <span>
            正在显示 <strong>{filterAgent.name}</strong> <span className="moments-filter-banner-handle">@{filterAgent.id}</span> 的动态
          </span>
          <button
            aria-label="清除筛选，查看全部"
            className="moments-filter-banner-clear"
            onClick={() => {
              setFilterAgentId(undefined);
              // 同步清父组件的 momentsInitialFilter，避免切走再回时 useEffect 再套上
              onClearFilter();
            }}
            type="button"
          >
            <X size={14} />
            <span>查看全部</span>
          </button>
        </div>
      ) : null}
      {error ? <div className="moments-error">{error}</div> : null}
      <div className="moments-body">
        <div className="moments-feed">
          {loading && posts.length === 0 ? (
            <div className="moments-feed-placeholder">加载中…</div>
          ) : posts.length === 0 ? (
            <div className="moments-feed-placeholder">
              {filterAgent
                ? <>{filterAgent.name} 还没发过 Moments。<br />点右上角相机图标让 TA 发一条。</>
                : <>还没人发过 Moments。<br />点右上角相机图标，让某位 Agent 发第一条。</>}
            </div>
          ) : (
            <>
            {visiblePosts.map((post, idx) => {
              const agent = agentLookup.get(post.agentId);
              if (!agent) return null;
              return (
                <article className={`moment-card ${idx === 0 ? "first" : ""}`} key={post.id}>
                  <Avatar agent={agent} onOpenProfile={onOpenAgentProfile} />
                  <div className="moment-card-content">
                    <div className="moment-card-head">
                      <strong className="moment-card-name">{agent.name}</strong>
                      <span className="moment-card-handle">@{agent.id}</span>
                      <span className="moment-card-dot" aria-hidden="true">·</span>
                      <time>{formatMomentTime(post.createdAt)}</time>
                    </div>
                    <div className="moment-card-body">
                      <MarkdownText onImageClick={onImagePreview}>{post.body}</MarkdownText>
                    </div>
                  </div>
                </article>
              );
            })}
            {hiddenCount > 0 ? (
              <button
                className="moments-expand-more"
                onClick={() => setShowAll(true)}
                type="button"
              >
                <ChevronDown size={16} />
                <span>展开剩余 {hiddenCount} 条</span>
              </button>
            ) : null}
            </>
          )}
        </div>
        <aside className="moments-aside" aria-label="Featured agents">
          <div className="moments-widget">
            <h3>Who to follow</h3>
            <ul>
              {visibleAgents.map((agent) => (
                <li key={agent.id}>
                  <Avatar agent={agent} onOpenProfile={onOpenAgentProfile} />
                  <div>
                    <strong>{agent.name}</strong>
                    <span>@{agent.id}</span>
                    <small>{agent.role}</small>
                  </div>
                </li>
              ))}
            </ul>
          </div>
          <div className="moments-widget">
            <h3>Trending</h3>
            <ul className="moments-trending">
              <li>
                <small>Anime · 实时</small>
                <strong>《葬送的芙莉莲》</strong>
                <span>小丸子刚 awsl 过</span>
              </li>
              <li>
                <small>Writing · 今日</small>
                <strong>砍废话的标准</strong>
                <span>Sarah 在 Moments 里聊过</span>
              </li>
              <li>
                <small>Engineering · 本周</small>
                <strong>tsx watch 时序坑</strong>
                <span>Kai 实测踩过</span>
              </li>
            </ul>
          </div>
          <p className="moments-aside-foot">
            Telegram Agent · v0.1 MVP
          </p>
        </aside>
      </div>
    </section>
  );
}

function stripMomentMarkdown(body: string): string {
  // 摘要用：去掉 markdown 图片语法、加粗符号；超过 140 字符截断
  const text = body
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\n{2,}/g, "  ")
    .trim();
  return text.length > 140 ? `${text.slice(0, 140)}…` : text;
}

function formatMomentTime(ts: number): string {
  const diffMs = Date.now() - ts;
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return "刚刚";
  if (min < 60) return `${min} 分钟前`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} 小时前`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day} 天前`;
  return new Date(ts).toLocaleDateString("zh-CN");
}

function ImagePreviewModal({ image, onClose }: { image: ImagePreview; onClose: () => void }) {
  return createPortal(
    <div className="image-preview-backdrop" onClick={onClose} role="presentation">
      <section
        aria-label={image.alt ? `图片预览：${image.alt}` : "图片预览"}
        aria-modal="true"
        className="image-preview-modal"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <button autoFocus aria-label="Close image preview" className="image-preview-close" onClick={onClose} type="button">
          <X size={20} />
        </button>
        <img alt={image.alt} className="image-preview-image" src={image.src} />
        {image.alt ? <p className="image-preview-caption">{image.alt}</p> : null}
      </section>
    </div>,
    document.body,
  );
}

function ReviewModePanel({ artifacts, room }: { artifacts: ArtifactRecord[]; room: Room }) {
  const finishedCount = artifacts.filter((artifact) => ["success", "selected"].includes(artifact.status)).length;

  return (
    <aside className="review-banner">
      <div>
        <strong>Saved notes</strong>
        <span>{room.title}</span>
      </div>
      <ul>
        <li>{artifacts.length} notes linked to this chat.</li>
        <li>{finishedCount} notes are ready to read.</li>
        <li>Selected note details stay pinned in the right panel.</li>
      </ul>
    </aside>
  );
}

function Composer({
  agents,
  agentLookup,
  draft,
  mode,
  room,
  setDraft,
  onSend,
}: {
  agents: Agent[];
  agentLookup: AgentLookup;
  draft: string;
  mode: Mode;
  room: Room;
  setDraft: (value: string) => void;
  onSend: () => void;
}) {
  const [mentionMenuOpen, setMentionMenuOpen] = useState(false);
  const directAgent = room.agentId ? getAgentFrom(agentLookup, room.agentId) : undefined;
  const novaName = getAgentFrom(agentLookup, "main").name;
  const mentionCandidates = mentionCandidateIdsForRoom(room, agents.map((agent) => agent.id))
    .map((agentId) => getAgentFrom(agentLookup, agentId));
  const mentionHint = mentionCandidates.map((agent) => `@${agent.name}`).join(", ");
  const placeholder =
    directAgent
      ? `Message ${directAgent.name}`
      : mode === "review"
      ? `Leave a review note or mention @${getAgentFrom(agentLookup, "alex").name}.`
        : mode === "convene"
        ? `Add context for ${novaName} before convening again.`
        : `Message the room or mention ${mentionHint}.`;

  useEffect(() => {
    setMentionMenuOpen(false);
  }, [room.id]);

  useEffect(() => {
    if (draft.trim().length === 0) {
      setMentionMenuOpen(false);
    }
  }, [draft]);

  const insertMentionMarker = () => {
    setDraft(draftWithMentionMarker(draft));
    setMentionMenuOpen(true);
  };

  const selectMention = (agent: Agent) => {
    setDraft(draftWithSelectedMention(draft, agent.name));
    setMentionMenuOpen(false);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Escape" && mentionMenuOpen) {
      event.preventDefault();
      setMentionMenuOpen(false);
      return;
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  const handleSendButtonKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSend();
    }
  };

  return (
    <footer className="composer-wrap">
      <div className="composer">
        <button aria-label="Attach file">
          <Paperclip size={19} />
        </button>
        <button
          aria-expanded={mentionMenuOpen}
          aria-haspopup="listbox"
          aria-label="Mention agent"
          onClick={insertMentionMarker}
          type="button"
        >
          <AtSign size={19} />
        </button>
        {mentionMenuOpen ? (
          <div aria-label="Room agents" className="mention-menu" role="listbox">
            {mentionCandidates.map((agent) => (
              <button
                aria-label={`Mention ${agent.name}`}
                className="mention-option"
                key={agent.id}
                onClick={() => selectMention(agent)}
                role="option"
                type="button"
              >
                <Avatar agent={agent} small />
                <span>
                  <strong>{agent.name}</strong>
                  <small>{agent.role}</small>
                </span>
              </button>
            ))}
          </div>
        ) : null}
        <textarea
          aria-label="Message composer"
          onChange={(event) => {
            setDraft(event.target.value);
            if (event.target.value.endsWith("@")) {
              setMentionMenuOpen(true);
            }
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={1}
          value={draft}
        />
        <button aria-label="Emoji">
          <Smile size={19} />
        </button>
        <button aria-label="Voice message">
          <Mic size={19} />
        </button>
        <button
          aria-label="Send message"
          className="send"
          disabled={draft.trim().length === 0}
          onClick={(event) => event.preventDefault()}
          onKeyDown={handleSendButtonKeyDown}
          onMouseDown={(event) => {
            event.preventDefault();
            onSend();
          }}
          type="button"
        >
          <Send size={18} />
        </button>
      </div>
    </footer>
  );
}

function ContextPanel({
  agentLookup,
  room,
  activeExpression,
  runStatus,
  activeRunTitle,
  artifacts,
  approvedAgentMemory,
  approvedRoomMemory,
  memoryProposals,
  selectedArtifactId,
  onApproveMemoryProposal,
  onRejectMemoryProposal,
  onSelectArtifact,
  onClose,
}: {
  agentLookup: AgentLookup;
  room: Room;
  activeExpression: AgentExpression;
  runStatus: string;
  activeRunTitle?: string;
  artifacts: ArtifactRecord[];
  approvedAgentMemory?: string;
  approvedRoomMemory?: string;
  memoryProposals: MemoryProposalRecord[];
  selectedArtifactId?: string;
  onApproveMemoryProposal: (proposalId: string) => void;
  onRejectMemoryProposal: (proposalId: string) => void;
  onSelectArtifact: (artifactId: string) => void;
  onClose: () => void;
}) {
  const isActiveRun = runStatus === "running" || runStatus === "awaiting_input" || runStatus === "stalled";
  const replyStatusLabel =
    runStatus === "running"
      ? "Preparing reply"
      : runStatus === "finished"
        ? "Reply sent"
        : runStatus === "awaiting_input"
          ? "Waiting for input"
          : runStatus === "error" || runStatus === "stalled"
            ? "Reply paused"
            : "No active reply";
  const focusSections = contextPanelFocusSections({
    artifactCount: artifacts.length,
    hasApprovedMemory: Boolean(approvedAgentMemory || approvedRoomMemory),
    memoryProposalCount: memoryProposals.length,
    runStatus,
  });
  const shouldShow = (section: (typeof focusSections)[number]) => focusSections.includes(section);
  const focusedArtifacts = artifacts.slice(0, 3);

  return (
    <aside className="context-panel">
      <div className="context-header">
        <div>
          <span className="panel-label">Context queue</span>
          <h2>{room.title}</h2>
        </div>
        <button aria-label="Collapse context" onClick={onClose}>
          <ChevronDown size={18} />
        </button>
      </div>

      {shouldShow("memoryApproval") ? (
        <MemoryApprovalPanel
          proposals={memoryProposals}
          onApprove={onApproveMemoryProposal}
          onReject={onRejectMemoryProposal}
        />
      ) : null}

      {shouldShow("replyStatus") ? (
        <section className="context-section">
          <div className="section-title">
            <span>Reply status</span>
            <CircleDot size={16} />
          </div>
          <div className="run-card">
            <div className="run-card-top">
              <span className={`pulse-dot ${isActiveRun ? runStatus : "finished"}`} />
              <strong>{replyStatusLabel}</strong>
            </div>
            <p>{activeRunTitle ? activityCueTextForExpression(activeExpression) : "No one is active here."}</p>
          </div>
        </section>
      ) : null}

      {shouldShow("approvedContext") ? (
        <ApprovedContextPanel
          agentLookup={agentLookup}
          agentMemory={approvedAgentMemory}
          roomMemory={approvedRoomMemory}
        />
      ) : null}

      {shouldShow("notes") ? (
        <section className="context-section artifacts">
          <div className="section-title">
            <span>Notes</span>
            <FileText size={16} />
          </div>
          {focusedArtifacts.map((artifact) => (
            <ArtifactCard
              artifact={artifact}
              agentLookup={agentLookup}
              key={artifact.id}
              onSelect={() => onSelectArtifact(artifact.id)}
              selected={artifact.id === selectedArtifactId}
            />
          ))}
          {artifacts.length > focusedArtifacts.length ? (
            <p className="context-muted-line">+{artifacts.length - focusedArtifacts.length} older notes hidden</p>
          ) : null}
        </section>
      ) : null}

      {focusSections.length === 0 ? (
        <section className="context-empty-state">
          <Check size={17} />
          <strong>Clear</strong>
          <p>No pending memory, active reply, approved context, or notes.</p>
        </section>
      ) : null}
    </aside>
  );
}

function ApprovedContextPanel({
  agentLookup,
  agentMemory,
  roomMemory,
}: {
  agentLookup: AgentLookup;
  agentMemory?: string;
  roomMemory?: string;
}) {
  return (
    <section className="context-section approved-context-section">
      <div className="section-title">
        <span>Approved context</span>
        <Pin size={16} />
      </div>
      <div className="approved-context-list">
        {agentMemory ? (
          <div className="approved-context-block">
            <span>Agent memory</span>
            <p>{themeAgentNames(agentMemory, agentLookup)}</p>
          </div>
        ) : null}
        {roomMemory ? (
          <div className="approved-context-block">
            <span>Room summary</span>
            <p>{themeAgentNames(roomMemory, agentLookup)}</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}

// presence 内部 enum → 用户看得懂的中文短词
function presenceLabelZh(p: string | undefined): { label: string; key: "online" | "idle" | "offline" } {
  switch (p) {
    case "online":
    case "observing":
    case "thinking":
      return { label: "在线", key: "online" };
    case "idle":
      return { label: "暂离", key: "idle" };
    case "offline":
      return { label: "离线", key: "offline" };
    default:
      return { label: "在线", key: "online" };
  }
}

function AgentProfilePopover({
  agent,
  onClose,
  onMessage,
  onMoments,
  position,
  presence,
}: {
  agent: Agent;
  copied: boolean;
  onClose: () => void;
  onCopySoul: (agent: Agent) => void;
  onMessage: (agentId: string) => void;
  onMoments: () => void;
  position: AgentProfileAnchor;
  presence: string;
}) {
  // 精简版：头像 + name + handle + role + 一行 bio + 中文状态 + Message + Moments + Close。
  const presenceInfo = presenceLabelZh(presence);
  return (
    <section
      aria-label={`${agent.name} profile`}
      className="agent-profile-popover compact"
      role="dialog"
      style={{ top: position.top, left: position.left }}
    >
      <header className="agent-card-head">
        <Avatar agent={agent} />
        <div>
          <h3>{agent.name}</h3>
          <p>
            <span className="agent-card-handle-text">@{agent.id}</span>
            <span aria-hidden="true"> · </span>
            {agent.role}
          </p>
        </div>
        <span className={`status-chip ${presenceInfo.key}`}>
          <span className={`status-dot ${presenceInfo.key}`} aria-hidden="true" />
          {presenceInfo.label}
        </span>
        <button aria-label="Close profile" className="agent-card-close" onClick={onClose}>
          <X size={16} />
        </button>
      </header>

      {agent.profile ? <p className="agent-card-summary">{agent.profile}</p> : null}

      <footer className="agent-card-actions compact">
        <button onClick={() => onMessage(agent.id)} type="button">
          <MessageCircle size={18} />
          <span>Message</span>
        </button>
        <button onClick={onMoments} type="button">
          <Camera size={18} />
          <span>Moments</span>
        </button>
      </footer>
    </section>
  );
}

function ProfileField({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div className="profile-field">
      <span>{label}</span>
      <div>{children}</div>
    </div>
  );
}

function MemoryApprovalPanel({
  proposals,
  onApprove,
  onReject,
}: {
  proposals: MemoryProposalRecord[];
  onApprove: (proposalId: string) => void;
  onReject: (proposalId: string) => void;
}) {
  return (
    <section className="context-section memory-approval-section">
      <div className="section-title">
        <span>Pending memory</span>
        <FileText size={16} />
      </div>

      <div className="memory-proposal-list">
        {proposals.map((proposal) => (
          <article className="memory-proposal" key={proposal.id}>
            <div className="memory-proposal-head">
              <strong>{memoryProposalCategoryLabel(proposal.category)}</strong>
              <span>{Math.round(proposal.confidence * 100)}%</span>
            </div>
            <p>{proposal.text}</p>
            {proposal.evidence ? <small>{proposal.evidence}</small> : null}
            <div className="memory-proposal-actions">
              <button onClick={() => onApprove(proposal.id)} type="button">
                <Check size={15} />
                <span>Approve</span>
              </button>
              <button onClick={() => onReject(proposal.id)} type="button">
                <X size={15} />
                <span>Reject</span>
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function memoryProposalCategoryLabel(category: MemoryProposalRecord["category"]): string {
  return {
    facts: "Fact",
    preferences: "Preference",
    decisions: "Decision",
    rejected: "Rejected",
  }[category];
}

function ArtifactCard({
  agentLookup,
  artifact,
  selected,
  onSelect,
}: {
  agentLookup: AgentLookup;
  artifact: ArtifactRecord;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button className={`artifact-card ${selected ? "selected" : ""}`} onClick={onSelect}>
      <div className="artifact-icon">
        {artifact.kind === "code" ? <FileCode2 size={17} /> : <FileText size={17} />}
      </div>
      <div>
        <div className="artifact-title">
          <strong>{artifact.title}</strong>
          <span>{artifact.status}</span>
        </div>
        <p>{artifact.content || "Still writing this note."}</p>
        <small>
          {themeAgentNames(artifact.source, agentLookup)} · {artifact.version} · {artifact.kind}
        </small>
      </div>
    </button>
  );
}

function Avatar({
  agent,
  onOpenProfile,
  small = false,
}: {
  agent: Agent;
  onOpenProfile?: OpenAgentProfile;
  small?: boolean;
}) {
  const className = `avatar ${small ? "small" : ""} ${onOpenProfile ? "avatar-button" : ""}`;
  // agent.avatarUrl 来自 personas/<id>/avatar.png；inline 优先级 > 主题 CSS rule。
  // 没图就走既有 CSS（sarah/kai/alex/main 各主题里硬编码的 background-image）或纯 initials。
  const style = {
    "--agent-color": agent.color,
    ...(agent.avatarUrl
      ? {
          backgroundImage: `url("${agent.avatarUrl}")`,
          backgroundSize: "145%",
          backgroundPosition: "center 18%",
        }
      : {}),
  } as CSSProperties;
  const content = <span className="avatar-initials">{agent.initials}</span>;

  if (!onOpenProfile) {
    return (
      <div aria-label={`${agent.name} avatar`} className={className} data-agent-id={agent.id} style={style}>
        {content}
      </div>
    );
  }

  return (
    <button
      aria-label={`Open ${agent.name} profile`}
      className={className}
      data-agent-id={agent.id}
      onClick={(event) => {
        event.stopPropagation();
        onOpenProfile(agent.id, event.currentTarget);
      }}
      style={style}
      type="button"
    >
      {content}
    </button>
  );
}

async function streamRemoteAgentRunEvents({
  endpoint,
  payload,
  onEvent,
  onError,
}: {
  endpoint: string;
  payload: unknown;
  onEvent: (event: AgentUXEvent) => void;
  onError: (error: unknown) => void;
}) {
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Agent run request failed with HTTP ${response.status}`);
    }
    if (!response.body) {
      throw new Error("Agent run response did not include a stream body.");
    }

    const reader = response.body.getReader();
    const textDecoder = new TextDecoder();
    const sseDecoder = new AgentUXSSEDecoder();

    while (true) {
      const chunk = await reader.read();
      if (chunk.done) {
        break;
      }
      for (const record of sseDecoder.decode(textDecoder.decode(chunk.value, { stream: true }))) {
        if (record.kind === "event") {
          onEvent(record.event);
        }
        if (record.kind === "error") {
          throw record.error;
        }
      }
    }

    for (const record of sseDecoder.decode(textDecoder.decode())) {
      if (record.kind === "event") {
        onEvent(record.event);
      }
      if (record.kind === "error") {
        throw record.error;
      }
    }
    for (const record of sseDecoder.flush()) {
      if (record.kind === "event") {
        onEvent(record.event);
      }
      if (record.kind === "error") {
        throw record.error;
      }
    }
  } catch (error) {
    onError(error);
  }
}

function createClientRunErrorEvent(
  descriptor: Pick<RunDescriptor, "runId" | "roomId">,
  error: unknown,
): AgentUXEvent {
  return agentUXEventBuilders.runError(
    {
      id: `${descriptor.runId}-client-error`,
      runId: descriptor.runId,
      threadId: `room-${descriptor.roomId}`,
      seq: 10_001,
      ts: Date.now(),
      visibility: "user",
    },
    {
      code: "AGENT_RUN_STREAM_ERROR",
      category: "network",
      retryable: true,
      userMessage: "The reply could not reach the local API.",
      developerMessage: error instanceof Error ? error.message : String(error),
    },
  );
}

function createConveneRunScript({
  runId,
  roomId,
  prompt,
  selectedAgentIds,
  agentLookup,
}: {
  runId: string;
  roomId: string;
  prompt: string;
  selectedAgentIds: string[];
  agentLookup: AgentLookup;
}): FakeRunScript {
  const selectedNames = selectedAgentIds.map((agentId) => getAgentFrom(agentLookup, agentId).name).join(" + ");
  const hostName = getAgentFrom(agentLookup, "main").name;

  return createFakeRunScript({
    runId,
    roomId,
    trigger: "convene",
    title: selectedNames ? `${hostName} brings in ${selectedNames}` : `${hostName} holds the room`,
    prompt,
    agentIds: ["main", ...selectedAgentIds],
    conveneSelection: selectedAgentIds,
    agentLookup,
  });
}

function createFakeRunScript({
  runId,
  roomId,
  trigger,
  title,
  prompt,
  agentIds,
  conveneSelection,
  agentLookup,
}: {
  runId: string;
  roomId: string;
  trigger: AgentRunTrigger;
  title: string;
  prompt: string;
  agentIds: string[];
  conveneSelection?: string[];
  agentLookup: AgentLookup;
}): FakeRunScript {
  const now = Date.now();
  const threadId = `room-${roomId}`;
  const events: TimedAgentUXEvent[] = [];
  let seq = 1;
  let offset = 0;

  const push = (
    wait: number,
    eventName: string,
    build: (meta: ReturnType<typeof buildEventMeta>) => AgentUXEvent,
    messageId?: string,
  ) => {
    offset += wait;
    const meta = buildEventMeta({
      eventName,
      messageId,
      now,
      offset,
      runId,
      seq: seq++,
      threadId,
    });
    events.push({ event: build(meta), delay: offset });
  };

  push(0, "run-started", (meta) =>
    agentUXEventBuilders.runStarted(meta, {
      title,
      metadata: { roomId, agentIds, trigger },
    }),
  );
  push(160, "reasoning", (meta) =>
    agentUXEventBuilders.reasoningStatus(meta, {
      reasoningId: `${runId}-routing`,
      status: "planning",
      label:
        trigger === "convene"
          ? "Main is choosing who should answer"
          : trigger === "direct"
            ? "Thinking through the reply"
            : "Thinking through the mention",
      metadata: { roomId, trigger },
    }),
  );

  agentIds.forEach((agentId, index) => {
    const agent = getAgentFrom(agentLookup, agentId);
    const textId = `${runId}-${agentId}-text`;
    const messageId = `msg-${runId}-${agentId}`;
    const chunks = trigger === "convene" && agentId === "main"
      ? novaConveneChunks(conveneSelection ?? [], agentLookup)
      : agentResponseChunks(agentId, prompt, trigger, agentLookup);
    const artifactTitle = artifactTitleFor(agentId, trigger);
    const artifactId = `artifact-${runId}-${agentId}`;

    push(index === 0 ? 260 : 520, `text-started-${agentId}`, (meta) =>
      agentUXEventBuilders.textStarted(meta, {
        textId,
        role: "assistant",
        format: "markdown",
        metadata: { agentId, roomId, trigger },
      }),
      messageId,
    );

    chunks.forEach((chunk, chunkIndex) => {
      push(chunkIndex === 0 ? 420 : 540, `text-delta-${agentId}-${chunkIndex}`, (meta) =>
        agentUXEventBuilders.textDelta(meta, {
          textId,
          delta: chunk,
          metadata: { agentId, roomId, trigger },
        }),
        messageId,
      );
    });

    push(260, `artifact-created-${agentId}`, (meta) =>
      agentUXEventBuilders.artifactCreated(meta, {
        artifactId,
        kind: agentId === "kai" ? "code" : "custom",
        title: artifactTitle,
        mimeType: "text/markdown",
        metadata: {
          agentId,
          roomId,
          sourceAgent: agent.name,
          sourceAgentId: agentId,
          trigger,
          version: "v1",
        },
      }),
    );
    push(360, `artifact-delta-${agentId}`, (meta) =>
      agentUXEventBuilders.artifactDelta(meta, {
        artifactId,
        format: "text",
        delta: artifactContentFor(agentId, trigger, agentLookup),
        metadata: {
          agentId,
          roomId,
          sourceAgent: agent.name,
          sourceAgentId: agentId,
          trigger,
          version: "v1",
        },
      }),
    );
    push(360, `artifact-finished-${agentId}`, (meta) =>
      agentUXEventBuilders.artifactFinished(meta, {
        artifactId,
        status: "success",
        metadata: {
          agentId,
          roomId,
          sourceAgent: agent.name,
          sourceAgentId: agentId,
          trigger,
          version: "v1",
        },
      }),
    );
    push(220, `text-finished-${agentId}`, (meta) =>
      agentUXEventBuilders.textFinished(meta, {
        textId,
        metadata: { agentId, roomId, trigger },
      }),
      messageId,
    );
  });

  push(260, "reasoning-done", (meta) =>
    agentUXEventBuilders.reasoningStatus(meta, {
      reasoningId: `${runId}-routing`,
      status: "done",
      label:
        trigger === "convene"
          ? "Choice made"
          : trigger === "direct"
            ? "Reply sent"
            : "Mention answered",
      metadata: { roomId, trigger },
    }),
  );
  push(220, "run-finished", (meta) =>
    agentUXEventBuilders.runFinished(meta, {
      usage: { inputTokens: 320, outputTokens: 180 * agentIds.length, totalTokens: 320 + 180 * agentIds.length },
      assessment: {
        outcome: "success",
        summary:
          trigger === "convene"
            ? `${getAgentFrom(agentLookup, "main").name} brought the right people into the thread.`
            : trigger === "direct"
              ? "The direct chat reply finished."
              : "The mentioned reply finished.",
      },
      metadata: { roomId, trigger },
    }),
  );

  return {
    runId,
    roomId,
    title,
    trigger,
    agentIds,
    events,
  };
}

function buildEventMeta({
  eventName,
  messageId,
  now,
  offset,
  runId,
  seq,
  threadId,
}: {
  eventName: string;
  messageId?: string;
  now: number;
  offset: number;
  runId: string;
  seq: number;
  threadId: string;
}) {
  const meta = {
    id: `${runId}-${seq}-${eventName}`,
    runId,
    threadId,
    seq,
    ts: now + offset,
    visibility: "user" as const,
  };

  return messageId ? { ...meta, messageId } : meta;
}

function nextRunId(kind: string, ref: MutableRefObject<number>): string {
  const index = ref.current;
  ref.current += 1;
  return `run-${kind}-${index}-${Date.now()}`;
}

function getAgent(agentId: string): Agent {
  return agentById.get(agentId) ?? agents[0];
}

function getAgentFrom(agentLookup: AgentLookup, agentId: string): Agent {
  return agentLookup.get(agentId) ?? getAgent(agentId);
}

function getOptionalAgentFrom(agentLookup: AgentLookup, agentId: string): Agent | undefined {
  return agentLookup.get(agentId) ?? agentById.get(agentId);
}

function agentsForTheme(theme: AppTheme, sourceAgents: readonly Agent[] = agents): Agent[] {
  return sourceAgents.map((agent) => {
    const persona = theme.agentPersonas[agent.id];
    return persona ? { ...agent, ...persona } : agent;
  });
}

interface ServerAgentPayload {
  id: string;
  name: string;
  role: string;
  profile: string;
  model: string;
  hidden: boolean;
  emoji?: string | null;
  color: string;
  initials: string;
  presence?: AgentPresence;
  avatarUrl?: string;
  bestFor?: string[];
}

interface ServerRoomPayload {
  id: string;
  kind: "agent" | "room";
  title: string;
  agentId: string | null;
  memberIds: string[];
  lastMessage: string | null;
  lastActivityAt: number | null;
}

interface ServerMessagePayload {
  id: string;
  roomId: string;
  sender: "human" | "agent" | "system";
  agentId: string | null;
  body: string;
  createdAt: number;
  mediaPaths?: string[];
}

function formatMessageTime(ts: number): string {
  const d = new Date(ts);
  const now = new Date();
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  return sameDay
    ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString([], { month: "short", day: "numeric" });
}

function serverMessageToChatMessage(s: ServerMessagePayload): ChatMessage {
  const author =
    s.sender === "human"
      ? "Ricky"
      : s.sender === "agent"
        ? s.agentId ?? "Agent"
        : "System";
  return {
    id: s.id,
    sender: s.sender,
    agentId: s.agentId ?? undefined,
    author,
    time: formatMessageTime(s.createdAt),
    body: s.body,
    createdAt: s.createdAt,
    mediaPaths: s.mediaPaths ?? [],
  };
}

function markdownMediaAltForIndex(body: string, idx: number): string | undefined {
  const mediaLinkRe = /!\[([^\]]*)\]\(\/api\/messages\/[a-z0-9_-]+\/media\/(\d+)(?:\.[a-z0-9]+)?\)/gi;
  for (const match of body.matchAll(mediaLinkRe)) {
    if (Number(match[2]) === idx) {
      return match[1]?.replace(/\\([\]\\])/g, "$1") || undefined;
    }
  }
  return undefined;
}

function mediaItemsForMessage(message: ChatMessage): TimelineRunMedia[] {
  if (!message.mediaPaths || message.mediaPaths.length === 0) {
    return [];
  }

  const prefix = `${message.id}-`;
  return message.mediaPaths
    .map((filename, order): TimelineRunMedia | undefined => {
      if (!filename.startsWith(prefix)) return undefined;
      const suffix = filename.slice(prefix.length);
      const match = suffix.match(/^(\d+)\.([a-z0-9]+)$/i);
      if (!match) return undefined;
      const idx = Number(match[1]);
      const ext = match[2].toLowerCase();
      const kind: "image" | "audio" | undefined =
        /^(mp3|wav|flac|ogg|m4a)$/.test(ext)
          ? "audio"
          : /^(png|jpg|jpeg|webp)$/.test(ext)
            ? "image"
            : undefined;
      if (!kind) return undefined;
      return {
        idx: Number.isFinite(idx) ? idx : order,
        alt: markdownMediaAltForIndex(message.body, idx) ?? (kind === "audio" ? "音频" : "图"),
        status: "ready",
        kind,
        mediaUrl: `/api/messages/${message.id}/media/${idx}.${ext}`,
      };
    })
    .filter((item): item is TimelineRunMedia => Boolean(item))
    .sort((left, right) => left.idx - right.idx);
}

function mergeServerAgents(server: readonly ServerAgentPayload[], fallback: readonly Agent[]): Agent[] {
  const fallbackById = new Map(fallback.map((a) => [a.id, a]));
  return server
    .filter((s) => !s.hidden)
    .map((s): Agent => {
      const base = fallbackById.get(s.id);
      const emoji = s.emoji ?? undefined;
      const presence = s.presence;
      if (base) {
        return {
          ...base,
          name: s.name,
          role: s.role,
          profile: s.profile,
          model: s.model,
          color: s.color,
          initials: s.initials,
          emoji,
          presence,
          avatarUrl: s.avatarUrl,
          bestFor: s.bestFor ?? [],
        };
      }
      return {
        id: s.id,
        name: s.name,
        role: s.role,
        profile: s.profile,
        model: s.model,
        color: s.color,
        initials: s.initials,
        emoji,
        presence,
        avatarUrl: s.avatarUrl,
        soul: { identity: "", personality: "", bestFor: [], workingStyle: [], boundaries: [] },
        capabilities: [],
        bestFor: s.bestFor ?? [],
        enabledSkillIds: [],
        skillPolicy: "ask_first",
        permissions: defaultAgentPermissions,
        status: "observing",
      };
    });
}

function serverRoomsToCreatedRooms(server: readonly ServerRoomPayload[], baseRooms: readonly Room[]): Room[] {
  const baseIds = new Set(baseRooms.map((room) => room.id));
  return server
    .filter((room) => room.kind === "room" && !baseIds.has(room.id))
    .map((room): Room => {
      const mode = roomModeFromCreatedRoomId(room.id);
      const template = templateRoomForMode(mode, baseRooms);
      return {
        id: room.id,
        title: room.title,
        goal: template?.goal ?? "自定义群聊",
        summary: template?.summary,
        lastMessage: room.lastMessage ?? "等待你发起任务。",
        lastActivityAt: room.lastActivityAt ?? undefined,
        time: "—",
        kind: "room",
        memberIds: room.memberIds,
        runMode: mode,
      };
    });
}

function directRoomsForAgents(
  agents: readonly Agent[],
  existingRooms: readonly Room[],
  serverRooms: readonly ServerRoomPayload[],
): Room[] {
  const existingIds = new Set(existingRooms.map((room) => room.id));
  const existingAgentIds = new Set(existingRooms.map((room) => room.agentId).filter(Boolean));
  const serverByAgentId = new Map(
    serverRooms
      .filter((room) => room.kind === "agent" && room.agentId)
      .map((room) => [room.agentId!, room]),
  );

  return agents
    .filter((agent) => !existingIds.has(agent.id) && !existingAgentIds.has(agent.id))
    .map((agent): Room => {
      const serverRoom = serverByAgentId.get(agent.id);
      return {
        id: serverRoom?.id ?? agent.id,
        title: agent.name,
        goal: `Direct ${agent.role} chat`,
        summary: `Direct chat with ${agent.name}.`,
        lastMessage: serverRoom?.lastMessage ?? "还没有对话。",
        lastActivityAt: serverRoom?.lastActivityAt ?? undefined,
        time: "—",
        kind: "agent",
        agentId: agent.id,
        memberIds: [agent.id],
      };
    });
}

function recentDirectRoomIds(
  serverRooms: readonly ServerRoomPayload[],
  messagesByRoom: Readonly<Record<string, readonly ChatMessage[]>>,
): Set<string> {
  const ids = new Set<string>();
  for (const room of serverRooms) {
    if (room.kind === "agent" && room.lastMessage) ids.add(room.id);
  }
  for (const [roomId, messages] of Object.entries(messagesByRoom)) {
    if (messages.length > 0) ids.add(roomId);
  }
  return ids;
}

function roomModeFromCreatedRoomId(id: string): Exclude<RemoteAgentRunMode, "direct"> {
  if (id.startsWith("group-brainstorm-")) return "parallel";
  if (id.startsWith("group-polish-")) return "loop";
  return "sequential";
}

function templateRoomForMode(mode: Exclude<RemoteAgentRunMode, "direct">, baseRooms: readonly Room[]): Room | undefined {
  return baseRooms.find((room) => room.template && room.runMode === mode);
}

function roomsForAgents(roomList: readonly Room[], agentLookup: AgentLookup): Room[] {
  return roomList.map((room) => {
    const directAgent = room.agentId ? getOptionalAgentFrom(agentLookup, room.agentId) : undefined;
    return {
      ...room,
      title: directAgent?.name ?? themeAgentNames(room.title, agentLookup),
      goal: themeAgentNames(room.goal, agentLookup),
      lastMessage: themeAgentNames(room.lastMessage, agentLookup),
    };
  });
}

function membersForRoom(room: Room, agentLookup: AgentLookup): Agent[] {
  return room.memberIds.map((agentId) => getAgentFrom(agentLookup, agentId));
}

function roomRunMode(room: Room): RemoteAgentRunMode {
  if (room.kind === "agent") {
    return "direct";
  }
  if (room.runMode) {
    return room.runMode;
  }
  if (room.id === "brainstorm") {
    return "parallel";
  }
  if (room.id === "polish") {
    return "loop";
  }
  return "sequential";
}

function templateFlowCopy(mode: Exclude<RemoteAgentRunMode, "direct">): {
  kicker: string;
  relation: string;
  diagram: Array<{ kind: string; connector: string; items: string[] }>;
  steps: [string, string, string];
  details: [string, string, string];
  useCases: string[];
} {
  if (mode === "parallel") {
    return {
      kicker: "ParallelAgent · 独立任务并行跑",
      relation: "任务之间没有依赖，可以同时开始。",
      diagram: [
        { kind: "parallel", connector: "", items: ["调研 A", "调研 B", "调研 C"] },
        { kind: "merge", connector: "→", items: ["多路结果", "汇总判断"] },
      ],
      steps: ["拆成独立问题", "同时探索", "汇总成方向"],
      details: [
        "把一个大问题拆成几个互不等待的小任务。",
        "每个 Agent 从自己的角度独立输出，避免互相带偏。",
        "把不同答案放回同一个群聊，方便比较和取舍。",
      ],
      useCases: ["头脑风暴", "竞品调研", "资料搜集", "多角度风险评估", "方案发散", "用户反馈归类"],
    };
  }
  if (mode === "loop") {
    return {
      kicker: "LoopAgent · 反复改到达标",
      relation: "产出需要被评审，不满意就继续改。",
      diagram: [
        { kind: "loop", connector: "→", items: ["初稿", "评审", "修改"] },
        { kind: "exit", connector: "→", items: ["达标", "交付"] },
      ],
      steps: ["先产出版本", "给出评审结论", "必要时再改"],
      details: [
        "Producer 先做一个可以被检查的版本。",
        "Critic 明确指出哪里不达标，并给出继续或结束的判断。",
        "通常 2-4 轮收敛，适合追求质量而不是一次性回答。",
      ],
      useCases: ["文案打磨", "PRD 修订", "代码审查后重构", "提示词优化", "设计稿评审", "方案质量验收"],
    };
  }
  return {
    kicker: "SequentialAgent · 上游输出给下游",
    relation: "任务之间有先后依赖，后一步必须接住前一步。",
    diagram: [
      { kind: "sequential", connector: "→", items: ["写", "审", "改"] },
      { kind: "output", connector: "→", items: ["上游输出", "下游输入"] },
    ],
    steps: ["确定先后顺序", "逐棒交接", "最后汇总回复"],
    details: [
      "先让最适合的 Agent 完成第一步。",
      "下一位 Agent 读取前一位结果继续推进，不从头再来。",
      "适合流程清楚、每一步都依赖上一结果的工作。",
    ],
    useCases: ["写作 → 审稿 → 改稿", "需求分析 → 技术方案 → 实施计划", "代码生成 → Code Review → 重构", "调研 → 总结 → 决策建议", "翻译 → 润色 → 校对"],
  };
}

function convenePromptForRoom(room: Room): string {
  return [
    "Convene this room as a bounded visible team pass.",
    `Room goal: ${room.goal}`,
    room.summary ? `Room operating contract: ${room.summary}` : undefined,
    "Use multiple visible speakers only for brainstorming, adversarial convergence, fault localization, review, or high-uncertainty decisions.",
    "If the next move is straightforward execution, choose one owner and keep everyone else silent.",
    "End with a durable decision, next owner, or one awaiting_input question.",
  ]
    .filter(Boolean)
    .join("\n");
}

function roomPreview(
  room: Room,
  messages: ChatMessage[] | undefined,
  activeRun: RunDescriptor | undefined,
  status: string,
  agentLookup: AgentLookup,
): string {
  if (activeRun?.roomId === room.id && status === "running") {
    const names = activeRun.agentIds.map((agentId) => getAgentFrom(agentLookup, agentId).name).join(" + ");
    return `${names} ${activeRun.agentIds.length === 1 ? "is" : "are"} typing...`;
  }

  const lastMessage = messages?.at(-1);
  return themeAgentNames(lastMessage?.body ?? room.lastMessage, agentLookup);
}

function roomLastActivityAt(room: Room, messages: ChatMessage[] | undefined, activeRun: RunDescriptor | undefined): number {
  if (activeRun?.roomId === room.id) {
    return Date.now();
  }

  return messages?.at(-1)?.createdAt ?? room.lastActivityAt ?? 0;
}

function roomTime(room: Room, messages: ChatMessage[] | undefined, activeRun: RunDescriptor | undefined): string {
  if (activeRun?.roomId === room.id) {
    return "Now";
  }

  const lastMessage = messages?.at(-1);
  if (lastMessage) {
    return lastMessage.time;
  }
  if (room.lastActivityAt) {
    return formatMessageTime(room.lastActivityAt);
  }
  return room.time;
}

function themeAgentNames(text: string, agentLookup: AgentLookup): string {
  return agents.reduce((current, agent) => {
    const themedAgent = getAgentFrom(agentLookup, agent.id);
    if (themedAgent.name === agent.name) {
      return current;
    }

    return current.replace(new RegExp(`\\b${escapeRegExp(agent.name)}\\b`, "g"), themedAgent.name);
  }, text);
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function agentIdFromMessageId(messageId?: string): string | undefined {
  if (!messageId) {
    return undefined;
  }
  return agents.find((agent) => messageId.endsWith(`-${agent.id}`))?.id;
}

function deriveAllAgentStatuses(
  events: readonly AgentUXEvent[],
  runRegistry: Record<string, RunDescriptor>,
): Record<string, AgentStatus> {
  const statuses: Record<string, AgentStatus> = Object.fromEntries(agents.map((agent) => [agent.id, agent.status]));
  const descriptors = Object.values(runRegistry).sort((left, right) => left.startedAt - right.startedAt);

  for (const descriptor of descriptors) {
    const runStatus = runStatusForRun(events, descriptor.runId);
    const runStatuses = deriveAgentStatuses(events, descriptor.runId, descriptor, runStatus);

    descriptor.agentIds.forEach((agentId) => {
      statuses[agentId] = runStatuses[agentId] ?? statuses[agentId];
    });
  }

  return statuses;
}

function deriveTimelineRunMessages(
  events: readonly AgentUXEvent[],
  runRegistry: Record<string, RunDescriptor>,
  runIds: readonly string[],
): Record<string, TimelineRunMessage[]> {
  const targetRunIds = new Set(runIds);
  const runErrors = new Map<string, AgentUXEvent & { type: "run.error" }>();
  const awaitingInputs = new Map<string, AgentUXEvent & { type: "run.awaiting_input" }>();
  const mediaByMessageId = new Map<string, TimelineRunMedia[]>();
  const textMessages = new Map<
    string,
    {
      id: string;
      runId: string;
      agentId: string;
      text: string;
      finished: boolean;
      firstSeq: number;
    }
  >();

  for (const event of events) {
    if (!targetRunIds.has(event.runId)) {
      continue;
    }

    if (event.type === "run.error") {
      runErrors.set(event.runId, event);
    }

    if (event.type === "run.awaiting_input") {
      awaitingInputs.set(event.runId, event);
    }

    if (event.type === "media.started" || event.type === "media.ready" || event.type === "media.failed") {
      const messageId = event.messageId ?? stringFromUnknown(event.payload.messageId);
      const idx = numberFromUnknown(event.payload.idx);
      if (messageId && idx !== undefined) {
        const existing = mediaByMessageId.get(messageId) ?? [];
        const previous = existing.find((item) => item.idx === idx);
        const payloadKind = stringFromUnknown(event.payload.kind);
        const kind: "image" | "audio" =
          payloadKind === "audio" ? "audio" : payloadKind === "image" ? "image" : previous?.kind ?? "image";
        const nextMedia: TimelineRunMedia = {
          idx,
          alt: stringFromUnknown(event.payload.alt) ?? previous?.alt ?? (kind === "audio" ? "音乐" : "图"),
          status:
            event.type === "media.ready"
              ? "ready"
              : event.type === "media.failed"
                ? "failed"
                : "started",
          kind,
          mediaUrl: stringFromUnknown(event.payload.mediaUrl) ?? previous?.mediaUrl,
          reason: stringFromUnknown(event.payload.reason) ?? previous?.reason,
        };
        mediaByMessageId.set(messageId, [...existing.filter((item) => item.idx !== idx), nextMedia].sort((left, right) => left.idx - right.idx));
      }
    }

    if (event.type === "text.started") {
      const descriptor = runRegistry[event.runId];
      const agentId =
        stringFromUnknown(event.payload.agentId) ??
        metadataString(event.payload.metadata, "agentId") ??
        agentIdFromMessageId(event.messageId) ??
        descriptor?.agentIds[0] ??
        "main";
      textMessages.set(event.payload.textId, {
        id: event.messageId ?? `msg-${event.runId}-${agentId}`,
        runId: event.runId,
        agentId,
        text: "",
        finished: false,
        firstSeq: event.seq,
      });
    }

    if (event.type === "text.delta") {
      const existing = textMessages.get(event.payload.textId);
      if (existing) {
        existing.text += event.payload.delta;
      }
    }

    if (event.type === "text.finished") {
      const existing = textMessages.get(event.payload.textId);
      if (existing) {
        existing.finished = true;
      }
    }
  }

  const messagesByAnchor: Record<string, TimelineRunMessage[]> = {};
  for (const descriptor of Object.values(runRegistry)) {
    if (!targetRunIds.has(descriptor.runId)) {
      continue;
    }

    const status = runStatusForRun(events, descriptor.runId);
    const runTextMessages = [...textMessages.values()]
      .filter((message) => message.runId === descriptor.runId)
      .sort((left, right) => left.firstSeq - right.firstSeq);
    const visibleRunTextMessages = runTextMessages.filter((message) => {
      const media = mediaByMessageId.get(message.id) ?? [];
      return message.text.trim().length > 0 || media.length > 0 || (status === "running" && !message.finished);
    });
    const runError = runErrors.get(descriptor.runId);
    const awaitingInput = awaitingInputs.get(descriptor.runId);
    const messages =
      visibleRunTextMessages.length > 0
        ? visibleRunTextMessages.map((message): TimelineRunMessage => {
            const streaming = status === "running" && !message.finished;
            return {
              id: message.id,
              runId: message.runId,
              agentId: message.agentId,
              text: message.text,
              media: mediaByMessageId.get(message.id) ?? [],
              streaming,
              status,
              expression: pickAgentExpression({
                agentId: message.agentId,
                runId: message.runId,
                trigger: descriptor.trigger,
                runStatus: status,
                streaming,
                hasText: message.text.trim().length > 0,
              }),
            };
          })
        : status === "error" && runError
          ? [
              {
                id: `${descriptor.runId}-visible-error`,
                runId: descriptor.runId,
                agentId: descriptor.agentIds[0],
                text: runError.payload.userMessage ?? "I could not send that reply. Check the local model connection, then try again.",
                media: [],
                streaming: false,
                status,
                expression: pickAgentExpression({
                  agentId: descriptor.agentIds[0],
                  runId: descriptor.runId,
                  trigger: descriptor.trigger,
                  runStatus: status,
                  streaming: false,
                  hasText: true,
                }),
              },
            ]
        : status === "finished" && runTextMessages.length > 0
          ? [
              {
                id: `${descriptor.runId}-empty-output`,
                runId: descriptor.runId,
                agentId: descriptor.agentIds[0],
                text: "这次没有生成出可显示的内容，可以重新发一次。",
                media: [],
                streaming: false,
                status: "stalled",
                expression: pickAgentExpression({
                  agentId: descriptor.agentIds[0],
                  runId: descriptor.runId,
                  trigger: descriptor.trigger,
                  runStatus: "stalled",
                  streaming: false,
                  hasText: true,
                }),
              },
            ]
        : status === "awaiting_input" && awaitingInput
          ? [
              {
                id: `${descriptor.runId}-awaiting-input`,
                runId: descriptor.runId,
                agentId: descriptor.agentIds[0],
                text: awaitingInput.payload.message ?? "Input is required before this run can continue.",
                media: [],
                streaming: false,
                status,
                expression: pickAgentExpression({
                  agentId: descriptor.agentIds[0],
                  runId: descriptor.runId,
                  trigger: descriptor.trigger,
                  runStatus: status,
                  streaming: false,
                  hasText: true,
                }),
              },
            ]
        : status === "running"
          ? [
              {
                id: `pending-${descriptor.runId}-${descriptor.agentIds[0]}`,
                runId: descriptor.runId,
                agentId: descriptor.agentIds[0],
                text: "",
                media: [],
                streaming: true,
                status,
                expression: pickAgentExpression({
                  agentId: descriptor.agentIds[0],
                  runId: descriptor.runId,
                  trigger: descriptor.trigger,
                  runStatus: status,
                  streaming: true,
                  hasText: false,
                }),
              },
            ]
          : [];

    if (messages.length > 0) {
      messagesByAnchor[descriptor.anchorMessageId] = [
        ...(messagesByAnchor[descriptor.anchorMessageId] ?? []),
        ...messages,
      ];
    }
  }

  return messagesByAnchor;
}

function deriveAgentStatuses(
  events: readonly AgentUXEvent[],
  activeRunId: string | undefined,
  descriptor: RunDescriptor | undefined,
  runStatus: string,
): Record<string, AgentStatus> {
  const statuses: Record<string, AgentStatus> = Object.fromEntries(agents.map((agent) => [agent.id, agent.status]));
  if (!activeRunId || !descriptor) {
    return statuses;
  }

  const textAgents = new Map<string, string>();
  const finishedTextIds = new Set<string>();

  for (const event of events) {
    if (event.runId !== activeRunId) {
      continue;
    }

    if (event.type === "text.started") {
      const agentId =
        stringFromUnknown(event.payload.agentId) ??
        metadataString(event.payload.metadata, "agentId") ??
        agentIdFromMessageId(event.messageId);
      if (agentId) {
        textAgents.set(event.payload.textId, agentId);
        statuses[agentId] = "working";
      }
    }

    if (event.type === "text.finished") {
      const agentId =
        textAgents.get(event.payload.textId) ??
        stringFromUnknown(event.payload.agentId) ??
        metadataString(event.payload.metadata, "agentId");
      if (agentId) {
        finishedTextIds.add(event.payload.textId);
        statuses[agentId] = "done";
      }
    }
  }

  if (runStatus === "running") {
    const unfinishedAgentIds = [...textAgents.entries()]
      .filter(([textId]) => !finishedTextIds.has(textId))
      .map(([, agentId]) => agentId);
    if (unfinishedAgentIds.length === 0) {
      statuses[descriptor.agentIds[0]] = "thinking";
    } else {
      unfinishedAgentIds.forEach((agentId) => {
        statuses[agentId] = "working";
      });
    }
  }

  return statuses;
}

function deriveAgentUXArtifacts(events: readonly AgentUXEvent[]): ArtifactRecord[] {
  const artifacts = new Map<string, ArtifactRecord>();

  for (const event of events) {
    if (event.type === "artifact.created") {
      const sourceAgentId = metadataString(event.payload.metadata, "sourceAgentId") ?? "main";
      artifacts.set(event.payload.artifactId, {
        id: event.payload.artifactId,
        roomId: metadataString(event.payload.metadata, "roomId") ?? "launch",
        title: event.payload.title ?? "Untitled note",
        kind: event.payload.kind,
        sourceAgentId,
        source: metadataString(event.payload.metadata, "sourceAgent") ?? getAgent(sourceAgentId).name,
        version: metadataString(event.payload.metadata, "version") ?? "v1",
        status: "created",
        content: "",
        origin: "agentux",
        updatedAt: event.ts,
      });
    }

    if (event.type === "artifact.delta") {
      const existing = artifacts.get(event.payload.artifactId);
      const sourceAgentId = metadataString(event.payload.metadata, "sourceAgentId") ?? existing?.sourceAgentId ?? "main";
      artifacts.set(event.payload.artifactId, {
        id: event.payload.artifactId,
        roomId: metadataString(event.payload.metadata, "roomId") ?? existing?.roomId ?? "launch",
        title: existing?.title ?? "Untitled note",
        kind: existing?.kind ?? "custom",
        sourceAgentId,
        source: metadataString(event.payload.metadata, "sourceAgent") ?? existing?.source ?? getAgent(sourceAgentId).name,
        version: metadataString(event.payload.metadata, "version") ?? existing?.version ?? "v1",
        status: "streaming",
        content: `${existing?.content ?? ""}${artifactDeltaText(event.payload.delta)}`,
        origin: "agentux",
        updatedAt: event.ts,
      });
    }

    if (event.type === "artifact.finished") {
      const existing = artifacts.get(event.payload.artifactId);
      const sourceAgentId = metadataString(event.payload.metadata, "sourceAgentId") ?? existing?.sourceAgentId ?? "main";
      artifacts.set(event.payload.artifactId, {
        id: event.payload.artifactId,
        roomId: metadataString(event.payload.metadata, "roomId") ?? existing?.roomId ?? "launch",
        title: existing?.title ?? "Untitled note",
        kind: existing?.kind ?? "custom",
        sourceAgentId,
        source: metadataString(event.payload.metadata, "sourceAgent") ?? existing?.source ?? getAgent(sourceAgentId).name,
        version: metadataString(event.payload.metadata, "version") ?? existing?.version ?? "v1",
        status: event.payload.status,
        content: existing?.content ?? "",
        origin: "agentux",
        updatedAt: event.ts,
      });
    }
  }

  return [...artifacts.values()].sort((left, right) => right.updatedAt - left.updatedAt);
}

function metadataString(metadata: Record<string, unknown> | undefined, key: string): string | undefined {
  const value = metadata?.[key];
  return typeof value === "string" ? value : undefined;
}

function stringFromUnknown(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function numberFromUnknown(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isInteger(value)) {
    return value;
  }
  if (typeof value === "string" && /^\d+$/.test(value)) {
    return Number(value);
  }
  return undefined;
}

function artifactDeltaText(delta: unknown): string {
  if (typeof delta === "string") {
    return delta;
  }

  return JSON.stringify(delta, null, 2);
}

function novaConveneChunks(selectedAgentIds: string[], agentLookup: AgentLookup): string[] {
  const selectedNames = selectedAgentIds.map((agentId) => getAgentFrom(agentLookup, agentId).name).join(" and ");
  if (!selectedNames) {
    return [
      "I am holding this as a bounded room pass. ",
      "No non-host speaker is needed yet, so I will keep the next move with one owner or ask for one missing input.",
    ];
  }
  return [
    "I am convening the room only for the visible contrast this task needs. ",
    `Routing choice: ${selectedNames} will take this pass while everyone else stays observing. `,
    "Long notes should land in artifacts so the chat stays readable.",
  ];
}

function agentResponseChunks(agentId: string, prompt: string, trigger: AgentRunTrigger, agentLookup: AgentLookup): string[] {
  const shortPrompt = prompt.length > 96 ? `${prompt.slice(0, 93)}...` : prompt;
  const agent = getAgentFrom(agentLookup, agentId);

  switch (agentId) {
    case "main":
      return [
        `I see the request: "${shortPrompt}". `,
        "I will pick one visible owner unless the task needs review, debugging, brainstorming, or a decision pass.",
      ];
    case "kai":
      return [
        trigger === "convene"
          ? "I am taking the implementation slice. "
          : trigger === "direct"
            ? `I am taking this direct ${agent.name} room request: "${shortPrompt}". `
            : `I am taking @${agent.name} from "${shortPrompt}". `,
        "I will keep the reply practical and avoid turning a scoped build task into a room-wide discussion. ",
        "Any patch map belongs in the side panel so the conversation does not get crowded.",
      ];
    case "sarah":
      return [
        trigger === "convene"
          ? "I am checking the assumptions behind this route. "
          : trigger === "direct"
            ? `I am checking this direct ${agent.name} room request: "${shortPrompt}". `
            : `I am checking the assumptions in "${shortPrompt}". `,
        "The important proof is whether room selection, reply state, and saved-note state all update from visible interactions.",
      ];
    case "alex":
      return [
        trigger === "convene"
          ? "I am reviewing the interface behavior while the route runs. "
          : trigger === "direct"
            ? `I am reviewing this direct ${agent.name} room request: "${shortPrompt}". `
            : `I am reviewing the UI implications of "${shortPrompt}". `,
        "The selected room, mode switch, and note detail need to stay visually calm and immediately scannable.",
      ];
    default:
      return ["I am preparing a local response for this room."];
  }
}

function artifactTitleFor(agentId: string, trigger: AgentRunTrigger): string {
  const prefix = trigger === "convene" ? "Convene" : trigger === "direct" ? "Direct" : "Mention";

  switch (agentId) {
    case "main":
      return `${prefix} routing note`;
    case "kai":
      return `${prefix} implementation map`;
    case "sarah":
      return `${prefix} evidence checklist`;
    case "alex":
      return `${prefix} UI review notes`;
    default:
      return `${prefix} note`;
  }
}

function artifactContentFor(agentId: string, trigger: AgentRunTrigger, agentLookup: AgentLookup): string {
  const label = trigger === "convene" ? "Convene route" : trigger === "direct" ? "Direct room response" : "Mention response";
  const hostName = getAgentFrom(agentLookup, "main").name;

  switch (agentId) {
    case "main":
      return `## ${label}\n- Host: ${hostName}\n- Default: one visible owner\n- Team pass only for brainstorm, review, debug, or high-uncertainty decisions\n- Output remains linked to room context`;
    case "kai":
      return `## ${label}\n- Append human messages immediately\n- Keep direct chats local and quick\n- Mirror useful reply notes into the right panel\n- Keep saved notes selectable without crowding the chat`;
    case "sarah":
      return `## ${label}\n- Verify room selection sync\n- Check mode state transitions\n- Confirm saved notes appear as the reply develops`;
    case "alex":
      return `## ${label}\n- Preserve Telegram Desktop density\n- Keep Cumora-style blue-white surfaces\n- Show selected note details without changing the layout rhythm`;
    default:
      return `## ${label}\n- Local saved note`;
  }
}

> ⚠️ **[STALE — 2026-05-29]** 这是基于 "Main spawn Bram/Nova/Atlas/Iris" 的早期 GPT 设计，第 9 轮已被原生 multi-agent 模型推翻（visible subagent = OpenClaw `agents.list[]` 各一项）。**当前实现快照看 [`00_README.md`](00_README.md)** / [`../CLAUDE.md`](../CLAUDE.md)；历史决策链见 [`../temp_design.md`](../temp_design.md)。

---

# MVP 数据模型

以下是 MVP 推荐的数据模型。目标是把“身份、会话、任务、权限、产物、审计、进化”分开。

## Entity Overview

```text
User
AgentProfile
AgentInstance
Conversation
RoomMember
Message
PersonaSession
Run
Artifact
ContextPackSnapshot
PermissionGrant
AuditEvent
EvolutionPatch
```

## User

```ts
type User = {
  id: string
  name: string
  timezone?: string
  settings: {
    defaultModelBudget?: string
    privacyMode: 'strict' | 'balanced' | 'open'
  }
}
```

## AgentProfile

模板层。定义 Bram/Luna/Echo 这种角色的默认配置。

```ts
type AgentProfile = {
  id: string
  name: string
  role: string
  avatarUrl?: string
  soulTemplate: string
  defaultModel: string
  defaultSkills: string[]
  defaultTools: string[]
  defaultPermissions: PermissionPolicy
  defaultSandboxPolicy: SandboxPolicy
  createdAt: string
  updatedAt: string
}
```

## AgentInstance

用户拥有的某个小人实例。

```ts
type AgentInstance = {
  id: string
  userId: string
  profileId: string
  displayName: string
  runtimeType: RuntimeType
  runtimeAgentId?: string
  workspaceRef: string
  memoryRef: string
  status: AgentStatus
  modelOverride?: string
  toolOverrides?: string[]
  permissionPolicyOverride?: PermissionPolicy
  createdAt: string
  lastActiveAt?: string
}
```

## Conversation

DM 和 room 统一建模。

```ts
type Conversation = {
  id: string
  ownerUserId: string
  type: 'dm' | 'room'
  title?: string
  pinned: boolean
  mode: 'chat' | 'convene' | 'review'
  visibilityPolicy: VisibilityPolicy
  routingPolicy: RoutingPolicy
  createdAt: string
  updatedAt: string
}
```

## RoomMember

```ts
type RoomMember = {
  conversationId: string
  agentInstanceId: string
  role: 'participant' | 'silent' | 'reviewer' | 'observer'
  speakingPolicy: 'mentioned' | 'proactive' | 'coordinator_selected' | 'silent'
  contextAccess: 'room_only' | 'shared_snippets' | 'full_room'
  joinedAt: string
}
```

## Message

```ts
type Message = {
  id: string
  conversationId: string
  senderType: 'user' | 'subagent' | 'system_card'
  senderId: string
  text?: string
  cardType?: 'summary' | 'review' | 'permission' | 'status'
  visible: boolean
  sourceRunId?: string
  artifactIds: string[]
  createdAt: string
}
```

## PersonaSession

```ts
type PersonaSession = {
  id: string
  conversationId: string
  agentInstanceId: string
  runtimeType: RuntimeType
  runtimeSessionKey?: string
  parentSessionKey?: string
  state: 'active' | 'idle' | 'closed' | 'recovering'
  lastContextPackId?: string
  createdAt: string
  updatedAt: string
}
```

## Run

```ts
type Run = {
  id: string
  kind: 'dm_turn' | 'group_round' | 'review' | 'worker' | 'reflection' | 'evolution'
  conversationId?: string
  agentInstanceId?: string
  parentRunId?: string
  runtimeType: RuntimeType
  model?: string
  status: 'queued' | 'running' | 'waiting_permission' | 'succeeded' | 'failed' | 'cancelled'
  inputContextPackId?: string
  outputMessageIds: string[]
  outputArtifactIds: string[]
  cost?: number
  latencyMs?: number
  startedAt?: string
  endedAt?: string
}
```

## Artifact

```ts
type Artifact = {
  id: string
  ownerUserId: string
  conversationId?: string
  creatorAgentId?: string
  sourceRunId: string
  type: 'review' | 'summary' | 'report' | 'patch' | 'diff' | 'file' | 'image' | 'note'
  title: string
  contentRef: string
  visibility: 'private' | 'room' | 'agent_only' | 'audit_only'
  createdAt: string
}
```

## PermissionGrant

```ts
type PermissionGrant = {
  id: string
  userId: string
  agentInstanceId?: string
  conversationId?: string
  runId?: string
  scope: 'read_file' | 'write_file' | 'exec_shell' | 'web' | 'credential' | 'share_private_context' | 'modify_agent_config'
  resource: string
  decision: 'allow_once' | 'allow_session' | 'allow_room' | 'deny'
  expiresAt?: string
  createdAt: string
}
```

## AuditEvent

```ts
type AuditEvent = {
  id: string
  runId?: string
  conversationId?: string
  eventType: 'route' | 'context_pack' | 'tool_call' | 'permission' | 'worker_spawn' | 'artifact_created' | 'error' | 'evolution_patch'
  publicSummary: string
  redactedPayloadRef?: string
  createdAt: string
}
```

## EvolutionPatch

```ts
type EvolutionPatch = {
  id: string
  targetAgentInstanceId: string
  patchType: 'memory' | 'soul' | 'skill' | 'tool' | 'model' | 'permission' | 'runtime_code'
  proposedDiff: string
  reason: string
  evidenceRefs: string[]
  riskLevel: 'low' | 'medium' | 'high'
  approvalStatus: 'auto_applied' | 'pending' | 'approved' | 'rejected' | 'rolled_back'
  createdByRunId: string
  createdAt: string
}
```

## Shared Types

```ts
type RuntimeType = 'openclaw' | 'codex' | 'claude_code' | 'hermes' | 'gemini_cli' | 'custom'

type AgentStatus = 'online' | 'thinking' | 'working' | 'waiting' | 'away' | 'offline'

type PermissionPolicy = {
  fileRead: 'deny' | 'ask' | 'allow_scoped'
  fileWrite: 'deny' | 'ask' | 'allow_scoped'
  shellExec: 'deny' | 'ask' | 'allow_sandboxed'
  webAccess: 'deny' | 'ask' | 'allow'
  credentialAccess: 'deny' | 'ask'
  sharePrivateContext: 'deny' | 'ask'
}

type SandboxPolicy = {
  mode: 'off' | 'ask' | 'required'
  workspaceAccess: 'none' | 'ro' | 'rw'
  networkAccess: 'off' | 'allowlist' | 'open'
}

type RoutingPolicy = {
  default: 'direct' | 'coordinator_selected'
  maxAgentsPerRound: number
  maxRounds: number
  allowParallel: boolean
}

type VisibilityPolicy = {
  showAuditByDefault: boolean
  allowPrivateContextSharing: 'never' | 'ask' | 'room_default'
}
```

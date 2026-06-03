# Agent Communication Protocol

> Date: 2026-05-31. This is the current protocol note for visible OpenClaw agents in group rooms. It supersedes the stale 01-12 design files for agent-to-agent communication, but does not replace the broader Admin/Evolution recommendation in `13_ADMIN_SUPERVISOR_AND_EVOLUTION_RECOMMENDATION.md`.

## Decision

Agents do not talk to each other directly.

All cross-agent information flow goes through the product orchestrator:

```text
User
→ Backend Orchestrator
→ optional hidden Main scheduling decision
→ per-agent ContextPack
→ OpenClaw visible agent
→ messages / artifacts / audit
→ next per-agent ContextPack
```

Main is a hidden scheduler and judge. Main is not a message bus and should not appear as a normal room speaker.

## Current MVP

The current implementation supports the minimum useful group path:

```text
Group user message
→ frontend resolves target agent ids
→ backend validates target ids are room members
→ frontend/backend resolve room mode
→ backend calls OpenClaw agents through mode-specific runner
→ each agent gets its own room-scoped sessionUser
→ each agent output is inserted as its own message
```

Important current guarantees:

```text
DM room:
  target = room.agentId

Group room with @mentions:
  target = mentioned agents that are members of the room

Group room without @mentions:
  target = current room.memberIds order

Room mode:
  relay       sequential
  brainstorm parallel
  polish      loop

Session isolation:
  sessionUser = me:<roomId>:<agentId>
```

This is intentionally still an MVP. It proves that multiple visible OpenClaw configured agents can participate in one room without sharing one raw transcript or one persona prompt, and that the three visible room types now have distinct backend behavior.

## Room Modes

### 接龙房 / Sequential

Purpose: pipeline handoff.

MVP behavior:

```text
Sarah → Alex → Kai
```

Each member speaks once, in order, then the run stops.

This room is not a meeting and not an infinite discussion. A user message should not cause agents to continue debating until they decide the topic is clear. The product should preserve user control, low latency, and predictable cost.

Phase 2 behavior:

```text
Round 1: selected sequence speaks once
Main judges:
  stop      enough, end
  continue  one bounded repair round
  escalate ask user for missing input
```

Hard limits for Phase 2:

```text
default decision: stop
max_rounds: 2
continue only when output is missing required format, contains direct conflict, or lacks a critical input
escalate when user input is required
```

Main may decide order in Phase 2, but Main still only returns structured scheduling JSON. The backend executes it.

Example Main decision:

```json
{
  "mode": "sequential",
  "sequence": ["alex", "sarah", "kai"],
  "max_rounds": 1,
  "reason": "Product framing first, then wording, then implementation risk."
}
```

### 头脑风暴房 / Parallel

Purpose: independent perspectives.

Target behavior:

```text
Main splits or confirms task
→ Sarah / Alex / Kai run independently
→ Merger or Main produces a summary artifact
```

MVP behavior:

```text
User prompt
→ Sarah / Alex / Kai receive independent prompts
→ all selected agents run as parallel fanout
→ each visible output is inserted as its own message
→ run stops
```

Parallel agents should not see each other's raw output during the first fanout. The merge step may receive summaries or artifact refs.

Current limitation: there is no Merger artifact yet. MVP intentionally stops after independent visible outputs so the room has real parallel behavior without introducing hidden Main summarization as a fake chat message.

### 打磨房 / Loop

Purpose: producer / critic iteration.

Target behavior:

```text
producer drafts
→ critic returns verdict
→ approved: stop
→ revise: producer updates
→ escalate: ask user or Main
```

MVP behavior:

```text
producer = first selected room member
critic   = second selected room member

producer drafts
→ critic reviews and must end with VERDICT: approved | revise | escalate
→ approved: stop
→ escalate: stop and leave the critique visible
→ revise: producer gets one bounded repair turn, then stop
```

Loop mode is the only room type where multiple rounds are expected. It must have:

```text
verdict_required: true
max_rounds: fixed small number
exit condition: approved | escalate | max_rounds
```

## ContextPack

The current backend prompt builders are temporary MVP ContextPack plumbing. They are still text prompts, not persisted structured ContextPack records.

Current MVP shape:

```text
hard constraints extracted from the user request, repeated at top and bottom
one-sentence constraints are tightened to: max 40 Chinese chars, no name prefix
user original request
previous agent outputs as text, compacted when the combined predecessor context is too long
instruction to continue from previous outputs
```

Target ContextPack shape:

```yaml
room_id: relay
room_goal: "一个干完下一个干（写 → 审 → 改）"
mode: sequential
round: 1
your_agent_id: kai
your_role: implementer | critic | writer | pm | merger
your_task_this_round: "Check implementation risk and close the sequence."
inputs:
  user_request:
    type: raw
    text: "..."
  previous_outputs:
    - agent_id: sarah
      type: summary
      artifact_id: msg_...
      text: "..."
    - agent_id: alex
      type: summary
      artifact_id: msg_...
      text: "..."
expected_output:
  key: implementation_note
  format: markdown
verdict_required: false
constraints:
  - "Do not prefix your answer with your name; UI already shows identity."
  - "Do not mention or summon another agent."
redactions:
  - source: "room_history"
    reason: "Only current turn and direct predecessors are relevant."
```

## Input Granularity Rules

Default rules:

```text
Direct predecessor output:
  full text if short, summary if long

Parallel sibling outputs:
  summary + artifact_id

Older turns:
  artifact_id only, unless explicitly retrieved

DM raw transcripts:
  not included by default

Other room history:
  not included by default

Persona files:
  only target agent's own OpenClaw workspace is loaded by OpenClaw
```

Current MVP thresholds:

```text
if combined predecessor outputs > 1500 chars:
  compact each predecessor output with head + tail + omitted character count

minimum compacted predecessor budget:
  350 chars per predecessor

if context was omitted:
  mark it inline as [... omitted N chars ...]
```

Thresholds still needed before scaling beyond MVP:

```text
replace head/tail compaction with summary + artifact refs
preserve direct predecessor at higher fidelity than older predecessors
record redactions in audit/context snapshot
```

## Mentions

User mentions are routing hints:

```text
"@Alex 看这个"
→ only Alex responds if Alex is a room member
```

Agent-authored mentions are not routing triggers in MVP.

If Sarah writes `@Kai`, the backend must not automatically add Kai, call Kai, or modify sequence. Allowing agents to summon agents would create a hidden side channel outside the orchestrator's ContextPack boundary.

Phase 2 may support agent requests for another agent only as structured output:

```json
{
  "request_next_agent": "kai",
  "reason": "Needs implementation feasibility check"
}
```

The backend or Main must approve or reject that request.

## Main Intervention Points

Main should not run for every message in MVP.

Allowed Main intervention points for Phase 2:

```text
1. sequential order selection
2. parallel task split
3. parallel merge / merger selection
4. loop stop / continue / escalate judgment
5. deviation handling when output is malformed or missing required verdict
```

Main outputs structured decisions, for example:

```json
{
  "decision": "stop",
  "reason": "All required roles spoke once and the final answer is usable.",
  "next_sequence": []
}
```

Main decisions should be stored as state/audit, not inserted as normal chat messages.

## Current Debt

Acceptable MVP debt:

```text
buildAgentPrompt is text-based
no context_pack_snapshots table
no audit_events table
no compatibility check hook
parallel has no Merger artifact yet
loop verdict is prompt-enforced and regex-parsed, not stored as structured state
Main is not yet called for scheduling
hard constraint extraction is regex-based, not semantic
```

Debt that must be paid before scaling:

```text
replace text prompt concatenation with structured ContextPack
replace head/tail compaction with summary + artifact refs
record redactions when context is omitted
prevent agent-authored @mentions from becoming implicit routing
persist Main scheduling decisions outside messages
persist loop max_rounds and verdict decisions as state/audit
```

## Implementation Notes

Current relevant files:

```text
frontend/src/agentRoomState.ts
  resolves direct / mention / group target agent ids

frontend/src/remoteAgentRun.ts
  sends runId, prompt, agentIds, memberIds

backend/src/routes/messages.ts
  validates room membership
  runs target agents via direct / sequential / parallel / loop mode
  uses me:<roomId>:<agentId> session isolation
  writes one message per agent output
```

The code should keep `buildAgentPrompt()` clearly understood as temporary MVP plumbing. It should not be treated as the final ContextPack implementation.

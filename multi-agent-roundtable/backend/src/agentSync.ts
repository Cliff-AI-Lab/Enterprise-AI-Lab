import { readFileSync, existsSync } from "node:fs";
import { isAbsolute, resolve } from "node:path";
import { upsertAgent, ensureDirectRoom, ensureCollaborationRoom } from "./db.js";

interface OpenClawAgentListItem {
  id: string;
  workspace: string;
  model?: { primary?: string };
}

interface OpenClawConfig {
  agents?: {
    defaults?: { model?: { primary?: string } };
    list?: OpenClawAgentListItem[];
  };
}

interface ParsedIdentity {
  name?: string;
  role?: string;
  vibe?: string;
  emoji?: string;
  bestFor?: string[];
}

const FALLBACK_COLORS: Record<string, string> = {
  sarah: "#17b890",
  alex: "#ff8a65",
  kai: "#7c5cff",
  main: "#42a5f5",
  maruko: "#f472b6",
  architect: "#2563eb",
  mira: "#d946ef",
  lin: "#0f766e",
  iris: "#ca8a04",
};

function parseIdentityMd(text: string): ParsedIdentity {
  const out: ParsedIdentity = {};
  for (const line of text.split("\n")) {
    const m = line.match(/^\s*-\s*(name|role|vibe|emoji|bestfor)\s*:\s*(.+?)\s*$/i);
    if (!m || !m[1] || !m[2]) continue;
    const key = m[1].toLowerCase();
    if (key === "bestfor") {
      // 接受英文 ',' 和中文 '，' 作分隔符
      out.bestFor = m[2].split(/\s*[,，]\s*/).map((s) => s.trim()).filter(Boolean);
    } else if (key === "name" || key === "role" || key === "vibe" || key === "emoji") {
      out[key] = m[2];
    }
  }
  return out;
}

const HIDDEN_IDS = new Set(["main"]);

// Persistent map agentId → absolute workspace directory.
// Filled by syncAgentsFromOpenClaw() at boot; queried by routes that need to
// read/write persona files (SOUL.md / avatar.png) without parsing openclaw.json
// on every request.
const agentWorkspaceMap = new Map<string, string>();

export function getAgentWorkspace(agentId: string): string | undefined {
  return agentWorkspaceMap.get(agentId);
}

export function syncAgentsFromOpenClaw(): void {
  const root = process.env.PROJECT_ROOT ?? resolve(process.cwd(), "..");
  const cfgPath = resolve(root, "openclaw.json");

  if (!existsSync(cfgPath)) {
    console.warn(`[agentSync] ${cfgPath} not found; skipping sync.`);
    return;
  }

  const cfg: OpenClawConfig = JSON.parse(readFileSync(cfgPath, "utf8"));
  const defaultModel = cfg.agents?.defaults?.model?.primary ?? "ruidong/ruidong-std";
  const list = cfg.agents?.list ?? [];

  agentWorkspaceMap.clear();

  for (const item of list) {
    const workspace = isAbsolute(item.workspace) ? item.workspace : resolve(root, item.workspace);
    agentWorkspaceMap.set(item.id, workspace);
    const identityPath = resolve(workspace, "IDENTITY.md");
    let identity: ParsedIdentity = {};
    if (existsSync(identityPath)) {
      identity = parseIdentityMd(readFileSync(identityPath, "utf8"));
    } else {
      console.warn(`[agentSync] ${identityPath} missing; using fallback for ${item.id}`);
    }

    const name = identity.name ?? capitalize(item.id);
    const role = identity.role ?? "Agent";
    const profile = identity.vibe ?? "";
    const model = (item.model?.primary ?? defaultModel).replace(/^[^/]+\//, "");
    const hidden = HIDDEN_IDS.has(item.id);

    upsertAgent({
      id: item.id,
      name,
      role,
      profile,
      model,
      hidden,
      emoji: identity.emoji,
      color: FALLBACK_COLORS[item.id] ?? "#2563eb",
      initials: name.charAt(0).toUpperCase(),
      bestFor: identity.bestFor,
    });

    if (!hidden) {
      ensureDirectRoom(item.id, name);
    }
  }

  ensureCollaborationRoom({
    id: "relay",
    title: "接龙房",
    memberIds: ["sarah", "alex", "kai"],
    runMode: "sequential",
  });
  ensureCollaborationRoom({
    id: "brainstorm",
    title: "头脑风暴房",
    memberIds: ["sarah", "alex", "kai"],
    runMode: "parallel",
  });
  ensureCollaborationRoom({
    id: "polish",
    title: "打磨房",
    memberIds: ["sarah", "alex"],
    runMode: "loop",
  });
  ensureCollaborationRoom({
    id: "template-relay",
    title: "接力工作",
    memberIds: [],
    runMode: "sequential",
  });
  ensureCollaborationRoom({
    id: "template-brainstorm",
    title: "并行探索",
    memberIds: [],
    runMode: "parallel",
  });
  ensureCollaborationRoom({
    id: "template-polish",
    title: "迭代打磨",
    memberIds: [],
    runMode: "loop",
  });

  console.log(`[agentSync] synced ${list.length} agents from openclaw.json`);
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

import type { AgentSoul } from "./agentSouls";

export type AgentSkillPolicy = "manual" | "auto_when_relevant" | "ask_first";
export type AgentPermissionMode = "off" | "ask" | "allow";
export type AgentPermissionKey = "webAccess" | "fileRead" | "fileWrite" | "shell" | "codeEdit" | "mediaGenerate";

export type AgentPermissionSet = Record<AgentPermissionKey, AgentPermissionMode>;

export type AgentSkillDefinition = {
  id: string;
  name: string;
  category: string;
  description: string;
};

export type AgentConfigurableFields = {
  id: string;
  name: string;
  role: string;
  profile: string;
  model: string;
  providerProfile?: string;
  capabilities: string[];
  soul: AgentSoul;
  soulMarkdown?: string;
  enabledSkillIds: string[];
  skillPolicy: AgentSkillPolicy;
  permissions: AgentPermissionSet;
};

export type AgentConfigOverride = Partial<
    Pick<
      AgentConfigurableFields,
      | "name"
      | "role"
      | "profile"
      | "model"
      | "providerProfile"
      | "capabilities"
      | "soulMarkdown"
      | "enabledSkillIds"
      | "skillPolicy"
    >
  > & {
  soul?: Partial<AgentSoul>;
  permissions?: Partial<AgentPermissionSet>;
};

export type AgentConfigOverridesById = Record<string, AgentConfigOverride>;
export type AgentConfigStorage = Pick<Storage, "getItem" | "setItem">;

export const agentConfigStorageKey = "agentelegram_agent_configs";
export const WORKSPACE_PROVIDER_MODEL_ID = "workspace provider";

export const AGENT_SKILLS: AgentSkillDefinition[] = [
  {
    id: "project-scope",
    name: "Project scoping",
    category: "Planning",
    description: "Clarify goals, constraints, owners, and next decisions.",
  },
  {
    id: "code-patch",
    name: "Code patching",
    category: "Build",
    description: "Plan implementation changes and produce patch-oriented notes.",
  },
  {
    id: "research-check",
    name: "Research check",
    category: "Research",
    description: "Separate facts, assumptions, evidence gaps, and verification paths.",
  },
  {
    id: "design-review",
    name: "Design review",
    category: "Design",
    description: "Review layout density, hierarchy, copy, and interaction clarity.",
  },
  {
    id: "test-triage",
    name: "Test triage",
    category: "Quality",
    description: "Read failures, identify likely owners, and define focused verification.",
  },
  {
    id: "image-generation",
    name: "Image generation",
    category: "Media",
    description: "Create image artifacts through approved media generation tools.",
  },
  {
    id: "audio-generation",
    name: "Audio generation",
    category: "Media",
    description: "Create short audio or music artifacts through approved media generation tools.",
  },
];

export const defaultAgentPermissions: AgentPermissionSet = {
  webAccess: "ask",
  fileRead: "ask",
  fileWrite: "ask",
  shell: "ask",
  codeEdit: "ask",
  mediaGenerate: "ask",
};

export const permissionLabels: Record<AgentPermissionKey, string> = {
  webAccess: "Web access",
  fileRead: "Read files",
  fileWrite: "Write files",
  shell: "Run commands",
  codeEdit: "Edit code",
  mediaGenerate: "Generate media",
};

export const permissionModes: Array<{ value: AgentPermissionMode; label: string }> = [
  { value: "off", label: "Off" },
  { value: "ask", label: "Ask first" },
  { value: "allow", label: "Allow" },
];

export const skillPolicyOptions: Array<{ value: AgentSkillPolicy; label: string }> = [
  { value: "manual", label: "Manual" },
  { value: "ask_first", label: "Ask first" },
  { value: "auto_when_relevant", label: "Auto when relevant" },
];

export const providerProfileOptions: Array<{ value: string; label: string }> = [
  { value: "", label: "Workspace provider" },
];

export function readAgentConfigOverrides(
  storage: AgentConfigStorage | undefined = browserStorage(),
): AgentConfigOverridesById {
  if (!storage) {
    return {};
  }

  const raw = storage.getItem(agentConfigStorageKey);
  if (!raw) {
    return {};
  }

  try {
    return normalizeAgentConfigOverrides(JSON.parse(raw));
  } catch {
    return {};
  }
}

export function writeAgentConfigOverrides(
  storage: AgentConfigStorage | undefined = browserStorage(),
  overrides: AgentConfigOverridesById,
): AgentConfigOverridesById {
  const normalized = normalizeAgentConfigOverrides(overrides);
  storage?.setItem(agentConfigStorageKey, JSON.stringify(normalized));
  return normalized;
}

export function applyAgentConfigOverrides<T extends AgentConfigurableFields>(
  agents: readonly T[],
  overridesById: AgentConfigOverridesById,
): T[] {
  return agents.map((agent) => {
    const override = overridesById[agent.id];
    if (!override) {
      return agent;
    }

    return {
      ...agent,
      ...stringPatch("name", override.name),
      ...stringPatch("role", override.role),
      ...stringPatch("profile", override.profile),
      ...stringPatch("model", override.model),
      ...stringPatch("providerProfile", override.providerProfile),
      ...stringPatch("soulMarkdown", override.soulMarkdown),
      capabilities: override.capabilities ?? agent.capabilities,
      enabledSkillIds: override.enabledSkillIds ?? agent.enabledSkillIds,
      skillPolicy: override.skillPolicy ?? agent.skillPolicy,
      permissions: { ...agent.permissions, ...override.permissions },
      soul: {
        ...agent.soul,
        ...override.soul,
        bestFor: override.soul?.bestFor ?? agent.soul.bestFor,
        workingStyle: override.soul?.workingStyle ?? agent.soul.workingStyle,
        boundaries: override.soul?.boundaries ?? agent.soul.boundaries,
      },
    };
  });
}

export function normalizeAgentConfigOverrides(value: unknown): AgentConfigOverridesById {
  if (!isRecord(value)) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(value).flatMap(([agentId, candidate]) => {
      if (!isRecord(candidate)) {
        return [];
      }
      const normalized = normalizeAgentConfigOverride(candidate);
      return Object.keys(normalized).length > 0 ? [[agentId, normalized]] : [];
    }),
  );
}

function normalizeAgentConfigOverride(value: Record<string, unknown>): AgentConfigOverride {
  const override: AgentConfigOverride = {};
  assignString(override, "name", value.name);
  assignString(override, "role", value.role);
  assignString(override, "profile", value.profile);
  assignString(override, "model", value.model);
  if (isProviderProfile(value.providerProfile)) {
    override.providerProfile = value.providerProfile;
  }
  assignString(override, "soulMarkdown", value.soulMarkdown);

  const capabilities = stringList(value.capabilities);
  if (capabilities) {
    override.capabilities = capabilities;
  }

  const enabledSkillIds = stringList(value.enabledSkillIds)?.filter((skillId) =>
    AGENT_SKILLS.some((skill) => skill.id === skillId),
  );
  if (enabledSkillIds) {
    override.enabledSkillIds = enabledSkillIds;
  }

  if (isSkillPolicy(value.skillPolicy)) {
    override.skillPolicy = value.skillPolicy;
  }

  if (isRecord(value.permissions)) {
    const permissions: Partial<AgentPermissionSet> = {};
    for (const key of Object.keys(defaultAgentPermissions) as AgentPermissionKey[]) {
      if (isPermissionMode(value.permissions[key])) {
        permissions[key] = value.permissions[key];
      }
    }
    if (Object.keys(permissions).length > 0) {
      override.permissions = permissions;
    }
  }

  if (isRecord(value.soul)) {
    const soul: Partial<AgentSoul> = {};
    assignString(soul, "identity", value.soul.identity);
    assignString(soul, "personality", value.soul.personality);
    const bestFor = stringList(value.soul.bestFor);
    const workingStyle = stringList(value.soul.workingStyle);
    const boundaries = stringList(value.soul.boundaries);
    if (bestFor) soul.bestFor = bestFor;
    if (workingStyle) soul.workingStyle = workingStyle;
    if (boundaries) soul.boundaries = boundaries;
    if (Object.keys(soul).length > 0) {
      override.soul = soul;
    }
  }

  return override;
}

function stringPatch<K extends string>(key: K, value: string | undefined): Partial<Record<K, string>> {
  return value ? { [key]: value } as Partial<Record<K, string>> : {};
}

function assignString<T extends object, K extends keyof T & string>(target: T, key: K, value: unknown): void {
  if (typeof value === "string" && value.trim().length > 0) {
    target[key] = value.trim() as T[K];
  }
}

function stringList(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }

  const normalized = value.flatMap((item) => (typeof item === "string" && item.trim() ? [item.trim()] : []));
  return normalized.length > 0 ? Array.from(new Set(normalized)) : undefined;
}

function isSkillPolicy(value: unknown): value is AgentSkillPolicy {
  return value === "manual" || value === "auto_when_relevant" || value === "ask_first";
}

function isPermissionMode(value: unknown): value is AgentPermissionMode {
  return value === "off" || value === "ask" || value === "allow";
}

function isProviderProfile(value: unknown): value is string {
  return providerProfileOptions.some((option) => option.value && option.value === value);
}

function browserStorage(): AgentConfigStorage | undefined {
  return typeof window === "undefined" ? undefined : window.localStorage;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

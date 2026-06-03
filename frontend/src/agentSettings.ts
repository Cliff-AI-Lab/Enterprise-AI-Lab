import {
  MODEL_PROVIDERS,
  getDefaultModelForProvider,
  getProviderConfig,
  isAgentRunProvider,
  normalizeBaseUrl,
  type AgentRunProvider,
} from "./modelProviders";

export type { AgentRunProvider } from "./modelProviders";

export type ProviderRuntimeSettings = {
  baseUrl: string;
  model: string;
  apiKey: string;
};

export type ProviderRuntimeSettingsByProvider = Record<AgentRunProvider, ProviderRuntimeSettings>;

export type AgentRunSettings = {
  provider: AgentRunProvider;
  providers: ProviderRuntimeSettingsByProvider;
};

export type AgentRunSettingsStorage = Pick<Storage, "getItem" | "setItem">;

export const agentRunSettingsStorageKey = "agentelegram_agent_run_settings";

export const defaultAgentRunSettings: AgentRunSettings = {
  provider: defaultProviderFromEnvironment(),
  providers: defaultProviderRuntimeSettings(),
};

export function readAgentRunSettings(storage: AgentRunSettingsStorage | undefined = browserStorage()): AgentRunSettings {
  if (!storage) {
    return applyEnvironmentOverrides(defaultAgentRunSettings);
  }

  const raw = storage.getItem(agentRunSettingsStorageKey);
  if (!raw) {
    return applyEnvironmentOverrides(defaultAgentRunSettings);
  }

  try {
    return applyEnvironmentOverrides(normalizeAgentRunSettings(JSON.parse(raw)));
  } catch {
    return applyEnvironmentOverrides(defaultAgentRunSettings);
  }
}

export function writeAgentRunSettings(
  storage: AgentRunSettingsStorage | undefined = browserStorage(),
  settings: AgentRunSettings,
): AgentRunSettings {
  const normalized = applyEnvironmentOverrides(normalizeAgentRunSettings(settings));
  storage?.setItem(agentRunSettingsStorageKey, JSON.stringify(normalized));
  return normalized;
}

export function normalizeAgentRunSettings(value: unknown): AgentRunSettings {
  const record = isRecord(value) ? value : {};
  const provider = isAgentRunProvider(record.provider) ? record.provider : defaultAgentRunSettings.provider;
  const providers = defaultProviderRuntimeSettings();
  const persistedProviders = isRecord(record.providers) ? record.providers : {};

  for (const providerConfig of MODEL_PROVIDERS) {
    const persistedCandidate = persistedProviders[providerConfig.id];
    const persisted = isRecord(persistedCandidate) ? persistedCandidate : {};
    providers[providerConfig.id] = normalizeProviderRuntimeSettings(providerConfig.id, persisted);
  }

  if (record.provider === "lmstudio" || stringValue(record.lmStudioBaseUrl) || stringValue(record.lmStudioModel)) {
    providers.lmstudio = normalizeProviderRuntimeSettings("lmstudio", {
      ...providers.lmstudio,
      baseUrl: stringValue(record.lmStudioBaseUrl) ?? providers.lmstudio.baseUrl,
      model: stringValue(record.lmStudioModel) ?? providers.lmstudio.model,
    });
  }

  if (isAgentRunProvider(record.provider)) {
    const current = providers[record.provider];
    providers[record.provider] = normalizeProviderRuntimeSettings(record.provider, {
      ...current,
      baseUrl: stringValue(record.baseUrl) ?? current.baseUrl,
      model: stringValue(record.model) ?? current.model,
      apiKey: stringValue(record.apiKey) ?? current.apiKey,
    });
  }

  return {
    provider,
    providers,
  };
}

export function getActiveProviderRuntime(settings: AgentRunSettings): ProviderRuntimeSettings {
  const normalized = normalizeAgentRunSettings(settings);
  return normalized.providers[normalized.provider];
}

export function switchAgentRunProvider(settings: AgentRunSettings, provider: AgentRunProvider): AgentRunSettings {
  return normalizeAgentRunSettings({
    ...settings,
    provider,
  });
}

export function updateProviderRuntimeSettings(
  settings: AgentRunSettings,
  provider: AgentRunProvider,
  patch: Partial<ProviderRuntimeSettings>,
): AgentRunSettings {
  return normalizeAgentRunSettings({
    ...settings,
    providers: {
      ...settings.providers,
      [provider]: {
        ...settings.providers[provider],
        ...patch,
      },
    },
  });
}

function defaultProviderRuntimeSettings(): ProviderRuntimeSettingsByProvider {
  const defaults = Object.fromEntries(
    MODEL_PROVIDERS.map((provider) => [
      provider.id,
      {
        baseUrl: provider.baseUrl,
        model: getDefaultModelForProvider(provider.id),
        apiKey: "",
      },
    ]),
  ) as ProviderRuntimeSettingsByProvider;

  const provider = defaultProviderFromEnvironment();
  defaults[provider] = normalizeProviderRuntimeSettings(provider, {
    ...defaults[provider],
    baseUrl: environmentString("VITE_AGENT_RUN_BASE_URL") ?? defaults[provider].baseUrl,
    model: environmentString("VITE_AGENT_RUN_MODEL") ?? defaults[provider].model,
  });

  return defaults;
}

function normalizeProviderRuntimeSettings(
  provider: AgentRunProvider,
  value: Record<string, unknown>,
): ProviderRuntimeSettings {
  const providerConfig = getProviderConfig(provider);
  const baseUrl = stringValue(value.baseUrl) ?? providerConfig.baseUrl;
  const model = stringValue(value.model) ?? providerConfig.defaultModel;
  const apiKey = stringValue(value.apiKey) ?? "";

  return {
    baseUrl: baseUrl ? normalizeBaseUrl(baseUrl) : "",
    model,
    apiKey,
  };
}

function browserStorage(): AgentRunSettingsStorage | undefined {
  return typeof window === "undefined" ? undefined : window.localStorage;
}

function applyEnvironmentOverrides(settings: AgentRunSettings): AgentRunSettings {
  const provider = defaultProviderFromEnvironment();
  if (!environmentString("VITE_AGENT_RUN_PROVIDER")) {
    return settings;
  }

  return normalizeAgentRunSettings({
    ...settings,
    provider,
    providers: {
      ...settings.providers,
      [provider]: {
        ...settings.providers[provider],
        baseUrl: environmentString("VITE_AGENT_RUN_BASE_URL") ?? settings.providers[provider].baseUrl,
        model: environmentString("VITE_AGENT_RUN_MODEL") ?? settings.providers[provider].model,
      },
    },
  });
}

function defaultProviderFromEnvironment(): AgentRunProvider {
  const provider = environmentString("VITE_AGENT_RUN_PROVIDER");
  return isAgentRunProvider(provider) ? provider : "fake";
}

function environmentString(key: string): string | undefined {
  const value = (import.meta.env as Record<string, string | undefined>)[key];
  return stringValue(value);
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

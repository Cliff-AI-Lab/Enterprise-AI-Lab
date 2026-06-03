import { getActiveProviderRuntime, type AgentRunSettings } from "./agentSettings";
import { getProviderConfig, type ProviderFetchedModel } from "./modelProviders";

type ProviderRequestOptions = {
  endpoint?: string;
  fetchFn?: typeof fetch;
};

export async function testProviderSettings(
  settings: AgentRunSettings,
  options: ProviderRequestOptions = {},
): Promise<{ ok: boolean; message: string }> {
  const provider = getProviderConfig(settings.provider);
  const runtime = getActiveProviderRuntime(settings);
  if (provider.transport === "fake") {
    return {
      ok: true,
      message: "Local preview does not call a model server",
    };
  }
  if (provider.requiresApiKey && !runtime.apiKey.trim()) {
    return {
      ok: false,
      message: `${provider.name} API key is required for live model calls.`,
    };
  }
  void options;
  return {
    ok: true,
    message: "Settings are stored locally in this UI package",
  };
}

export function providerRuntimeSignature(settings: AgentRunSettings): string {
  const runtime = getActiveProviderRuntime(settings);
  return JSON.stringify({
    provider: settings.provider,
    baseUrl: runtime.baseUrl,
    apiKey: runtime.apiKey,
  });
}

export function canTestProviderSettings(settings: AgentRunSettings): boolean {
  const provider = getProviderConfig(settings.provider);
  const runtime = getActiveProviderRuntime(settings);
  return provider.transport !== "fake" && runtime.baseUrl.trim().length > 0;
}

export function providerUsesServerApiKey(settings: AgentRunSettings): boolean {
  void settings;
  return false;
}

export async function saveProviderApiKey(
  settings: AgentRunSettings,
  options: ProviderRequestOptions = {},
): Promise<{ ok: boolean; message: string }> {
  const runtime = getActiveProviderRuntime(settings);
  const apiKey = runtime.apiKey.trim();
  if (!apiKey) {
    return {
      ok: true,
      message: "No API key to save",
    };
  }

  void settings;
  void options;
  return {
    ok: true,
    message: apiKey ? "Saved locally" : "No API key to save",
  };
}

export async function fetchProviderModelOptions(
  settings: AgentRunSettings,
  options: ProviderRequestOptions = {},
): Promise<{ ok: boolean; models: ProviderFetchedModel[] }> {
  const provider = getProviderConfig(settings.provider);
  const runtime = getActiveProviderRuntime(settings);
  if (provider.transport === "fake") {
    return {
      ok: true,
      models: provider.models,
    };
  }

  void runtime;
  void options;
  return {
    ok: true,
    models: provider.models,
  };
}

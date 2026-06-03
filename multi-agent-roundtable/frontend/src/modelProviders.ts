export type ModelCapability =
  | "reasoning"
  | "vision"
  | "code"
  | "long-context"
  | "structured-output"
  | "tools"
  | "web-search";

export type ModelOption = {
  id: string;
  name: string;
  provider: string;
  contextLength: number;
  maxOutputTokens: number;
  defaultTemperature: number;
  capabilities?: ModelCapability[];
};

export type ProviderFetchedModel = {
  id: string;
  name?: string;
  provider?: string;
  contextLength?: number;
  maxOutputTokens?: number;
};

export type AgentRunProvider =
  | "fake"
  | "lmstudio"
  | "ruidong"
  | "openrouter"
  | "openai"
  | "deepseek"
  | "zhipu"
  | "kimi"
  | "qwen";

export type ProviderTransport = "fake" | "openai-compatible";

export type ProviderConfig = {
  id: AgentRunProvider;
  name: string;
  description: string;
  baseUrl: string;
  keyPrefix: string;
  keyLink?: string;
  requiresApiKey: boolean;
  transport: ProviderTransport;
  defaultModel: string;
  models: ModelOption[];
};

export const MODEL_PROVIDERS: ProviderConfig[] = [
  {
    id: "fake",
    name: "Local preview",
    description: "Built-in chat preview. No model server call.",
    baseUrl: "",
    keyPrefix: "",
    requiresApiKey: false,
    transport: "fake",
    defaultModel: "local-preview",
    models: [
      {
        id: "local-preview",
        name: "Local preview",
        provider: "AgentTelegram",
        contextLength: 0,
        maxOutputTokens: 0,
        defaultTemperature: 0,
      },
    ],
  },
  {
    id: "lmstudio",
    name: "LM Studio",
    description: "Local OpenAI-compatible server at localhost.",
    baseUrl: "http://127.0.0.1:1234/v1",
    keyPrefix: "",
    requiresApiKey: false,
    transport: "openai-compatible",
    defaultModel: "local-model",
    models: [
      {
        id: "local-model",
        name: "Current loaded model",
        provider: "LM Studio",
        contextLength: 32768,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
      },
    ],
  },
  {
    id: "ruidong",
    name: "Ruidong AI",
    description: "OpenAI-compatible aggregator for chat and code models.",
    baseUrl: "https://iruidong.com/v1",
    keyPrefix: "sk-rd",
    keyLink: "https://iruidong.com/help/zh-CN#models-list",
    requiresApiKey: true,
    transport: "openai-compatible",
    defaultModel: "ruidong-flash",
    models: [
      {
        id: "ruidong-flash",
        name: "Ruidong Flash",
        provider: "Ruidong AI",
        contextLength: 128000,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["code", "tools"],
      },
      {
        id: "ruidong-plus",
        name: "Ruidong Plus",
        provider: "Ruidong AI",
        contextLength: 128000,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["reasoning", "code", "tools"],
      },
      {
        id: "ruidong-pro-intl",
        name: "Ruidong Pro Intl",
        provider: "Ruidong AI",
        contextLength: 128000,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["reasoning", "code", "tools"],
      },
      {
        id: "claude-sonnet-4-5",
        name: "Claude Sonnet 4.5",
        provider: "Anthropic",
        contextLength: 200000,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["reasoning", "vision", "code", "long-context", "tools"],
      },
      {
        id: "qwen3-coder",
        name: "Qwen3 Coder",
        provider: "Ruidong AI",
        contextLength: 131072,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["code", "long-context", "tools"],
      },
      {
        id: "deepseek-v4-flash",
        name: "DeepSeek V4 Flash",
        provider: "Ruidong AI",
        contextLength: 128000,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["reasoning", "code", "tools"],
      },
      {
        id: "deepseek-v3",
        name: "DeepSeek V3",
        provider: "Ruidong AI",
        contextLength: 64000,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["code", "tools"],
      },
      {
        id: "glm-5-turbo",
        name: "GLM-5 Turbo",
        provider: "Ruidong AI",
        contextLength: 128000,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["reasoning", "code", "tools"],
      },
      {
        id: "qwen-vl",
        name: "Qwen VL",
        provider: "Ruidong AI",
        contextLength: 32768,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["vision", "tools"],
      },
    ],
  },
  {
    id: "openrouter",
    name: "OpenRouter",
    description: "Single OpenAI-compatible API for many hosted models.",
    baseUrl: "https://openrouter.ai/api/v1",
    keyPrefix: "sk-or-",
    keyLink: "https://openrouter.ai/keys",
    requiresApiKey: true,
    transport: "openai-compatible",
    defaultModel: "deepseek/deepseek-v4-flash",
    models: [
      {
        id: "deepseek/deepseek-v4-flash",
        name: "DeepSeek V4 Flash",
        provider: "DeepSeek",
        contextLength: 1048576,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["code", "long-context", "tools"],
      },
      {
        id: "anthropic/claude-sonnet-4",
        name: "Claude Sonnet 4",
        provider: "Anthropic",
        contextLength: 200000,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["vision", "code", "long-context", "tools"],
      },
      {
        id: "anthropic/claude-3.5-sonnet",
        name: "Claude 3.5 Sonnet",
        provider: "Anthropic",
        contextLength: 200000,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["vision", "code", "long-context", "tools"],
      },
      {
        id: "openai/gpt-4o",
        name: "GPT-4o",
        provider: "OpenAI",
        contextLength: 128000,
        maxOutputTokens: 16384,
        defaultTemperature: 1,
        capabilities: ["vision", "code", "long-context", "tools"],
      },
      {
        id: "openai/gpt-4o-mini",
        name: "GPT-4o Mini",
        provider: "OpenAI",
        contextLength: 128000,
        maxOutputTokens: 16384,
        defaultTemperature: 1,
        capabilities: ["vision", "long-context", "tools"],
      },
      {
        id: "google/gemini-2.0-flash-exp:free",
        name: "Gemini 2.0 Flash Free",
        provider: "Google",
        contextLength: 1000000,
        maxOutputTokens: 8192,
        defaultTemperature: 1,
        capabilities: ["vision", "long-context", "tools"],
      },
      {
        id: "deepseek/deepseek-v4-pro",
        name: "DeepSeek V4 Pro",
        provider: "DeepSeek",
        contextLength: 64000,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["code", "tools"],
      },
      {
        id: "deepseek/deepseek-chat",
        name: "DeepSeek Chat",
        provider: "DeepSeek",
        contextLength: 64000,
        maxOutputTokens: 8192,
        defaultTemperature: 1,
        capabilities: ["code", "tools"],
      },
    ],
  },
  {
    id: "openai",
    name: "OpenAI",
    description: "OpenAI chat models through the platform API.",
    baseUrl: "https://api.openai.com/v1",
    keyPrefix: "sk-",
    keyLink: "https://platform.openai.com/api-keys",
    requiresApiKey: true,
    transport: "openai-compatible",
    defaultModel: "gpt-4o-mini",
    models: [
      {
        id: "gpt-4o",
        name: "GPT-4o",
        provider: "OpenAI",
        contextLength: 128000,
        maxOutputTokens: 16384,
        defaultTemperature: 1,
        capabilities: ["vision", "code", "long-context", "tools"],
      },
      {
        id: "gpt-4o-mini",
        name: "GPT-4o Mini",
        provider: "OpenAI",
        contextLength: 128000,
        maxOutputTokens: 16384,
        defaultTemperature: 1,
        capabilities: ["vision", "long-context", "tools"],
      },
      {
        id: "gpt-4-turbo",
        name: "GPT-4 Turbo",
        provider: "OpenAI",
        contextLength: 128000,
        maxOutputTokens: 4096,
        defaultTemperature: 1,
        capabilities: ["vision", "long-context", "tools"],
      },
      {
        id: "o1-mini",
        name: "o1 Mini",
        provider: "OpenAI",
        contextLength: 128000,
        maxOutputTokens: 65536,
        defaultTemperature: 1,
        capabilities: ["reasoning", "code", "long-context"],
      },
    ],
  },
  {
    id: "deepseek",
    name: "DeepSeek",
    description: "OpenAI-compatible DeepSeek chat and reasoner models.",
    baseUrl: "https://api.deepseek.com",
    keyPrefix: "sk-",
    keyLink: "https://platform.deepseek.com/api_keys",
    requiresApiKey: true,
    transport: "openai-compatible",
    defaultModel: "deepseek-chat",
    models: [
      {
        id: "deepseek-chat",
        name: "DeepSeek Chat",
        provider: "DeepSeek",
        contextLength: 64000,
        maxOutputTokens: 8192,
        defaultTemperature: 1,
        capabilities: ["code", "tools"],
      },
      {
        id: "deepseek-coder",
        name: "DeepSeek Coder",
        provider: "DeepSeek",
        contextLength: 64000,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["code", "tools"],
      },
      {
        id: "deepseek-reasoner",
        name: "DeepSeek R1",
        provider: "DeepSeek",
        contextLength: 64000,
        maxOutputTokens: 8192,
        defaultTemperature: 0.6,
        capabilities: ["reasoning", "code"],
      },
    ],
  },
  {
    id: "zhipu",
    name: "Zhipu AI",
    description: "OpenAI-compatible GLM models.",
    baseUrl: "https://open.bigmodel.cn/api/paas/v4",
    keyPrefix: "",
    keyLink: "https://open.bigmodel.cn/usercenter/apikeys",
    requiresApiKey: true,
    transport: "openai-compatible",
    defaultModel: "glm-4-flash",
    models: [
      {
        id: "glm-4-plus",
        name: "GLM-4 Plus",
        provider: "Zhipu",
        contextLength: 128000,
        maxOutputTokens: 4096,
        defaultTemperature: 0.7,
        capabilities: ["long-context", "tools"],
      },
      {
        id: "glm-4-air",
        name: "GLM-4 Air",
        provider: "Zhipu",
        contextLength: 128000,
        maxOutputTokens: 4096,
        defaultTemperature: 0.7,
        capabilities: ["long-context", "tools"],
      },
      {
        id: "glm-4-flash",
        name: "GLM-4 Flash",
        provider: "Zhipu",
        contextLength: 128000,
        maxOutputTokens: 4096,
        defaultTemperature: 0.7,
        capabilities: ["long-context", "tools"],
      },
      {
        id: "glm-4v-plus",
        name: "GLM-4V Plus",
        provider: "Zhipu",
        contextLength: 8192,
        maxOutputTokens: 4096,
        defaultTemperature: 0.7,
        capabilities: ["vision", "tools"],
      },
    ],
  },
  {
    id: "kimi",
    name: "Moonshot",
    description: "OpenAI-compatible Moonshot Kimi models.",
    baseUrl: "https://api.moonshot.cn/v1",
    keyPrefix: "sk-",
    keyLink: "https://platform.moonshot.cn/console/api-keys",
    requiresApiKey: true,
    transport: "openai-compatible",
    defaultModel: "moonshot-v1-32k",
    models: [
      {
        id: "moonshot-v1-8k",
        name: "Moonshot v1 8K",
        provider: "Moonshot",
        contextLength: 8000,
        maxOutputTokens: 4096,
        defaultTemperature: 0.7,
        capabilities: ["tools"],
      },
      {
        id: "moonshot-v1-32k",
        name: "Moonshot v1 32K",
        provider: "Moonshot",
        contextLength: 32000,
        maxOutputTokens: 4096,
        defaultTemperature: 0.7,
        capabilities: ["tools"],
      },
      {
        id: "moonshot-v1-128k",
        name: "Moonshot v1 128K",
        provider: "Moonshot",
        contextLength: 128000,
        maxOutputTokens: 4096,
        defaultTemperature: 0.7,
        capabilities: ["long-context", "tools", "web-search"],
      },
    ],
  },
  {
    id: "qwen",
    name: "Alibaba Cloud",
    description: "OpenAI-compatible DashScope Qwen models.",
    baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    keyPrefix: "sk-",
    keyLink: "https://dashscope.console.aliyun.com/apiKey",
    requiresApiKey: true,
    transport: "openai-compatible",
    defaultModel: "qwen-plus",
    models: [
      {
        id: "qwen-max",
        name: "Qwen Max",
        provider: "Alibaba",
        contextLength: 32000,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["code", "tools"],
      },
      {
        id: "qwen-plus",
        name: "Qwen Plus",
        provider: "Alibaba",
        contextLength: 131072,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["long-context", "tools"],
      },
      {
        id: "qwen-turbo",
        name: "Qwen Turbo",
        provider: "Alibaba",
        contextLength: 131072,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["long-context", "tools"],
      },
      {
        id: "qwen2.5-coder-32b-instruct",
        name: "Qwen 2.5 Coder 32B",
        provider: "Alibaba",
        contextLength: 131072,
        maxOutputTokens: 8192,
        defaultTemperature: 0.7,
        capabilities: ["code", "long-context", "tools"],
      },
    ],
  },
];

const providerIds = new Set(MODEL_PROVIDERS.map((provider) => provider.id));

export function getProviderConfig(providerId: AgentRunProvider): ProviderConfig {
  return MODEL_PROVIDERS.find((provider) => provider.id === providerId) ?? MODEL_PROVIDERS[0];
}

export function getDefaultModelForProvider(providerId: AgentRunProvider): string {
  return getProviderConfig(providerId).defaultModel;
}

export function isAgentRunProvider(value: unknown): value is AgentRunProvider {
  return typeof value === "string" && providerIds.has(value as AgentRunProvider);
}

export function isRemoteAgentRunProvider(providerId: AgentRunProvider): boolean {
  return getProviderConfig(providerId).transport === "openai-compatible";
}

export function filterProviderModels(models: readonly ModelOption[], query: string, limit = 10): ModelOption[] {
  const normalizedQuery = normalizeModelSearchText(query);
  if (!normalizedQuery) {
    return models.slice(0, limit);
  }

  const tokens = normalizedQuery.split(" ");
  return models
    .filter((model) => {
      const searchable = normalizeModelSearchText(`${model.provider} ${model.name} ${model.id}`);
      return tokens.every((token) => searchable.includes(token));
    })
    .slice(0, limit);
}

export function mergeProviderModels(
  catalogModels: readonly ModelOption[],
  fetchedModels: readonly ProviderFetchedModel[],
): ModelOption[] {
  const byId = new Map<string, ModelOption>();
  for (const model of catalogModels) {
    byId.set(model.id, model);
  }

  for (const model of fetchedModels) {
    if (!model.id.trim()) {
      continue;
    }

    const catalogModel = byId.get(model.id);
    byId.set(model.id, {
      id: model.id,
      name: model.name?.trim() || catalogModel?.name || model.id,
      provider: model.provider?.trim() || catalogModel?.provider || "Provider",
      contextLength: model.contextLength ?? catalogModel?.contextLength ?? 0,
      maxOutputTokens: model.maxOutputTokens ?? catalogModel?.maxOutputTokens ?? 0,
      defaultTemperature: catalogModel?.defaultTemperature ?? 0.7,
      ...(catalogModel?.capabilities ? { capabilities: catalogModel.capabilities } : {}),
    });
  }

  return [...byId.values()];
}

export function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.trim().replace(/\/+$/, "");
}

function normalizeModelSearchText(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

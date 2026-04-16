// 睿动统一AI平台 — OpenAI兼容接口
const IRUIDONG_BASE_URL = "https://iruidong.com/v1"

interface ChatMessage {
  role: "system" | "user" | "assistant"
  content: string
}

interface ChatCompletionResponse {
  choices: { message: { content: string } }[]
}

function getApiKey(): string {
  return (import.meta as any).env?.VITE_IRUIDONG_API_KEY ?? "sk-needkey"
}

export async function chatCompletion(
  messages: ChatMessage[],
  options?: { model?: string; temperature?: number; maxTokens?: number }
): Promise<string> {
  const { model = "deepseek-v3.1", temperature = 0.7, maxTokens = 2000 } = options ?? {}

  const response = await fetch(`${IRUIDONG_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getApiKey()}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages,
      temperature,
      max_tokens: maxTokens,
    }),
  })

  if (!response.ok) {
    throw new Error(`iRuidong API error: ${response.status} ${response.statusText}`)
  }

  const data: ChatCompletionResponse = await response.json()
  return data.choices[0].message.content
}

export async function chatCompletionStream(
  messages: ChatMessage[],
  onChunk: (text: string) => void,
  options?: { model?: string; temperature?: number }
): Promise<void> {
  const { model = "deepseek-v3.1", temperature = 0.7 } = options ?? {}

  const response = await fetch(`${IRUIDONG_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${getApiKey()}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages,
      temperature,
      stream: true,
    }),
  })

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()
  if (!reader) throw new Error("No response body")

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const text = decoder.decode(value)
    for (const line of text.split("\n")) {
      if (line.startsWith("data: ") && line !== "data: [DONE]") {
        try {
          const json = JSON.parse(line.slice(6))
          const content = json.choices?.[0]?.delta?.content
          if (content) onChunk(content)
        } catch { /* skip parse errors in stream */ }
      }
    }
  }
}

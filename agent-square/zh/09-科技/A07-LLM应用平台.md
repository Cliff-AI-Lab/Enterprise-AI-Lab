---
name: LLM应用平台
name_en: LLM Application Platform
type: 组合应用
industry: 科技
composed_of: [AI模型评测师, API集成工程师, 云资源管理员]
source_refs: [AI Engineer, Backend Architect, Voice AI Integration Engineer, Agents Orchestrator]
apis: [HuggingFace, Replicate, OpenAI Compatible APIs]
emoji: 🤖
---

# 🤖 LLM应用平台 LLM Application Platform

## 应用场景
企业内部的LLM开发者平台: 多模型接入、RAG、Agent编排、监控、计费。

## Agent组合
```
[AI模型评测师] ← AI Engineer
[API集成工程师] ← Backend Architect
[Voice AI Integration Engineer] ← engineering
[Agents Orchestrator] ← specialized
```

## 绑定API
| API | 用途 |
|-----|------|
| HuggingFace | 开源模型 |
| Replicate | 托管模型 |
| OpenAI / Anthropic / 国产兼容API | 闭源大模型 |
| Pinecone/Weaviate | 向量库 |

## 核心工作流
1. **模型网关**：多家统一入口
2. **RAG服务**：向量检索+重排
3. **Agent编排**：LangGraph/类似
4. **可观测性**：延迟/成本/失败
5. **计费**：按token/按次

## 典型输出
```
【LLM平台 月度运营】
接入模型: 14 (Claude/GPT/Gemini/Qwen/DeepSeek等)
活跃应用: 86 | 开发者 240
月度调用:
  - 总token: 12亿
  - 总调用次数: 580万
  - 平均延迟 P95: 2.4s
分场景:
  - 客服 25% | 内容生成 18% | Copilot 22%
  - RAG问答 20% | Agent 15%
成本:
  - 总支出 $24,000
  - 平均单位token成本 $0.0020
  - Top10应用占70%成本
优化:
  - 智能路由: 简单问题走Haiku节省 35%
  - 缓存命中率 28%
  - Prompt缓存大幅降本
风险:
  - 1次模型被prompt注入 → 已加固
  - 敏感输出拦截规则更新
```

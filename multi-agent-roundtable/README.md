# 多智能体协作平台 · 虚拟专家圆桌会议

温氏集团企业级多智能体决策辅助平台。基于**睿动 agent harness**(`rd-agent-core`)直连国产大模型(iruidong),让企业随时召集多个 AI 专家进行多视角讨论,模拟真实专家圆桌会议,沉淀为可导出的会议纪要。

> 运行时:Python + FastAPI,端口 `18790`,自带 Web UI(单文件多视图,零构建)。完全不依赖 OpenClaw。

## 功能(对齐 PRD P0 + P1)

| 模块 | 能力 |
|---|---|
| 专家智能体管理 | 创建/编辑/启停、头像配色、SOUL 人设、专业技能、专属模型;外部 API 注册;上传文件/抽取 wiki 做知识升级,可据知识快速生成业务专家 |
| 智能主持人 | 自动拆解议程(≥3,人工可确认/排序/增删)→ 安排发言顺序 → 调度专家 → 语义冲突检测与追问 → 阶段总结 → 最终结论 + 风险清单 + 行动建议 |
| 会议管理 | 1V1 / 多人圆桌两种模式;会议列表(按状态筛选)、详情时序回放;分步推进、人工确认 |
| 人类参与(P1) | 会议中随时发言(主持人优先回应)、指令式干预 |
| 纪要导出 | Markdown / Word(docx)/ PDF(含中文字体) |
| 监控仪表盘 | 进行中会议与可介入、正在讨论的专家、已形成纪要数、专家响应时长、超时/失败告警、人工接管(暂停/恢复/结束) |
| 多模型 | 睿动 key 遍历可用模型、按专家选模型 + 联通测试、失败自动降级 |
| 协作模式扩展 | 接龙 / 头脑风暴 / 打磨 三种多智能体协作模式,与圆桌共用一套事件协议 |

## 快速开始

```bash
cd multi-agent-roundtable/runtime/service
cp .env.example .env        # 填入 RUIDONG_API_KEY
uv sync                      # 或 pip install -e .
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18790
```

打开 http://127.0.0.1:18790 。

## 目录

- `runtime/service/` — 圆桌运行时(FastAPI):`app/main.py` 路由、`roundtable.py` 主持人编排、`modes.py` 三种协作模式、`experts.py` 预置专家、`knowledge.py` 知识检索、`skills.py` 技能、`export.py` 纪要导出、`store.py` sqlite 持久化、`static/index.html` 前端
- `runtime/agent-core/` — 睿动 agent harness 本地包(rd-agent-core / rd-llm-adapter / rd-agent-contracts)
- `docs/` — 需求 PRD 与设计文档
- `backend/` `frontend/` `personas/` — 早期 TelegramAgent(OpenClaw)产物,设计参考,非本运行时

> ⚠️ `runtime/service/.env` 含真实 API key,已被 `.gitignore` 排除,切勿提交。

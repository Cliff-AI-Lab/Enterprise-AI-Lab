"""专业技能目录:每个技能 = 一段注入专家 system prompt 的方法论指引。

轻量实现(prompt 注入),与知识层同思路保留升级 seam:
日后要让技能变成真实工具调用,在 SKILLS 条目上加 tool=ToolDefinition,
由 llm.generate 的 tools 参数透传给 rd-agent-core(框架已支持),调用方不变。
"""
from __future__ import annotations

SKILLS: list[dict] = [
    {
        "id": "finance-calc",
        "name": "财务测算",
        "desc": "投资回收期 / IRR / 现金流压力测试",
        "prompt": "发言涉及投资判断时,给出量化测算:投资回收期、关键假设下的现金流压力点、"
                  "敏感性区间(乐观/中性/悲观),并标注哪些数字是估算。",
    },
    {
        "id": "risk-stress",
        "name": "风险压力测试",
        "desc": "极端情景推演 / 触发条件-影响-兜底",
        "prompt": "对讨论的方案做极端情景推演:列出 1-2 个最致命的情景,"
                  "每个按「触发条件 → 影响 → 兜底动作」三段输出。",
    },
    {
        "id": "benchmark",
        "name": "行业对标",
        "desc": "对标头部企业 / 行业均值定位",
        "prompt": "把讨论对象与行业头部和行业均值对标:给出 1-2 个可比对象,"
                  "指出差距所在与差距量级(倍数或百分比区间)。",
    },
    {
        "id": "kn-cite",
        "name": "知识引用",
        "desc": "严格依据挂载的专业资料发言并标注出处",
        "prompt": "你挂载了专业资料:结论必须能追溯到资料中的依据,引用时点明出处片段;"
                  "资料没覆盖的部分明确说「资料未覆盖,以下是推断」。",
    },
    {
        "id": "swot",
        "name": "SWOT 分析",
        "desc": "优势/劣势/机会/威胁结构化拆解",
        "prompt": "适时用 SWOT 框架组织观点:各维度最多 2 条、必须具体,不写空泛形容词。",
    },
    {
        "id": "exec-path",
        "name": "落地路径拆解",
        "desc": "把建议拆成阶段计划与里程碑",
        "prompt": "给出建议时附最小落地路径:2-4 个阶段、每阶段的里程碑与可量化的验收标准。",
    },
]

SKILL_BY_ID = {s["id"]: s for s in SKILLS}


def skill_guidance(skill_ids: list[str]) -> str:
    """把专家选用的技能拼成 system prompt 注入块。"""
    chosen = [SKILL_BY_ID[i] for i in skill_ids if i in SKILL_BY_ID]
    if not chosen:
        return ""
    lines = [f"- {s['name']}:{s['prompt']}" for s in chosen]
    return "你具备以下专业技能,发言时按其方法论执行:\n" + "\n".join(lines)

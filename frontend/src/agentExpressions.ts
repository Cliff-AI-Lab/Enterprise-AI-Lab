import type { AgentRunTrigger } from "./agentRoomState";

export type AgentExpressionPhase =
  | "thinking"
  | "deciding"
  | "checking"
  | "composing"
  | "polishing"
  | "settled"
  | "idle"
  | "stuck";

export type AgentExpressionMotion = "tilt" | "nod" | "furrow" | "shrug" | "scan" | "still";

export type AgentExpressionTemplate = {
  label: string;
  action: string;
  detail: string;
  motion: AgentExpressionMotion;
};

export type AgentExpression = AgentExpressionTemplate & {
  phase: AgentExpressionPhase;
  tone: "active" | "calm" | "done" | "warning";
};

export type AgentExpressionContext = {
  agentId: string;
  runId?: string;
  trigger?: AgentRunTrigger;
  runStatus?: string;
  streaming?: boolean;
  hasText?: boolean;
};

// generic fallback expressions — short, vivid, Chinese
export const agentExpressionLexicon: Record<AgentExpressionPhase, readonly AgentExpressionTemplate[]> = {
  thinking: [
    { label: "thinking", action: "皱了皱眉", detail: "", motion: "furrow" },
    { label: "thinking", action: "歪头想了想", detail: "", motion: "tilt" },
    { label: "thinking", action: "盯着屏幕发呆", detail: "", motion: "scan" },
    { label: "thinking", action: "捏着下巴", detail: "", motion: "tilt" },
  ],
  deciding: [
    { label: "choosing", action: "环顾一圈", detail: "", motion: "scan" },
    { label: "choosing", action: "点了点头", detail: "", motion: "nod" },
    { label: "choosing", action: "停顿了一下", detail: "", motion: "still" },
  ],
  checking: [
    { label: "checking", action: "眯起眼睛", detail: "", motion: "furrow" },
    { label: "checking", action: "凑近一点", detail: "", motion: "scan" },
    { label: "checking", action: "皱眉重读", detail: "", motion: "furrow" },
  ],
  composing: [
    { label: "typing", action: "正在敲字", detail: "", motion: "nod" },
    { label: "typing", action: "手指敲键盘", detail: "", motion: "nod" },
    { label: "typing", action: "在写了", detail: "", motion: "nod" },
  ],
  polishing: [
    { label: "shaping", action: "调了调用词", detail: "", motion: "tilt" },
    { label: "shaping", action: "再读一遍", detail: "", motion: "nod" },
    { label: "shaping", action: "斟酌片刻", detail: "", motion: "still" },
  ],
  settled: [
    { label: "sent", action: "发出去了", detail: "", motion: "still" },
    { label: "sent", action: "靠回椅背", detail: "", motion: "still" },
  ],
  idle: [
    { label: "online", action: "在线，等你说", detail: "", motion: "still" },
    { label: "online", action: "看着你呢", detail: "", motion: "still" },
  ],
  stuck: [
    { label: "paused", action: "耸了耸肩", detail: "", motion: "shrug" },
    { label: "paused", action: "卡了一下", detail: "", motion: "shrug" },
  ],
};

const agentExpressionOverrides: Record<string, Partial<Record<AgentExpressionPhase, readonly AgentExpressionTemplate[]>>> = {
  main: {
    thinking: [
      { label: "routing", action: "在分流", detail: "", motion: "scan" },
      { label: "routing", action: "看谁该接", detail: "", motion: "tilt" },
    ],
    deciding: [
      { label: "routing", action: "把活派给谁", detail: "", motion: "scan" },
      { label: "routing", action: "判断该谁回", detail: "", motion: "nod" },
    ],
    idle: [
      { label: "watching", action: "静静听着", detail: "", motion: "still" },
    ],
  },
  sarah: {
    thinking: [
      { label: "drafting", action: "把空话划掉", detail: "", motion: "furrow" },
      { label: "drafting", action: "敲了敲嘴唇", detail: "", motion: "tilt" },
      { label: "drafting", action: "在挑词", detail: "", motion: "scan" },
      { label: "drafting", action: "盯着\"打造\"两个字", detail: "", motion: "furrow" },
    ],
    checking: [
      { label: "checking", action: "圈出可疑形容词", detail: "", motion: "furrow" },
      { label: "checking", action: "数了数字数", detail: "", motion: "scan" },
      { label: "checking", action: "盯着\"赋能\"皱眉", detail: "", motion: "furrow" },
    ],
    composing: [
      { label: "writing", action: "正在写", detail: "", motion: "nod" },
      { label: "writing", action: "短句拆开", detail: "", motion: "nod" },
      { label: "writing", action: "在删修饰词", detail: "", motion: "furrow" },
    ],
    polishing: [
      { label: "polishing", action: "把这句砍一半", detail: "", motion: "furrow" },
      { label: "polishing", action: "再读一遍", detail: "", motion: "nod" },
      { label: "polishing", action: "形容词又删了俩", detail: "", motion: "still" },
    ],
    settled: [
      { label: "sent", action: "稿子甩出去了", detail: "", motion: "still" },
      { label: "sent", action: "下一稿等你回", detail: "", motion: "still" },
    ],
    idle: [
      { label: "online", action: "等你提需求", detail: "", motion: "still" },
      { label: "online", action: "笔尖搁着", detail: "", motion: "still" },
    ],
  },
  alex: {
    thinking: [
      { label: "framing", action: "在排优先级", detail: "", motion: "scan" },
      { label: "framing", action: "心算 RICE 分数", detail: "", motion: "tilt" },
      { label: "framing", action: "在拆需求", detail: "", motion: "furrow" },
    ],
    deciding: [
      { label: "framing", action: "决定砍哪条", detail: "", motion: "nod" },
      { label: "framing", action: "选 MVP 边界", detail: "", motion: "scan" },
    ],
    checking: [
      { label: "checking", action: "问\"谁会用\"", detail: "", motion: "furrow" },
      { label: "checking", action: "找量化指标", detail: "", motion: "scan" },
      { label: "checking", action: "在想验证路径", detail: "", motion: "tilt" },
    ],
    composing: [
      { label: "drafting", action: "在写 PRD", detail: "", motion: "nod" },
      { label: "drafting", action: "列优先级表", detail: "", motion: "nod" },
    ],
    polishing: [
      { label: "polishing", action: "把决策写成 memo", detail: "", motion: "nod" },
      { label: "polishing", action: "重排了一下", detail: "", motion: "tilt" },
    ],
    settled: [
      { label: "sent", action: "memo 已发", detail: "", motion: "still" },
      { label: "sent", action: "等你确认", detail: "", motion: "still" },
    ],
    idle: [
      { label: "online", action: "等你抛需求", detail: "", motion: "still" },
    ],
  },
  kai: {
    thinking: [
      { label: "debugging", action: "在定位 bug", detail: "", motion: "furrow" },
      { label: "debugging", action: "盯着 stacktrace", detail: "", motion: "scan" },
      { label: "debugging", action: "在二分排查", detail: "", motion: "furrow" },
      { label: "debugging", action: "想 root cause", detail: "", motion: "tilt" },
    ],
    checking: [
      { label: "checking", action: "在复现一次", detail: "", motion: "scan" },
      { label: "checking", action: "盯着 diff", detail: "", motion: "furrow" },
      { label: "checking", action: "翻 git blame", detail: "", motion: "scan" },
    ],
    composing: [
      { label: "coding", action: "在写补丁", detail: "", motion: "nod" },
      { label: "coding", action: "敲键盘中", detail: "", motion: "nod" },
      { label: "coding", action: "在改代码", detail: "", motion: "nod" },
    ],
    polishing: [
      { label: "reviewing", action: "把日志删了", detail: "", motion: "furrow" },
      { label: "reviewing", action: "再过一遍 diff", detail: "", motion: "nod" },
      { label: "reviewing", action: "缩了缩抽象", detail: "", motion: "still" },
    ],
    settled: [
      { label: "sent", action: "patch 发了", detail: "", motion: "still" },
      { label: "sent", action: "等你跑测试", detail: "", motion: "still" },
    ],
    stuck: [
      { label: "paused", action: "复现不出来", detail: "", motion: "shrug" },
      { label: "paused", action: "信号不够", detail: "", motion: "shrug" },
    ],
    idle: [
      { label: "online", action: "等你扔问题", detail: "", motion: "still" },
    ],
  },
};

export function pickAgentExpression(context: AgentExpressionContext): AgentExpression {
  const phase = expressionPhaseForContext(context);
  const templates = agentExpressionOverrides[context.agentId]?.[phase] ?? agentExpressionLexicon[phase];
  const template = templates[stableIndex(`${context.runId ?? "idle"}:${context.agentId}:${phase}`, templates.length)];

  return {
    ...template,
    phase,
    tone: toneForPhase(phase),
  };
}

export function activityCueTextForExpression(expression: Pick<AgentExpression, "action" | "detail">): string {
  return expression.detail ? `${expression.action} · ${expression.detail}` : expression.action;
}

export function expressionPhaseForContext(context: AgentExpressionContext): AgentExpressionPhase {
  if (context.runStatus === "error" || context.runStatus === "stalled" || context.runStatus === "awaiting_input") {
    return "stuck";
  }

  if (!context.runStatus || context.runStatus === "idle") {
    return "idle";
  }

  if (!context.streaming && context.runStatus !== "running") {
    return "settled";
  }

  if (context.trigger === "convene" && context.agentId === "main" && !context.hasText) {
    return "deciding";
  }

  if (context.agentId === "sarah") {
    return context.hasText ? "composing" : "thinking";
  }

  if (context.agentId === "alex") {
    return context.hasText ? "polishing" : "thinking";
  }

  if (context.agentId === "kai") {
    return context.hasText ? "composing" : "thinking";
  }

  return context.hasText ? "composing" : "thinking";
}

function toneForPhase(phase: AgentExpressionPhase): AgentExpression["tone"] {
  if (phase === "settled") {
    return "done";
  }
  if (phase === "idle") {
    return "calm";
  }
  if (phase === "stuck") {
    return "warning";
  }

  return "active";
}

function stableIndex(seed: string, count: number): number {
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) | 0;
  }

  return Math.abs(hash) % count;
}

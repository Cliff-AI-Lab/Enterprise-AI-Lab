import type { AgentExpression } from "./agentExpressions";

export type AgentRunDisplayInput = {
  expression: AgentExpression;
  hasText: boolean;
  status: string;
  activityCueLength: number;
};

export type AgentRunDisplayState = {
  showActivityCue: boolean;
  showTypingWait: boolean;
  showReplyBubble: boolean;
  avatarMotionClass: string;
  cueDurationMs: number;
  typingDelayMs: number;
};

export function agentRunDisplayState({
  expression,
  hasText,
  status,
  activityCueLength,
}: AgentRunDisplayInput): AgentRunDisplayState {
  const runningWithoutText = status === "running" && !hasText;
  const cueDurationMs = Math.min(1800, Math.max(900, activityCueLength * 28));

  return {
    showActivityCue: runningWithoutText,
    showTypingWait: runningWithoutText,
    showReplyBubble: hasText || status === "error" || status === "stalled",
    avatarMotionClass: runningWithoutText && expression.motion !== "still" ? `motion-${expression.motion}` : "",
    cueDurationMs,
    typingDelayMs: cueDurationMs + 240,
  };
}

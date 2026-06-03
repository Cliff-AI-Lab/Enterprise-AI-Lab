export type ContextPanelSection = "memoryApproval" | "replyStatus" | "approvedContext" | "notes";

export type ContextPanelFocusInput = {
  artifactCount: number;
  hasApprovedMemory: boolean;
  memoryProposalCount: number;
  runStatus: string;
};

const attentionRunStatuses = new Set(["running", "awaiting_input", "stalled", "error"]);

export function contextPanelFocusSections(input: ContextPanelFocusInput): ContextPanelSection[] {
  const sections: ContextPanelSection[] = [];

  if (input.memoryProposalCount > 0) {
    sections.push("memoryApproval");
  }

  if (attentionRunStatuses.has(input.runStatus)) {
    sections.push("replyStatus");
  }

  if (input.hasApprovedMemory) {
    sections.push("approvedContext");
  }

  if (input.artifactCount > 0) {
    sections.push("notes");
  }

  return sections;
}

export function shouldExposeContextPanel(input: ContextPanelFocusInput): boolean {
  return contextPanelFocusSections(input).length > 0;
}

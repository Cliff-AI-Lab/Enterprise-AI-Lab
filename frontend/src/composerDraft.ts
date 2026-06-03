export const initialComposerDraft = "";

export function clearComposerDraftAfterSend(
  setDraft: (value: string) => void,
  schedule: (callback: () => void) => void = (callback) => window.setTimeout(callback, 0),
): void {
  setDraft("");
  schedule(() => setDraft(""));
}

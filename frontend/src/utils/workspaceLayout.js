export const LATEST_THRESHOLD = 96;
export function isNearLatest({ scrollHeight, scrollTop, clientHeight }) {
  return scrollHeight - scrollTop - clientHeight <= LATEST_THRESHOLD;
}

// An unmodified shortcut while focus is outside editable fields avoids OS/browser chords.
export function isNewConversationShortcut(event) {
  if (event.defaultPrevented || event.repeat || event.isComposing || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return false;
  if (event.key.toLowerCase() !== 'n') return false;
  const target = event.target;
  return !target?.isContentEditable && !target?.closest?.('input, textarea, select, [contenteditable]:not([contenteditable="false"]), [role="textbox"], dialog[open]');
}

export function scrollAdjustment(previous, next, followLatest) {
  if (!previous || followLatest) return { top: next.scrollHeight, newMessages: false };
  // Preserve the visible exchange when older history is prepended.
  if (previous.first !== next.first && previous.last === next.last) {
    return { top: previous.scrollTop + next.scrollHeight - previous.scrollHeight, newMessages: false };
  }
  return { top: null, newMessages: previous.last !== next.last };
}

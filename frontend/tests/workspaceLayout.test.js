import test from 'node:test';
import assert from 'node:assert/strict';
import { isNearLatest, scrollAdjustment, isNewConversationShortcut } from '../src/utils/workspaceLayout.js';

test('near-latest threshold distinguishes reading history from the bottom', () => {
  assert.equal(isNearLatest({ scrollHeight: 1000, clientHeight: 400, scrollTop: 550 }), true);
  assert.equal(isNearLatest({ scrollHeight: 1000, clientHeight: 400, scrollTop: 300 }), false);
  assert.equal(isNearLatest({ scrollHeight: 200, clientHeight: 400, scrollTop: 0 }), true);
});

test('a new answer does not pull a reader away from older messages', () => {
  const previous = { first: 'u1', last: 'a1', scrollHeight: 1000, scrollTop: 200 };
  const next = { first: 'u1', last: 'a2', scrollHeight: 1600 };
  assert.deepEqual(scrollAdjustment(previous, next, false), { top: null, newMessages: true });
  assert.deepEqual(scrollAdjustment(previous, next, true), { top: 1600, newMessages: false });
});

test('prepending older messages keeps the same visible content offset', () => {
  const previous = { first: 'u20', last: 'a25', scrollHeight: 1500, scrollTop: 100 };
  assert.deepEqual(scrollAdjustment(previous, { first: 'u1', last: 'a25', scrollHeight: 3000 }, false), { top: 1600, newMessages: false });
});

test('initial history opens at the latest exchange and metadata renders do not move a reader', () => {
  assert.deepEqual(scrollAdjustment(null, { scrollHeight: 900 }, false), { top: 900, newMessages: false });
  const previous = { first: 'u1', last: 'a1', scrollHeight: 1000, scrollTop: 100 };
  assert.deepEqual(scrollAdjustment(previous, { ...previous, scrollHeight: 1050 }, false), { top: null, newMessages: false });
});

const shortcut = (extra = {}) => ({ key: 'n', target: { closest: () => null }, ...extra });
test('new conversation shortcut avoids editable fields and open dialogs', () => {
  assert.equal(isNewConversationShortcut(shortcut()), true);
  assert.equal(isNewConversationShortcut(shortcut({ target: { isContentEditable: true } })), false);
  for (const element of ['input', 'textarea', 'select', '[role="textbox"]', 'dialog[open]']) {
    assert.equal(isNewConversationShortcut(shortcut({ target: { closest: selector => selector.includes(element) ? {} : null } })), false);
  }
});

test('shortcuts respect modifiers, composition, handled events and auto-repeat', () => {
  for (const flag of ['ctrlKey', 'metaKey', 'altKey', 'shiftKey', 'isComposing', 'repeat', 'defaultPrevented']) {
    assert.equal(isNewConversationShortcut(shortcut({ [flag]: true })), false);
  }
  assert.equal(isNewConversationShortcut(shortcut({ key: 'Escape' })), false);
});

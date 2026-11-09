import test from 'node:test';
import assert from 'node:assert/strict';
import { messageBlocks, inlineTokens, safeLink } from '../src/utils/messageFormatting.js';

test('formats headings, paragraphs, lists and quotes without losing text', () => {
  const blocks = messageBlocks('# Findings\n\nFirst **result**.\n\n- One\n- Two\n\n3. Third\n4. Fourth\n\n> A quotation');
  assert.deepEqual(blocks.map(b => b.type), ['heading', 'paragraph', 'list', 'list', 'quote']);
  assert.deepEqual(blocks[2].items, ['One', 'Two']);
  assert.equal(blocks[3].start, 3);
  assert.equal(blocks[4].text, 'A quotation');
});

test('preserves indentation, HTML and markdown inside fenced code', () => {
  const blocks = messageBlocks('```python\n  print("<script>not HTML</script>")\n# a comment\n```\n\nDone');
  assert.equal(blocks[0].type, 'code');
  assert.equal(blocks[0].language, 'python');
  assert.equal(blocks[0].text, '  print("<script>not HTML</script>")\n# a comment');
  assert.equal(blocks[1].text, 'Done');
});

test('supports tilde fences and incomplete code while retaining content', () => {
  assert.equal(messageBlocks('~~~js\na()\n~~~')[0].text, 'a()');
  assert.equal(messageBlocks('```\nunfinished')[0].text, 'unfinished');
});

test('an inner shorter fence cannot terminate a longer code fence', () => {
  assert.equal(messageBlocks('````md\n```js\nconst x = 1;\n```\n````')[0].text, '```js\nconst x = 1;\n```');
});

test('formats tables with explicit headers and rows', () => {
  const [table] = messageBlocks('| Name | Value |\n| :--- | ---: |\n| A | **12** |');
  assert.equal(table.type, 'table');
  assert.deepEqual(table.headers, ['Name', 'Value']);
  assert.deepEqual(table.rows, [['A', '**12**']]);
});

test('keeps HTML as text rather than producing HTML tokens', () => {
  assert.deepEqual(inlineTokens('<img src=x onerror=alert(1)>'), [{ type: 'text', text: '<img src=x onerror=alert(1)>' }]);
  assert.equal(messageBlocks('<script>alert(1)</script>')[0].type, 'paragraph');
});

test('inline formatting distinguishes code, emphasis, strong text and safe links', () => {
  assert.deepEqual(inlineTokens('`x` **bold** *em* [source](https://example.test/report)').filter(t => t.type !== 'text').map(t => t.type), ['code', 'strong', 'em', 'link']);
});

test('rejects executable, data and protocol-relative links', () => {
  for (const url of ['javascript:alert(1)', 'data:text/html,test', 'vbscript:msgbox(1)', '//example.test', '/relative', 'file:///etc/passwd']) assert.equal(safeLink(url), null);
  assert.equal(inlineTokens('[unsafe](javascript:alert%281%29)')[0].type, 'text');
  assert.equal(safeLink('https://example.test/report'), 'https://example.test/report');
  assert.equal(safeLink('mailto:person@example.test'), 'mailto:person@example.test');
});

test('blank input and Windows newlines do not create empty display blocks', () => {
  assert.deepEqual(messageBlocks(' \n\n'), []);
  assert.deepEqual(messageBlocks('one\r\ntwo'), [{ type: 'paragraph', text: 'one\ntwo' }]);
});

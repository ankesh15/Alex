// A deliberately small Markdown subset. HTML is always rendered as escaped text.
export function safeLink(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:', 'mailto:'].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}

export function inlineTokens(text) {
  const expression = /(`[^`\n]+`|\*\*[^*\n]+\*\*|\*[^*\n]+\*|\[[^\]\n]+\]\([^\s)]+\))/g;
  const tokens = [];
  let position = 0;
  for (const match of text.matchAll(expression)) {
    if (match.index > position) tokens.push({ type: 'text', text: text.slice(position, match.index) });
    const value = match[0];
    if (value.startsWith('`')) tokens.push({ type: 'code', text: value.slice(1, -1) });
    else if (value.startsWith('**')) tokens.push({ type: 'strong', text: value.slice(2, -2) });
    else if (value.startsWith('*')) tokens.push({ type: 'em', text: value.slice(1, -1) });
    else {
      const parts = /^\[([^\]]+)\]\((.+)\)$/.exec(value);
      const href = safeLink(parts[2]);
      tokens.push(href ? { type: 'link', text: parts[1], href } : { type: 'text', text: value });
    }
    position = match.index + value.length;
  }
  if (position < text.length) tokens.push({ type: 'text', text: text.slice(position) });
  return tokens;
}

const cells = line => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim());
const separator = line => line.includes('|') && cells(line).every(cell => /^:?-{3,}:?$/.test(cell));
const listItem = line => /^\s*([-+*]|\d+\.)\s+(.+)$/.exec(line);
const fence = line => /^\s{0,3}(`{3,}|~{3,})(.*)$/.exec(line);

export function messageBlocks(content = '') {
  const lines = String(content).replace(/\r\n?/g, '\n').split('\n');
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i += 1; continue; }
    const opening = fence(line);
    if (opening) {
      const code = [];
      const language = opening[2].trim().split(/\s+/)[0];
      i += 1;
      while (i < lines.length) {
        const closing = fence(lines[i]);
        if (closing && closing[1][0] === opening[1][0] && closing[1].length >= opening[1].length && !closing[2].trim()) break;
        code.push(lines[i++]);
      }
      if (i < lines.length) i += 1;
      blocks.push({ type: 'code', language, text: code.join('\n') });
    } else if (/^#{1,6}\s+/.test(line)) {
      blocks.push({ type: 'heading', level: line.match(/^#+/)[0].length, text: line.replace(/^#+\s+/, '') });
      i += 1;
    } else if (i + 1 < lines.length && line.includes('|') && separator(lines[i + 1])) {
      const headers = cells(line);
      const rows = [];
      i += 2;
      while (i < lines.length && lines[i].includes('|') && lines[i].trim()) rows.push(cells(lines[i++]));
      blocks.push({ type: 'table', headers, rows });
    } else if (listItem(line)) {
      const ordered = /^\s*\d+\./.test(line);
      const start = ordered ? Number.parseInt(line.trim(), 10) : undefined;
      const items = [];
      while (i < lines.length && listItem(lines[i]) && /^\s*\d+\./.test(lines[i]) === ordered) items.push(listItem(lines[i++])[2]);
      blocks.push({ type: 'list', ordered, start, items });
    } else if (/^>\s?/.test(line)) {
      const quote = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) quote.push(lines[i++].replace(/^>\s?/, ''));
      blocks.push({ type: 'quote', text: quote.join('\n') });
    } else {
      const paragraph = [lines[i++]];
      while (i < lines.length && lines[i].trim() && !fence(lines[i]) && !/^#{1,6}\s+|^>\s?/.test(lines[i]) && !listItem(lines[i]) && !(lines[i].includes('|') && separator(lines[i + 1] || ''))) paragraph.push(lines[i++]);
      blocks.push({ type: 'paragraph', text: paragraph.join('\n') });
    }
  }
  return blocks;
}

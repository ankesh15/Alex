import React from 'react';
import CopyButton from './CopyButton';
import { inlineTokens, messageBlocks } from '../utils/messageFormatting';

function Inline({ text }) {
  return inlineTokens(text).map((token, index) => {
    if (token.type === 'link') return <a key={index} href={token.href} target="_blank" rel="noopener noreferrer">{token.text}</a>;
    if (token.type === 'text') return <React.Fragment key={index}>{token.text}</React.Fragment>;
    const Tag = token.type;
    return <Tag key={index}>{token.text}</Tag>;
  });
}
function CodeBlock({ block }) {
  return <div className="code-block">
    <div className="flex items-center justify-between gap-3 px-4 py-1.5 border-b border-slate-200 text-xs text-slate-500">
      <span className="truncate font-mono">{block.language || 'Code'}</span>
      <CopyButton text={block.text} label="Copy code" />
    </div><pre><code>{block.text}</code></pre>
  </div>;
}
export default function MessageContent({ content }) {
  return <div className="message-content">{messageBlocks(content).map((block, index) => {
    if (block.type === 'code') return <CodeBlock key={index} block={block} />;
    if (block.type === 'heading') {
      const Heading = block.level <= 2 ? 'h2' : 'h3';
      return <Heading key={index}><Inline text={block.text} /></Heading>;
    }
    if (block.type === 'quote') return <blockquote key={index}><Inline text={block.text} /></blockquote>;
    if (block.type === 'list') {
      const List = block.ordered ? 'ol' : 'ul';
      return <List key={index} start={block.start}>{block.items.map((item, n) => <li key={n}><Inline text={item} /></li>)}</List>;
    }
    if (block.type === 'table') return <div key={index} className="overflow-x-auto rounded-lg" role="region" aria-label="Response table" tabIndex={0}>
      <table><thead><tr>{block.headers.map((cell, n) => <th scope="col" key={n}><Inline text={cell} /></th>)}</tr></thead>
        <tbody>{block.rows.map((row, n) => <tr key={n}>{block.headers.map((_, col) => <td key={col}><Inline text={row[col] || ''} /></td>)}</tr>)}</tbody></table>
    </div>;
    return <p key={index}><Inline text={block.text} /></p>;
  })}</div>;
}

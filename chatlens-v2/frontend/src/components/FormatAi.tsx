import React from "react";

/** Render a single line with inline **bold** and *italic* converted to React elements. */
function renderInline(line: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  // Split on **bold** and *italic* patterns
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*)/g;
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(line)) !== null) {
    if (match.index > last) nodes.push(line.slice(last, match.index));
    if (match[2]) {
      nodes.push(<strong key={match.index}>{match[2]}</strong>);
    } else if (match[3]) {
      nodes.push(<em key={match.index}>{match[3]}</em>);
    }
    last = regex.lastIndex;
  }
  if (last < line.length) nodes.push(line.slice(last));
  return nodes;
}

export function FormatAi({ text }: { text: string }) {
  if (!text) return null;
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let listItems: React.ReactNode[] = [];
  let listKey = 0;

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(<ul key={`ul-${listKey}`} className="ml-4 list-disc space-y-0.5">{listItems}</ul>);
      listItems = [];
      listKey++;
    }
  };

  lines.forEach((line, i) => {
    if (line.startsWith("- ") || line.startsWith("* ")) {
      listItems.push(<li key={i}>{renderInline(line.slice(2))}</li>);
      return;
    }
    flushList();
    if (line.startsWith("### ")) {
      elements.push(<h3 key={i} className="text-[0.9rem] font-semibold text-brand-text-bright mt-3 mb-1">{renderInline(line.slice(4))}</h3>);
    } else if (line.startsWith("## ")) {
      elements.push(<h2 key={i} className="text-[0.95rem] font-semibold text-brand-text-bright mt-3 mb-1">{renderInline(line.slice(3))}</h2>);
    } else if (line.startsWith("# ")) {
      elements.push(<h1 key={i} className="text-[1rem] font-semibold text-brand-text-bright mt-3 mb-1">{renderInline(line.slice(2))}</h1>);
    } else {
      elements.push(<p key={i} className="my-1.5">{line ? renderInline(line) : <br />}</p>);
    }
  });
  flushList();
  return <>{elements}</>;
}

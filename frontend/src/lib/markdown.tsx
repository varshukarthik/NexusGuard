import { FileText } from "lucide-react";
import { ReactNode } from "react";

// Safe markdown renderer (no HTML injection — everything is rendered as React text nodes).
// Supports: headings, paragraphs, bullet & numbered lists (with continuation lines), tables, fenced code blocks,
// blockquotes, bold / italic / inline code, and [DOC-xxxx] citation chips that open the source document.
function inline(text: string, onCite?: (id: string) => void, key = ""): ReactNode[] {
  const out: ReactNode[] = [];
  const rx = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`|\[((?:DOC|ORB)-[\w-]+)\])/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = rx.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const t = m[0];
    const k = `${key}-${i++}`;
    if (t.startsWith("**")) out.push(<strong key={k} className="font-semibold text-slate-900 dark:text-white">{t.slice(2, -2)}</strong>);
    else if (t.startsWith("`")) out.push(<code key={k} className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[0.85em] dark:bg-slate-800">{t.slice(1, -1)}</code>);
    else if (t.startsWith("[")) {
      const id = m[2];
      out.push(
        <button key={k} onClick={() => onCite?.(id)} title={`Open source document ${id}`} aria-label={`Open source document ${id}`}
          className="mx-0.5 inline-flex translate-y-[-1px] items-center gap-0.5 rounded-md bg-brand-50 px-1.5 py-px align-middle font-mono text-[10.5px] font-medium text-brand-700 ring-1 ring-inset ring-brand-200 hover:bg-brand-100 dark:bg-brand-500/10 dark:text-brand-300 dark:ring-brand-500/30">
          <FileText className="h-2.5 w-2.5" />{id}
        </button>);
    } else out.push(<em key={k}>{t.slice(1, -1)}</em>);
    last = m.index + t.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const cells = (row: string) => row.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

export function Markdown({ text, onCite }: { text: string; onCite?: (id: string) => void }) {
  const lines = text.replace(/\r/g, "").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let k = 0;
  const key = () => `b${k++}`;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    // fenced code
    if (line.trim().startsWith("```")) {
      const body: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) body.push(lines[i++]);
      i++;
      blocks.push(<pre key={key()} className="overflow-x-auto rounded-lg bg-slate-900 p-3 font-mono text-[12.5px] leading-relaxed text-slate-100 scroll-thin">{body.join("\n")}</pre>);
      continue;
    }
    // table
    if (line.trim().startsWith("|") && i + 1 < lines.length && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1])) {
      const head = cells(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) rows.push(cells(lines[i++]));
      const kk = key();
      blocks.push(
        <div key={kk} className="overflow-x-auto rounded-lg border border-slate-200 scroll-thin dark:border-slate-800">
          <table className="md-table">
            <thead><tr>{head.map((h, j) => <th key={j} scope="col">{inline(h, onCite, `${kk}h${j}`)}</th>)}</tr></thead>
            <tbody>{rows.map((r, ri) => <tr key={ri}>{r.map((c, ci) => <td key={ci}>{inline(c, onCite, `${kk}r${ri}c${ci}`)}</td>)}</tr>)}</tbody>
          </table>
        </div>);
      continue;
    }
    // heading
    const h = /^(#{1,4})\s+(.*)$/.exec(line);
    if (h) {
      const kk = key();
      blocks.push(<p key={kk} className={h[1].length <= 2 ? "pt-1 text-[15.5px] font-semibold text-slate-900 dark:text-white" : "pt-1 text-[14.5px] font-semibold text-slate-900 dark:text-white"}>{inline(h[2], onCite, kk)}</p>);
      i++;
      continue;
    }
    // blockquote
    if (line.startsWith(">")) {
      const q: string[] = [];
      while (i < lines.length && lines[i].startsWith(">")) q.push(lines[i++].replace(/^>\s?/, ""));
      const kk = key();
      blocks.push(<blockquote key={kk} className="border-l-2 border-brand-300 pl-3 text-slate-600 dark:border-brand-500/50 dark:text-slate-400">{inline(q.join(" "), onCite, kk)}</blockquote>);
      continue;
    }
    // lists
    const li = /^\s*([-*•]|\d+[.)])\s+(.*)$/.exec(line);
    if (li) {
      const ordered = /\d/.test(li[1]);
      const items: string[] = [];
      while (i < lines.length) {
        const m = /^\s*([-*•]|\d+[.)])\s+(.*)$/.exec(lines[i]);
        if (m && /\d/.test(m[1]) === ordered) { items.push(m[2]); i++; continue; }
        if (items.length && /^\s{2,}\S/.test(lines[i])) { items[items.length - 1] += "\n" + lines[i].trim(); i++; continue; }
        break;
      }
      const kk = key();
      const content = (it: string, j: number) => it.split("\n").map((part, pi) => <span key={pi} className={pi ? "block text-slate-500 dark:text-slate-400" : undefined}>{inline(part, onCite, `${kk}${j}p${pi}`)}</span>);
      blocks.push(ordered ? (
        <ol key={kk} className="space-y-1.5">
          {items.map((it, j) => (
            <li key={j} className="flex gap-2.5"><span className="mt-[2px] flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[11px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">{j + 1}</span><span className="min-w-0">{content(it, j)}</span></li>
          ))}
        </ol>
      ) : (
        <ul key={kk} className="space-y-1 pl-1">
          {items.map((it, j) => (
            <li key={j} className="flex gap-2"><span className="mt-[9px] h-1 w-1 shrink-0 rounded-full bg-slate-400" /><span className="min-w-0">{content(it, j)}</span></li>
          ))}
        </ul>
      ));
      continue;
    }
    // paragraph
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() && !/^\s*([-*•]|\d+[.)])\s+/.test(lines[i]) && !lines[i].trim().startsWith("|")
      && !lines[i].trim().startsWith("```") && !/^#{1,4}\s/.test(lines[i]) && !lines[i].startsWith(">")) para.push(lines[i++].trim());
    if (!para.length) { para.push(lines[i++].trim()); }
    const kk = key();
    blocks.push(<p key={kk}>{inline(para.join(" "), onCite, kk)}</p>);
  }
  return <div className="space-y-3 text-[14.5px] leading-relaxed text-slate-700 dark:text-slate-300">{blocks}</div>;
}

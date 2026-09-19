import { AlertTriangle, Bot, Briefcase, Building2, Check, CheckCircle2, ChevronDown, Circle, CircleSlash, Clock, Copy,
  Database, Eye, FileText, FolderKanban, Loader2, RefreshCw, ShieldAlert, ThumbsDown, ThumbsUp, User, X,
  XCircle } from "lucide-react";
import { useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import { Markdown } from "../lib/markdown";
import type { Action, ChatMessage, RecordRef, TimelineStep } from "../lib/types";
import { Button, ClassBadge, cx, fmtDate, RiskBadge, Spinner } from "../lib/ui";
import { NovaMark } from "./Brand";
import { RequestAccess } from "./DocumentDrawer";

const AGENT_TONE: Record<string, string> = {
  "Knowledge Agent": "bg-sky-50 text-sky-700 ring-sky-200 dark:bg-sky-500/10 dark:text-sky-300 dark:ring-sky-500/30",
  "HR Agent": "bg-violet-50 text-violet-700 ring-violet-200 dark:bg-violet-500/10 dark:text-violet-300 dark:ring-violet-500/30",
  "IT Agent": "bg-cyan-50 text-cyan-700 ring-cyan-200 dark:bg-cyan-500/10 dark:text-cyan-300 dark:ring-cyan-500/30",
  "Project Agent": "bg-indigo-50 text-indigo-700 ring-indigo-200 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-500/30",
  "Document Agent": "bg-slate-100 text-slate-700 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700",
  "Analytics Agent": "bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-500/30",
  "Workflow Agent": "bg-amber-50 text-amber-800 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-500/30",
  "Productivity Agent": "bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-500/10 dark:text-rose-300 dark:ring-rose-500/30",
};

export const AgentChip = ({ name }: { name: string }) => (
  <span className={cx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset", AGENT_TONE[name] ?? AGENT_TONE["Document Agent"])}>
    <Bot className="h-3 w-3" />{name}</span>
);

function StepIcon({ s }: { s: TimelineStep["status"] }) {
  switch (s) {
    case "done": return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
    case "active": return <Clock className="h-4 w-4 animate-pulse text-amber-500" />;
    case "pending": return <Circle className="h-4 w-4 text-slate-300 dark:text-slate-600" />;
    case "denied": return <XCircle className="h-4 w-4 text-rose-500" />;
    case "blocked": return <ShieldAlert className="h-4 w-4 text-rose-500" />;
    case "warning": return <AlertTriangle className="h-4 w-4 text-amber-500" />;
    default: return <CircleSlash className="h-4 w-4 text-rose-400" />;
  }
}

/** Compact, safe view of what the agents did (never hidden reasoning — only high-level actions and tool calls). */
export function AgentActivity({ steps, defaultOpen, live }: { steps: TimelineStep[]; defaultOpen?: boolean; live?: boolean }) {
  const [open, setOpen] = useState(!!defaultOpen);
  const tools = new Set(steps.filter((s) => s.tool).map((s) => s.tool)).size;
  const waiting = steps.some((s) => s.status === "active");
  const blocked = steps.some((s) => s.status === "denied" || s.status === "blocked");
  const trail = steps.filter((s) => !["identity", "audit", "output_guard", "input_guard"].includes(s.key) && !s.key.startsWith("exec_")).slice(-5);
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/70 dark:border-slate-800 dark:bg-slate-900/60">
      <button onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs">
        {live ? <Loader2 className="h-3.5 w-3.5 animate-spin text-brand-500" /> : <Bot className="h-3.5 w-3.5 text-brand-500" />}
        <span className="font-semibold text-slate-700 dark:text-slate-200">Agent activity</span>
        <span className="hidden min-w-0 flex-1 truncate text-slate-400 sm:block">
          {live ? trail.map((s) => s.label).join("  →  ") : `${steps.length} steps · ${tools} tool${tools === 1 ? "" : "s"}`}
        </span>
        {waiting && !live && <span className="rounded bg-amber-100 px-1.5 py-px text-[10.5px] font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-300">Awaiting confirmation</span>}
        {blocked && !live && <span className="rounded bg-rose-100 px-1.5 py-px text-[10.5px] font-semibold text-rose-700 dark:bg-rose-500/15 dark:text-rose-300">Policy enforced</span>}
        <ChevronDown className={cx("ml-auto h-3.5 w-3.5 shrink-0 text-slate-400 transition", open && "rotate-180")} />
      </button>
      {open && (
        <ol className="px-3 pb-3" aria-label="Agent activity steps">
          {steps.map((s, i) => (
            <li key={s.key + i} className="relative flex gap-2.5 pb-2 last:pb-0">
              {i < steps.length - 1 && <span className="absolute left-[7.5px] top-5 h-[calc(100%-12px)] w-px bg-slate-200 dark:bg-slate-700" />}
              <span className="relative z-10 mt-px bg-slate-50 dark:bg-slate-900">{live && i === steps.length - 1 ? <Loader2 className="h-4 w-4 animate-spin text-brand-500" /> : <StepIcon s={s.status} />}</span>
              <div className="min-w-0 flex-1">
                <p className={cx("text-[13px] font-medium", s.status === "pending" ? "text-slate-400" : s.status === "denied" || s.status === "blocked" ? "text-rose-700 dark:text-rose-300" : "text-slate-700 dark:text-slate-200")}>
                  {s.label}
                  {s.tool && <span className="ml-1.5 rounded bg-white px-1 py-px font-mono text-[10px] font-normal text-slate-500 ring-1 ring-slate-200 dark:bg-slate-800 dark:ring-slate-700">{s.tool}()</span>}
                </p>
                {s.detail && <p className="truncate text-xs text-slate-500">{s.detail}</p>}
              </div>
              {!live && <span className="font-mono text-[10px] text-slate-400">{s.t_ms}ms</span>}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export function ActionCard({ action, onChange }: { action: Action; onChange: (a: Action) => void }) {
  const { notify, bump } = useApp();
  const [busy, setBusy] = useState<"ok" | "no" | null>(null);
  const [subject, setSubject] = useState(action.preview.fields?.find((f) => f[0] === "Subject")?.[1] ?? "");
  const [body, setBody] = useState(action.preview.body ?? "");
  const pending = action.status === "pending_confirmation";
  const editable = pending && !!action.preview.editable?.length;

  async function decide(ok: boolean) {
    setBusy(ok ? "ok" : "no");
    try {
      const r = await api.post<Action>(`/actions/${action.id}/${ok ? "confirm" : "cancel"}`,
        ok ? { overrides: editable ? { subject, body } : undefined } : {});
      onChange(r);
      bump();
      notify(ok ? (r.result.message ?? "Done") : "Cancelled — nothing was executed");
    } catch (e: any) { notify(e.message, "err"); } finally { setBusy(null); }
  }

  return (
    <div className={cx("overflow-hidden rounded-xl border shadow-card", pending ? "border-brand-200 dark:border-brand-500/40" : "border-slate-200 dark:border-slate-800")}>
      <div className={cx("flex items-center gap-2 px-4 py-2.5 text-sm", pending ? "bg-brand-50 dark:bg-brand-500/10" : "bg-slate-50 dark:bg-slate-900")}>
        <Bot className="h-4 w-4 text-brand-600" />
        <span className="font-semibold text-slate-800 dark:text-slate-100">{pending ? "Confirmation required" : action.preview.title}</span>
        <span className="ml-auto flex items-center gap-2"><RiskBadge risk={action.risk} />
          {action.status === "executed" && <span className="flex items-center gap-1 text-xs font-semibold text-emerald-600"><Check className="h-3.5 w-3.5" />Done</span>}
          {action.status === "cancelled" && <span className="text-xs font-semibold text-slate-500">Cancelled</span>}
          {action.status === "failed" && <span className="text-xs font-semibold text-rose-600">Failed</span>}
        </span>
      </div>
      <div className="bg-white px-4 py-3 dark:bg-slate-950/40">
        <dl className="grid grid-cols-1 gap-x-3 gap-y-1.5 text-sm sm:grid-cols-[140px_1fr]">
          {(action.preview.fields ?? []).filter((f) => !(editable && f[0] === "Subject")).map(([k, v]) => (
            <div key={k} className="contents"><dt className="text-slate-500">{k}</dt><dd className="font-medium text-slate-800 dark:text-slate-200">{v}</dd></div>
          ))}
          {editable && <><dt className="pt-1.5 text-slate-500">Subject</dt><dd><input className="input !py-1" value={subject} onChange={(e) => setSubject(e.target.value)} aria-label="Email subject" /></dd></>}
        </dl>
        {action.preview.body !== undefined && (
          editable
            ? <textarea className="input mt-3 min-h-[130px] font-[inherit] leading-relaxed" value={body} onChange={(e) => setBody(e.target.value)} aria-label="Email body" />
            : <div className="mt-3 whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm text-slate-700 ring-1 ring-slate-200 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-800">{action.preview.body}</div>
        )}
        {action.preview.warning && <p className="mt-2 flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-300"><AlertTriangle className="h-3.5 w-3.5" />{action.preview.warning}</p>}
        {action.result?.message && !pending && (
          <p className={cx("mt-3 rounded-lg px-3 py-2 text-sm", action.status === "executed" ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-300" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300")}>
            {action.result.message}
          </p>
        )}
      </div>
      {pending && (
        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-100 bg-slate-50/60 px-4 py-2.5 dark:border-slate-800 dark:bg-slate-900/60">
          <span className="mr-auto text-[11px] text-slate-500">Nothing is submitted until you confirm · logged to audit</span>
          <Button onClick={() => decide(false)} disabled={!!busy}>{busy === "no" ? <Spinner /> : <X className="h-4 w-4" />}Cancel</Button>
          <Button variant="primary" onClick={() => decide(true)} disabled={!!busy}>{busy === "ok" ? <Spinner /> : <Check className="h-4 w-4" />}Confirm &amp; submit</Button>
        </div>
      )}
    </div>
  );
}

const RECORD_ICON: Record<string, any> = { project: FolderKanban, employee: User, task: Briefcase, department: Building2,
  dataset: Database, document: FileText };

function RecordCard({ r }: { r: RecordRef }) {
  const I = RECORD_ICON[r.type] ?? Database;
  return (
    <div className="flex items-start gap-2.5 rounded-xl border border-slate-200 bg-white p-2.5 dark:border-slate-800 dark:bg-slate-900">
      <div className="rounded-lg bg-slate-100 p-1.5 text-slate-500 dark:bg-slate-800"><I className="h-4 w-4" /></div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium text-slate-800 dark:text-slate-100">{r.title}</p>
        <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500">
          <span className="font-mono">{r.id}</span>{r.detail && <>· {r.detail}</>}{r.updated && <>· updated {fmtDate(r.updated)}</>}
          <ClassBadge level={r.classification} size="xs" />
        </p>
      </div>
    </div>
  );
}

export function AssistantMessage({ msg, latest, onUpdate, onRegenerate }:
  { msg: ChatMessage; latest: boolean; onUpdate: (m: ChatMessage) => void; onRegenerate?: () => void }) {
  const { openDoc, notify, me } = useApp();
  const m = msg.meta ?? {};
  const [ctxOpen, setCtxOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const denied = m.access_denied;

  function updateAction(a: Action) {
    const actions = (m.actions ?? []).map((x) => (x.id === a.id ? a : x));
    const timeline = (m.timeline ?? []).map((s) => {
      if (s.key === `await_${a.id}`) return { ...s, status: "done" as const, detail: a.status === "executed" ? "Confirmed by you" : "Cancelled by you" };
      if (s.key === `exec_${a.id}`) return { ...s, status: a.status === "executed" ? ("done" as const) : ("failed" as const), detail: a.result?.message ?? s.detail };
      return s;
    });
    onUpdate({ ...msg, meta: { ...m, actions, timeline } });
  }

  async function copy() {
    try { await navigator.clipboard.writeText(msg.content); setCopied(true); setTimeout(() => setCopied(false), 1500); }
    catch { notify("Couldn't copy to clipboard", "err"); }
  }
  async function feedback(rating: number) {
    const next = m.feedback === rating ? 0 : rating;
    try {
      await api.post(`/messages/${msg.id}/feedback`, { rating: next });
      onUpdate({ ...msg, meta: { ...m, feedback: next } });
      if (next) notify("Thanks — your feedback helps improve answers");
    } catch (e: any) { notify(e.message, "err"); }
  }

  const records = (m.records ?? []).filter((r) => r.type !== "task").slice(0, 6);
  const canAct = !msg.id.startsWith("tmp") && !m.seeded;

  return (
    <div className="group/msg flex gap-3 animate-fade-in">
      <NovaMark className="mt-0.5 h-8 w-8" />
      <div className="min-w-0 flex-1 space-y-3">
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="mr-1 font-semibold text-slate-900 dark:text-white">NovaTech Solutions</span>
          {(m.agents ?? []).map((a) => <AgentChip key={a} name={a} />)}
          {m.question_type && <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">{m.question_type}</span>}
          {m.engine && !m.seeded && m.engine !== "offline" && <span className="rounded-full bg-brand-50 px-2 py-0.5 font-medium text-brand-700 dark:bg-brand-500/10 dark:text-brand-300">{m.engine === "openai" ? "LLM" : "Offline engine (fallback)"}</span>}
          {m.duration_ms !== undefined && <span className="text-slate-400">{(m.duration_ms / 1000).toFixed(2)}s</span>}
        </div>
        {(m.notices ?? []).map((n) => <p key={n} className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">{n}</p>)}
        {!!m.timeline?.length && <AgentActivity steps={m.timeline} />}

        {(m.security ?? []).map((s, i) => (
          <div key={i} role="status" className={cx("flex items-start gap-2.5 rounded-xl border px-3.5 py-2.5 text-sm",
            s.type === "dlp_redaction" ? "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200" : "border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200")}>
            {s.type === "dlp_redaction" ? <Eye className="mt-0.5 h-4 w-4 shrink-0" /> : <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />}
            <div>
              <p className="font-semibold">{s.type === "dlp_redaction" ? "Sensitive data masked" : s.type === "exfiltration_blocked" ? "Outbound data blocked" : "Security policy enforced"}</p>
              <p className="text-[13px] opacity-90">{s.message}{s.redactions && ` (${s.redactions.map((r) => `${r.type} ×${r.count}`).join(", ")})`}</p>
            </div>
          </div>
        ))}

        {denied && denied.document_ids?.[0] && !me.is_guest && (
          <div className="rounded-xl border border-slate-200/80 bg-slate-50/60 p-3 dark:border-slate-800/80 dark:bg-slate-900/40">
            <RequestAccess docId={denied.document_ids[0]} />
          </div>
        )}

        {msg.content && <Markdown text={msg.content} onCite={openDoc} />}

        {(m.actions ?? []).map((a) => <ActionCard key={a.id} action={a} onChange={updateAction} />)}

        {!!m.sources?.length && (
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Sources</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {m.sources.map((s) => (
                <button key={s.doc_id} onClick={() => openDoc(s.doc_id)}
                  className="focus-ring group flex items-start gap-2.5 rounded-xl border border-slate-200 bg-white p-2.5 text-left transition hover:border-brand-300 hover:shadow-card dark:border-slate-800 dark:bg-slate-900">
                  <div className="rounded-lg bg-brand-50 p-1.5 text-brand-600 dark:bg-brand-500/10 dark:text-brand-300"><FileText className="h-4 w-4" /></div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[13px] font-medium text-slate-800 group-hover:text-brand-700 dark:text-slate-100">{s.title}</p>
                    <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500">
                      <span className="font-mono">{s.doc_id}</span>· {s.department} · updated {fmtDate(s.updated_at ?? s.effective_date)}
                      <ClassBadge level={s.classification} size="xs" />
                      {!s.is_latest && <span className="rounded bg-amber-100 px-1 text-[10px] font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-300">SUPERSEDED</span>}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {!!records.length && (
          <div>
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Records used</p>
            <div className="grid gap-2 sm:grid-cols-2">{records.map((r) => <RecordCard key={r.type + r.id} r={r} />)}</div>
          </div>
        )}

        {!!m.context_manifest?.length && !me.is_guest && (
          <div className="text-xs">
            <button onClick={() => setCtxOpen(!ctxOpen)} aria-expanded={ctxOpen} className="flex items-center gap-1 text-slate-400 hover:text-slate-600">
              <Eye className="h-3.5 w-3.5" />What the AI was allowed to see <ChevronDown className={cx("h-3 w-3 transition", ctxOpen && "rotate-180")} />
            </button>
            {ctxOpen && (
              <div className="mt-2 rounded-lg border border-slate-200 p-2.5 dark:border-slate-800">
                {m.context_manifest.map((c) => (
                  <p key={c.doc_id} className="flex flex-wrap items-center gap-2 py-0.5"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /><span className="font-mono">{c.doc_id}</span>{c.title}<ClassBadge level={c.classification} size="xs" /></p>
                ))}
                {(m.withheld ?? []).map((w) => (
                  <p key={w.doc_id} className="flex items-center gap-2 py-0.5 text-rose-600"><XCircle className="h-3.5 w-3.5" /><span className="font-mono">{w.doc_id}</span>withheld by access policy<ClassBadge level={w.classification} size="xs" /></p>
                ))}
              </div>
            )}
          </div>
        )}

        {canAct && (
          <div className="flex items-center gap-0.5 text-slate-400 opacity-100 transition sm:opacity-0 sm:group-hover/msg:opacity-100 sm:focus-within:opacity-100" role="toolbar" aria-label="Response actions">
            <button onClick={copy} className="focus-ring rounded-md p-1.5 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800" title="Copy" aria-label="Copy response">
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}</button>
            {latest && onRegenerate && <button onClick={onRegenerate} className="focus-ring rounded-md p-1.5 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800" title="Regenerate" aria-label="Regenerate response"><RefreshCw className="h-3.5 w-3.5" /></button>}
            <button onClick={() => feedback(1)} aria-pressed={m.feedback === 1} className={cx("focus-ring rounded-md p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800", m.feedback === 1 ? "text-emerald-600" : "hover:text-slate-700")} title="Helpful" aria-label="Mark as helpful"><ThumbsUp className="h-3.5 w-3.5" /></button>
            <button onClick={() => feedback(-1)} aria-pressed={m.feedback === -1} className={cx("focus-ring rounded-md p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800", m.feedback === -1 ? "text-rose-600" : "hover:text-slate-700")} title="Not helpful" aria-label="Mark as not helpful"><ThumbsDown className="h-3.5 w-3.5" /></button>
          </div>
        )}
      </div>
    </div>
  );
}

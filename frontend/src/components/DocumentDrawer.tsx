import { AlertTriangle, FileText, History, Lock, Send, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { useApp } from "../lib/app";
import type { DocRow } from "../lib/types";
import { Button, ClassBadge, cx, Drawer, fmtDate, Spinner } from "../lib/ui";

type Doc = DocRow & { content: string; redactions: { type: string; count: number }[]; chunks: number;
  versions: { id: string; version: string; effective_date: string; status: string; accessible: boolean }[] };

export function RequestAccess({ docId, compact }: { docId: string; compact?: boolean }) {
  const { notify, bump } = useApp();
  const [state, setState] = useState<"idle" | "form" | "busy" | "done">("idle");
  const [why, setWhy] = useState("");
  if (state === "done") return <p className="text-xs font-medium text-emerald-600">✓ Access request sent to the document owner</p>;
  if (state === "idle") return <Button size="sm" onClick={() => setState("form")}><Send className="h-3.5 w-3.5" />Request access</Button>;
  return (
    <div className={cx("flex gap-2", compact ? "flex-col" : "flex-col sm:flex-row")}>
      <input className="input !py-1.5 text-xs" placeholder="Business justification" value={why} onChange={(e) => setWhy(e.target.value)} />
      <Button size="sm" variant="primary" disabled={state === "busy"} onClick={async () => {
        setState("busy");
        try { await api.post("/approvals", { type: "document_access", document_id: docId, justification: why || "Needed for my work" }); setState("done"); bump(); }
        catch (e: any) { notify(e.message, "err"); setState("form"); }
      }}>{state === "busy" ? <Spinner /> : <Send className="h-3.5 w-3.5" />}Submit</Button>
    </div>
  );
}

export default function DocumentDrawer({ id, onClose }: { id: string | null; onClose: () => void }) {
  const [doc, setDoc] = useState<Doc | null>(null);
  const [err, setErr] = useState<ApiError | null>(null);
  const [cur, setCur] = useState<string | null>(id);
  useEffect(() => setCur(id), [id]);
  useEffect(() => {
    if (!cur) return;
    setDoc(null); setErr(null);
    api.get<Doc>(`/documents/${cur}`).then(setDoc).catch(setErr);
  }, [cur]);

  return (
    <Drawer open={!!id} onClose={onClose} title={<span className="flex items-center gap-2"><FileText className="h-4 w-4 text-brand-600" />{doc?.title ?? cur}</span>}>
      {!doc && !err && <div className="flex justify-center p-10"><Spinner className="h-5 w-5" /></div>}
      {err && (
        <div className="p-8 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-rose-50 text-rose-600 dark:bg-rose-500/10"><Lock className="h-5 w-5" /></div>
          <p className="font-semibold text-slate-900 dark:text-white">{err.status === 403 ? "Access denied" : "Unavailable"}</p>
          <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">{err.message}</p>
          {err.status === 403 && <p className="mt-1 text-xs text-slate-400">This attempt was recorded in the audit log.</p>}
          {err.status === 403 && cur && <div className="mt-4 flex justify-center"><RequestAccess docId={cur} /></div>}
        </div>
      )}
      {doc && (
        <div className="space-y-5 p-5">
          <div className="flex flex-wrap items-center gap-2">
            <ClassBadge level={doc.classification} />
            <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-xs dark:bg-slate-800">{doc.id}</span>
            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs dark:bg-slate-800">v{doc.version}</span>
            <span className={cx("rounded px-2 py-0.5 text-xs font-medium", doc.status === "published" ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300" : "bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-300")}>{doc.status.replace("_", " ")}</span>
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
            {[["Department", doc.department], ["Owner", doc.owner], ["Effective", fmtDate(doc.effective_date)], ["Type", doc.doc_type],
              ["Allowed departments", doc.allowed_departments.join(", ") || "—"], ["Indexed chunks", String(doc.chunks)]].map(([k, v]) => (
              <div key={k}><p className="text-[11px] uppercase tracking-wider text-slate-400">{k}</p><p className="font-medium text-slate-800 dark:text-slate-200">{v}</p></div>
            ))}
          </div>
          {doc.status === "superseded" && (
            <div className="flex gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-500/10 dark:text-amber-300"><History className="mt-0.5 h-4 w-4 shrink-0" />This version is superseded. The assistant always prefers the latest authorized version.</div>
          )}
          {doc.security_flags?.length > 0 && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300">
              <p className="flex items-center gap-2 font-semibold"><ShieldAlert className="h-4 w-4" />Quarantined — potential prompt injection</p>
              <ul className="mt-2 space-y-1 text-xs">{doc.security_flags.map((f, i) => <li key={i}><b>{f.category}</b>: “{f.evidence}”</li>)}</ul>
            </div>
          )}
          {doc.ai_classification && (
            <div className="rounded-lg border border-brand-200 bg-brand-50/60 p-3 text-sm dark:border-brand-500/30 dark:bg-brand-500/10">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-brand-600">AI classification</p>
              <p className="mt-1 flex items-center gap-2"><ClassBadge level={doc.ai_classification} /> <span className="text-slate-600 dark:text-slate-300">{doc.ai_classification_reason}</span></p>
            </div>
          )}
          {doc.versions.length > 1 && (
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Version history</p>
              <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
                {doc.versions.map((v) => (
                  <button key={v.id} disabled={!v.accessible} onClick={() => setCur(v.id)}
                    className={cx("flex w-full items-center justify-between px-3 py-2 text-left text-sm", v.id === doc.id ? "bg-slate-50 dark:bg-slate-800/60" : "hover:bg-slate-50 dark:hover:bg-slate-800/40", !v.accessible && "opacity-60")}>
                    <span className="font-mono text-xs">{v.id} · v{v.version}</span>
                    <span className="text-xs text-slate-500">{fmtDate(v.effective_date)} · {v.status}{!v.accessible && " · 🔒"}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {doc.redactions?.length > 0 && (
            <p className="flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-300"><AlertTriangle className="h-3.5 w-3.5" />Sensitive values were redacted by DLP: {doc.redactions.map((r) => `${r.type}×${r.count}`).join(", ")}</p>
          )}
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Content</p>
            <div className="whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-[13.5px] leading-relaxed text-slate-700 ring-1 ring-slate-200 dark:bg-slate-950 dark:text-slate-300 dark:ring-slate-800">{doc.content}</div>
            <p className="mt-2 text-[11px] text-slate-400">Fictional demo document. Your view was recorded in the audit log.</p>
          </div>
        </div>
      )}
    </Drawer>
  );
}

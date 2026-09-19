import { CheckCircle2, FlaskConical, Play, ShieldAlert, ShieldCheck, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import { Markdown } from "../lib/markdown";
import { Button, Card, ClassBadge, cx, PageHeader, Spinner } from "../lib/ui";

interface Preset { id: string; name: string; expect: string; user: object; documents: object[]; prompt: string }
interface Decision { document_id: string; title: string; classification: string; version: string; effective_date: string; allowed: boolean; rule: string; reason: string; sent_to_llm: boolean; withheld_relevant: boolean; superseded: boolean; quarantined: boolean }
interface Result {
  answer: string; engine: string; decisions: Decision[]; llm_context: string; safe_refusal: boolean; duration_ms: number;
  conflicts: { note: string }[]; quarantined: { doc_id: string; categories: string }[];
  checks: { unauthorized_sent_to_llm: string[]; leak_check_passed: boolean; authorized_docs: number; denied_docs: number };
  audit_trail: { ts: string; event: string; [k: string]: unknown }[];
}

export default function PolicyLab() {
  const { notify } = useApp();
  const [presets, setPresets] = useState<Preset[]>([]);
  const [active, setActive] = useState("A");
  const [user, setUser] = useState("");
  const [docs, setDocs] = useState("");
  const [prompt, setPrompt] = useState("");
  const [res, setRes] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get<Preset[]>("/policy-lab/presets").then((p) => { setPresets(p); load(p[0]); }).catch(() => {}); }, []);
  function load(p: Preset) {
    setActive(p.id); setRes(null);
    setUser(JSON.stringify(p.user, null, 2)); setDocs(JSON.stringify(p.documents, null, 2)); setPrompt(p.prompt);
  }
  async function run() {
    let u, d;
    try { u = JSON.parse(user); d = JSON.parse(docs); } catch { return notify("user.json / documents.json must be valid JSON", "err"); }
    setBusy(true);
    try { setRes(await api.post<Result>("/policy-lab/evaluate", { user: u, documents: d, prompt })); }
    catch (e: any) { notify(e.message, "err"); } finally { setBusy(false); }
  }
  const preset = presets.find((p) => p.id === active);

  return (
    <div className="mx-auto max-w-7xl p-6">
      <PageHeader icon={<FlaskConical className="h-5 w-5" />} title="Policy Lab"
        subtitle="Run authorization test inputs (user.json + documents.json + prompt) through the exact production authorization + RAG pipeline in an isolated sandbox tenant." />
      <div className="mb-4 flex flex-wrap gap-2">
        {presets.map((p) => (
          <button key={p.id} onClick={() => load(p)} className={cx("rounded-lg border px-3 py-1.5 text-sm font-medium transition",
            active === p.id ? "border-brand-300 bg-brand-50 text-brand-700 dark:border-brand-500/40 dark:bg-brand-500/10 dark:text-brand-300" : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300")}>{p.name}</button>
        ))}
      </div>
      {preset && <p className="mb-4 rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-600 dark:bg-slate-900 dark:text-slate-300"><b>Expected:</b> {preset.expect}</p>}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,4fr)_minmax(0,8fr)]">
        <div className="space-y-3">
          <Card className="p-3"><p className="mb-1.5 font-mono text-xs font-semibold text-slate-500">user.json</p>
            <textarea className="input h-32 font-mono text-xs" spellCheck={false} value={user} onChange={(e) => setUser(e.target.value)} /></Card>
          <Card className="p-3"><p className="mb-1.5 font-mono text-xs font-semibold text-slate-500">documents.json</p>
            <textarea className="input h-72 font-mono text-xs" spellCheck={false} value={docs} onChange={(e) => setDocs(e.target.value)} /></Card>
          <Card className="p-3"><p className="mb-1.5 font-mono text-xs font-semibold text-slate-500">prompt</p>
            <input className="input" value={prompt} onChange={(e) => setPrompt(e.target.value)} /></Card>
          <Button variant="primary" className="w-full" onClick={run} disabled={busy}>{busy ? <Spinner /> : <Play className="h-4 w-4" />}Run through permission engine</Button>
        </div>
        <div className="space-y-4">
          {!res && !busy && <Card className="flex h-full min-h-[300px] items-center justify-center p-8 text-center text-sm text-slate-500">Choose a preset or edit the JSON, then run it. You'll see every authorization decision, the exact context given to the LLM, and an automated leakage check.</Card>}
          {busy && <Card className="flex min-h-[300px] items-center justify-center"><Spinner className="h-6 w-6 text-brand-500" /></Card>}
          {res && (
            <>
              <div className={cx("flex items-start gap-3 rounded-xl border p-4",
                res.checks.leak_check_passed ? "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200" : "border-rose-200 bg-rose-50 text-rose-900")}>
                {res.checks.leak_check_passed ? <ShieldCheck className="h-5 w-5 shrink-0" /> : <ShieldAlert className="h-5 w-5 shrink-0" />}
                <div className="text-sm">
                  <p className="font-semibold">{res.checks.leak_check_passed ? "PASS — no unauthorized content reached the LLM or the answer" : `FAIL — leaked: ${res.checks.unauthorized_sent_to_llm.join(", ")}`}</p>
                  <p className="opacity-80">{res.checks.authorized_docs} authorized · {res.checks.denied_docs} denied · engine {res.engine} · {res.duration_ms} ms{res.safe_refusal && " · safe refusal"}</p>
                </div>
              </div>
              <Card className="overflow-hidden">
                <p className="border-b border-slate-100 px-4 py-2.5 text-sm font-semibold dark:border-slate-800">Authorization decisions (before retrieval)</p>
                <div className="overflow-x-auto"><table className="w-full min-w-[520px] text-sm">
                  <thead><tr className="border-b border-slate-100 dark:border-slate-800"><th className="th">Document</th><th className="th">Class</th><th className="th">Decision</th><th className="th">Sent to LLM</th></tr></thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">{res.decisions.map((d) => (
                    <tr key={d.document_id}>
                      <td className="td"><p className="font-mono text-xs font-semibold">{d.document_id}</p><p className="text-xs text-slate-500">{d.title} · v{d.version} · {d.effective_date}</p>
                        <p className="mt-1 space-x-1 text-[10.5px] font-semibold">
                          {d.withheld_relevant && <span className="rounded bg-rose-100 px-1 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300">RELEVANT · WITHHELD</span>}
                          {d.superseded && <span className="rounded bg-amber-100 px-1 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300">SUPERSEDED</span>}
                          {d.quarantined && <span className="rounded bg-rose-100 px-1 text-rose-700">QUARANTINED</span>}
                        </p></td>
                      <td className="td"><ClassBadge level={d.classification} size="xs" /></td>
                      <td className="td">{d.allowed ? <span className="flex items-center gap-1 text-xs font-semibold text-emerald-600"><CheckCircle2 className="h-3.5 w-3.5" />ALLOW</span> : <span className="flex items-center gap-1 text-xs font-semibold text-rose-600"><XCircle className="h-3.5 w-3.5" />DENY</span>}<p className="max-w-[200px] text-[11px] text-slate-500">{d.reason}</p></td>
                      <td className="td text-xs font-semibold">{d.sent_to_llm ? <span className="text-emerald-600">yes</span> : <span className="text-slate-400">no</span>}</td>

                    </tr>))}</tbody>
                </table></div>
              </Card>
              <Card className="p-4">
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Answer</p>
                <Markdown text={res.answer} />
              </Card>
              <Card className="p-4">
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Exact context sent to the LLM</p>
                <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-3 font-mono text-[11px] leading-relaxed text-slate-200 scroll-thin">{res.llm_context}</pre>
              </Card>
              <Card className="p-4">
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Audit trail</p>
                <ol className="space-y-1 font-mono text-[11px]">
                  {res.audit_trail.map((e, i) => {
                    const { ts, event, ...rest } = e;
                    return <li key={i} className="flex gap-2"><span className="text-slate-400">{ts.slice(11, 23)}</span><span className="font-semibold text-brand-600">{event}</span><span className="truncate text-slate-500">{JSON.stringify(rest)}</span></li>;
                  })}
                </ol>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

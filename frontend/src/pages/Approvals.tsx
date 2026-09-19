import { CalendarDays, Check, ClipboardCheck, FileLock2, Inbox, Send, Tags, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import type { Approval } from "../lib/types";
import { Avatar, Button, Card, ClassBadge, cx, Empty, fmtDate, fmtTime, PageHeader, RiskBadge, Spinner } from "../lib/ui";

const TYPE_ICON: Record<string, any> = { leave: CalendarDays, document_access: FileLock2, classification: Tags, general: ClipboardCheck };
const TYPE_LABEL: Record<string, string> = { leave: "Leave", document_access: "Document access", classification: "Classification review", general: "General" };

function ApprovalCard({ a, canDecide, onDone }: { a: Approval; canDecide: boolean; onDone: () => void }) {
  const { notify, bump, openDoc } = useApp();
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [cls, setCls] = useState<string>(a.details.suggested ?? "");
  const Icon = TYPE_ICON[a.type] ?? ClipboardCheck;
  async function decide(ok: boolean) {
    setBusy(ok ? "a" : "r");
    try {
      await api.post(`/approvals/${a.id}/${ok ? "approve" : "reject"}`, { note, classification: a.type === "classification" && ok ? cls : undefined });
      notify(ok ? "Approved" : "Rejected"); bump(); onDone();
    } catch (e: any) { notify(e.message, "err"); } finally { setBusy(null); }
  }
  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-slate-100 p-2 text-slate-600 dark:bg-slate-800 dark:text-slate-300"><Icon className="h-4 w-4" /></div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium text-slate-900 dark:text-white">{a.title}</p>
            <RiskBadge risk={a.risk} />
            <span className={cx("rounded px-1.5 py-0.5 text-[11px] font-semibold",
              a.status === "pending" ? "bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-300" : a.status === "approved" ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300" : "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300")}>{a.status}</span>
          </div>
          <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
            <Avatar name={a.requester.name} className="h-5 w-5 text-[9px]" />{a.requester.name} · {a.requester.title} · {a.requester.department} · {fmtTime(a.created_at)}
          </div>
          <div className="mt-2.5 space-y-1 text-sm text-slate-600 dark:text-slate-300">
            <p className="text-xs text-slate-400">{TYPE_LABEL[a.type]} · approver: {a.approver}</p>
            {a.type === "leave" && <p>{a.details.leave_type} leave · {a.details.days} day(s) · {fmtDate(a.details.start_date)}{a.details.end_date !== a.details.start_date && ` → ${fmtDate(a.details.end_date)}`} — “{a.details.reason}”</p>}
            {a.type === "document_access" && <p className="flex flex-wrap items-center gap-2"><button className="font-mono text-xs text-brand-600 hover:underline" onClick={() => a.resource_id && openDoc(a.resource_id)}>{a.resource_id}</button><ClassBadge level={a.details.classification} size="xs" /> {a.details.duration_days}-day read grant — “{a.details.justification}”</p>}
            {a.type === "classification" && (
              <div className="rounded-lg border border-brand-200 bg-brand-50/60 p-2.5 dark:border-brand-500/30 dark:bg-brand-500/10">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-brand-600">AI classification ({a.details.engine})</p>
                <p className="mt-1 flex flex-wrap items-center gap-2">Detected <ClassBadge level={a.details.final ?? a.details.suggested} /> <span className="text-xs">Reason: “{a.details.reason}”</span></p>
                {a.details.sensitive_entities?.length > 0 && <p className="mt-1 text-xs">Sensitive entities: {a.details.sensitive_entities.join(", ")}</p>}
                {a.resource_id && <button className="mt-1 text-xs text-brand-600 hover:underline" onClick={() => openDoc(a.resource_id!)}>Preview {a.resource_id} →</button>}
              </div>
            )}
            {a.decision_note && <p className="text-xs italic">Note: {a.decision_note}</p>}
          </div>
          {canDecide && a.status === "pending" && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {a.type === "classification" && (
                <select className="input !w-auto !py-1.5 text-xs" value={cls} onChange={(e) => setCls(e.target.value)}>
                  {["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"].map((c) => <option key={c}>{c}</option>)}
                </select>
              )}
              <input className="input !w-auto flex-1 !py-1.5 text-xs" placeholder="Decision note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
              <Button size="sm" onClick={() => decide(false)} disabled={!!busy}>{busy === "r" ? <Spinner /> : <X className="h-3.5 w-3.5" />}Reject</Button>
              <Button size="sm" variant="success" onClick={() => decide(true)} disabled={!!busy}>{busy === "a" ? <Spinner /> : <Check className="h-3.5 w-3.5" />}{a.type === "classification" ? "Approve & publish" : "Approve"}</Button>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

export default function Approvals() {
  const { version, me } = useApp();
  const [data, setData] = useState<{ inbox: Approval[]; mine: Approval[] } | null>(null);
  const [tab, setTab] = useState<"inbox" | "mine">("inbox");
  const load = () => api.get<{ inbox: Approval[]; mine: Approval[] }>("/approvals").then(setData).catch(() => {});
  useEffect(() => { load(); }, [version, me.user_id]);
  const list = data ? data[tab] : [];
  const pending = data?.inbox.filter((a) => a.status === "pending").length ?? 0;
  return (
    <div className="mx-auto max-w-4xl p-6">
      <PageHeader icon={<ClipboardCheck className="h-5 w-5" />} title="Approvals"
        subtitle="Human-in-the-loop decisions: leave, document access and AI classification reviews. Self-approval is blocked server-side." />
      <div className="mb-4 flex gap-1 rounded-lg bg-slate-100 p-1 text-sm dark:bg-slate-900">
        {([["inbox", `Needs my decision (${pending})`, Inbox], ["mine", `My requests (${data?.mine.length ?? 0})`, Send]] as const).map(([k, l, I]) => (
          <button key={k} onClick={() => setTab(k)} className={cx("flex flex-1 items-center justify-center gap-2 rounded-md py-1.5 font-medium", tab === k ? "bg-white shadow-sm dark:bg-slate-800" : "text-slate-500")}><I className="h-4 w-4" />{l}</button>
        ))}
      </div>
      {!data ? <div className="flex justify-center p-10"><Spinner /></div> : list.length === 0 ? (
        <Empty icon={<ClipboardCheck className="h-5 w-5" />} title={tab === "inbox" ? "Nothing needs your decision" : "You haven't requested anything"} text={tab === "inbox" ? "Switch to Priya Reddy (manager) or Ananya Rao (HR) to see pending approvals." : undefined} />
      ) : (
        <div className="space-y-3">{list.map((a) => <ApprovalCard key={a.id} a={a} canDecide={tab === "inbox"} onDone={load} />)}</div>
      )}
    </div>
  );
}

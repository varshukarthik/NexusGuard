import { CalendarDays, CheckCircle2, Circle, ListChecks, Mail, Ticket, Timer } from "lucide-react";
import { useEffect, useState } from "react";
import { ActionCard } from "../components/Message";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import type { Action } from "../lib/types";
import { Card, cx, Empty, fmtDate, fmtTime, PageHeader, Spinner } from "../lib/ui";

interface Work {
  tasks: { id: string; title: string; project: string; priority: string; status: string; due: string | null }[];
  leave_requests: { id: string; type: string; start: string; end: string; days: number; reason: string; status: string }[];
  tickets: { id: string; title: string; priority: string; category: string; status: string; created_at: string }[];
  emails: { id: string; to: string; subject: string; status: string; created_at: string }[];
  requests: { id: string; type: string; title: string; status: string; created_at: string }[];
  pending_actions: Action[];
}

const PRI: Record<string, string> = { High: "text-rose-600 bg-rose-50 dark:bg-rose-500/10", Medium: "text-amber-700 bg-amber-50 dark:bg-amber-500/10", Low: "text-slate-600 bg-slate-100 dark:bg-slate-800" };
const STATUS: Record<string, string> = {
  approved: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300",
  rejected: "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300",
  pending_manager_approval: "bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-300",
};

export default function Tasks() {
  const { version, me } = useApp();
  const [w, setW] = useState<Work | null>(null);
  const load = () => api.get<Work>("/my/work").then(setW).catch(() => {});
  useEffect(() => { load(); }, [version, me.user_id]);
  if (!w) return <div className="flex justify-center p-20"><Spinner /></div>;
  const open = w.tasks.filter((t) => t.status !== "done");
  return (
    <div className="mx-auto max-w-6xl p-4 sm:p-6">
      <PageHeader icon={<ListChecks className="h-5 w-5" />} title="My Work" subtitle="Your tasks, requests, tickets and actions the assistant has prepared for you." />
      {w.pending_actions.length > 0 && (
        <div className="mb-6">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Awaiting your confirmation ({w.pending_actions.length})</p>
          <div className="grid gap-3 lg:grid-cols-2">{w.pending_actions.map((a) => <ActionCard key={a.id} action={a} onChange={() => load()} />)}</div>
        </div>
      )}
      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 dark:border-slate-800">
            <p className="font-semibold">Tasks</p><span className="text-xs text-slate-500">{open.length} open · {w.tasks.length - open.length} done</span>
          </div>
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {w.tasks.map((t) => (
              <li key={t.id} className="flex items-center gap-3 px-4 py-3">
                {t.status === "done" ? <CheckCircle2 className="h-[18px] w-[18px] text-emerald-500" /> : t.status === "in_progress" ? <Timer className="h-4 w-4 text-brand-500" /> : <Circle className="h-4 w-4 text-slate-300" />}
                <div className="min-w-0 flex-1">
                  <p className={cx("text-sm font-medium", t.status === "done" ? "text-slate-400 line-through" : "text-slate-800 dark:text-slate-100")}>{t.title}</p>
                  <p className="text-xs text-slate-500">{t.project} · <span className="font-mono">{t.id}</span></p>
                </div>
                <span className={cx("rounded px-1.5 py-0.5 text-[11px] font-semibold", PRI[t.priority])}>{t.priority}</span>
                <span className="flex w-24 items-center justify-end gap-1 text-xs text-slate-500"><CalendarDays className="h-3.5 w-3.5" />{fmtDate(t.due)}</span>
              </li>
            ))}
          </ul>
        </Card>
        <div className="space-y-5">
          <Card>
            <p className="border-b border-slate-100 px-4 py-3 font-semibold dark:border-slate-800">Leave requests</p>
            {w.leave_requests.length === 0 ? <p className="px-4 py-5 text-sm text-slate-500">None yet — ask the assistant to “submit leave for Monday”.</p> :
              <ul className="divide-y divide-slate-100 dark:divide-slate-800">{w.leave_requests.map((l) => (
                <li key={l.id} className="px-4 py-2.5 text-sm">
                  <div className="flex justify-between"><span className="font-medium">{l.type} · {l.days}d</span><span className={cx("rounded px-1.5 text-[11px] font-semibold", STATUS[l.status])}>{l.status.replace(/_/g, " ")}</span></div>
                  <p className="text-xs text-slate-500">{fmtDate(l.start)}{l.end !== l.start && ` → ${fmtDate(l.end)}`} · {l.id}</p>
                </li>))}</ul>}
          </Card>
          <Card>
            <p className="border-b border-slate-100 px-4 py-3 font-semibold dark:border-slate-800">Service requests</p>
            {(w.requests ?? []).length === 0 ? <p className="px-4 py-5 text-sm text-slate-500">No access, software, document or procurement requests.</p> :
              <ul className="divide-y divide-slate-100 dark:divide-slate-800">{w.requests.slice(0, 8).map((r) => (
                <li key={r.id} className="px-4 py-2.5 text-sm"><p className="font-medium">{r.title}</p><p className="text-xs text-slate-500">{r.id} · {r.type} · {r.status.replace(/_/g, " ")} · {fmtDate(r.created_at)}</p></li>))}</ul>}
          </Card>
          <Card>
            <p className="flex items-center gap-2 border-b border-slate-100 px-4 py-3 font-semibold dark:border-slate-800"><Ticket className="h-4 w-4 text-slate-400" />IT tickets</p>
            {w.tickets.length === 0 ? <p className="px-4 py-5 text-sm text-slate-500">No tickets.</p> :
              <ul className="divide-y divide-slate-100 dark:divide-slate-800">{w.tickets.map((t) => (
                <li key={t.id} className="px-4 py-2.5 text-sm"><p className="font-medium">{t.title}</p><p className="text-xs text-slate-500">{t.id} · {t.priority} · {t.category} · {t.status}</p></li>))}</ul>}
          </Card>
          <Card>
            <p className="flex items-center gap-2 border-b border-slate-100 px-4 py-3 font-semibold dark:border-slate-800"><Mail className="h-4 w-4 text-slate-400" />Sent via AI (simulated)</p>
            {w.emails.length === 0 ? <p className="px-4 py-5 text-sm text-slate-500">No emails sent.</p> :
              <ul className="divide-y divide-slate-100 dark:divide-slate-800">{w.emails.map((e) => (
                <li key={e.id} className="px-4 py-2.5 text-sm"><p className="font-medium">{e.subject}</p><p className="text-xs text-slate-500">To {e.to} · {fmtTime(e.created_at)}</p></li>))}</ul>}
          </Card>
        </div>
      </div>
      {w.tasks.length === 0 && <Empty icon={<ListChecks />} title="No tasks" />}
    </div>
  );
}

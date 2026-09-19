import { Activity, AlertTriangle, BarChart3, Ban, Bot, CheckCircle2, Database, FileText, Globe2, Lock, MessageSquare,
  ScrollText, Users, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AgentChip } from "../components/Message";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import { Card, ClassBadge, Empty, fmtTime, PageHeader, ResultBadge, Spinner, title } from "../lib/ui";

interface Metrics {
  kpis: Record<string, number>;
  requests_over_time: { date: string; requests: number; denied: number; blocked: number; queries: number }[];
  access_by_classification: { classification: string; allowed: number; denied: number }[];
  document_classifications: { classification: string; count: number }[];
  tool_usage: { tool: string; count: number }[];
  agent_usage: { agent: string; count: number }[];
  response_outcomes: { status: string; count: number }[];
  alerts_by_type: { type: string; count: number }[];
  top_denied_users: { user: string; count: number }[];
  records_by_table: { table: string; count: number }[];
  recent_events: { id: string; ts: string; user_name: string; action: string; resource: string; permission_result: string; risk: string }[];
}

// Reference palette (dataviz skill): blue = volume/allowed, red = denied (status), orange = blocked.
const PAL = {
  light: { blue: "#2a78d6", red: "#e34948", orange: "#eb6834", grid: "#e8e7e3", axis: "#52514e", tip: "#ffffff" },
  dark: { blue: "#3987e5", red: "#e66767", orange: "#d95926", grid: "#2e2e2b", axis: "#c3c2b7", tip: "#1a1a19" },
};

const KPI = [
  ["total_users", "Employees (users)", Users], ["active_users", "Active users", Activity], ["guest_sessions", "Guest sessions (7d)", Globe2],
  ["documents", "Knowledge documents", FileText], ["database_records", "Database records", Database], ["queries", "AI queries (7d)", MessageSquare],
  ["successful_responses", "Successful responses", CheckCircle2], ["failed_responses", "Denied / blocked / not found", XCircle],
  ["permission_denials", "Access-denied events (7d)", Lock], ["blocked_requests", "Blocked requests (7d)", Ban],
  ["security_alerts", "Open security alerts", AlertTriangle], ["audit_events", "Audit events (all time)", ScrollText],
] as const;

function Panel({ label, sub, children, h = "h-64" }: { label: string; sub?: string; children: React.ReactNode; h?: string }) {
  return <Card className="p-4"><p className="font-semibold">{label}</p>{sub && <p className="text-xs text-slate-500">{sub}</p>}<div className={`mt-3 ${h}`}>{children}</div></Card>;
}

export default function Admin() {
  const { can, version } = useApp();
  const [m, setM] = useState<Metrics | null>(null);
  const [err, setErr] = useState("");
  const dark = document.documentElement.classList.contains("dark");
  const c = dark ? PAL.dark : PAL.light;
  useEffect(() => { api.get<Metrics>("/admin/metrics").then(setM).catch((e) => setErr(e.message)); }, [version]);
  if (!can("admin:dashboard")) return <div className="p-6"><Empty icon={<Lock className="h-5 w-5" />} title="Admin dashboard is restricted" text="Requires the administrator role." /></div>;
  if (err) return <div className="p-6"><Empty icon={<AlertTriangle className="h-5 w-5" />} title="Couldn't load metrics" text={err} /></div>;
  if (!m) return <div className="flex justify-center p-20"><Spinner /></div>;
  const axis = { stroke: c.axis, fontSize: 11, tickLine: false, axisLine: false };
  const tip = { contentStyle: { background: c.tip, border: `1px solid ${c.grid}`, borderRadius: 8, fontSize: 12 }, cursor: { fill: dark ? "rgba(255,255,255,.04)" : "rgba(0,0,0,.03)" } };
  const maxAgent = Math.max(1, ...m.agent_usage.map((a) => a.count));
  const docTotal = m.document_classifications.reduce((a, b) => a + b.count, 0) || 1;

  return (
    <div className="mx-auto max-w-7xl space-y-5 p-4 sm:p-6">
      <PageHeader icon={<BarChart3 className="h-5 w-5" />} title="Admin Dashboard" subtitle="Platform usage, agent activity and governance across the NovaTech Solutions tenant. No confidential content is shown here." />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 2xl:grid-cols-6">
        {KPI.map(([k, l, I]) => (
          <Card key={k} className="p-4">
            <div className="flex items-center justify-between gap-2 text-slate-500"><span className="text-xs font-medium leading-tight">{l}</span><I className="h-4 w-4 shrink-0" /></div>
            <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">{(m.kpis[k] ?? 0).toLocaleString()}</p>
          </Card>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel label="Activity over time" sub="Audited events per day (last 7 days)">
          <ResponsiveContainer>
            <LineChart data={m.requests_over_time} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
              <CartesianGrid stroke={c.grid} vertical={false} />
              <XAxis dataKey="date" {...axis} /><YAxis {...axis} allowDecimals={false} />
              <Tooltip {...tip} /><Legend iconType="plainline" wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="requests" name="All events" stroke={c.blue} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
              <Line type="monotone" dataKey="denied" name="Denied" stroke={c.red} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
              <Line type="monotone" dataKey="blocked" name="Blocked" stroke={c.orange} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </Panel>
        <Panel label="Authorization decisions by classification" sub="Document & record reads (last 7 days)">
          <ResponsiveContainer>
            <BarChart data={m.access_by_classification.map((x) => ({ ...x, classification: title(x.classification.toLowerCase()) }))} margin={{ top: 8, right: 12, left: -18, bottom: 0 }} barGap={2}>
              <CartesianGrid stroke={c.grid} vertical={false} />
              <XAxis dataKey="classification" {...axis} /><YAxis {...axis} allowDecimals={false} />
              <Tooltip {...tip} /><Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="allowed" name="Allowed" fill={c.blue} radius={[4, 4, 0, 0]} maxBarSize={28} />
              <Bar dataKey="denied" name="Denied" fill={c.red} radius={[4, 4, 0, 0]} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
        <Panel label="Tool usage" sub="Tool executions by the agents (all time)">
          <ResponsiveContainer>
            <BarChart data={m.tool_usage} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
              <CartesianGrid stroke={c.grid} horizontal={false} />
              <XAxis type="number" {...axis} allowDecimals={false} /><YAxis type="category" dataKey="tool" {...axis} width={140} />
              <Tooltip {...tip} />
              <Bar dataKey="count" name="Executions" fill={c.blue} radius={[0, 4, 4, 0]} maxBarSize={16} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
        <Card className="p-4">
          <p className="font-semibold">Agent usage</p><p className="text-xs text-slate-500">Agents engaged per answered request</p>
          <div className="mt-4 space-y-2.5">
            {m.agent_usage.length === 0 && <p className="text-sm text-slate-500">No agent runs yet.</p>}
            {m.agent_usage.map((a) => (
              <div key={a.agent} className="flex items-center gap-3 text-sm">
                <span className="w-40 shrink-0"><AgentChip name={a.agent} /></span>
                <div className="h-2 flex-1 rounded-full bg-slate-100 dark:bg-slate-800" title={`${a.agent}: ${a.count}`}><div className="h-2 rounded-full" style={{ width: `${(a.count / maxAgent) * 100}%`, background: c.blue }} /></div>
                <span className="w-10 text-right font-mono text-xs">{a.count}</span>
              </div>
            ))}
          </div>
          <p className="mt-5 text-xs font-semibold uppercase tracking-wider text-slate-400">Response outcomes</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {m.response_outcomes.map((o) => <span key={o.status} className="rounded-md bg-slate-100 px-2 py-1 text-xs dark:bg-slate-800">{title(o.status)} <b className="ml-1">{o.count}</b></span>)}
          </div>
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="p-4">
          <p className="font-semibold">Knowledge by classification</p><p className="text-xs text-slate-500">Published & superseded documents</p>
          <div className="mt-4 space-y-3">
            {m.document_classifications.map((d) => (
              <div key={d.classification}>
                <div className="flex items-center justify-between text-sm"><ClassBadge level={d.classification} /><span className="font-mono text-xs">{d.count.toLocaleString()} · {Math.round((d.count / docTotal) * 100)}%</span></div>
                <div className="mt-1.5 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800"><div className="h-1.5 rounded-full bg-slate-500 dark:bg-slate-400" style={{ width: `${(d.count / docTotal) * 100}%` }} /></div>
              </div>
            ))}
          </div>
        </Card>
        <Card className="p-4 lg:col-span-2">
          <p className="font-semibold">Database records</p><p className="text-xs text-slate-500">Synthetic enterprise dataset (fictional) — {m.kpis.database_records.toLocaleString()} rows</p>
          <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-3">
            {m.records_by_table.map((r) => (
              <div key={r.table} className="flex items-center justify-between border-b border-slate-100 py-1.5 text-[13px] dark:border-slate-800">
                <span className="text-slate-600 dark:text-slate-300">{r.table}</span><span className="font-mono text-xs">{r.count.toLocaleString()}</span></div>
            ))}
          </div>
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-4">
          <p className="font-semibold">Recent audit events</p>
          <div className="mt-2 divide-y divide-slate-100 dark:divide-slate-800">
            {m.recent_events.map((e) => (
              <div key={e.id} className="flex items-center gap-3 py-2 text-[13px]">
                <span className="w-28 shrink-0 text-xs text-slate-500">{fmtTime(e.ts)}</span>
                <span className="min-w-0 flex-1 truncate"><b className="font-medium">{e.user_name || "—"}</b> · <span className="font-mono text-xs">{e.action}</span></span>
                <ResultBadge value={e.permission_result} />
              </div>
            ))}
          </div>
        </Card>
        <Card className="p-4">
          <p className="font-semibold">Most denied users (7d)</p>
          <div className="mt-2 divide-y divide-slate-100 dark:divide-slate-800">
            {m.top_denied_users.map((u) => (
              <div key={u.user} className="flex items-center gap-3 py-2 text-sm">
                <span className="w-44 truncate">{u.user}</span>
                <div className="h-2 flex-1 rounded-full bg-slate-100 dark:bg-slate-800"><div className="h-2 rounded-full" style={{ width: `${(u.count / m.top_denied_users[0].count) * 100}%`, background: c.red }} /></div>
                <span className="w-10 text-right font-mono text-xs">{u.count}</span>
              </div>
            ))}
          </div>
          <p className="mt-5 flex items-center gap-1.5 text-xs text-slate-500"><Bot className="h-3.5 w-3.5" />Answer feedback: {m.kpis.positive_feedback ?? 0} helpful · {m.kpis.negative_feedback ?? 0} not helpful</p>
        </Card>
      </div>
    </div>
  );
}

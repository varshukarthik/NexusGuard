import { Activity, AlertTriangle, ArrowDown, ArrowRight, Brain, Cloud, Database, Eye, Globe, Lock, Network, Server,
  Shield, ShieldCheck, Siren, Waves } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import type { Alert, AuditRow } from "../lib/types";
import { Button, Card, ClassBadge, cx, Drawer, Empty, fmtTime, PageHeader, ResultBadge, RiskBadge, SimBadge, Spinner } from "../lib/ui";

interface Layer { key: string; name: string; status: string; mode: string; detail: string }
const ICONS: Record<string, any> = { ddos: Waves, waf: Shield, rate: Activity, tls: Lock, encryption: Database, network: Network,
  rbac: ShieldCheck, injection: Siren, dlp: Eye, audit: Activity };

function Node({ icon: I, title, sub, sim, tone = "slate" }: { icon: any; title: string; sub?: string; sim?: boolean; tone?: string }) {
  return (
    <div className={cx("relative flex min-w-[128px] flex-1 items-center gap-2 rounded-xl border bg-white px-3 py-2.5 shadow-card dark:bg-slate-900",
      sim ? "border-dashed border-violet-300 dark:border-violet-500/40" : tone === "brand" ? "border-brand-300 dark:border-brand-500/40" : "border-slate-200 dark:border-slate-700")}>
      <I className={cx("h-4 w-4 shrink-0", sim ? "text-violet-500" : "text-brand-600")} />
      <div className="min-w-0"><p className="text-[12.5px] font-semibold leading-tight">{title}</p>{sub && <p className="text-[10.5px] leading-tight text-slate-500">{sub}</p>}</div>
    </div>
  );
}
const Arrow = () => <ArrowRight className="hidden h-4 w-4 shrink-0 text-slate-300 lg:block" />;

export function Architecture() {
  return (
    <Card className="p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <p className="font-semibold">VPC-ready deployment architecture</p>
        <div className="flex items-center gap-3 text-[11px] text-slate-500">
          <span className="flex items-center gap-1"><span className="h-3 w-5 rounded border border-dashed border-violet-400" />Prototype simulation</span>
          <span className="flex items-center gap-1"><span className="h-3 w-5 rounded border border-brand-400" />Implemented in app</span>
        </div>
      </div>
      <div className="flex flex-col items-stretch gap-2 lg:flex-row lg:items-center">
        <Node icon={Globe} title="Internet" sub="Employees (browser)" />
        <Arrow /><Node icon={Waves} title="DDoS Protection" sub="Shield / Cloudflare" sim />
        <Arrow /><Node icon={Shield} title="WAF" sub="OWASP managed rules" sim />
        <Arrow /><Node icon={Network} title="Load Balancer" sub="TLS 1.3 termination" sim />
        <Arrow /><Node icon={Server} title="FastAPI gateway" sub="AuthN · rate limit · RBAC" tone="brand" />
      </div>
      <div className="my-2 flex justify-end pr-16"><ArrowDown className="h-4 w-4 text-slate-300" /></div>
      <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 p-4 dark:border-slate-700 dark:bg-slate-950/40">
        <p className="mb-3 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500"><Lock className="h-3 w-3" />Private subnets · no public IPs</p>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <Node icon={ShieldCheck} title="Permission engine" sub="check(user, document)" tone="brand" />
          <Node icon={Brain} title="Agent + RAG service" sub="tools · guardrails · DLP" tone="brand" />
          <Node icon={Database} title="PostgreSQL + pgvector" sub="tenant-scoped (company_id)" tone="brand" />
          <Node icon={Cloud} title="OpenAI API" sub="egress via NAT · key server-side" />
        </div>
      </div>
      <p className="mt-3 text-xs text-slate-500">The database and AI/RAG services are never exposed to the internet. The LLM only ever receives excerpts that passed the permission engine; the OpenAI key lives in server environment variables.</p>
    </Card>
  );
}

function AlertDrawer({ alert, onClose, onChange }: { alert: Alert | null; onClose: () => void; onChange: () => void }) {
  const { can, notify } = useApp();
  const [data, setData] = useState<{ events: AuditRow[]; user: any; summary: Record<string, number> } | null>(null);
  useEffect(() => { if (alert) { setData(null); api.get<any>(`/security-alerts/${alert.id}/activity`).then(setData).catch(() => {}); } }, [alert]);
  async function set(status: string) {
    try { await api.patch(`/security-alerts/${alert!.id}`, { status }); notify(`Alert marked ${status}`); onChange(); onClose(); }
    catch (e: any) { notify(e.message, "err"); }
  }
  return (
    <Drawer open={!!alert} onClose={onClose} title={<span className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-amber-500" />Investigate alert</span>}>
      {alert && (
        <div className="space-y-4 p-5">
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-500/30 dark:bg-amber-500/10">
            <p className="flex items-center gap-2 font-semibold">⚠️ {alert.title} <RiskBadge risk={alert.risk} /></p>
            <dl className="mt-2 grid grid-cols-[90px_1fr] gap-y-1 text-sm">
              <dt className="text-slate-500">User</dt><dd>{alert.user_name}{data?.user && ` · ${data.user.title} · clearance ${data.user.clearance}`}</dd>
              <dt className="text-slate-500">Pattern</dt><dd>{alert.pattern}</dd>
              <dt className="text-slate-500">Status</dt><dd className="capitalize">{alert.status}</dd>
              <dt className="text-slate-500">Detected</dt><dd>{fmtTime(alert.ts)} · rule {String(alert.details.rule ?? alert.alert_type)}</dd>
            </dl>
            {can("security:admin") && (
              <div className="mt-3 flex gap-2">
                {alert.status !== "investigating" && <Button size="sm" onClick={() => set("investigating")}>Mark investigating</Button>}
                {alert.status !== "resolved" && <Button size="sm" variant="success" onClick={() => set("resolved")}>Resolve</Button>}
              </div>
            )}
          </div>
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Related activity (±24h)</p>
            {!data ? <Spinner /> : data.events.length === 0 ? <p className="text-sm text-slate-500">No related audit events (seeded historical alert).</p> : (
              <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
                {data.events.map((e) => (
                  <div key={e.id} className="flex items-start gap-3 px-3 py-2 text-xs">
                    <span className="w-28 shrink-0 text-slate-500">{fmtTime(e.ts)}</span>
                    <div className="min-w-0 flex-1"><p className="font-medium">{e.action} {e.resource && `· ${e.resource}`}</p>{e.query && <p className="truncate text-slate-500">“{e.query}”</p>}</div>
                    {e.classification && <ClassBadge level={e.classification} size="xs" />}
                    <ResultBadge value={e.permission_result} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </Drawer>
  );
}

export default function SecurityCenter() {
  const { can, version } = useApp();
  const [status, setStatus] = useState<{ layers: Layer[]; counters: Record<string, number> } | null>(null);
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [sel, setSel] = useState<Alert | null>(null);
  const [filter, setFilter] = useState<"active" | "all">("active");
  const loadAlerts = () => can("security:read") && api.get<Alert[]>("/security-alerts").then(setAlerts).catch(() => {});
  useEffect(() => { api.get<any>("/security/status").then(setStatus).catch(() => {}); loadAlerts(); }, [version]);
  const shown = (alerts ?? []).filter((a) => filter === "all" || a.status !== "resolved");

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <PageHeader icon={<Shield className="h-5 w-5" />} title="Security Center"
        subtitle="Infrastructure and AI security posture. Components marked “Prototype Simulation” are represented, not actually deployed." />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5">
        {status?.layers.map((l) => {
          const I = ICONS[l.key] ?? Shield;
          return (
            <Card key={l.key} className="p-3.5">
              <div className="flex items-center justify-between gap-2"><I className="h-4 w-4 shrink-0 text-brand-600" /><SimBadge mode={l.mode} /></div>
              <p className="mt-2.5 text-sm font-semibold">{l.name}</p>
              <p className="mt-0.5 flex items-center gap-1.5 text-xs font-semibold text-emerald-600"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />{l.status}</p>
              <p className="mt-1.5 text-[11.5px] leading-snug text-slate-500">{l.detail}</p>
            </Card>
          );
        })}
      </div>
      <Architecture />
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-800">
          <p className="flex items-center gap-2 font-semibold"><Siren className="h-4 w-4 text-rose-500" />Security alerts <span className="text-xs font-normal text-slate-500">rule-based anomaly detection</span></p>
          {alerts && <div className="flex gap-1 rounded-lg bg-slate-100 p-0.5 text-xs dark:bg-slate-800">
            {(["active", "all"] as const).map((f) => <button key={f} onClick={() => setFilter(f)} className={cx("rounded-md px-2.5 py-1 font-medium capitalize", filter === f ? "bg-white shadow-sm dark:bg-slate-700" : "text-slate-500")}>{f}</button>)}
          </div>}
        </div>
        {!can("security:read") ? (
          <Empty icon={<Lock className="h-5 w-5" />} title="Restricted to security administrators" text="Your role lacks security:read. Switch to Arjun Nair (Security Admin) or Vikram Mehta (Executive) to inspect alerts." />
        ) : !alerts ? <div className="flex justify-center p-8"><Spinner /></div> : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {shown.map((a) => (
              <div key={a.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <div className={cx("rounded-lg p-2", a.risk === "LOW" || a.risk === "MEDIUM" ? "bg-amber-50 text-amber-600 dark:bg-amber-500/10" : "bg-rose-50 text-rose-600 dark:bg-rose-500/10")}><AlertTriangle className="h-4 w-4" /></div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{a.title} <span className="font-normal text-slate-500">· {a.user_name}</span></p>
                  <p className="text-xs text-slate-500">{a.pattern} · {fmtTime(a.ts)}</p>
                </div>
                <span className={cx("rounded px-1.5 py-0.5 text-[11px] font-semibold capitalize",
                  a.status === "open" ? "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300" : a.status === "investigating" ? "bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-300" : "bg-slate-100 text-slate-500 dark:bg-slate-800")}>{a.status}</span>
                <RiskBadge risk={a.risk} />
                <Button size="sm" onClick={() => setSel(a)}>Inspect</Button>
              </div>
            ))}
            {shown.length === 0 && <p className="p-6 text-center text-sm text-slate-500">No active alerts.</p>}
          </div>
        )}
      </Card>
      <AlertDrawer alert={sel} onClose={() => setSel(null)} onChange={loadAlerts} />
    </div>
  );
}

import { useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, Bot, CheckCircle2 , FileCheck2, Lock, Play, ShieldCheck, Square, Workflow } from "lucide-react";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import type { AgentPlan, ChatMessage } from "../lib/types";
import { Button, Card, cx, RiskBadge, Spinner } from "../lib/ui";

const EXAMPLES = [
  "Prepare everything I need for tomorrow's client meeting.",
  "I need next Friday off and please let my manager know.",
  "Summarize my open work and prepare my weekly report.",
  "My VPN is broken. Create everything needed to resolve the issue.",
  "Find everything I need for Project Phoenix and flag anything I cannot access."
];

export default function WorkMode() {
  const { notify, go, bump, can } = useApp();
  const [goal,setGoal]=useState("");
  const [plan,setPlan]=useState<AgentPlan|null>(null);
  const [busy,setBusy]=useState(false);
  const [running,setRunning]=useState(false);
  const [overview,setOverview]=useState<any|null>(null);
  const [result,setResult]=useState<ChatMessage|null>(null);
  useEffect(() => { api.get<any>("/agentic/overview").then(setOverview).catch(() => {}); }, []);

  async function createPlan() {
    if (!goal.trim()) return;
    setBusy(true); setResult(null);
    try { setPlan(await api.post<AgentPlan>("/agentic/plan",{goal:goal.trim()})); }
    catch(e:any){notify(e.message,"err")} finally{setBusy(false)}
  }

  async function execute() {
    if(!goal.trim()) return;
    setRunning(true);
    try {
      // Reuse the production chat/agent pipeline: Work Mode is an orchestration surface,
      // not a second, weaker execution engine.
      const r=await api.post<{assistant_message:ChatMessage}>("/chat",{message:goal.trim()});
      setResult(r.assistant_message); bump();
    } catch(e:any){notify(e.message,"err")} finally{setRunning(false)}
  }

  return <div className="mx-auto max-w-6xl space-y-5 p-6">
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-brand-600"><Bot className="h-4 w-4"/>Agentic Work Mode</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">What would you like me to get done?</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">Describe an outcome. The NovaTech Solutions agents create a governed plan, checks permissions and risk, pauses at approval gates, executes through the same secure tool gateway, and reports what was verified.</p>
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300"><ShieldCheck className="h-4 w-4"/>Security controls active</div>
      </div>
      <div className="mt-5 flex flex-col gap-2 sm:flex-row">
        <textarea value={goal} onChange={e=>setGoal(e.target.value)} rows={3} placeholder="Example: Prepare everything I need for tomorrow's client meeting…" className="input flex-1 resize-none"/>
        <Button variant="primary" onClick={createPlan} disabled={!goal.trim()||busy} className="sm:self-end">{busy?<Spinner/>:<Workflow className="h-4 w-4"/>}Create governed plan</Button>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">{EXAMPLES.map(x=><button key={x} onClick={()=>setGoal(x)} className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-500 hover:border-brand-300 hover:text-brand-700 dark:border-slate-700">{x}</button>)}</div>
    </div>

    {plan && <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <div><p className="font-semibold">Execution plan</p><p className="mt-0.5 text-xs text-slate-500">{plan.steps.length} steps · dependencies enforced</p></div>
          <RiskBadge risk={plan.overall_risk}/>
        </div>
        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {plan.steps.map((s,i)=><div key={s.id} className="flex gap-3 px-5 py-4">
            <div className={cx("mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold",s.approval_required?"bg-amber-50 text-amber-700 dark:bg-amber-500/10":"bg-slate-100 text-slate-600 dark:bg-slate-800")}>{i+1}</div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2"><p className="text-sm font-medium">{s.label}</p>{s.approval_required&&<span className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 dark:bg-amber-500/10">APPROVAL GATE</span>}<span className="text-[10px] uppercase tracking-wider text-slate-400">{s.kind}</span></div>
              <p className="mt-1 text-xs text-slate-500">Risk: {s.risk}{s.tool&&` · tool: ${s.tool}`}{s.depends_on.length>0&&` · after ${s.depends_on.join(", ")}`}</p>
            </div>
            {s.id==="verify"?<FileCheck2 className="h-4 w-4 text-brand-500"/>:s.approval_required?<AlertTriangle className="h-4 w-4 text-amber-500"/>:<CheckCircle2 className="h-4 w-4 text-emerald-500"/>}
          </div>)}
        </div>
        <div className="flex flex-wrap gap-2 border-t border-slate-100 bg-slate-50/70 px-5 py-4 dark:border-slate-800 dark:bg-slate-950/40">
          <Button variant="primary" onClick={execute} disabled={running}>{running?<Spinner/>:<Play className="h-4 w-4"/>}Run with agents</Button>
          <Button onClick={()=>{setPlan(null);setResult(null)}}><Square className="h-4 w-4"/>Clear plan</Button>
          <span className="ml-auto flex items-center gap-1.5 text-xs text-slate-500"><Lock className="h-3.5 w-3.5"/>No step bypasses authorization</span>
        </div>
      </Card>

      <div className="space-y-3">
        <Card className="p-4"><p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Governance</p>
          <div className="mt-3 space-y-2">{plan.principles.map(p=><div key={p} className="flex items-center gap-2 text-sm"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500"/>{p}</div>)}</div>
        </Card>
        <Card className="p-4"><p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Lifecycle</p>
          <div className="mt-3 space-y-2 text-xs text-slate-600 dark:text-slate-300">
            {["Understand goal","Plan & check policy","Execute permitted work","Human approval where required","Verify side effects","Audit everything"].map((x,i)=><div key={x} className="flex items-center gap-2"><span className="font-mono text-slate-400">{String(i+1).padStart(2,"0")}</span>{x}</div>)}
          </div>
        </Card>
      </div>
    </div>}

    {can("security:read") && <Card className="p-4">
      <div className="flex flex-wrap items-center justify-between gap-2"><div><p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Red Team Mode · safe simulation</p><p className="mt-1 text-sm font-medium">Demonstrate the security boundary without executing a real exploit.</p></div><span className="rounded bg-amber-50 px-2 py-1 text-[10px] font-semibold text-amber-700 dark:bg-amber-500/10">NO REAL ATTACK</span></div>
      <div className="mt-3 flex flex-wrap gap-1.5">{["Prompt Injection","Data Exfiltration","Privilege Escalation","Malicious Document","Cross-Tenant Access","Tool Abuse","PII Leakage","Indirect Prompt Injection"].map(x=><button key={x} onClick={async()=>{try{const r=await api.post<any>("/agentic/red-team",{attack_type:x});notify(`${x}: blocked · ${r.audit_event}`)}catch(e:any){notify(e.message,"err")}}} className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs hover:border-rose-300 hover:text-rose-700 dark:border-slate-800">{x}</button>)}</div>
    </Card>}

    {overview && <div className="grid gap-4 lg:grid-cols-3">
      {overview.metrics && <Card className="p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">AI observability</p>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {[["Workflow runs",overview.metrics.workflow_runs],["Tool calls",overview.metrics.tool_executions],["Pending approvals",overview.metrics.pending_approvals],["Active alerts",overview.metrics.active_alerts],["Avg latency",`${overview.metrics.avg_workflow_ms} ms`],["Est. cost",`$${overview.metrics.estimated_cost_usd}`]].map(([k,v])=><div key={String(k)} className="rounded-lg bg-slate-50 p-2.5 dark:bg-slate-950"><p className="text-[10px] text-slate-400">{k}</p><p className="mt-0.5 font-mono text-sm font-semibold">{v}</p></div>)}
        </div>
        <p className="mt-2 text-[10px] text-slate-400">{overview.metrics.note}</p>
      </Card>}
      <Card className="p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">AI firewall</p>
        <div className="mt-3 space-y-2">{overview.firewall.map((x:any)=><div key={x.layer} className="flex items-start gap-2"><CheckCircle2 className={cx("mt-0.5 h-3.5 w-3.5 shrink-0",x.status==="ENFORCED"?"text-emerald-500":"text-amber-500")}/><div><p className="text-xs font-medium">{x.layer} · {x.status}</p><p className="text-[10px] text-slate-500">{x.controls.join(" · ")}</p></div></div>)}</div>
      </Card>
      {overview.access_review && <Card className="p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Access governance</p>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {[["Employees",overview.access_review.employees],["Reviews due",overview.access_review.reviews_required],["High privilege",overview.access_review.high_privilege_accounts],["Temp grants",overview.access_review.temporary_grants],["Expired grants",overview.access_review.expired_grants],["Stale permissions",overview.access_review.stale_permissions]].map(([k,v])=><div key={String(k)} className="rounded-lg border border-slate-200 p-2.5 dark:border-slate-800"><p className="text-[10px] text-slate-400">{k}</p><p className="mt-0.5 font-semibold">{v}</p></div>)}
        </div>
        <p className="mt-2 text-[10px] text-slate-400">Review and revoke changes remain administrator-controlled.</p>
      </Card>}
      <Card className="p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Enterprise connectors</p>
        <div className="mt-3 space-y-2">{overview.connectors.map((x:any)=><div key={x.id} className="flex items-center gap-2 rounded-lg border border-slate-200 px-2.5 py-2 dark:border-slate-800"><div className="min-w-0 flex-1"><p className="text-xs font-medium">{x.name}</p><p className="text-[10px] text-slate-500">{x.category} · {x.scopes.join(", ")}</p></div><span className="rounded bg-violet-50 px-1.5 py-0.5 text-[9px] font-semibold text-violet-700 dark:bg-violet-500/10 dark:text-violet-300">{x.mode}</span></div>)}</div>
      </Card>
    </div>}

    {result && <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-2"><div><p className="font-semibold">Agent result</p><p className="text-xs text-slate-500">Returned by the same production agent pipeline used by AI Assistant.</p></div><Button onClick={()=>go("chat")}>Open conversation <ArrowRight className="h-4 w-4"/></Button></div>
      <div className="mt-4 rounded-xl bg-slate-50 p-4 text-sm leading-6 whitespace-pre-wrap dark:bg-slate-950">{result.content}</div>
      {result.meta?.timeline && <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{result.meta.timeline.slice(-8).map((s:any)=><div key={s.key} className="rounded-lg border border-slate-200 p-3 dark:border-slate-800"><p className="text-xs font-medium">{s.label}</p><p className="mt-1 text-[11px] text-slate-500">{s.status} · {s.detail||"completed"}</p></div>)}</div>}
    </Card>}
  </div>
}

import { Cpu, Database, KeyRound, LogOut, Settings as Cog, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import { Card, ClassBadge, fmtTime, PageHeader } from "../lib/ui";

export default function Settings() {
  const { me } = useApp();
  const [health, setHealth] = useState<any>(null);
  const [perm, setPerm] = useState<any>(null);
  useEffect(() => {
    api.get("/health").then(setHealth).catch(() => {});
    api.get("/permissions").then(setPerm).catch(() => {});
  }, []);
  const Row = ({ k, v }: { k: string; v: React.ReactNode }) => (
    <div className="flex justify-between gap-4 py-2 text-sm"><span className="text-slate-500">{k}</span><span className="text-right font-medium">{v}</span></div>
  );
  return (
    <div className="mx-auto max-w-5xl space-y-5 p-6">
      <PageHeader icon={<Cog className="h-5 w-5" />} title="Settings" subtitle="Your profile, session, permission matrix and platform configuration." />
      <div className="grid gap-5 md:grid-cols-2">
        <Card className="p-4">
          <p className="mb-2 flex items-center gap-2 font-semibold"><KeyRound className="h-4 w-4 text-brand-600" />Identity & session</p>
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            <Row k="Name" v={me.full_name} /><Row k="Email" v={me.email} /><Row k="Employee ID" v={me.employee_code} />
            <Row k="Department / role" v={`${me.department} · ${me.role_name}`} /><Row k="Clearance" v={<ClassBadge level={me.clearance} />} />
            <Row k="Auth method" v={me.auth_method === "saml-password" ? "Password (demo identity store)" : "Company SSO (demo IdP)"} /><Row k="Session started" v={fmtTime(me.session_started)} /><Row k="Session expires" v={fmtTime(me.session_expires)} />
          </div>
        </Card>
        <Card className="p-4">
          <p className="mb-2 flex items-center gap-2 font-semibold"><Cpu className="h-4 w-4 text-brand-600" />Platform</p>
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            <Row k="AI engine" v={health?.ai_engine === "openai" ? `OpenAI · ${health.model}` : "Offline deterministic engine"} />
            <Row k="Embeddings" v={<span className="font-mono text-xs">{health?.embeddings}</span>} />
            <Row k="Database" v={<span className="flex items-center gap-1"><Database className="h-3.5 w-3.5" />{health?.database}{health?.pgvector && " + pgvector"}</span>} />
            <Row k="Tenant" v={`${me.company_name} (${me.company_id})`} />
          </div>
          {health?.ai_engine !== "openai" && (
            <p className="mt-3 rounded-lg bg-slate-100 p-2.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              To enable OpenAI, set <code className="font-mono">OPENAI_API_KEY</code> in <code className="font-mono">backend/.env</code> and restart the backend. The key is read server-side only and never sent to the browser.
            </p>
          )}
        </Card>
      </div>
      {perm && (
        <Card className="p-4">
          <p className="mb-3 flex items-center gap-2 font-semibold"><ShieldCheck className="h-4 w-4 text-brand-600" />Tool permissions (least privilege)</p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {perm.tools.map((t: any) => (
              <div key={t.tool} className={`rounded-lg border px-3 py-2 text-xs ${t.allowed ? "border-slate-200 dark:border-slate-700" : "border-dashed border-slate-200 opacity-60 dark:border-slate-700"}`}>
                <p className="font-mono font-semibold">{t.tool}()</p>
                <p className="text-slate-500">{t.permission} · risk {t.risk}{t.confirm && " · confirmation"}</p>
                <p className={t.allowed ? "font-semibold text-emerald-600" : "font-semibold text-rose-500"}>{t.allowed ? "✓ allowed" : "✕ not permitted"}</p>
              </div>
            ))}
          </div>
          <p className="mb-2 mt-5 font-semibold">Document scope by classification</p>
          <div className="grid gap-2 sm:grid-cols-4">
            {Object.entries(perm.levels).map(([k, v]: any) => (
              <div key={k} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"><ClassBadge level={k} /><p className="mt-2 text-lg font-semibold">{v.accessible}<span className="text-sm font-normal text-slate-400"> / {v.total}</span></p></div>
            ))}
          </div>
        </Card>
      )}
      <p className="flex items-center gap-1.5 text-xs text-slate-400"><LogOut className="h-3.5 w-3.5" />Use the sign-out button in the top bar to end the session (revoked server-side).</p>
    </div>
  );
}

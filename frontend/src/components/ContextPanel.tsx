import { BadgeCheck, Building2, ChevronDown, Clock, Cpu, Fingerprint, KeyRound, Network, ShieldCheck, X } from "lucide-react";
import { useState } from "react";
import { useApp } from "../lib/app";
import { Avatar, ClassBadge, cx, fmtTime } from "../lib/ui";

const LEVELS = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"];

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 py-1.5 text-[13px]">
      <span className="text-slate-500">{label}</span>
      <span className="text-right font-medium text-slate-800 dark:text-slate-200">{children}</span>
    </div>
  );
}

export default function ContextPanel({ onClose }: { onClose: () => void }) {
  const { me } = useApp();
  const [perms, setPerms] = useState(false);
  const lvl = LEVELS.indexOf(me.clearance);
  return (
    <aside className="hidden w-[300px] shrink-0 overflow-y-auto border-l border-slate-200 bg-white xl:block dark:border-slate-800 dark:bg-slate-900/60 scroll-thin">
      <div className="flex items-center justify-between px-5 pb-2 pt-4">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{me.is_guest ? "Guest access" : "Access context"}</p>
        <button onClick={onClose} className="rounded p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Close panel"><X className="h-4 w-4" /></button>
      </div>
      <div className="px-5">
        <div className="flex items-center gap-3 rounded-xl bg-gradient-to-br from-slate-50 to-brand-50/60 p-3 ring-1 ring-slate-200/70 dark:from-slate-800/60 dark:to-brand-500/10 dark:ring-slate-700">
          <Avatar name={me.full_name} className="h-11 w-11 text-sm" />
          <div className="min-w-0">
            <p className="truncate font-semibold text-slate-900 dark:text-white">{me.full_name}</p>
            <p className="truncate text-xs text-slate-500">{me.job_title}</p>
            <p className="mt-0.5 flex items-center gap-1 text-[11px] font-medium text-emerald-600"><BadgeCheck className="h-3 w-3" />{me.is_guest ? "Public access only" : "Identity verified"}</p>
          </div>
        </div>

        {!me.is_guest && <div className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
          <Row label="Employee ID"><span className="font-mono text-xs">{me.employee_code}</span></Row>
          <Row label="Department">{me.department}</Row>
          <Row label="Role">{me.role_name}</Row>
          <Row label="Manager">{me.manager?.name ?? "—"}</Row>
          <Row label="Tenant"><span className="inline-flex items-center gap-1"><Building2 className="h-3 w-3 text-slate-400" />{me.company_name}</span></Row>
        </div>}

        <p className="mb-2 mt-5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Access level</p>
        <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-800">
          <div className="flex items-center justify-between"><span className="text-xs text-slate-500">Clearance</span><ClassBadge level={me.clearance} /></div>
          <div className="mt-3 grid grid-cols-4 gap-1">
            {LEVELS.map((l, i) => (
              <div key={l} title={l} className={cx("h-1.5 rounded-full", i <= lvl ? ["bg-emerald-500", "bg-sky-500", "bg-amber-500", "bg-rose-500"][i] : "bg-slate-200 dark:bg-slate-700")} />
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-1">
            {(me.access_scopes ?? []).map((s) => (
              <span key={s} className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">✓ {s}</span>
            ))}
          </div>
          <p className="mt-3 text-xs text-slate-500">
            <span className="font-semibold text-slate-800 dark:text-slate-200">{me.documents_accessible}</span> of {me.documents_total} documents in scope
            {!!me.active_grants?.length && <> · {me.active_grants.length} temporary grant(s)</>}
          </p>
        </div>

        <button onClick={() => setPerms(!perms)} className="mb-2 mt-5 flex w-full items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Active permissions ({me.permissions.length}) <ChevronDown className={cx("h-3.5 w-3.5 transition", perms && "rotate-180")} />
        </button>
        {perms && (
          <div className="flex flex-wrap gap-1">
            {me.permissions.map((p) => (
              <span key={p} className="rounded bg-brand-50 px-1.5 py-0.5 font-mono text-[10.5px] text-brand-700 dark:bg-brand-500/10 dark:text-brand-300">{p}</span>
            ))}
          </div>
        )}

        <p className="mb-2 mt-5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Current session</p>
        <div className="space-y-2 rounded-xl border border-slate-200 p-3 text-xs dark:border-slate-800">
          <p className="flex items-center gap-2"><KeyRound className="h-3.5 w-3.5 text-slate-400" /><span className="text-slate-500">Method</span><span className="ml-auto font-medium">{me.is_guest ? "Guest session" : me.auth_method === "saml-password" ? "Password" : "Company SSO (demo)"}</span></p>
          <p className="flex items-center gap-2"><Fingerprint className="h-3.5 w-3.5 text-slate-400" /><span className="text-slate-500">Session</span><span className="ml-auto font-mono">{me.session_id.slice(-10)}</span></p>
          <p className="flex items-center gap-2"><Network className="h-3.5 w-3.5 text-slate-400" /><span className="text-slate-500">IP</span><span className="ml-auto font-mono">{me.ip}</span></p>
          <p className="flex items-center gap-2"><Clock className="h-3.5 w-3.5 text-slate-400" /><span className="text-slate-500">Expires</span><span className="ml-auto">{fmtTime(me.session_expires)}</span></p>
        </div>

        <p className="mb-2 mt-5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">AI engine</p>
        <div className="mb-6 space-y-2 rounded-xl border border-slate-200 p-3 text-xs dark:border-slate-800">
          <p className="flex items-center gap-2"><Cpu className="h-3.5 w-3.5 text-slate-400" /><span className="font-medium">{me.ai_engine?.provider === "openai" ? "LLM + multi-agent RAG" : "Multi-agent RAG (offline engine)"}</span></p>
          <p className="text-slate-500">{me.ai_engine?.model}</p>
          <p className="flex items-center gap-2 text-slate-500"><ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />RBAC enforced before retrieval</p>
        </div>
      </div>
    </aside>
  );
}

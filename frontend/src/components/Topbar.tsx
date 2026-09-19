import { ChevronDown, Globe2, LogOut, Menu, Moon, PanelRight, Sun, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import type { Page, Persona } from "../lib/types";
import { Avatar, ClassBadge, cx, Spinner } from "../lib/ui";

const TITLES: Record<Page, string> = {
  chat: "AI Assistant", work: "Work Mode", tasks: "My Work", approvals: "Approvals", documents: "Knowledge Base",
  security: "Security Center", audit: "Audit Logs", admin: "Admin Dashboard", lab: "Policy Lab", settings: "Settings",
};

export default function Topbar({ page, panel, togglePanel, onSignOut, onMenu }:
  { page: Page; panel: boolean; togglePanel: () => void; onSignOut: () => void; onMenu: () => void }) {
  const { me, switchUser, notify } = useApp();
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));

  useEffect(() => { api.get<{ personas: Persona[] }>("/auth/sso/config").then((r) => setPersonas(r.personas)).catch(() => {}); }, []);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try { localStorage.setItem("novatech-theme", dark ? "dark" : "light"); } catch { /* */ }
  }, [dark]);

  async function sw(email: string) {
    setBusy(email);
    try { await switchUser(email); setOpen(false); } catch (e: any) { notify(e.message, "err"); } finally { setBusy(null); }
  }

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b border-slate-200 bg-white/85 px-3 backdrop-blur sm:px-4 dark:border-slate-800 dark:bg-slate-900/70">
      <button onClick={onMenu} className="focus-ring rounded-lg p-2 text-slate-500 hover:bg-slate-100 md:hidden dark:hover:bg-slate-800" aria-label="Open menu"><Menu className="h-5 w-5" /></button>
      <div className="flex min-w-0 items-center gap-2 text-sm">
        <span className="hidden text-slate-400 sm:inline">NovaTech Solutions</span>
        <span className="hidden text-slate-300 sm:inline">/</span>
        <h1 className="truncate font-medium text-slate-900 dark:text-white">{TITLES[page]}</h1>
        {me.is_guest && (
          <span className="ml-1 inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-300">
            <Globe2 className="h-3 w-3" />Guest Mode</span>
        )}
      </div>
      <div className="ml-auto flex items-center gap-1">
        {personas.length > 0 && (
          <div className="relative hidden sm:block">
            <button onClick={() => setOpen(!open)} aria-expanded={open} aria-haspopup="menu"
              className="focus-ring flex items-center gap-1.5 rounded-lg border border-dashed border-slate-300 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
              <Users className="h-3.5 w-3.5" /><span className="hidden sm:inline">Switch demo identity</span><ChevronDown className="h-3 w-3" />
            </button>
            {open && (
              <>
                <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
                <div role="menu" className="absolute right-0 z-40 mt-2 w-80 rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl dark:border-slate-700 dark:bg-slate-900">
                  <p className="px-2.5 pb-1.5 pt-1 text-[11px] leading-snug text-slate-500">Development/demo only — re-authenticates as another fictional employee so you can compare permissions.</p>
                  {personas.map((p) => (
                    <button key={p.email} onClick={() => sw(p.email)} disabled={!!busy} role="menuitem"
                      className={cx("flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-800", p.email === me.email && "bg-brand-50 dark:bg-brand-500/10")}>
                      <Avatar name={p.full_name} className="h-7 w-7 text-[10px]" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[13px] font-medium text-slate-800 dark:text-slate-100">{p.full_name}</p>
                        <p className="truncate text-[11px] text-slate-500">{p.note}</p>
                      </div>
                      {busy === p.email ? <Spinner /> : <ClassBadge level={p.clearance} size="xs" />}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
        <button onClick={() => setDark(!dark)} title="Toggle theme" aria-label="Toggle dark mode" className="focus-ring rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800">{dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}</button>
        <button onClick={togglePanel} title="Access context" aria-label="Toggle access context panel" aria-pressed={panel} className={cx("focus-ring hidden rounded-lg p-2 hover:bg-slate-100 xl:block dark:hover:bg-slate-800", panel ? "text-brand-600" : "text-slate-500")}><PanelRight className="h-4 w-4" /></button>
        <div className="ml-1 flex items-center gap-2 border-l border-slate-200 pl-2 sm:pl-3 dark:border-slate-800">
          <Avatar name={me.full_name} className="hidden h-8 w-8 text-xs sm:flex" />
          <div className="hidden leading-tight lg:block">
            <p className="text-[13px] font-medium text-slate-900 dark:text-white">{me.full_name}</p>
            <p className="text-[11px] text-slate-500">{me.is_guest ? "Public access" : me.job_title}</p>
          </div>
          <button onClick={onSignOut} title="Sign out" aria-label="Sign out" className="focus-ring rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800"><LogOut className="h-4 w-4" /></button>
        </div>
      </div>
    </header>
  );
}

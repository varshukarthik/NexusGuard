import { Globe2, LogOut, Menu, Moon, PanelRight, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { useApp } from "../lib/app";
import type { Page } from "../lib/types";
import { Avatar, cx } from "../lib/ui";

const TITLES: Record<Page, string> = {
  chat: "AI Assistant", work: "Work Mode", tasks: "My Work", approvals: "Approvals", documents: "Knowledge Base",
  connectors: "Connectors & Skills", security: "Security Center", audit: "Audit Logs", admin: "Admin Dashboard",
  lab: "Policy Lab", settings: "Settings",
};

export default function Topbar({ page, panel, togglePanel, onSignOut, onMenu }:
  { page: Page; panel: boolean; togglePanel: () => void; onSignOut: () => void; onMenu: () => void }) {
  const { me } = useApp();
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try { localStorage.setItem("novatech-theme", dark ? "dark" : "light"); } catch { /* */ }
  }, [dark]);

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

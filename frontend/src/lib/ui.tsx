import { AlertTriangle, CheckCircle2, Globe2, Loader2, Lock, ShieldAlert, X, XCircle } from "lucide-react";
import { ReactNode, useEffect } from "react";
import type { Classification } from "./types";

export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

export const CLS_STYLE: Record<Classification, { label: string; cls: string; dot: string }> = {
  PUBLIC: { label: "Public", cls: "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-400/20", dot: "bg-emerald-500" },
  INTERNAL: { label: "Internal", cls: "bg-sky-50 text-sky-700 ring-sky-600/20 dark:bg-sky-500/10 dark:text-sky-300 dark:ring-sky-400/20", dot: "bg-sky-500" },
  CONFIDENTIAL: { label: "Confidential", cls: "bg-amber-50 text-amber-800 ring-amber-600/25 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-400/20", dot: "bg-amber-500" },
  RESTRICTED: { label: "Restricted", cls: "bg-rose-50 text-rose-700 ring-rose-600/20 dark:bg-rose-500/10 dark:text-rose-300 dark:ring-rose-400/20", dot: "bg-rose-500" },
};

export function ClassBadge({ level, size = "sm" }: { level?: string; size?: "xs" | "sm" }) {
  const key = (level || "INTERNAL").toUpperCase() as Classification;
  const s = CLS_STYLE[key] ?? CLS_STYLE.INTERNAL;
  const Icon = key === "RESTRICTED" ? Lock : key === "PUBLIC" ? Globe2 : null;
  return (
    <span className={cx("inline-flex items-center gap-1 rounded-md font-medium ring-1 ring-inset whitespace-nowrap",
      size === "xs" ? "px-1.5 py-0 text-[10.5px]" : "px-2 py-0.5 text-xs", s.cls)}>
      {Icon ? <Icon className="h-3 w-3" /> : <span className={cx("h-1.5 w-1.5 rounded-full", s.dot)} />}
      {s.label}
    </span>
  );
}

const RISK: Record<string, string> = {
  LOW: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  MEDIUM: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300",
  HIGH: "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
  CRITICAL: "bg-rose-600 text-white",
};
export const RiskBadge = ({ risk }: { risk: string }) => (
  <span className={cx("inline-flex rounded px-1.5 py-0.5 text-[11px] font-semibold tracking-wide", RISK[risk] ?? RISK.LOW)}>{risk}</span>
);

export function ResultBadge({ value }: { value: string }) {
  const v = value.toUpperCase();
  const map: Record<string, [string, ReactNode]> = {
    ALLOWED: ["text-emerald-700 bg-emerald-50 dark:bg-emerald-500/10 dark:text-emerald-300", <CheckCircle2 className="h-3 w-3" />],
    DENIED: ["text-rose-700 bg-rose-50 dark:bg-rose-500/10 dark:text-rose-300", <XCircle className="h-3 w-3" />],
    BLOCKED: ["text-rose-700 bg-rose-50 dark:bg-rose-500/10 dark:text-rose-300", <ShieldAlert className="h-3 w-3" />],
    REDACTED: ["text-amber-800 bg-amber-50 dark:bg-amber-500/10 dark:text-amber-300", <AlertTriangle className="h-3 w-3" />],
  };
  const [cls, icon] = map[v] ?? ["text-slate-600 bg-slate-100 dark:bg-slate-800 dark:text-slate-300", null];
  return <span className={cx("inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-semibold", cls)}>{icon}{v}</span>;
}

export function Button({ children, variant = "secondary", size = "md", className, ...rest }:
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger" | "success"; size?: "sm" | "md" }) {
  const v = {
    primary: "bg-brand-600 text-white hover:bg-brand-700 shadow-sm disabled:bg-brand-400",
    secondary: "bg-white text-slate-700 ring-1 ring-inset ring-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-200 dark:ring-slate-700 dark:hover:bg-slate-800",
    ghost: "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
    danger: "bg-rose-600 text-white hover:bg-rose-700",
    success: "bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm",
  }[variant];
  return (
    <button {...rest} className={cx("inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition disabled:cursor-not-allowed disabled:opacity-60",
      size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3.5 py-2 text-sm", v, className)}>{children}</button>
  );
}

export const Card = ({ children, className }: { children: ReactNode; className?: string }) => (
  <div className={cx("rounded-xl border border-slate-200 bg-white shadow-card dark:border-slate-800 dark:bg-slate-900", className)}>{children}</div>
);

export const Spinner = ({ className }: { className?: string }) => <Loader2 className={cx("h-4 w-4 animate-spin", className)} />;

export function PageHeader({ title, subtitle, icon, actions }: { title: string; subtitle?: string; icon?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        {icon && <div className="mt-0.5 rounded-lg bg-brand-50 p-2 text-brand-600 dark:bg-brand-500/10 dark:text-brand-300">{icon}</div>}
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">{title}</h1>
          {subtitle && <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
        </div>
      </div>
      {actions}
    </div>
  );
}

export function Empty({ icon, title, text, action }: { icon: ReactNode; title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center py-14 text-center">
      <div className="mb-3 rounded-full bg-slate-100 p-3 text-slate-400 dark:bg-slate-800">{icon}</div>
      <p className="font-medium text-slate-700 dark:text-slate-200">{title}</p>
      {text && <p className="mt-1 max-w-sm text-sm text-slate-500">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Drawer({ open, onClose, title, children, width = "max-w-2xl" }:
  { open: boolean; onClose: () => void; title: ReactNode; children: ReactNode; width?: string }) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-[1px]" onClick={onClose} />
      <div className={cx("relative flex h-full w-full flex-col bg-white shadow-2xl animate-fade-in dark:bg-slate-900", width)}>
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3.5 dark:border-slate-800">
          <div className="min-w-0 font-semibold text-slate-900 dark:text-white">{title}</div>
          <button onClick={onClose} className="rounded-md p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Close"><X className="h-5 w-5" /></button>
        </div>
        <div className="flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}

export function Toast({ msg, kind, onClose }: { msg: string; kind: "ok" | "err"; onClose: () => void }) {
  useEffect(() => { const t = setTimeout(onClose, 4200); return () => clearTimeout(t); }, [onClose]);
  return (
    <div className={cx("fixed bottom-5 left-1/2 z-[60] -translate-x-1/2 rounded-lg px-4 py-2.5 text-sm font-medium shadow-lg animate-fade-in",
      kind === "ok" ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900" : "bg-rose-600 text-white")}>{msg}</div>
  );
}

export const fmtTime = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: true }) : "—";
export const fmtDate = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";
export const initials = (n: string) => n.split(" ").map((x) => x[0]).slice(0, 2).join("").toUpperCase();
export const title = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const SimBadge = ({ mode }: { mode: string }) => (
  <span className={cx("whitespace-nowrap rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
    mode.startsWith("Enforced") ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300"
      : "bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300")}>{mode}</span>
);

export const Avatar = ({ name, className }: { name: string; className?: string }) => (
  <div className={cx("flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-violet-500 font-semibold text-white", className ?? "h-8 w-8 text-xs")}>{initials(name)}</div>
);

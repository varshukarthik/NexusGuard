import { cx } from "../lib/ui";

/** NovaTech Solutions mark — an original four-point "nova" spark on a navy tile. */
export function NovaMark({ className, tile = true }: { className?: string; tile?: boolean }) {
  return (
    <svg viewBox="0 0 32 32" className={cx("shrink-0", className ?? "h-8 w-8")} aria-hidden="true">
      {tile && <rect width="32" height="32" rx="8" className="fill-ink-900 dark:fill-white" />}
      <path d="M16 5c.9 5.6 5.4 10.1 11 11-5.6.9-10.1 5.4-11 11-.9-5.6-5.4-10.1-11-11 5.6-.9 10.1-5.4 11-11z"
        className={tile ? "fill-brand-500 dark:fill-brand-600" : "fill-brand-500"} />
      <circle cx="16" cy="16" r="2.2" className={tile ? "fill-white dark:fill-ink-900" : "fill-white"} />
    </svg>
  );
}

export function BrandLockup({ sub = "Enterprise Intelligence Platform", size = "md", invert = false }:
  { sub?: string | null; size?: "sm" | "md" | "lg"; invert?: boolean }) {
  const mark = { sm: "h-7 w-7", md: "h-9 w-9", lg: "h-11 w-11" }[size];
  const name = { sm: "text-[14px]", md: "text-[15px]", lg: "text-[18px]" }[size];
  return (
    <div className="flex items-center gap-2.5" aria-label="NovaTech Solutions">
      <NovaMark className={mark} />
      <div className="leading-tight">
        <p className={cx("font-semibold tracking-tight", name, invert ? "text-white" : "text-slate-900 dark:text-white")}>
          NovaTech <span className="font-normal opacity-70">Solutions</span></p>
        {sub && <p className={cx("text-[10.5px] font-medium uppercase tracking-[0.14em]", invert ? "text-slate-400" : "text-slate-500")}>{sub}</p>}
      </div>
    </div>
  );
}

import { NovaMark } from "./Brand";

/** Branded loading screen shown while the session and workspace are restored. */
export default function Splash({ label = "Preparing your secure workspace" }: { label?: string }) {
  return (
    <div className="flex h-full min-h-screen flex-col items-center justify-center bg-slate-50 dark:bg-slate-950" role="status" aria-live="polite">
      <div className="animate-rise flex flex-col items-center">
        <NovaMark className="h-14 w-14" />
        <p className="mt-5 text-lg font-semibold tracking-tight text-slate-900 dark:text-white">NovaTech Solutions</p>
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-500">Enterprise Intelligence Platform</p>
        <div className="mt-7 h-[3px] w-44 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
          <div className="h-full w-1/3 rounded-full bg-brand-600 animate-bar" />
        </div>
        <p className="mt-3 text-xs text-slate-500">{label}…</p>
      </div>
    </div>
  );
}

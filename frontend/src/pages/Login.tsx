import { AlertCircle, ArrowLeft, ArrowRight, Bot, ChevronDown, Database, Eye, EyeOff, Globe2, KeyRound, Loader2, Lock, ShieldCheck, X } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import { BrandLockup, NovaMark } from "../components/Brand";
import { api, setToken } from "../lib/api";
import type { Persona } from "../lib/types";
import { Avatar, ClassBadge, cx } from "../lib/ui";

interface SSOConfig { idp_name: string; demo_mode: boolean; guest_mode: boolean; personas: Persona[]; demo_password_hint: string | null }

const ID_RX = /^([^@\s]+@[^@\s]+\.[^@\s]+|[A-Za-z]{2,5}-\d{3,6})$/;

const PILLARS = [
  { icon: Database, title: "Secure enterprise knowledge", text: "Policies, projects and records — retrieved only when your role is allowed to see them." },
  { icon: Bot, title: "Intelligent agents", text: "Specialised HR, IT, project, analytics and workflow agents that plan and act for you." },
  { icon: ShieldCheck, title: "Controlled access", text: "Server-side authorization before every answer, human approval for every action, full audit." },
];

export default function Login({ onLoggedIn, onBack }: { onLoggedIn: () => void; onBack?: () => void }) {
  const [cfg, setCfg] = useState<SSOConfig | null>(null);
  const [ident, setIdent] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [remember, setRemember] = useState(false);
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState("");
  const [forgot, setForgot] = useState(false);
  const [sso, setSso] = useState(false);
  const [demoOpen, setDemoOpen] = useState(false);
  const idRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.get<SSOConfig>("/auth/sso/config").then(setCfg).catch(() => setErr("Can't reach the NovaTech Solutions service right now."));
    idRef.current?.focus();
  }, []);

  const idError = touched && !ID_RX.test(ident.trim()) ? "Enter a corporate email (name@novatech.demo) or employee ID (NT-1042)." : "";
  const pwError = touched && !password ? "Enter your password." : "";

  async function run(key: string, p: Promise<{ token: string }>, keep = remember) {
    setBusy(key); setErr("");
    try {
      const r = await p;
      setToken(r.token, keep);
      onLoggedIn();
    } catch (e: any) {
      setErr(e.message || "Sign-in failed.");
      setBusy(null);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (!ID_RX.test(ident.trim()) || !password) return;
    run("pw", api.post("/auth/login", { email: ident.trim(), password }));
  }

  const inputCls = "w-full rounded-lg border bg-white px-3.5 py-2.5 text-[14px] text-slate-900 placeholder:text-slate-400 transition focus:outline-none focus:ring-4 dark:bg-slate-900 dark:text-white";
  const ok = "border-slate-300 focus:border-brand-500 focus:ring-brand-500/15 dark:border-slate-700";
  const bad = "border-rose-400 focus:border-rose-500 focus:ring-rose-500/15";

  return (
    <div className="flex min-h-full bg-white dark:bg-slate-950">
      {/* ---- Brand panel ---- */}
      <section className="relative hidden w-[46%] max-w-[680px] flex-col justify-between overflow-hidden bg-ink-900 px-12 py-10 text-white lg:flex" aria-label="About the platform">
        <div className="pointer-events-none absolute inset-0 opacity-[0.07] [background-image:linear-gradient(to_right,#fff_1px,transparent_1px),linear-gradient(to_bottom,#fff_1px,transparent_1px)] [background-size:56px_56px]" />
        <div className="pointer-events-none absolute -right-40 -top-40 h-[30rem] w-[30rem] rounded-full bg-brand-600/25 blur-[110px]" />
        <div className="relative"><BrandLockup invert size="lg" /></div>
        <div className="relative max-w-md animate-rise">
          <p className="text-[12px] font-semibold uppercase tracking-[0.22em] text-brand-300">Intelligent. Secure. Agentic.</p>
          <h1 className="mt-4 text-[40px] font-semibold leading-[1.1] tracking-[-0.02em]">The enterprise intelligence platform for NovaTech Solutions.</h1>
          <p className="mt-4 text-[15px] leading-relaxed text-slate-300">Secure enterprise knowledge. Intelligent agents. Controlled access.</p>
          <ul className="mt-10 space-y-5">
            {PILLARS.map((p, i) => (
              <li key={p.title} className="flex gap-3.5 animate-rise" style={{ animationDelay: `${120 + i * 90}ms` }}>
                <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/[0.06] ring-1 ring-white/10"><p.icon className="h-4 w-4 text-brand-300" /></span>
                <div><p className="text-[14px] font-semibold">{p.title}</p><p className="mt-0.5 text-[13px] leading-relaxed text-slate-400">{p.text}</p></div>
              </li>
            ))}
          </ul>
        </div>
        <div className="relative flex items-center gap-5 text-[11.5px] text-slate-500">
          <span className="flex items-center gap-1.5"><Lock className="h-3.5 w-3.5" />Role-based access control</span>
          <span className="flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5" />Every decision audited</span>
        </div>
      </section>

      {/* ---- Sign-in ---- */}
      <main className="flex flex-1 flex-col">
        <div className="flex items-center justify-between px-5 py-5 sm:px-8 lg:hidden">
          <BrandLockup size="sm" />
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="text-xs font-medium text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            >
              Back
            </button>
          )}
        </div>
        <div className="flex flex-1 items-center justify-center px-4 pb-10 sm:px-8">
          <div className="w-full max-w-[420px] animate-rise">
            {onBack && (
              <button
                type="button"
                onClick={onBack}
                className="mb-5 inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                <span>Back to Overview</span>
              </button>
            )}
            {!sso ? (
              <>
                <div className="mb-7">
                  <h2 className="text-[26px] font-semibold tracking-[-0.02em] text-slate-900 dark:text-white">Sign in</h2>
                  <p className="mt-1.5 text-[14px] text-slate-500 dark:text-slate-400">Welcome to NovaTech Solutions. Use your corporate account to continue.</p>
                </div>

                {err && (
                  <div role="alert" className="mb-5 flex items-start gap-2.5 rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-3 text-[13px] text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200">
                    <AlertCircle className="mt-px h-4 w-4 shrink-0" /><span className="flex-1">{err}</span>
                    <button onClick={() => setErr("")} aria-label="Dismiss error" className="rounded p-0.5 hover:bg-rose-100 dark:hover:bg-rose-500/20"><X className="h-3.5 w-3.5" /></button>
                  </div>
                )}

                <form onSubmit={submit} noValidate className="space-y-4">
                  <div>
                    <label htmlFor="ident" className="mb-1.5 block text-[13px] font-medium text-slate-700 dark:text-slate-300">Corporate email or employee ID</label>
                    <input id="ident" ref={idRef} value={ident} onChange={(e) => setIdent(e.target.value)} onBlur={() => ident && setTouched(true)}
                      autoComplete="username" placeholder="name@novatech.demo or NT-1042" aria-invalid={!!idError} aria-describedby={idError ? "ident-err" : undefined}
                      className={cx(inputCls, idError ? bad : ok)} />
                    {idError && <p id="ident-err" className="mt-1.5 text-[12px] text-rose-600 dark:text-rose-400">{idError}</p>}
                  </div>
                  <div>
                    <div className="mb-1.5 flex items-center justify-between">
                      <label htmlFor="pw" className="text-[13px] font-medium text-slate-700 dark:text-slate-300">Password</label>
                      <button type="button" onClick={() => setForgot((f) => !f)} className="focus-ring rounded text-[12.5px] font-medium text-brand-700 hover:text-brand-800 dark:text-brand-400">Forgot password?</button>
                    </div>
                    <div className="relative">
                      <input id="pw" type={show ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)}
                        autoComplete="current-password" placeholder="Enter your password" aria-invalid={!!pwError}
                        className={cx(inputCls, "pr-11", pwError ? bad : ok)} />
                      <button type="button" onClick={() => setShow((s) => !s)} aria-label={show ? "Hide password" : "Show password"} aria-pressed={show}
                        className="focus-ring absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800">
                        {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                    {pwError && <p className="mt-1.5 text-[12px] text-rose-600 dark:text-rose-400">{pwError}</p>}
                  </div>
                  {forgot && (
                    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3.5 py-3 text-[12.5px] leading-relaxed text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                      Passwords are managed by NovaTech IT. Use the self-service reset in the identity portal, or call the IT Service Desk on extension 4357.
                      <span className="mt-1 block text-slate-400">Demo environment: password reset is not connected.</span>
                    </div>
                  )}
                  <label className="flex w-fit cursor-pointer items-center gap-2 text-[13px] text-slate-600 dark:text-slate-400">
                    <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500/30" />
                    Remember me on this device
                  </label>
                  <button type="submit" disabled={!!busy}
                    className="focus-ring group flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-[14px] font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-70">
                    {busy === "pw" ? <><Loader2 className="h-4 w-4 animate-spin" />Signing in…</> : <>Sign in<ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" /></>}
                  </button>
                </form>

                <div className="my-6 flex items-center gap-3 text-[11px] font-medium uppercase tracking-[0.14em] text-slate-400">
                  <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />or<span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
                </div>

                <div className="grid gap-2.5">
                  <button onClick={() => { setErr(""); setSso(true); }} disabled={!!busy}
                    className="focus-ring flex w-full items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white py-2.5 text-[14px] font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800">
                    <KeyRound className="h-4 w-4" />Continue with company SSO
                  </button>
                  {cfg?.guest_mode !== false && (
                    <button onClick={() => run("guest", api.post("/auth/guest"), false)} disabled={!!busy}
                      className="focus-ring group flex w-full items-center justify-center gap-2 rounded-lg border border-brand-200 bg-brand-50/60 py-2.5 text-[14px] font-medium text-brand-800 transition hover:border-brand-300 hover:bg-brand-50 dark:border-brand-500/30 dark:bg-brand-500/10 dark:text-brand-200 dark:hover:bg-brand-500/15">
                      {busy === "guest" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Globe2 className="h-4 w-4" />}Continue as Guest
                    </button>
                  )}
                  <p className="text-center text-[12px] text-slate-500">Guest Mode shows public company information only.</p>
                </div>

                {cfg?.demo_mode && (
                  <div className="mt-7 rounded-lg border border-dashed border-slate-300 dark:border-slate-700">
                    <button onClick={() => setDemoOpen((o) => !o)} aria-expanded={demoOpen}
                      className="focus-ring flex w-full items-center justify-between rounded-lg px-3.5 py-2.5 text-left text-[12.5px] font-medium text-slate-600 dark:text-slate-300">
                      Demo accounts (development only)<ChevronDown className={cx("h-4 w-4 transition", demoOpen && "rotate-180")} />
                    </button>
                    {demoOpen && (
                      <div className="border-t border-dashed border-slate-300 px-3.5 pb-3 pt-2 dark:border-slate-700">
                        <p className="mb-2 text-[11.5px] text-slate-500">Fictional users. Password for all: <code className="rounded bg-slate-100 px-1 font-mono text-slate-700 dark:bg-slate-800 dark:text-slate-200">{cfg.demo_password_hint}</code></p>
                        <div className="space-y-1">
                          {cfg.personas.filter((p) => p.company === "NovaTech Solutions").map((p) => (
                            <button key={p.email} onClick={() => { setIdent(p.email); setPassword(cfg.demo_password_hint ?? ""); setTouched(false); }}
                              className="focus-ring flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left hover:bg-slate-50 dark:hover:bg-slate-800/60">
                              <Avatar name={p.full_name} className="h-6 w-6 text-[9px]" />
                              <span className="min-w-0 flex-1"><span className="block truncate text-[12.5px] font-medium text-slate-800 dark:text-slate-100">{p.full_name}</span>
                                <span className="block truncate text-[11px] text-slate-500">{p.note}</span></span>
                              <ClassBadge level={p.clearance} size="xs" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            ) : (
              <div>
                <button onClick={() => setSso(false)} className="focus-ring mb-6 rounded text-[13px] font-medium text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">← Back to sign in</button>
                <div className="flex items-center gap-3"><NovaMark className="h-10 w-10" />
                  <div><h2 className="text-[20px] font-semibold tracking-tight text-slate-900 dark:text-white">Company single sign-on</h2>
                    <p className="text-[13px] text-slate-500">{cfg?.idp_name ?? "NovaTech SSO"}</p></div></div>
                {err && <div role="alert" className="mt-5 rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-3 text-[13px] text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200">{err}</div>}
                {cfg?.demo_mode ? (
                  <>
                    <p className="mb-2 mt-6 text-[12px] font-medium uppercase tracking-[0.12em] text-slate-400">Choose a demo identity</p>
                    <div className="space-y-2">
                      {cfg.personas.map((p) => (
                        <button key={p.email} disabled={!!busy} onClick={() => run(p.email, api.post("/auth/sso/demo", { email: p.email }))}
                          className="focus-ring flex w-full items-center gap-3 rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 text-left transition hover:border-brand-300 hover:bg-brand-50/40 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-brand-500/40">
                          {busy === p.email ? <Loader2 className="h-8 w-8 animate-spin p-1.5 text-brand-600" /> : <Avatar name={p.full_name} />}
                          <span className="min-w-0 flex-1"><span className="block truncate text-[14px] font-medium text-slate-900 dark:text-white">{p.full_name}</span>
                            <span className="block truncate text-[12px] text-slate-500">{p.job_title} · {p.company}</span></span>
                          <ClassBadge level={p.clearance} size="xs" />
                        </button>
                      ))}
                    </div>
                    <p className="mt-4 text-[12px] leading-relaxed text-slate-500">Demonstration identity provider — production deployments connect NovaTech's SAML 2.0 / OIDC IdP.</p>
                  </>
                ) : <p className="mt-6 text-[13px] text-slate-500">Single sign-on is not configured in this environment.</p>}
              </div>
            )}
          </div>
        </div>
        <footer className="flex flex-col items-center justify-between gap-2 border-t border-slate-100 px-6 py-4 text-[11.5px] text-slate-400 sm:flex-row dark:border-slate-800">
          <p>© 2026 NovaTech Solutions. Fictional company — demonstration data only.</p>
          <p className="flex items-center gap-1.5"><Lock className="h-3 w-3" />Protected by role-based access control</p>
        </footer>
      </main>
    </div>
  );
}

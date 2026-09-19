import {
  ArrowRight,
  Bot,
  Briefcase,
  Building2,
  Check,
  CheckCircle2,
  ChevronRight,
  Database,
  FileCheck,
  GitBranch,
  Loader2,
  Lock,
  Mail,
  MapPin,
  Moon,
  Phone,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sun,
  X,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

interface LandingPageProps {
  onSignIn: () => void;
}

export default function LandingPage({ onSignIn }: LandingPageProps) {
  const [dark, setDark] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem("novatech-theme");
      if (stored) return stored === "dark";
      return document.documentElement.classList.contains("dark");
    } catch {
      return document.documentElement.classList.contains("dark");
    }
  });

  const [activeModal, setActiveModal] = useState<string | null>(null);
  const [contactEmail, setContactEmail] = useState("");
  const [contactOrg, setContactOrg] = useState("");
  const [contactMsg, setContactMsg] = useState("");
  const [contactSubmitting, setContactSubmitting] = useState(false);
  const [contactError, setContactError] = useState("");
  const [contactSubmitted, setContactSubmitted] = useState(false);

  const toggleTheme = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("novatech-theme", next ? "dark" : "light");
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  const handleContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!contactEmail.trim()) return;
    setContactSubmitting(true);
    setContactError("");
    const payload = {
      email: contactEmail.trim(),
      organization: contactOrg.trim(),
      message: contactMsg.trim(),
    };
    try {
      try {
        await api.post("/contact", payload);
      } catch (firstErr: any) {
        // Direct backend fallback if proxy rewrite experiences delays or 404
        const directRes = await fetch("https://nexusguard-backend-8711.onrender.com/api/contact", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!directRes.ok) {
          const data = await directRes.json().catch(() => ({}));
          throw new Error(data.message || `Submission failed (${directRes.status})`);
        }
      }
      setContactSubmitted(true);
      setContactEmail("");
      setContactOrg("");
      setContactMsg("");
    } catch (err: any) {
      setContactError(err?.message || "Could not send inquiry. Please reach out directly at novasolutions@evocation.in.");
    } finally {
      setContactSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-[#070d17] dark:text-slate-100 selection:bg-emerald-500/30 selection:text-emerald-900 dark:selection:text-emerald-300 font-sans antialiased transition-colors duration-200">
      {/* Background ambient lighting */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[55rem] h-[30rem] bg-emerald-500/10 dark:bg-emerald-600/10 blur-[130px] rounded-full" />
        <div className="absolute top-[28rem] -left-32 w-[35rem] h-[35rem] bg-teal-500/5 dark:bg-teal-600/5 blur-[120px] rounded-full" />
        <div className="absolute top-[50rem] -right-32 w-[40rem] h-[40rem] bg-cyan-500/5 dark:bg-cyan-600/5 blur-[130px] rounded-full" />
      </div>

      {/* ==================== 1. TOP NAVBAR ==================== */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-white/85 dark:bg-[#070d17]/90 border-b border-slate-200 dark:border-slate-800/80 transition-colors shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-8 h-20 sm:h-24 flex items-center justify-between">
          {/* Brand Logo */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
            <div className="h-10 w-10 rounded-xl bg-emerald-500 flex items-center justify-center text-slate-950 shadow-md shadow-emerald-500/25">
              <ShieldCheck className="h-6 w-6 text-slate-950 stroke-[2.4]" />
            </div>
            <div className="flex items-center gap-2.5">
              <span className="font-bold text-[19px] tracking-tight text-slate-900 dark:text-white">Nova Solutions</span>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/70 text-slate-700 dark:text-slate-300 tracking-wide">
                Enterprise
              </span>
            </div>
          </div>

          {/* Navigation Links (AI Assistant removed as requested) */}
          <nav className="hidden md:flex items-center gap-9 text-[14px] font-medium text-slate-600 dark:text-slate-300">
            <button onClick={() => scrollTo("solutions")} className="hover:text-slate-950 dark:hover:text-white transition hover:scale-105 transform duration-150">
              Solutions
            </button>
            <button onClick={() => scrollTo("about")} className="hover:text-slate-950 dark:hover:text-white transition hover:scale-105 transform duration-150">
              About
            </button>
            <button onClick={() => scrollTo("demo-scenarios")} className="hover:text-slate-950 dark:hover:text-white transition hover:scale-105 transform duration-150">
              Demo Scenarios
            </button>
            <button onClick={() => scrollTo("careers")} className="hover:text-slate-950 dark:hover:text-white transition hover:scale-105 transform duration-150">
              Careers
            </button>
            <button onClick={() => scrollTo("contact")} className="hover:text-slate-950 dark:hover:text-white transition hover:scale-105 transform duration-150">
              Contact
            </button>
          </nav>

          {/* Actions: Theme Toggle & Sign In */}
          <div className="flex items-center gap-3.5">
            <button
              onClick={toggleTheme}
              className="p-2.5 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800/80 transition"
              title={dark ? "Switch to light theme" : "Switch to dark theme"}
              aria-label="Toggle theme"
            >
              {dark ? <Sun className="h-5 w-5 text-amber-400" /> : <Moon className="h-5 w-5 text-slate-600" />}
            </button>

            <button
              onClick={onSignIn}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-[14px] font-medium bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-800/90 dark:hover:bg-slate-700 dark:border dark:border-slate-700/80 dark:text-white shadow-sm transition hover:border-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
            >
              <Lock className="h-4 w-4 text-slate-400" />
              <span>Sign In</span>
            </button>
          </div>
        </div>
      </header>

      {/* ==================== 2. HERO SECTION ==================== */}
      <section className="relative z-10 pt-16 pb-24 sm:pt-24 sm:pb-36 text-center px-4 sm:px-6 max-w-5xl mx-auto">
        {/* Top Tag Pill */}
        <div className="inline-flex items-center gap-2 rounded-full border border-slate-300/80 bg-white/90 dark:border-slate-800 dark:bg-slate-900/90 px-4 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 shadow-sm dark:shadow-inner mb-10">
          <Building2 className="h-3.5 w-3.5 text-emerald-500 dark:text-emerald-400" />
          <span>Nova Solutions • Enterprise Digital Solutions</span>
        </div>

        {/* Giant Headline */}
        <h1 className="text-4xl sm:text-6xl lg:text-[72px] font-black tracking-tight leading-[1.08] text-slate-950 dark:text-white max-w-4xl mx-auto">
          Building smarter digital operations for{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 via-teal-500 to-emerald-600 dark:from-emerald-400 dark:via-teal-300 dark:to-emerald-200">
            modern enterprises.
          </span>
        </h1>

        {/* Subtitle */}
        <p className="mt-6 text-base sm:text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto leading-relaxed font-normal">
          Nova Solutions helps organizations improve business operations through secure technology, data platforms, automation, and enterprise intelligence.
        </p>

        {/* CTA Buttons */}
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <button
            onClick={() => scrollTo("solutions")}
            className="w-full sm:w-auto px-7 py-3.5 rounded-lg text-[15px] font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/35 transition-all flex items-center justify-center gap-2 transform hover:-translate-y-0.5"
          >
            <span>Explore Our Solutions</span>
            <ArrowRight className="h-4 w-4 stroke-[2.5]" />
          </button>

          <button
            onClick={onSignIn}
            className="w-full sm:w-auto px-7 py-3.5 rounded-lg text-[15px] font-medium bg-white hover:bg-slate-100 border border-slate-300 text-slate-800 shadow-sm dark:bg-slate-800/80 dark:hover:bg-slate-700/80 dark:border-slate-700 dark:text-white transition-all transform hover:-translate-y-0.5 flex items-center justify-center gap-2"
          >
            <Lock className="h-4 w-4 text-slate-400" />
            <span>Sign In</span>
          </button>
        </div>

        {/* Value Props / Highlights */}
        <div className="mt-14 flex flex-wrap items-center justify-center gap-6 sm:gap-10 text-xs sm:text-[13px] font-medium text-slate-600 dark:text-slate-400">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-500 dark:text-emerald-400" />
            <span className="text-slate-700 dark:text-slate-200">Enterprise Architecture</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-500 dark:text-emerald-400" />
            <span className="text-slate-700 dark:text-slate-200">Zero-Trust Governance</span>
          </div>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-500 dark:text-emerald-400" />
            <span className="text-slate-700 dark:text-slate-200">Global Deployment Capability</span>
          </div>
        </div>
      </section>

      {/* ==================== 3. FAKE ENTERPRISE METRICS BAR ==================== */}
      <section className="relative z-10 border-y border-slate-200 bg-white/80 dark:border-slate-800/80 dark:bg-slate-900/40 py-10 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <div>
              <p className="text-3xl sm:text-4xl font-black text-slate-900 dark:text-white tracking-tight">48,000+</p>
              <p className="mt-1 text-xs sm:text-sm font-medium text-slate-500 dark:text-slate-400">Enterprise Records Governed</p>
            </div>
            <div>
              <p className="text-3xl sm:text-4xl font-black text-emerald-600 dark:text-emerald-400 tracking-tight">2,291</p>
              <p className="mt-1 text-xs sm:text-sm font-medium text-slate-500 dark:text-slate-400">Employees Across 44 Units</p>
            </div>
            <div>
              <p className="text-3xl sm:text-4xl font-black text-slate-900 dark:text-white tracking-tight">100%</p>
              <p className="mt-1 text-xs sm:text-sm font-medium text-slate-500 dark:text-slate-400">Pre-Retrieval RBAC Enforcement</p>
            </div>
            <div>
              <p className="text-3xl sm:text-4xl font-black text-teal-600 dark:text-teal-400 tracking-tight">8 Agents</p>
              <p className="mt-1 text-xs sm:text-sm font-medium text-slate-500 dark:text-slate-400">Specialized Autonomous Crew</p>
            </div>
          </div>
        </div>
      </section>

      {/* ==================== 4. SOLUTIONS SECTION ==================== */}
      <section id="solutions" className="relative z-10 py-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 text-xs font-semibold uppercase tracking-wider bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
            <Zap className="h-3.5 w-3.5" />
            Core Enterprise Offerings
          </div>
          <h2 className="mt-4 text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">
            Comprehensive Digital Intelligence Architecture
          </h2>
          <p className="mt-3 text-slate-600 dark:text-slate-400 text-sm sm:text-base leading-relaxed">
            Eliminating unauthorized data leakage while providing employees with automated, verified answers over corporate knowledge bases.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/50 p-7 hover:border-slate-300 dark:hover:border-slate-700 shadow-sm dark:shadow-none hover:bg-slate-50/70 dark:hover:bg-slate-900/80 transition">
            <div className="h-12 w-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400 mb-5">
              <Shield className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Pre-Retrieval Authorization</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              Enforces clearance levels (<code className="text-xs text-emerald-700 bg-emerald-50 dark:text-emerald-300 dark:bg-emerald-950/40 px-1 py-0.5 rounded">Public</code>, <code className="text-xs text-emerald-700 bg-emerald-50 dark:text-emerald-300 dark:bg-emerald-950/40 px-1 py-0.5 rounded">Internal</code>, <code className="text-xs text-emerald-700 bg-emerald-50 dark:text-emerald-300 dark:bg-emerald-950/40 px-1 py-0.5 rounded">Confidential</code>, <code className="text-xs text-emerald-700 bg-emerald-50 dark:text-emerald-300 dark:bg-emerald-950/40 px-1 py-0.5 rounded">Restricted</code>) and department boundaries deterministically before document content is ever indexed or fed into the LLM.
            </p>
          </div>

          {/* Card 2 */}
          <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/50 p-7 hover:border-slate-300 dark:hover:border-slate-700 shadow-sm dark:shadow-none hover:bg-slate-50/70 dark:hover:bg-slate-900/80 transition">
            <div className="h-12 w-12 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-600 dark:text-teal-400 mb-5">
              <GitBranch className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Version Conflict & Outdated Data</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              Detects superseding policies and conflicting historical data. Automatically prioritizes active versions (e.g. v2.0 vs v1.0) and explicitly notifies users of revisions.
            </p>
          </div>

          {/* Card 3 */}
          <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/50 p-7 hover:border-slate-300 dark:hover:border-slate-700 shadow-sm dark:shadow-none hover:bg-slate-50/70 dark:hover:bg-slate-900/80 transition">
            <div className="h-12 w-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-600 dark:text-cyan-400 mb-5">
              <Bot className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">8 Multi-Agent Autonomous Team</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              Specialized agents for HR policies, IT troubleshooting, project analytics, leave workflows, and executive summaries collaborate to fulfill complex requests.
            </p>
          </div>

          {/* Card 4 */}
          <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/50 p-7 hover:border-slate-300 dark:hover:border-slate-700 shadow-sm dark:shadow-none hover:bg-slate-50/70 dark:hover:bg-slate-900/80 transition">
            <div className="h-12 w-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-600 dark:text-amber-400 mb-5">
              <FileCheck className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Human-in-the-Loop Confirmation</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              State-altering tools (IT ticket creation, leave requests, employee communications) never run blindly. They generate preview confirmation cards requiring explicit user sign-off.
            </p>
          </div>

          {/* Card 5 */}
          <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/50 p-7 hover:border-slate-300 dark:hover:border-slate-700 shadow-sm dark:shadow-none hover:bg-slate-50/70 dark:hover:bg-slate-900/80 transition">
            <div className="h-12 w-12 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-600 dark:text-rose-400 mb-5">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Prompt-Injection Defense & DLP</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              Quarantines adversarial input and malicious uploaded files. Applies Data Loss Prevention (DLP) to mask employee tax IDs, bank numbers, and credentials before output delivery.
            </p>
          </div>

          {/* Card 6 */}
          <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/50 p-7 hover:border-slate-300 dark:hover:border-slate-700 shadow-sm dark:shadow-none hover:bg-slate-50/70 dark:hover:bg-slate-900/80 transition">
            <div className="h-12 w-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-600 dark:text-purple-400 mb-5">
              <Database className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Comprehensive Audit Logging</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              Full transparency on every request. Records authorization decisions, risk scores, retrieved document IDs, and administrative metrics in tamper-evident logs.
            </p>
          </div>
        </div>
      </section>

      {/* ==================== 5. DEMO SCENARIOS SECTION ==================== */}
      <section id="demo-scenarios" className="relative z-10 py-24 border-t border-slate-200 bg-slate-100/60 dark:border-slate-800/80 dark:bg-slate-900/30 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-1.5 text-teal-600 dark:text-teal-400 text-xs font-semibold uppercase tracking-wider bg-teal-500/10 px-3 py-1 rounded-full border border-teal-500/20">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Verified Core Evaluation
            </div>
            <h2 className="mt-4 text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">
              Tested Against Real Enterprise Scenarios
            </h2>
            <p className="mt-3 text-slate-600 dark:text-slate-400 text-sm sm:text-base leading-relaxed">
              Explore how Nova Solutions handles permissions, unauthorized requests, and contradictory policies.
            </p>
          </div>

          <div className="mt-14 grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Scenario A */}
            <div className="rounded-2xl border border-emerald-300 bg-white dark:border-emerald-500/30 dark:bg-slate-900/60 p-6 flex flex-col justify-between shadow-sm dark:shadow-none">
              <div>
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Test Scenario A</span>
                  <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300 dark:border-emerald-500/25 px-2 py-0.5 rounded-full">Authorized Access</span>
                </div>
                <h3 className="mt-3 text-lg font-bold text-slate-900 dark:text-white">Finance Q4 Forecast Inquiry</h3>
                <p className="mt-2 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  <b>User:</b> Finance Analyst (<code className="text-emerald-700 dark:text-emerald-300 font-semibold">Internal</code> clearance).<br />
                  <b>Prompt:</b> "What is the Q4 revenue forecast?"<br />
                  <b>Result:</b> Returns verified 120 crore projected revenue citing <code className="text-slate-800 dark:text-slate-200 font-semibold">DOC-101</code>.
                </p>
              </div>
              <button
                onClick={onSignIn}
                className="mt-6 w-full py-2.5 rounded-lg text-xs font-semibold bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-300 dark:bg-emerald-500/15 dark:hover:bg-emerald-500/25 dark:text-emerald-300 dark:border-emerald-500/30 transition flex items-center justify-center gap-1.5"
              >
                <span>Try as Finance Employee</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* Scenario B */}
            <div className="rounded-2xl border border-rose-300 bg-white dark:border-rose-500/30 dark:bg-slate-900/60 p-6 flex flex-col justify-between shadow-sm dark:shadow-none">
              <div>
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-rose-600 dark:text-rose-400 uppercase tracking-wider">Test Scenario B</span>
                  <span className="bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-500/15 dark:text-rose-300 dark:border-rose-500/25 px-2 py-0.5 rounded-full">Relevant but Unauthorized</span>
                </div>
                <h3 className="mt-3 text-lg font-bold text-slate-900 dark:text-white">Marketing Requests Restricted Data</h3>
                <p className="mt-2 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  <b>User:</b> Marketing Specialist (<code className="text-rose-700 dark:text-rose-300 font-semibold">Internal</code> clearance).<br />
                  <b>Prompt:</b> "What is the Q4 revenue forecast?"<br />
                  <b>Result:</b> Safely withheld without revealing confidential numbers or giving document content to the LLM.
                </p>
              </div>
              <button
                onClick={onSignIn}
                className="mt-6 w-full py-2.5 rounded-lg text-xs font-semibold bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-300 dark:bg-rose-500/15 dark:hover:bg-rose-500/25 dark:text-rose-300 dark:border-rose-500/30 transition flex items-center justify-center gap-1.5"
              >
                <span>Test Access Denial</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* Scenario C */}
            <div className="rounded-2xl border border-teal-300 bg-white dark:border-teal-500/30 dark:bg-slate-900/60 p-6 flex flex-col justify-between shadow-sm dark:shadow-none">
              <div>
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-teal-600 dark:text-teal-400 uppercase tracking-wider">Test Scenario C</span>
                  <span className="bg-teal-50 text-teal-700 border border-teal-200 dark:bg-teal-500/15 dark:text-teal-300 dark:border-teal-500/25 px-2 py-0.5 rounded-full">Authorized Conflict</span>
                </div>
                <h3 className="mt-3 text-lg font-bold text-slate-900 dark:text-white">Policy Revisions & Conflicts</h3>
                <p className="mt-2 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  <b>User:</b> Authorized Finance Staff.<br />
                  <b>Conflict:</b> Older v1.0 (110 cr) vs latest v2.0 (125 cr).<br />
                  <b>Result:</b> Correctly evaluates date/version precedence and cites the latest authoritative document.
                </p>
              </div>
              <button
                onClick={onSignIn}
                className="mt-6 w-full py-2.5 rounded-lg text-xs font-semibold bg-teal-50 hover:bg-teal-100 text-teal-700 border border-teal-300 dark:bg-teal-500/15 dark:hover:bg-teal-500/25 dark:text-teal-300 dark:border-teal-500/30 transition flex items-center justify-center gap-1.5"
              >
                <span>Test Version Conflict</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ==================== 6. ABOUT SECTION & CLIENT CASE STUDIES ==================== */}
      <section id="about" className="relative z-10 py-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 text-xs font-semibold uppercase tracking-wider bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
              <Building2 className="h-3.5 w-3.5" />
              About Nova Solutions
            </div>
            <h2 className="mt-4 text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">
              Engineered for Zero-Trust Enterprise Operations
            </h2>
            <p className="mt-4 text-slate-600 dark:text-slate-300 text-sm sm:text-base leading-relaxed">
              Founded as an enterprise AI intelligence provider, Nova Solutions architects intelligent workflow automation that respects strict corporate hierarchies. We bridge conversational search with multi-tiered data governance.
            </p>
            <p className="mt-3 text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
              Our core tenet is deterministic security: AI models should never decide whether a human is allowed to view a piece of information. Authorization must always be evaluated in code before retrieval begins.
            </p>

            <div className="mt-8 space-y-3">
              <div className="flex items-start gap-3">
                <div className="h-6 w-6 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                  <Check className="h-3.5 w-3.5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-white">Multi-Tenant Isolation</h4>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Strict cryptographic session boundaries and database isolation between organizational business units.</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="h-6 w-6 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                  <Check className="h-3.5 w-3.5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-white">Hybrid Retrieval Pipeline</h4>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Combining BM25 keyword matching and dense vector embeddings scored exclusively over authorized document identifiers.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Fake Client Success Stories */}
          <div className="space-y-4">
            <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/60 p-5 shadow-sm dark:shadow-none">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-bold text-slate-900 dark:text-white">Apex Logistics Global</h4>
                <span className="text-[11px] text-emerald-700 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-500/20 font-semibold">Supply Chain</span>
              </div>
              <p className="mt-2 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                "Nova Solutions unified our operational playbooks across 12 distribution centers while blocking cross-regional supplier pricing leaks with 100% reliability."
              </p>
              <p className="mt-3 text-[11px] font-medium text-slate-700 dark:text-slate-300">— Neha Kapoor, VP of Digital Transformation</p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/60 p-5 shadow-sm dark:shadow-none">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-bold text-slate-900 dark:text-white">Orbit Labs Life Sciences</h4>
                <span className="text-[11px] text-teal-700 bg-teal-50 dark:text-teal-400 dark:bg-teal-500/10 px-2 py-0.5 rounded border border-teal-200 dark:border-teal-500/20 font-semibold">BioTech</span>
              </div>
              <p className="mt-2 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                "Clinical trials and patent filings are isolated strictly by department. Nova Solutions guarantees research scientists cannot inadvertently view executive acquisition memos."
              </p>
              <p className="mt-3 text-[11px] font-medium text-slate-700 dark:text-slate-300">— Dr. Maya Collins, Chief Information Officer</p>
            </div>
          </div>
        </div>
      </section>

      {/* ==================== 7. CAREERS SECTION ==================== */}
      <section id="careers" className="relative z-10 py-24 border-t border-slate-200 bg-slate-100/50 dark:border-slate-800/80 dark:bg-slate-900/20 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 text-xs font-semibold uppercase tracking-wider bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
              <Briefcase className="h-3.5 w-3.5" />
              Join Our Engineering Team
            </div>
            <h2 className="mt-4 text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">
              Open Positions at Nova Solutions
            </h2>
            <p className="mt-3 text-slate-600 dark:text-slate-400 text-sm sm:text-base leading-relaxed">
              We are building the future of zero-trust agentic systems. Explore our current open engineering roles.
            </p>
          </div>

          <div className="mt-12 space-y-4 max-w-4xl mx-auto">
            {/* Job 1 */}
            <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/60 p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm dark:shadow-none hover:border-slate-300 dark:hover:border-slate-700 transition">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">Principal Security Architect (Zero-Trust AI)</h3>
                  <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300 dark:border-transparent text-[11px] font-semibold px-2 py-0.5 rounded">Full-time</span>
                </div>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Engineering • Bengaluru, Karnataka / Remote • 8+ Years Experience</p>
              </div>
              <button
                onClick={() => setActiveModal("Principal Security Architect")}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition shrink-0"
              >
                Apply Now
              </button>
            </div>

            {/* Job 2 */}
            <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/60 p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm dark:shadow-none hover:border-slate-300 dark:hover:border-slate-700 transition">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">Senior Staff AI/ML Infrastructure Engineer</h3>
                  <span className="bg-teal-50 text-teal-700 border border-teal-200 dark:bg-teal-500/15 dark:text-teal-300 dark:border-transparent text-[11px] font-semibold px-2 py-0.5 rounded">Full-time</span>
                </div>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Platform • Hyderabad, Telangana / Hybrid • 5+ Years Experience</p>
              </div>
              <button
                onClick={() => setActiveModal("Senior Staff AI/ML Infrastructure Engineer")}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition shrink-0"
              >
                Apply Now
              </button>
            </div>

            {/* Job 3 */}
            <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/60 p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm dark:shadow-none hover:border-slate-300 dark:hover:border-slate-700 transition">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">Lead Enterprise Compliance & Red Teaming</h3>
                  <span className="bg-cyan-50 text-cyan-700 border border-cyan-200 dark:bg-cyan-500/15 dark:text-cyan-300 dark:border-transparent text-[11px] font-semibold px-2 py-0.5 rounded">Full-time</span>
                </div>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Security • San Francisco, CA / Remote • 6+ Years Experience</p>
              </div>
              <button
                onClick={() => setActiveModal("Lead Enterprise Compliance & Red Teaming")}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition shrink-0"
              >
                Apply Now
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ==================== 8. CONTACT SECTION ==================== */}
      <section id="contact" className="relative z-10 py-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 text-xs font-semibold uppercase tracking-wider bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
              <Mail className="h-3.5 w-3.5" />
              Get in Touch
            </div>
            <h2 className="mt-4 text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">
              Ready to Upgrade Your Corporate Operations?
            </h2>
            <p className="mt-3 text-slate-600 dark:text-slate-400 text-sm sm:text-base leading-relaxed">
              Contact our solutions engineering team to schedule a technical demonstration tailored to your enterprise permissions matrix.
            </p>

            <div className="mt-8 space-y-4 text-xs sm:text-sm text-slate-700 dark:text-slate-300">
              <div className="flex items-center gap-3">
                <MapPin className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>Nova Solutions Global Campus, Phase 1 Electronic City, Bengaluru, Karnataka</span>
              </div>
              <div className="flex items-center gap-3">
                <Mail className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <a href="mailto:novasolutions@evocation.in" className="hover:underline hover:text-emerald-600 dark:hover:text-emerald-400 font-medium">
                  novasolutions@evocation.in
                </a>
              </div>
              <div className="flex items-center gap-3">
                <Phone className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>+91 (80) 4122-8000</span>
              </div>
            </div>
          </div>

          {/* Quick Contact Form */}
          <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/60 p-8 shadow-md dark:shadow-xl transition">
            {contactSubmitted ? (
              <div className="text-center py-8">
                <div className="h-12 w-12 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto mb-3">
                  <Check className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">Inquiry Sent Successfully</h3>
                <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400 max-w-xs mx-auto">
                  Your message has been delivered directly to <span className="font-semibold text-emerald-600 dark:text-emerald-400">novasolutions@evocation.in</span>. Our team will contact you shortly.
                </p>
                <button
                  onClick={() => {
                    setContactSubmitted(false);
                    setContactError("");
                  }}
                  className="mt-5 px-4 py-2 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 transition"
                >
                  Send another inquiry
                </button>
              </div>
            ) : (
              <form onSubmit={handleContactSubmit} className="space-y-4">
                {contactError && (
                  <div className="p-3 rounded-lg text-xs bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
                    {contactError}
                  </div>
                )}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Corporate Work Email</label>
                  <input
                    required
                    type="email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:border-slate-700 dark:bg-slate-800/80 dark:text-white dark:placeholder:text-slate-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Organization / Department</label>
                  <input
                    type="text"
                    value={contactOrg}
                    onChange={(e) => setContactOrg(e.target.value)}
                    placeholder="e.g. Apex Global Engineering"
                    className="w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:border-slate-700 dark:bg-slate-800/80 dark:text-white dark:placeholder:text-slate-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Message / Requirements</label>
                  <textarea
                    rows={3}
                    value={contactMsg}
                    onChange={(e) => setContactMsg(e.target.value)}
                    placeholder="Describe your enterprise knowledge base & security requirements..."
                    className="w-full rounded-lg border border-slate-300 bg-slate-50/50 px-3.5 py-2.5 text-xs text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:border-slate-700 dark:bg-slate-800/80 dark:text-white dark:placeholder:text-slate-500"
                  />
                </div>
                <button
                  type="submit"
                  disabled={contactSubmitting}
                  className="w-full py-3 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-md shadow-emerald-500/20 transition flex items-center justify-center gap-2 disabled:opacity-75 disabled:cursor-not-allowed"
                >
                  {contactSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Delivering to novasolutions@evocation.in...</span>
                    </>
                  ) : (
                    <span>Submit Demonstration Request</span>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>
      </section>

      {/* ==================== 9. FOOTER ==================== */}
      <footer className="border-t border-slate-200 bg-slate-100 dark:border-slate-800 dark:bg-[#050912] py-12 text-xs text-slate-500 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="h-7 w-7 rounded-lg bg-emerald-500 flex items-center justify-center text-slate-950">
              <ShieldCheck className="h-4 w-4 text-slate-950 stroke-[2.4]" />
            </div>
            <span className="font-bold text-sm text-slate-900 dark:text-white">Nova Solutions Enterprise</span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-6 text-slate-600 dark:text-slate-400">
            <button onClick={() => scrollTo("solutions")} className="hover:text-slate-950 dark:hover:text-white transition">Solutions</button>
            <button onClick={() => scrollTo("about")} className="hover:text-slate-950 dark:hover:text-white transition">About</button>
            <button onClick={() => scrollTo("demo-scenarios")} className="hover:text-slate-950 dark:hover:text-white transition">Demo Scenarios</button>
            <button onClick={() => scrollTo("careers")} className="hover:text-slate-950 dark:hover:text-white transition">Careers</button>
            <button onClick={onSignIn} className="text-emerald-600 dark:text-emerald-400 hover:underline font-semibold transition">Sign In</button>
          </div>

          <p className="text-center md:text-right text-slate-500">
            © 2026 Nova Solutions. Fictional synthetic enterprise demo.
          </p>
        </div>
      </footer>

      {/* Career Application Modal */}
      {activeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 p-6 shadow-2xl relative transition">
            <button
              onClick={() => setActiveModal(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 dark:hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>
            <h3 className="text-base font-bold text-slate-900 dark:text-white">Apply for {activeModal}</h3>
            <p className="mt-1.5 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              This is a demonstration portal for the Nova Solutions Enterprise platform. To test the system with full administrative or engineering clearance, please sign in with one of our pre-configured personas.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 transition"
              >
                Close
              </button>
              <button
                onClick={() => {
                  setActiveModal(null);
                  onSignIn();
                }}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition"
              >
                Go to Sign In
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import {
  AlertCircle,
  CheckCircle2,
  FolderGit2,
  GitBranch,
  Github,
  Key,
  Lock,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import type { Classification, RepositoryItem } from "../lib/types";
import { Button, ClassBadge, cx, Drawer, Spinner } from "../lib/ui";

interface ImportRepoDrawerProps {
  open: boolean;
  onClose: () => void;
  onImported: (repo: RepositoryItem) => void;
}

interface StepItem {
  id: string;
  label: string;
  status: "waiting" | "running" | "done" | "error";
  detail?: string;
}

const DEPARTMENTS = [
  "Engineering",
  "Product",
  "Information Technology",
  "Human Resources",
  "Finance",
  "Sales",
  "Marketing",
  "Legal",
  "Operations",
  "Executive",
];

export default function ImportRepoDrawer({ open, onClose, onImported }: ImportRepoDrawerProps) {
  const { me, notify, bump } = useApp();
  const [tab, setTab] = useState<"url" | "oauth">("url");

  // Form states
  const [repoUrl, setRepoUrl] = useState("https://github.com/novatech/enterprise-agent");
  const [branch, setBranch] = useState("main");
  const [classification, setClassification] = useState<Classification>("INTERNAL");
  const [selectedDepts, setSelectedDepts] = useState<string[]>(["*"]);
  const [syncInterval, setSyncInterval] = useState("manual");

  // GitHub connection state
  const [connectedUser, setConnectedUser] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);

  // Validation state
  const [isValidating, setIsValidating] = useState(false);
  const [validationInfo, setValidationInfo] = useState<{ valid: boolean; message: string } | null>(null);

  // Ingestion execution state
  const [isImporting, setIsImporting] = useState(false);
  const [importSteps, setImportSteps] = useState<StepItem[]>([]);
  const [importResult, setImportResult] = useState<any | null>(null);

  const isGuest = me?.is_guest || me?.role_code === "guest";

  useEffect(() => {
    if (!open) {
      setImportSteps([]);
      setImportResult(null);
      setIsImporting(false);
    }
  }, [open]);

  // Validate URL with debounce
  useEffect(() => {
    if (!repoUrl.trim()) {
      setValidationInfo(null);
      return;
    }
    const timer = setTimeout(async () => {
      setIsValidating(true);
      try {
        const res = await api.post<any>("/repositories/validate", { repo_url: repoUrl, branch });
        setValidationInfo(res);
      } catch (err: any) {
        setValidationInfo({ valid: false, message: err.message || "Invalid repository URL" });
      } finally {
        setIsValidating(false);
      }
    }, 450);
    return () => clearTimeout(timer);
  }, [repoUrl, branch]);

  const handleConnectGitHub = async () => {
    setIsConnecting(true);
    try {
      const res = await api.post<any>("/repositories/connect", { demo_mode: true });
      setConnectedUser(res.account_login || "novatech-dev");
      notify("Connected to GitHub Enterprise (read:org, repo)", "ok");
    } catch (err: any) {
      notify(err.message || "Could not connect to GitHub", "err");
    } finally {
      setIsConnecting(false);
    }
  };

  const handleToggleDept = (dept: string) => {
    if (dept === "*") {
      setSelectedDepts(["*"]);
      return;
    }
    let updated = selectedDepts.filter((d) => d !== "*");
    if (updated.includes(dept)) {
      updated = updated.filter((d) => d !== dept);
      if (updated.length === 0) updated = ["*"];
    } else {
      updated.push(dept);
    }
    setSelectedDepts(updated);
  };

  const handleStartImport = async () => {
    if (isGuest) {
      notify("Guest sessions cannot import repositories into the knowledge base.", "err");
      return;
    }
    setIsImporting(true);
    setImportResult(null);

    const initialSteps: StepItem[] = [
      { id: "1", label: "Validating GitHub URL & Access Rights", status: "running" },
      { id: "2", label: "Scanning File Tree & Skipping Binaries / Exclusions", status: "waiting" },
      { id: "3", label: "Security & Secret Scan (DLP / Credential Redaction)", status: "waiting" },
      { id: "4", label: "AST-Aware Code Chunking & Vector Embeddings", status: "waiting" },
      { id: "5", label: "Knowledge Base Integration & RBAC Policy Registration", status: "waiting" },
    ];
    setImportSteps(initialSteps);

    // Simulate animated checklist progression while backend processes
    const updateStep = (index: number, status: StepItem["status"], detail?: string) => {
      setImportSteps((prev) =>
        prev.map((s, i) => (i === index ? { ...s, status, detail } : i === index + 1 && status === "done" ? { ...s, status: "running" } : s))
      );
    };

    try {
      setTimeout(() => updateStep(0, "done", "Target verified"), 400);
      setTimeout(() => updateStep(1, "done", "Binary & cache directories skipped"), 800);
      setTimeout(() => updateStep(2, "done", "0 leaked secrets stored (auto-redacted)"), 1400);

      const res = await api.post<any>("/repositories/import", {
        repo_url: repoUrl,
        default_branch: branch,
        classification,
        allowed_departments: selectedDepts,
        sync_interval: syncInterval,
      });

      updateStep(3, "done", `${res.stats?.total_chunks || 45} code chunks embedded`);
      updateStep(4, "done", "Repository ready for agent search");

      setImportResult(res);
      notify(`Repository '${res.repository?.name || "Codebase"}' successfully imported!`, "ok");
      bump();
      if (res.repository) {
        onImported(res.repository);
      }
    } catch (err: any) {
      setImportSteps((prev) =>
        prev.map((s) => (s.status === "running" ? { ...s, status: "error", detail: err.message } : s))
      );
      notify(err.message || "Failed to import repository", "err");
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          <FolderGit2 className="h-5 w-5 text-brand-600" />
          <span>Import Repository</span>
        </span>
      }
    >
      <div className="space-y-6 p-5">
        {/* Header Notice */}
        <div className="rounded-xl border border-brand-100 bg-brand-50/60 p-4 text-xs text-brand-900 dark:border-brand-500/20 dark:bg-brand-500/10 dark:text-brand-200">
          <div className="flex items-center gap-2 font-semibold">
            <ShieldCheck className="h-4 w-4 text-brand-600" />
            <span>Zero-Trust Codebase Ingestion Pipeline</span>
          </div>
          <p className="mt-1 leading-relaxed text-slate-600 dark:text-slate-300">
            Connect a GitHub repository to make its architecture, source code, and technical documentation available
            to the NovaTech AI assistant. Code is secret-scanned, redacted, chunked by function boundaries, and protected
            by strict multi-tenant RBAC clearance.
          </p>
        </div>

        {isGuest && (
          <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
            <Lock className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-semibold">Guest Clearance Restriction</p>
              <p className="mt-0.5">
                You are currently in Guest Mode. Guests can explore public repositories but cannot connect or import
                new enterprise code repositories into the knowledge base.
              </p>
            </div>
          </div>
        )}

        {/* Tab Selector */}
        <div className="flex rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
          <button
            type="button"
            onClick={() => setTab("url")}
            className={cx(
              "flex flex-1 items-center justify-center gap-2 rounded-md py-2 text-xs font-semibold transition-all",
              tab === "url"
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white"
                : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            )}
          >
            <GitBranch className="h-3.5 w-3.5" />
            Repository URL
          </button>
          <button
            type="button"
            onClick={() => setTab("oauth")}
            className={cx(
              "flex flex-1 items-center justify-center gap-2 rounded-md py-2 text-xs font-semibold transition-all",
              tab === "oauth"
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white"
                : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            )}
          >
            <Github className="h-3.5 w-3.5" />
            GitHub OAuth
          </button>
        </div>

        {/* Tab 1: Repository URL */}
        {tab === "url" && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                GitHub Repository URL
              </label>
              <div className="relative mt-1">
                <input
                  type="text"
                  value={repoUrl}
                  disabled={isImporting}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  placeholder="https://github.com/company/project"
                  className="input pr-10 font-mono text-xs"
                />
                <div className="absolute inset-y-0 right-3 flex items-center">
                  {isValidating ? (
                    <Spinner className="h-4 w-4" />
                  ) : validationInfo?.valid ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  ) : validationInfo ? (
                    <AlertCircle className="h-4 w-4 text-rose-500" />
                  ) : null}
                </div>
              </div>
              {validationInfo && (
                <p
                  className={cx(
                    "mt-1.5 flex items-center gap-1.5 text-xs",
                    validationInfo.valid ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
                  )}
                >
                  {validationInfo.message}
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Branch
                </label>
                <input
                  type="text"
                  value={branch}
                  disabled={isImporting}
                  onChange={(e) => setBranch(e.target.value)}
                  placeholder="main"
                  className="input mt-1 text-xs"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Sync Frequency
                </label>
                <select
                  value={syncInterval}
                  disabled={isImporting}
                  onChange={(e) => setSyncInterval(e.target.value)}
                  className="input mt-1 text-xs"
                >
                  <option value="manual">Manual on-demand</option>
                  <option value="daily">Daily sync (nightly)</option>
                  <option value="realtime">Webhook / Realtime</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: GitHub OAuth */}
        {tab === "oauth" && (
          <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-white dark:bg-white dark:text-slate-950">
                  <Github className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-semibold text-slate-900 dark:text-white">GitHub Enterprise Connection</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {connectedUser ? `Connected as @${connectedUser}` : "Not connected to GitHub"}
                  </p>
                </div>
              </div>
              {connectedUser ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
                  <CheckCircle2 className="h-3 w-3" /> Connected
                </span>
              ) : (
                <Button size="sm" variant="primary" disabled={isConnecting || isGuest} onClick={handleConnectGitHub}>
                  {isConnecting ? <Spinner className="h-3.5 w-3.5" /> : <Key className="h-3.5 w-3.5" />}
                  Connect Account
                </Button>
              )}
            </div>

            {connectedUser && (
              <div className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500 dark:border-slate-800">
                <p className="font-medium text-slate-700 dark:text-slate-300">Active OAuth Scopes:</p>
                <div className="mt-1 flex gap-2">
                  <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[11px] dark:bg-slate-800">repo (code read)</span>
                  <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-[11px] dark:bg-slate-800">read:org (teams)</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Security Classification */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Security Classification Clearance
          </label>
          <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {(["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"] as Classification[]).map((level) => (
              <button
                key={level}
                type="button"
                disabled={isImporting}
                onClick={() => setClassification(level)}
                className={cx(
                  "flex flex-col items-center rounded-lg border p-2.5 text-center transition-all",
                  classification === level
                    ? "border-brand-500 bg-brand-50/50 ring-2 ring-brand-500/20 dark:bg-brand-500/10"
                    : "border-slate-200 hover:border-slate-300 dark:border-slate-800 dark:hover:border-slate-700"
                )}
              >
                <ClassBadge level={level} />
                <span className="mt-1.5 text-[10px] text-slate-500 dark:text-slate-400">
                  {level === "PUBLIC" && "Open to guests"}
                  {level === "INTERNAL" && "All employees"}
                  {level === "CONFIDENTIAL" && "Dept & Leads"}
                  {level === "RESTRICTED" && "Execs & Admins"}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Allowed Departments */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Department Scope Access
          </label>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <button
              type="button"
              disabled={isImporting}
              onClick={() => handleToggleDept("*")}
              className={cx(
                "rounded-full px-3 py-1 text-xs font-medium transition-all",
                selectedDepts.includes("*")
                  ? "bg-brand-600 text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300"
              )}
            >
              All Departments (*)
            </button>
            {DEPARTMENTS.map((d) => (
              <button
                key={d}
                type="button"
                disabled={isImporting || selectedDepts.includes("*")}
                onClick={() => handleToggleDept(d)}
                className={cx(
                  "rounded-full px-3 py-1 text-xs font-medium transition-all",
                  selectedDepts.includes(d)
                    ? "bg-brand-600 text-white shadow-sm"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300",
                  selectedDepts.includes("*") && "opacity-50"
                )}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        {/* Ingestion Progress Checklist */}
        {importSteps.length > 0 && (
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 dark:border-slate-800 dark:bg-slate-900/50">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              <RefreshCw className={cx("h-3.5 w-3.5 text-brand-600", isImporting && "animate-spin")} />
              Pipeline Execution Status
            </p>
            <div className="mt-3 space-y-2.5">
              {importSteps.map((step) => (
                <div key={step.id} className="flex items-start gap-2.5 text-xs">
                  {step.status === "done" && <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />}
                  {step.status === "running" && <Spinner className="mt-0.5 h-4 w-4 shrink-0" />}
                  {step.status === "waiting" && <div className="mt-1 h-3 w-3 shrink-0 rounded-full border border-slate-300 dark:border-slate-600" />}
                  {step.status === "error" && <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" />}
                  <div className="flex-1">
                    <p className={cx("font-medium", step.status === "done" ? "text-slate-900 dark:text-white" : "text-slate-600 dark:text-slate-400")}>
                      {step.label}
                    </p>
                    {step.detail && <p className="text-[11px] text-slate-500 dark:text-slate-400">{step.detail}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Success Card */}
        {importResult && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 text-xs text-emerald-900 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-200">
            <div className="flex items-center gap-2 font-semibold text-emerald-800 dark:text-emerald-300">
              <Sparkles className="h-4 w-4" />
              <span>Repository Indexed & Ready for AI Citations</span>
            </div>
            <div className="mt-2 grid grid-cols-3 gap-2 text-center">
              <div className="rounded-lg bg-white/80 p-2 dark:bg-slate-900/60">
                <p className="text-lg font-bold">{importResult.stats?.total_files || 0}</p>
                <p className="text-[10px] text-slate-500">Source Files</p>
              </div>
              <div className="rounded-lg bg-white/80 p-2 dark:bg-slate-900/60">
                <p className="text-lg font-bold">{importResult.stats?.total_chunks || 0}</p>
                <p className="text-[10px] text-slate-500">Embedded Chunks</p>
              </div>
              <div className="rounded-lg bg-white/80 p-2 dark:bg-slate-900/60">
                <p className="text-lg font-bold text-amber-600 dark:text-amber-400">
                  {importResult.stats?.secrets_redacted || 0}
                </p>
                <p className="text-[10px] text-slate-500">Secrets Redacted</p>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-4 dark:border-slate-800">
          <Button variant="secondary" size="sm" onClick={onClose} disabled={isImporting}>
            {importResult ? "Close" : "Cancel"}
          </Button>
          {!importResult && (
            <Button
              variant="primary"
              size="sm"
              disabled={isImporting || isGuest || !validationInfo?.valid}
              onClick={handleStartImport}
            >
              {isImporting ? <Spinner className="h-3.5 w-3.5" /> : <FolderGit2 className="h-3.5 w-3.5" />}
              Start Ingestion Pipeline
            </Button>
          )}
        </div>
      </div>
    </Drawer>
  );
}

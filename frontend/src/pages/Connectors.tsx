import {
  AlertCircle,
  AlertTriangle,
  Check,
  CheckCircle2,
  Cpu,
  FileCheck2,
  FileSpreadsheet,
  FolderGit2,
  Globe2,
  Mail,
  MessageSquare,
  Network,
  Play,
  PlayCircle,
  RefreshCw,
  Settings,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import type {
  AgentSkill,
  ComposedWorkflowResult,
  Connector,
} from "../lib/types";
import {
  Button,
  Card,
  ClassBadge,
  cx,
  Drawer,
  fmtDate,
  Spinner,
} from "../lib/ui";

interface AdminOverview {
  summary: {
    total_connectors: number;
    connected: number;
    healthy: number;
    degraded: number;
  };
  health: {
    connector_health: string;
    sync_health: string;
    authentication_health: string;
    permission_health: string;
  };
  usage: {
    total_indexed_items: number;
    github_repos: number;
    jira_issues: number;
    teams_messages: number;
    outlook_threads: number;
  };
  connected_services: Record<string, string>;
}

export default function ConnectorsPage() {
  const { notify } = useApp();
  const [tab, setTab] = useState<"connectors" | "skills" | "demo" | "governance">("connectors");
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [skills, setSkills] = useState<AgentSkill[]>([]);
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState<string | null>(null);

  // Drawer states
  const [selectedConnector, setSelectedConnector] = useState<Connector | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<AgentSkill | null>(null);
  const [agentAccessEdit, setAgentAccessEdit] = useState<Record<string, string>>({});

  // 1-Click Live Demo Workflow state
  const [targetService, setTargetService] = useState("authentication service");
  const [runningDemo, setRunningDemo] = useState(false);
  const [demoResult, setDemoResult] = useState<ComposedWorkflowResult | null>(null);
  const [proposalConfirmed, setProposalConfirmed] = useState(false);
  const [proposalActionLoading, setProposalActionLoading] = useState(false);

  // Quick skill runner state
  const [activeRunningSkill, setActiveRunningSkill] = useState<string | null>(null);
  const [skillRunResult, setSkillRunResult] = useState<any | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [connRes, skillRes, ovRes] = await Promise.all([
        api.get<{ connectors: Connector[] }>("/connectors"),
        api.get<{ skills: AgentSkill[] }>("/skills"),
        api.get<AdminOverview>("/connectors/admin/overview").catch(() => null),
      ]);
      setConnectors(connRes.connectors || []);
      setSkills(skillRes.skills || []);
      if (ovRes) setOverview(ovRes);
    } catch (err: any) {
      notify(err.message || "Failed to load connectors data", "err");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSync = async (connector: Connector) => {
    try {
      setSyncingId(connector.id);
      const res = await api.post<{ status: string; items_indexed: number; message: string }>(
        `/connectors/${connector.id}/sync`
      );
      notify(`Sync completed: ${res.items_indexed} items synchronized`, "ok");
      await fetchData();
    } catch (err: any) {
      notify(err.message || "Sync failed", "err");
    } finally {
      setSyncingId(null);
    }
  };

  const handleToggleConnection = async (connector: Connector) => {
    try {
      if (connector.status === "connected") {
        await api.post(`/connectors/${connector.id}/disconnect`);
        notify(`Disconnected from ${connector.name}`, "ok");
      } else {
        await api.post(`/connectors/${connector.id}/connect`, {
          mode: "DEMO CONNECTOR",
          account_name: `NovaTech ${connector.name} Service`,
        });
        notify(`Connected to ${connector.name} in Demo Mode`, "ok");
      }
      await fetchData();
    } catch (err: any) {
      notify(err.message || "Connection state change failed", "err");
    }
  };

  const handleSavePermissions = async () => {
    if (!selectedConnector) return;
    try {
      await api.patch(`/connectors/${selectedConnector.id}/permissions`, {
        agent_access: agentAccessEdit,
      });
      notify("Permissions and access policies updated successfully", "ok");
      setSelectedConnector(null);
      await fetchData();
    } catch (err: any) {
      notify(err.message || "Failed to update permissions", "err");
    }
  };

  const handleRunComposedWorkflow = async () => {
    try {
      setRunningDemo(true);
      setProposalConfirmed(false);
      const res = await api.post<ComposedWorkflowResult>("/skills/execute", {
        skill_id: "composed_workflow",
        target: targetService,
      });
      setDemoResult(res);
      notify("Cross-connector multi-skill assessment complete!", "ok");
    } catch (err: any) {
      notify(err.message || "Composed workflow execution failed", "err");
    } finally {
      setRunningDemo(false);
    }
  };

  const handleConfirmActionProposal = async () => {
    try {
      setProposalActionLoading(true);
      // Simulate ticket creation approval
      await new Promise((r) => setTimeout(r, 600));
      setProposalConfirmed(true);
      notify("Ticket NOVA-422 successfully created and assigned!", "ok");
    } catch (err: any) {
      notify(err.message || "Approval failed", "err");
    } finally {
      setProposalActionLoading(false);
    }
  };

  const handleRunSingleSkill = async (skill: AgentSkill) => {
    try {
      setActiveRunningSkill(skill.id);
      const params = skill.id === "skill_jira_mgmt"
        ? { action: "search", query: "token" }
        : skill.id === "skill_security_analysis"
        ? { target: "auth" }
        : skill.id === "skill_repo_analysis"
        ? { repo_name: "novatech/enterprise-agent" }
        : skill.id === "skill_doc_gen"
        ? { service: "Authentication Engine" }
        : { target: "auth router" };

      const res = await api.post<{ result: any }>(`/skills/execute`, {
        skill_id: skill.id,
        params,
      });
      setSkillRunResult({ skillId: skill.id, name: skill.name, data: res.result });
      notify(`Skill "${skill.name}" executed successfully`, "ok");
    } catch (err: any) {
      notify(err.message || "Skill run failed", "err");
    } finally {
      setActiveRunningSkill(null);
    }
  };

  const providerIcons: Record<string, any> = {
    github: FolderGit2,
    jira: FileSpreadsheet,
    outlook: Mail,
    teams: MessageSquare,
    entra: ShieldCheck,
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-8">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Enterprise Connectors & Skills
            </h1>
            <span className="rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-xs font-semibold text-indigo-600 dark:text-indigo-400">
              Enterprise Hub
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Connect organizational tools, discover reusable agent skills, and enforce zero-trust least privilege.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1 dark:border-slate-800 dark:bg-slate-900">
          <button
            onClick={() => setTab("connectors")}
            className={cx(
              "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              tab === "connectors"
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-800 dark:text-white"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            )}
          >
            <Network className="h-4 w-4" />
            Connectors ({connectors.length})
          </button>
          <button
            onClick={() => setTab("skills")}
            className={cx(
              "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              tab === "skills"
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-800 dark:text-white"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            )}
          >
            <Cpu className="h-4 w-4" />
            Skills Library ({skills.length})
          </button>
          <button
            onClick={() => setTab("demo")}
            className={cx(
              "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              tab === "demo"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
            )}
          >
            <Sparkles className="h-4 w-4" />
            Live Demo Flow
          </button>
          <button
            onClick={() => setTab("governance")}
            className={cx(
              "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              tab === "governance"
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-800 dark:text-white"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            )}
          >
            <Shield className="h-4 w-4" />
            Governance
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <Spinner className="h-8 w-8 text-indigo-600" />
        </div>
      ) : tab === "connectors" ? (
        /* ================= CONNECTORS TAB ================= */
        <div className="space-y-6">
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 dark:border-indigo-950 dark:bg-indigo-950/20">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-indigo-600 p-2 text-white">
                <Network className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                  Organizational Integration & Data Boundary
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Each connector operates under strict least-privilege scoping. Agents cannot write or execute changes without mandatory Human-in-the-Loop approval gates.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Zero-Trust Gateway Active
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {connectors.map((conn) => {
              const IconComponent = providerIcons[conn.provider] || Globe2;
              const isConnected = conn.status === "connected";
              const isSyncing = syncingId === conn.id;

              return (
                <Card
                  key={conn.id}
                  className="flex flex-col justify-between overflow-hidden border border-slate-200/80 bg-white transition hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
                >
                  <div className="p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="rounded-xl bg-slate-100 p-2.5 text-slate-800 dark:bg-slate-800 dark:text-slate-200">
                          <IconComponent className="h-6 w-6" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-slate-900 dark:text-white">
                            {conn.name}
                          </h3>
                          <span className="text-xs text-slate-500 dark:text-slate-400">
                            {conn.category}
                          </span>
                        </div>
                      </div>
                      <span
                        className={cx(
                          "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
                          isConnected
                            ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
                            : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                        )}
                      >
                        <span
                          className={cx(
                            "h-1.5 w-1.5 rounded-full",
                            isConnected ? "bg-emerald-500" : "bg-slate-400"
                          )}
                        />
                        {isConnected ? "Connected" : "Disconnected"}
                      </span>
                    </div>

                    <p className="mt-3 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                      {conn.description}
                    </p>

                    <div className="mt-4 space-y-2 border-t border-slate-100 pt-3 text-xs dark:border-slate-800">
                      <div className="flex justify-between text-slate-600 dark:text-slate-400">
                        <span className="font-medium">Mode:</span>
                        <span className="rounded bg-indigo-50 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                          {conn.mode}
                        </span>
                      </div>
                      <div className="flex justify-between text-slate-600 dark:text-slate-400">
                        <span className="font-medium">Account / Tenant:</span>
                        <span className="truncate max-w-[180px] font-mono text-[11px] text-slate-700 dark:text-slate-300">
                          {conn.account_name || "Enterprise Domain"}
                        </span>
                      </div>
                      <div className="flex justify-between text-slate-600 dark:text-slate-400">
                        <span className="font-medium">Items Indexed:</span>
                        <span className="font-semibold text-slate-900 dark:text-white">
                          {conn.sync_stats?.items_count ?? 0} records
                        </span>
                      </div>
                      <div className="flex justify-between text-slate-600 dark:text-slate-400">
                        <span className="font-medium">Last Synced:</span>
                        <span>{conn.last_synced_at ? fmtDate(conn.last_synced_at) : "Just now"}</span>
                      </div>
                    </div>

                    {/* Scopes Pill List */}
                    <div className="mt-3 flex flex-wrap gap-1">
                      {conn.scopes.slice(0, 3).map((s) => (
                        <span
                          key={s}
                          className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                        >
                          {s}
                        </span>
                      ))}
                      {conn.scopes.length > 3 && (
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500 dark:bg-slate-800">
                          +{conn.scopes.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions Footer */}
                  <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/50 p-3 dark:border-slate-800 dark:bg-slate-800/40">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        setSelectedConnector(conn);
                        setAgentAccessEdit(conn.agent_access || {});
                      }}
                      className="text-xs"
                    >
                      <Settings className="mr-1.5 h-3.5 w-3.5" />
                      Configure
                    </Button>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={isSyncing || !isConnected}
                        onClick={() => handleSync(conn)}
                        className="text-xs"
                      >
                        <RefreshCw className={cx("mr-1.5 h-3.5 w-3.5", isSyncing && "animate-spin")} />
                        {isSyncing ? "Syncing..." : "Sync"}
                      </Button>
                      <Button
                        size="sm"
                        variant={isConnected ? "ghost" : "primary"}
                        onClick={() => handleToggleConnection(conn)}
                        className={cx(
                          "text-xs",
                          isConnected && "text-rose-600 hover:bg-rose-50 hover:text-rose-700 dark:hover:bg-rose-950"
                        )}
                      >
                        {isConnected ? "Disconnect" : "Connect"}
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      ) : tab === "skills" ? (
        /* ================= SKILLS LIBRARY TAB ================= */
        <div className="space-y-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Reusable Agent Skills Library
              </h2>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                Modular, executable capabilities shared across NovaTech agents with schema-enforced safety policies.
              </p>
            </div>
            {skillRunResult && (
              <Button size="sm" variant="ghost" onClick={() => setSkillRunResult(null)}>
                <X className="mr-1 h-3.5 w-3.5" />
                Clear Output
              </Button>
            )}
          </div>

          {skillRunResult && (
            <Card className="border border-emerald-200 bg-emerald-50/40 p-4 dark:border-emerald-900 dark:bg-emerald-950/20">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  <span className="font-semibold text-sm text-emerald-900 dark:text-emerald-300">
                    Execution Output: {skillRunResult.name}
                  </span>
                </div>
                <span className="text-xs font-mono text-slate-500">HTTP 200 OK</span>
              </div>
              <pre className="max-h-60 overflow-y-auto rounded bg-slate-900 p-3 font-mono text-xs text-emerald-400">
                {JSON.stringify(skillRunResult.data, null, 2)}
              </pre>
            </Card>
          )}

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {skills.map((skill) => (
              <Card
                key={skill.id}
                className="flex flex-col justify-between border border-slate-200/80 bg-white p-5 transition hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400">
                      <Cpu className="h-5 w-5" />
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                        v{skill.version}
                      </span>
                      <span className="rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                        {skill.status}
                      </span>
                    </div>
                  </div>

                  <h3 className="mt-3 font-semibold text-slate-900 dark:text-white">
                    {skill.name}
                  </h3>
                  <p className="text-xs font-medium text-indigo-600 dark:text-indigo-400">
                    {skill.category}
                  </p>
                  <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                    {skill.description}
                  </p>

                  {/* Connectors & Agents */}
                  <div className="mt-4 space-y-2 border-t border-slate-100 pt-3 text-xs dark:border-slate-800">
                    <div>
                      <span className="text-[11px] font-medium text-slate-500">Required Connectors:</span>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {skill.required_connectors.map((rc) => (
                          <span
                            key={rc}
                            className="rounded bg-indigo-50/60 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300"
                          >
                            {rc}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <span className="text-[11px] font-medium text-slate-500">Active Agents:</span>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {skill.agents_using.map((ag) => (
                          <span
                            key={ag}
                            className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                          >
                            {ag}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-3 dark:border-slate-800">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setSelectedSkill(skill)}
                    className="text-xs"
                  >
                    View Specs
                  </Button>
                  <Button
                    size="sm"
                    variant="primary"
                    disabled={activeRunningSkill === skill.id}
                    onClick={() => handleRunSingleSkill(skill)}
                    className="text-xs"
                  >
                    <Play className={cx("mr-1.5 h-3 w-3", activeRunningSkill === skill.id && "animate-spin")} />
                    {activeRunningSkill === skill.id ? "Running..." : "Test Skill"}
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      ) : tab === "demo" ? (
        /* ================= 1-CLICK LIVE DEMO TAB ================= */
        <div className="space-y-8">
          {/* Hero Banner */}
          <div className="rounded-2xl border border-indigo-200 bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 p-6 text-white shadow-xl">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
              <div className="space-y-2 max-w-2xl">
                <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold backdrop-blur">
                  <Sparkles className="h-3.5 w-3.5 text-amber-300" />
                  Live Judge & Evaluation Flow
                </div>
                <h2 className="text-2xl font-bold tracking-tight">
                  Cross-Connector Multi-Skill Security & Engineering Pipeline
                </h2>
                <p className="text-sm text-indigo-200 leading-relaxed">
                  Triggers an automated, end-to-end pipeline across GitHub, Jira, Microsoft Teams, and Outlook. Discovers vulnerabilities, cross-references sprint tickets, checks chat sentiment, generates executive reports, and halts at the mandatory <strong>Human-in-the-Loop Confirmation Gate</strong>.
                </p>
              </div>

              <div className="flex flex-col gap-3 min-w-[240px]">
                <div>
                  <label className="block text-xs font-medium text-indigo-200 mb-1">
                    Target Component
                  </label>
                  <select
                    value={targetService}
                    onChange={(e) => setTargetService(e.target.value)}
                    className="w-full rounded-lg border border-indigo-700 bg-indigo-950/60 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  >
                    <option value="authentication service">Authentication & OAuth2 Service</option>
                    <option value="database connection pool">Database Session & Pooler</option>
                    <option value="api gateway & rate limiter">API Gateway & Rate Limiter</option>
                  </select>
                </div>
                <Button
                  size="md"
                  disabled={runningDemo}
                  onClick={handleRunComposedWorkflow}
                  className="w-full bg-emerald-500 hover:bg-emerald-600 text-white font-semibold shadow-lg shadow-emerald-500/20"
                >
                  <PlayCircle className={cx("mr-2 h-5 w-5", runningDemo && "animate-spin")} />
                  {runningDemo ? "Executing Pipeline..." : "Execute 1-Click Assessment"}
                </Button>
              </div>
            </div>
          </div>

          {/* Results Timeline & Visualization */}
          {demoResult && (
            <div className="space-y-6">
              {/* Pipeline Nodes */}
              <Card className="border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-4">
                  Multi-System Pipeline Execution Status
                </h3>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
                  {demoResult.pipeline.map((p, idx) => (
                    <div
                      key={p.id}
                      className="flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-slate-50 p-3 text-center dark:border-slate-800 dark:bg-slate-800/60"
                    >
                      <div
                        className={cx(
                          "mb-2 flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold",
                          p.status === "completed"
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                            : "bg-amber-100 text-amber-700 animate-pulse dark:bg-amber-950 dark:text-amber-300"
                        )}
                      >
                        {p.status === "completed" ? <Check className="h-4 w-4" /> : idx + 1}
                      </div>
                      <span className="text-xs font-semibold text-slate-900 dark:text-white">
                        {p.label}
                      </span>
                      <span className="text-[10px] uppercase text-slate-500 mt-0.5">
                        {p.status}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Timeline Steps Detail */}
              <Card className="border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                <h3 className="text-base font-semibold text-slate-900 dark:text-white mb-4">
                  Executed Steps & Connector Activity Log
                </h3>
                <div className="space-y-4">
                  {demoResult.timeline.map((step, idx) => (
                    <div key={idx} className="flex items-start gap-4">
                      <div
                        className={cx(
                          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                          step.status === "done"
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300"
                            : "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300"
                        )}
                      >
                        {idx + 1}
                      </div>
                      <div className="flex-1 rounded-lg border border-slate-100 bg-slate-50/60 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/30">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-900 dark:text-white">
                            {step.label}
                          </span>
                          <span className="rounded bg-slate-200 px-2 py-0.5 text-[10px] font-semibold text-slate-700 dark:bg-slate-700 dark:text-slate-300">
                            {step.connector}
                          </span>
                        </div>
                        <p className="mt-1 text-slate-600 dark:text-slate-300">
                          {step.detail}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Findings & Jira Issues Grid */}
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* Findings */}
                <Card className="border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                  <div className="flex items-center gap-2 mb-4">
                    <ShieldAlert className="h-5 w-5 text-rose-600" />
                    <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                      Identified Vulnerabilities & Risks ({demoResult.findings.length})
                    </h3>
                  </div>
                  <div className="space-y-3">
                    {demoResult.findings.map((f) => (
                      <div
                        key={f.id}
                        className="rounded-xl border border-rose-200 bg-rose-50/50 p-4 text-xs dark:border-rose-950 dark:bg-rose-950/20"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-rose-700 dark:text-rose-400">
                            [{f.severity}] {f.title}
                          </span>
                          <span className="rounded bg-rose-100 px-2 py-0.5 font-semibold text-rose-800 dark:bg-rose-900 dark:text-rose-200">
                            {f.category}
                          </span>
                        </div>
                        <p className="mt-1 text-slate-700 dark:text-slate-300">
                          {f.description}
                        </p>
                        <div className="mt-2 rounded bg-slate-900 p-2 font-mono text-[11px] text-rose-300">
                          Evidence: {f.evidence}
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>

                {/* Jira Sprint Backlog */}
                <Card className="border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                  <div className="flex items-center gap-2 mb-4">
                    <FileSpreadsheet className="h-5 w-5 text-indigo-600" />
                    <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                      Correlated Jira Backlog & Sprint Status
                    </h3>
                  </div>
                  <div className="space-y-3">
                    {demoResult.jira_issues.map((j) => (
                      <div
                        key={j.key}
                        className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/40"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-indigo-600 dark:text-indigo-400">
                            {j.key}: {j.title}
                          </span>
                          <span className="rounded bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                            {j.status}
                          </span>
                        </div>
                        <p className="mt-1 text-slate-600 dark:text-slate-400">
                          {j.summary}
                        </p>
                        <div className="mt-2 flex items-center gap-3 text-[11px] text-slate-500">
                          <span>Assignee: <strong>{j.assignee}</strong></span>
                          <span>Sprint: <strong>{j.sprint}</strong></span>
                          <span>Priority: <strong className="text-rose-600">{j.priority}</strong></span>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>

              {/* HUMAN-IN-THE-LOOP CONFIRMATION GATE */}
              <Card className="border-2 border-amber-400 bg-amber-50/50 p-6 shadow-md dark:border-amber-600 dark:bg-amber-950/20">
                <div className="flex items-start gap-4">
                  <div className="rounded-xl bg-amber-500 p-3 text-white">
                    <AlertTriangle className="h-6 w-6" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                        Human-in-the-Loop Confirmation Gate
                      </h3>
                      <span className="rounded-full bg-amber-200 px-3 py-1 text-xs font-bold text-amber-900 dark:bg-amber-900 dark:text-amber-200">
                        Mandatory Action Review
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                      The AI agent has proposed a write action modifying your organizational tracking system. Direct writes are prohibited under enterprise policy until authorized by an authenticated user.
                    </p>

                    <div className="mt-4 rounded-xl border border-amber-200 bg-white p-4 text-xs dark:border-slate-800 dark:bg-slate-900">
                      <div className="font-semibold text-slate-900 dark:text-white text-sm mb-3">
                        {demoResult.action_proposal.title}
                      </div>

                      <div className="grid grid-cols-2 gap-2 mb-3">
                        {demoResult.action_proposal.fields.map(([k, v]) => (
                          <div key={k} className="flex justify-between border-b border-slate-100 pb-1 dark:border-slate-800">
                            <span className="font-medium text-slate-500">{k}:</span>
                            <span className="font-semibold text-slate-900 dark:text-white">{v}</span>
                          </div>
                        ))}
                      </div>

                      <div>
                        <span className="font-medium text-slate-500">Ticket Body / Instructions:</span>
                        <p className="mt-1 rounded bg-slate-50 p-2 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                          {demoResult.action_proposal.body}
                        </p>
                      </div>

                      <div className="mt-3 flex items-center gap-2 text-amber-700 dark:text-amber-400 text-[11px]">
                        <AlertCircle className="h-4 w-4 shrink-0" />
                        <span>{demoResult.action_proposal.warning}</span>
                      </div>
                    </div>

                    <div className="mt-5 flex items-center gap-3">
                      {proposalConfirmed ? (
                        <div className="flex items-center gap-2 rounded-lg bg-emerald-100 px-4 py-2 text-sm font-semibold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                          <CheckCircle2 className="h-5 w-5" />
                          Issue NOVA-422 Created Successfully in Jira!
                        </div>
                      ) : (
                        <>
                          <Button
                            size="md"
                            variant="primary"
                            disabled={proposalActionLoading}
                            onClick={handleConfirmActionProposal}
                            className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
                          >
                            <Check className="mr-2 h-4 w-4" />
                            {proposalActionLoading ? "Authorizing & Creating..." : "Approve & Create Jira Ticket"}
                          </Button>
                          <Button
                            size="md"
                            variant="secondary"
                            onClick={() => notify("Proposal dismissed by user.", "ok")}
                          >
                            Dismiss / Reject
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </Card>

              {/* Synthesized Executive Cross-System Report */}
              <Card className="border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <FileCheck2 className="h-5 w-5 text-indigo-600" />
                    <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                      {demoResult.report.title}
                    </h3>
                  </div>
                  <span className="text-xs font-medium text-slate-500">
                    Sources: {demoResult.report.sources_used.join(" · ")}
                  </span>
                </div>

                <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-300 mb-4 bg-slate-50 p-3 rounded-lg dark:bg-slate-800/50">
                  {demoResult.report.executive_summary}
                </p>

                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  Cross-System Evidence Matrix
                </h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800">
                        <th className="pb-2">System</th>
                        <th className="pb-2">Record Identifier</th>
                        <th className="pb-2">Classification</th>
                        <th className="pb-2">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {demoResult.report.evidence_matrix.map((em, idx) => (
                        <tr key={idx} className="py-2">
                          <td className="py-2 font-semibold text-slate-900 dark:text-white">{em.system}</td>
                          <td className="py-2 font-mono text-slate-600 dark:text-slate-400">{em.record}</td>
                          <td className="py-2">
                            <ClassBadge level={em.classification} />
                          </td>
                          <td className="py-2 text-slate-700 dark:text-slate-300">{em.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mt-6 mb-2">
                  Actionable Next Steps
                </h4>
                <ul className="list-disc pl-5 text-xs text-slate-700 dark:text-slate-300 space-y-1">
                  {demoResult.report.recommendations.map((rec, idx) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              </Card>
            </div>
          )}
        </div>
      ) : (
        /* ================= GOVERNANCE & COMPLIANCE TAB ================= */
        <div className="space-y-6">
          {overview && (
            <>
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                <Card className="border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
                  <span className="text-xs font-medium text-slate-500">Connected Enterprise Systems</span>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-slate-900 dark:text-white">
                      {overview.summary.connected} / {overview.summary.total_connectors}
                    </span>
                    <span className="text-xs font-semibold text-emerald-600">Active</span>
                  </div>
                </Card>

                <Card className="border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
                  <span className="text-xs font-medium text-slate-500">Health & Availability</span>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-emerald-600">
                      {overview.health.connector_health}
                    </span>
                  </div>
                </Card>

                <Card className="border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
                  <span className="text-xs font-medium text-slate-500">Total Indexed Items</span>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-slate-900 dark:text-white">
                      {overview.usage.total_indexed_items}
                    </span>
                    <span className="text-xs text-slate-500">cross-system</span>
                  </div>
                </Card>

                <Card className="border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
                  <span className="text-xs font-medium text-slate-500">Authorization Model</span>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="text-xl font-bold text-indigo-600 dark:text-indigo-400">
                      Zero-Trust
                    </span>
                    <span className="text-xs text-slate-500">Least Privilege</span>
                  </div>
                </Card>
              </div>

              <Card className="border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                <h3 className="text-base font-semibold text-slate-900 dark:text-white mb-4">
                  Enterprise Security & Token Lifecycle
                </h3>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 text-xs dark:border-slate-800 dark:bg-slate-800/40">
                    <span className="font-semibold text-slate-900 dark:text-white">Sync Pipeline Integrity</span>
                    <p className="mt-1 text-slate-600 dark:text-slate-400">{overview.health.sync_health}</p>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 text-xs dark:border-slate-800 dark:bg-slate-800/40">
                    <span className="font-semibold text-slate-900 dark:text-white">Authentication Protocol</span>
                    <p className="mt-1 text-slate-600 dark:text-slate-400">{overview.health.authentication_health}</p>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 text-xs dark:border-slate-800 dark:bg-slate-800/40">
                    <span className="font-semibold text-slate-900 dark:text-white">RBAC Enforcement</span>
                    <p className="mt-1 text-slate-600 dark:text-slate-400">{overview.health.permission_health}</p>
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 text-xs dark:border-slate-800 dark:bg-slate-800/40">
                    <span className="font-semibold text-slate-900 dark:text-white">Write Action Safety</span>
                    <p className="mt-1 text-slate-600 dark:text-slate-400">100% of mutation tools gate on user confirmation.</p>
                  </div>
                </div>
              </Card>
            </>
          )}
        </div>
      )}

      {/* Connector Configuration & Access Control Drawer */}
      <Drawer
        open={Boolean(selectedConnector)}
        onClose={() => setSelectedConnector(null)}
        title={selectedConnector ? `Configure ${selectedConnector.name}` : ""}
        width="max-w-xl"
      >
        {selectedConnector && (
          <div className="space-y-6 text-sm">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Connection Details
              </span>
              <div className="mt-2 space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs dark:border-slate-800 dark:bg-slate-900">
                <div className="flex justify-between">
                  <span className="text-slate-500">Provider:</span>
                  <span className="font-mono text-slate-900 dark:text-white">{selectedConnector.provider}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Mode:</span>
                  <span className="font-semibold text-indigo-600">{selectedConnector.mode}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Account:</span>
                  <span className="text-slate-900 dark:text-white">{selectedConnector.account_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Scopes Granted:</span>
                  <span className="font-mono text-[11px] text-slate-700 dark:text-slate-300">
                    {selectedConnector.scopes.join(", ")}
                  </span>
                </div>
              </div>
            </div>

            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Agent Least-Privilege Access Control
              </span>
              <p className="mt-1 text-xs text-slate-500">
                Specify individual agent permissions for this connected resource.
              </p>

              <div className="mt-3 space-y-3">
                {[
                  "Engineering Agent",
                  "Security Agent",
                  "Executive Agent",
                  "Workflow Agent",
                  "Guest Agent",
                ].map((agent) => (
                  <div
                    key={agent}
                    className="flex items-center justify-between rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800"
                  >
                    <span className="font-medium text-slate-900 dark:text-white">{agent}</span>
                    <select
                      value={agentAccessEdit[agent] || "read_only"}
                      onChange={(e) =>
                        setAgentAccessEdit({ ...agentAccessEdit, [agent]: e.target.value })
                      }
                      className="rounded border border-slate-300 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-800"
                    >
                      <option value="read_only">Read-Only</option>
                      <option value="read_write">Read / Write (Proposal)</option>
                      <option value="none">No Access (Blocked)</option>
                    </select>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
              <Button variant="secondary" onClick={() => setSelectedConnector(null)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSavePermissions}>
                Save Permissions
              </Button>
            </div>
          </div>
        )}
      </Drawer>

      {/* Skill Specification Drawer */}
      <Drawer
        open={Boolean(selectedSkill)}
        onClose={() => setSelectedSkill(null)}
        title={selectedSkill ? `Specification: ${selectedSkill.name}` : ""}
        width="max-w-xl"
      >
        {selectedSkill && (
          <div className="space-y-6 text-sm">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Skill Identity & Category
              </span>
              <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                {selectedSkill.description}
              </p>
            </div>

            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                System Instructions
              </span>
              <pre className="mt-2 max-h-40 overflow-y-auto rounded-lg bg-slate-900 p-3 font-mono text-xs text-slate-300">
                {selectedSkill.instructions}
              </pre>
            </div>

            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Input Schema
              </span>
              <pre className="mt-2 rounded-lg bg-slate-100 p-3 font-mono text-xs text-slate-800 dark:bg-slate-800 dark:text-slate-200">
                {JSON.stringify(selectedSkill.input_schema, null, 2)}
              </pre>
            </div>

            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Security Restrictions
              </span>
              <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50/60 p-3 text-xs text-amber-800 dark:border-amber-950 dark:bg-amber-950/20 dark:text-amber-300">
                {selectedSkill.security_restrictions}
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}

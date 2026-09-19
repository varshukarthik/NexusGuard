export type Classification = "PUBLIC" | "INTERNAL" | "CONFIDENTIAL" | "RESTRICTED";

export interface Me {
  user_id: string;
  company_id: string;
  company_name: string;
  employee_code: string;
  full_name: string;
  email: string;
  department: string;
  role_code: string;
  role_name: string;
  job_title: string;
  clearance: Classification;
  permissions: string[];
  session_id: string;
  ip: string;
  auth_method: string;
  is_guest?: boolean;
  session_started: string | null;
  session_expires: string | null;
  manager?: { name: string; email: string } | null;
  location?: string;
  access_scopes?: string[];
  documents_accessible?: number;
  documents_total?: number;
  active_grants?: string[];
  ai_engine?: { provider: string; model: string; embeddings: string };
  database?: { dialect: string; pgvector: boolean };
}

export interface Persona {
  email: string;
  full_name: string;
  job_title: string;
  department: string;
  clearance: Classification;
  role: string;
  employee_code: string;
  company: string;
  note: string;
}

export interface TimelineStep {
  key: string;
  label: string;
  status: "done" | "active" | "pending" | "denied" | "blocked" | "failed" | "warning";
  detail: string;
  tool?: string | null;
  agent?: string | null;
  t_ms: number;
}

export interface Source {
  doc_id: string;
  title: string;
  classification: Classification;
  department: string;
  version: string;
  doc_type: string;
  effective_date: string;
  filename: string;
  owner: string;
  score: number;
  is_latest: boolean;
  superseded_by: string | null;
  snippet: string;
  updated_at?: string;
}

export interface RecordRef {
  type: string;
  id: string;
  title: string;
  classification: Classification;
  updated: string | null;
  detail: string;
}

export interface Action {
  id: string;
  tool: string;
  status: "pending_confirmation" | "executed" | "cancelled" | "failed";
  risk: string;
  preview: { title: string; fields?: [string, string][]; body?: string; warning?: string; editable?: string[] };
  result: { message?: string; reference?: string };
  created_at: string | null;
}

export interface SecurityEvent {
  type: "prompt_injection" | "dlp_redaction" | "exfiltration_blocked";
  message: string;
  source?: string;
  title?: string;
  categories?: string;
  redactions?: { type: string; count: number }[];
}

export interface MessageMeta {
  intent?: string;
  action_selected?: string;
  intent_status?: string;
  intent_data?: any;
  question_type?: string;
  agents?: string[];
  records?: RecordRef[];
  outcome?: string;
  guest?: boolean;
  feedback?: number;
  regenerated?: boolean;
  engine?: string;
  notices?: string[];
  timeline?: TimelineStep[];
  sources?: Source[];
  withheld?: { doc_id: string; classification: Classification; rule: string }[];
  access_denied?: { classification: Classification; count: number; document_ids: string[]; message: string } | null;
  conflicts?: { family: string; note: string; latest: Source; older: Source }[];
  actions?: Action[];
  security?: SecurityEvent[];
  context_manifest?: { doc_id: string; title: string; classification: Classification; chunks: number }[];
  duration_ms?: number;
  seeded?: boolean;
  plan?: AgentPlan;
  governance?: { approval_gates: string[]; overall_risk: string; data_minimization: boolean; tenant_boundary: string };
} 

export interface AgentPlanStep {
  id: string; label: string; kind: string; risk: string; approval_required: boolean;
  tool?: string | null; depends_on: string[];
}
export interface AgentPlan {
  goal: string; overall_risk: string; steps: AgentPlanStep[]; principles: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: string | null;
  meta: MessageMeta;
  created_at: string;
  pending?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface DocRow {
  id: string;
  title: string;
  filename: string;
  doc_type: string;
  department: string;
  classification: Classification;
  owner: string;
  version: string;
  effective_date: string;
  status: string;
  updated_at: string | null;
  allowed_departments: string[];
  allowed_roles: string[];
  source: string;
  ai_classification?: string | null;
  ai_classification_reason?: string | null;
  security_flags: { category: string; evidence: string; severity: number }[];
  tags?: string[];
  access: string;
  access_rule: string;
}

export interface AuditRow {
  id: string;
  ts: string;
  user_id: string | null;
  user_name: string;
  session_id: string;
  ip: string;
  action: string;
  query: string;
  resource: string;
  resource_id: string;
  classification: string;
  permission_result: string;
  tool: string;
  result: string;
  reason: string;
  risk: string;
  request_id: string;
  details: Record<string, unknown>;
}

export interface Alert {
  id: string;
  ts: string;
  user_id: string | null;
  user_name: string;
  alert_type: string;
  title: string;
  pattern: string;
  risk: string;
  status: "open" | "investigating" | "resolved";
  event_count: number;
  details: Record<string, unknown>;
}

export interface Approval {
  id: string;
  type: "leave" | "document_access" | "classification" | "general" | "service_request";
  title: string;
  status: string;
  risk: string;
  resource_id: string | null;
  details: Record<string, any>;
  requester: { name: string; title: string; department: string };
  approver: string;
  decision_note: string;
  created_at: string;
  decided_at: string | null;
}

export interface RepoTreeItem {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: RepoTreeItem[];
  language?: string;
  size?: number;
}

export interface SecurityFinding {
  type: string;
  file: string;
  line?: number;
  length?: number;
  timestamp?: string;
}

export interface RepositoryItem {
  id: string;
  company_id: string;
  name: string;
  repo_name: string;
  owner_login: string;
  clone_url: string;
  default_branch: string;
  classification: Classification;
  allowed_departments: string[];
  allowed_roles: string[];
  status: "SCANNING" | "INDEXING" | "READY" | "ERROR" | "FAILED";
  total_files: number;
  total_lines: number;
  total_chunks: number;
  sync_interval: string;
  last_synced_at: string | null;
  created_at: string | null;
  tree_structure: RepoTreeItem[];
  security_scan_report: SecurityFinding[];
  secrets_count: number;
  description: string | null;
  access: "granted" | "denied";
  access_rule: string;
}

export interface Connector {
  id: string;
  company_id: string;
  provider: "github" | "jira" | "outlook" | "teams" | "entra";
  name: string;
  category: string;
  description: string;
  status: "not_connected" | "connecting" | "connected" | "syncing" | "error" | "token_expired";
  auth_type: string;
  mode: "DEMO CONNECTOR" | "PRODUCTION";
  account_name: string;
  account_email: string;
  scopes: string[];
  resources: string[];
  agent_access: Record<string, string>;
  sync_stats: Record<string, any>;
  last_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConnectorItem {
  id: string;
  company_id: string;
  connector_id: string;
  provider: string;
  item_type: string;
  external_id: string;
  title: string;
  content: string;
  metadata_json: Record<string, any>;
  classification: Classification;
  url: string;
  author: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AgentSkill {
  id: string;
  name: string;
  category: string;
  description: string;
  version: string;
  status: "active" | "deprecated" | "draft" | "disabled";
  required_connectors: string[];
  required_permissions: string[];
  tools: string[];
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
  instructions: string;
  security_restrictions: string;
  agents_using: string[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SkillExecutionStep {
  step: string;
  label: string;
  connector: string;
  status: "done" | "active" | "pending" | "pending_confirmation";
  detail: string;
}

export interface ComposedWorkflowResult {
  workflow: string;
  target: string;
  status: "awaiting_confirmation" | "completed" | "failed";
  pipeline: Array<{ id: string; label: string; status: string }>;
  timeline: SkillExecutionStep[];
  findings: Array<{
    id: string;
    severity: string;
    category: string;
    title: string;
    description: string;
    affected_components: string[];
    remediation_status: string;
    evidence: string;
  }>;
  report: {
    title: string;
    executive_summary: string;
    findings_count: number;
    evidence_matrix: Array<{ system: string; record: string; classification: string; status: string }>;
    recommendations: string[];
    sources_used: string[];
  };
  jira_issues: Array<{
    key: string;
    title: string;
    summary: string;
    status: string;
    priority: string;
    assignee: string;
    sprint: string;
    url: string;
  }>;
  action_proposal: {
    title: string;
    summary: string;
    fields: Array<[string, string]>;
    body: string;
    warning: string;
    editable: string[];
  };
}

export type Page =
  | "chat" | "tasks" | "approvals" | "documents" | "connectors" | "security" | "audit" | "admin" | "lab" | "settings" | "work";



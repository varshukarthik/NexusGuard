import {
  AlertOctagon,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Circle,
  Clock,
  ExternalLink,
  EyeOff,
  FileText,
  FileUp,
  FolderGit2,
  GitBranch,
  Loader2,
  Lock,
  Search,
  ShieldAlert,
  SkipForward,
  Upload,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ImportRepoDrawer from "../components/ImportRepoDrawer";
import RepoDetailsDrawer from "../components/RepoDetailsDrawer";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import type { DocRow, RepositoryItem } from "../lib/types";
import { Button, Card, ClassBadge, cx, Drawer, Empty, fmtDate, PageHeader, Spinner } from "../lib/ui";

interface ListResp {
  documents: DocRow[];
  total: number;
  page: number;
  pages: number;
  page_size: number;
  accessible_total: number;
  hidden: { total: number; by_classification: Record<string, number> };
  facets: { departments: string[]; doc_types: string[] };
}
interface Sample {
  filename: string;
  label: string;
  kind: "danger" | "warning" | "ok";
  content: string;
}
interface Step {
  key: string;
  label: string;
  status: string;
  detail: string;
}
interface UploadResp {
  document: DocRow;
  steps: Step[];
  quarantined: boolean;
  message?: string;
  classification?: { classification: string; reason: string; engine: string };
  can_self_approve?: boolean;
}

const STATUS_STYLE: Record<string, string> = {
  published: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300",
  superseded: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
  pending_approval: "bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-300",
  quarantined: "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300",
  rejected: "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300",
};

function StepIcon({ s }: { s: string }) {
  if (s === "done") return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
  if (s === "blocked") return <XCircle className="h-4 w-4 text-rose-500" />;
  if (s === "active") return <Clock className="h-4 w-4 text-amber-500" />;
  if (s === "skipped") return <SkipForward className="h-4 w-4 text-slate-300" />;
  return <Circle className="h-4 w-4 text-slate-300" />;
}

function UploadPanel({ onUploaded }: { onUploaded: () => void }) {
  const { notify, go, bump } = useApp();
  const [samples, setSamples] = useState<Sample[]>([]);
  const [result, setResult] = useState<UploadResp | null>(null);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  useEffect(() => {
    api.get<Sample[]>("/documents/samples").then(setSamples).catch(() => {});
  }, []);

  async function upload(f: File) {
    setBusy(true);
    setResult(null);
    const fd = new FormData();
    fd.append("file", f);
    try {
      const r = await api.upload<UploadResp>("/documents", fd);
      setResult(r);
      onUploaded();
      bump();
    } catch (e: any) {
      notify(e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5 p-5">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]);
        }}
        className={cx(
          "rounded-xl border-2 border-dashed p-6 text-center transition",
          drag
            ? "border-brand-400 bg-brand-50/60 dark:bg-brand-500/10"
            : "border-slate-200 dark:border-slate-700"
        )}
      >
        <FileUp className="mx-auto h-7 w-7 text-slate-400" />
        <p className="mt-2 text-sm font-medium">
          Drop a file here or{" "}
          <button className="text-brand-600 hover:underline" onClick={() => file.current?.click()}>
            browse
          </button>
        </p>
        <p className="mt-1 text-xs text-slate-500">.txt .md .csv .json .html .docx (.pdf with pypdf) · max 2 MB</p>
        <input
          ref={file}
          type="file"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
        />
      </div>
      <div>
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Or use a demo file</p>
        <div className="grid gap-2 sm:grid-cols-3">
          {samples.map((s) => (
            <button
              key={s.filename}
              disabled={busy}
              onClick={() => upload(new File([s.content], s.filename, { type: "text/plain" }))}
              className={cx(
                "rounded-xl border p-3 text-left text-xs transition hover:shadow-card",
                s.kind === "danger"
                  ? "border-rose-200 hover:border-rose-300 dark:border-rose-500/30"
                  : s.kind === "warning"
                  ? "border-amber-200 dark:border-amber-500/30"
                  : "border-slate-200 dark:border-slate-700"
              )}
            >
              <p
                className={cx(
                  "font-semibold",
                  s.kind === "danger"
                    ? "text-rose-700 dark:text-rose-300"
                    : s.kind === "warning"
                    ? "text-amber-700 dark:text-amber-300"
                    : "text-slate-700 dark:text-slate-200"
                )}
              >
                {s.label}
              </p>
              <p className="mt-0.5 truncate text-slate-500">{s.filename}</p>
            </button>
          ))}
        </div>
      </div>
      {busy && (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Running ingestion pipeline…
        </div>
      )}
      {result && (
        <div className="animate-fade-in space-y-3">
          {result.quarantined ? (
            <div className="flex gap-3 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-rose-900 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200">
              <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" />
              <div>
                <p className="font-semibold">⚠ Potential prompt injection detected</p>
                <p className="text-sm">{result.message}</p>
                <p className="mt-1 text-xs opacity-80">
                  Security alert raised for the security team. Document status: quarantined.
                </p>
              </div>
            </div>
          ) : (
            result.classification && (
              <div className="rounded-xl border border-brand-200 bg-brand-50/60 p-3.5 dark:border-brand-500/30 dark:bg-brand-500/10">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-brand-600">AI classification</p>
                <p className="mt-1 flex items-center gap-2 text-sm">
                  Detected: <ClassBadge level={result.classification.classification} />
                </p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                  Reason: “{result.classification.reason}”
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  Requires approval by an authorized reviewer before publication — the document is <b>not searchable</b>{" "}
                  until then.
                </p>
                {result.can_self_approve && (
                  <Button size="sm" className="mt-2" onClick={() => go("approvals")}>
                    Review in Approvals →
                  </Button>
                )}
              </div>
            )
          )}
          <Card className="p-4">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Ingestion pipeline · {result.document.id}
            </p>
            <ol className="space-y-2">
              {result.steps.map((s) => (
                <li key={s.key} className="flex gap-2.5 text-sm">
                  <StepIcon s={s.status} />
                  <div>
                    <p
                      className={cx(
                        "font-medium",
                        s.status === "blocked" && "text-rose-700 dark:text-rose-300",
                        s.status === "skipped" && "text-slate-400"
                      )}
                    >
                      {s.label}
                    </p>
                    <p className="text-xs text-slate-500">{s.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
          </Card>
        </div>
      )}
    </div>
  );
}

export default function Documents() {
  const { openDoc, version, me, can } = useApp();
  const [section, setSection] = useState<"documents" | "repositories">("documents");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ListResp | null>(null);
  const [q, setQ] = useState("");
  const [dept, setDept] = useState("");
  const [cls, setCls] = useState("");
  const [type, setType] = useState("");
  const [since, setSince] = useState("");
  const [upload, setUpload] = useState(false);
  const [importRepo, setImportRepo] = useState(false);
  const [error, setError] = useState("");

  // Repositories state
  const [repos, setRepos] = useState<RepositoryItem[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<RepositoryItem | null>(null);
  const [repoLoading, setRepoLoading] = useState(false);

  const load = () => {
    const p = new URLSearchParams({
      q,
      department: dept,
      classification: cls,
      doc_type: type,
      since,
      page: String(page),
      page_size: "25",
    });
    api
      .get<ListResp>(`/documents?${p}`)
      .then((r) => {
        setData(r);
        setError("");
      })
      .catch((e) => setError(e.message));
  };

  const loadRepos = () => {
    setRepoLoading(true);
    api
      .get<{ repositories: RepositoryItem[] }>("/repositories")
      .then((r) => setRepos(r.repositories || []))
      .catch(() => {})
      .finally(() => setRepoLoading(false));
  };

  useEffect(() => {
    setPage(1);
  }, [q, dept, cls, type, since]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [q, dept, cls, type, since, page, version, me.user_id]);

  useEffect(() => {
    loadRepos();
  }, [version, me.user_id]);

  return (
    <div className="mx-auto max-w-7xl p-6">
      <PageHeader
        icon={<FileText className="h-5 w-5" />}
        title={me.is_guest ? "Public Knowledge" : "Knowledge Base"}
        subtitle={
          me.is_guest
            ? "Public NovaTech Solutions information. Internal knowledge requires an employee sign-in."
            : `${data ? data.accessible_total.toLocaleString() : "…"} documents available to your role. Every view is authorization-checked server-side and audited.`
        }
        actions={
          <div className="flex items-center gap-2">
            {!me.is_guest && (
              <Button
                variant="secondary"
                onClick={() => setImportRepo(true)}
                className="gap-2 border-slate-300 dark:border-slate-700"
              >
                <FolderGit2 className="h-4 w-4 text-brand-600" />
                <span>Import Repository</span>
              </Button>
            )}
            {can("documents:upload") && (
              <Button variant="primary" onClick={() => setUpload(true)}>
                <Upload className="h-4 w-4" />
                Upload document
              </Button>
            )}
          </div>
        }
      />

      {error && (
        <p
          role="alert"
          className="mb-4 rounded-lg bg-rose-50 px-4 py-2.5 text-sm text-rose-700 dark:bg-rose-500/10 dark:text-rose-300"
        >
          {error}
        </p>
      )}

      {/* Segmented Selector: Documents vs Repositories */}
      <div className="mb-4 flex items-center justify-between border-b border-slate-200 pb-3 dark:border-slate-800">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setSection("documents")}
            className={cx(
              "flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all",
              section === "documents"
                ? "bg-slate-900 text-white shadow-sm dark:bg-white dark:text-slate-900"
                : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
            )}
          >
            <FileText className="h-3.5 w-3.5" />
            Documents ({data ? data.accessible_total.toLocaleString() : 0})
          </button>
          <button
            type="button"
            onClick={() => setSection("repositories")}
            className={cx(
              "flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all",
              section === "repositories"
                ? "bg-slate-900 text-white shadow-sm dark:bg-white dark:text-slate-900"
                : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
            )}
          >
            <FolderGit2 className="h-3.5 w-3.5" />
            Code Repositories ({repos.length})
          </button>
        </div>

        {section === "repositories" && !me.is_guest && (
          <Button size="sm" variant="secondary" onClick={() => setImportRepo(true)} className="gap-1.5 text-xs">
            <FolderGit2 className="h-3.5 w-3.5 text-brand-600" />
            Connect New Repo
          </Button>
        )}
      </div>

      {section === "documents" && (
        <>
          {data && data.hidden.total > 0 && (
            <div className="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
              <EyeOff className="h-4 w-4 text-slate-400" />
              <b>{data.hidden.total.toLocaleString()}</b> document(s) hidden by access policy:
              {Object.entries(data.hidden.by_classification).map(([k, v]) => (
                <span key={k} className="flex items-center gap-1">
                  <ClassBadge level={k} size="xs" />×{v}
                </span>
              ))}
            </div>
          )}

          <Card>
            <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 p-3 dark:border-slate-800">
              <div className="relative min-w-[220px] flex-1">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                <input
                  className="input pl-9"
                  placeholder="Search by title, file or ID"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                />
              </div>
              <select className="input !w-auto" value={dept} onChange={(e) => setDept(e.target.value)}>
                <option value="">All departments</option>
                {data?.facets.departments.map((d) => (
                  <option key={d}>{d}</option>
                ))}
              </select>
              <select className="input !w-auto" value={cls} onChange={(e) => setCls(e.target.value)}>
                <option value="">All classifications</option>
                {["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"].map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
              <select className="input !w-auto" value={type} onChange={(e) => setType(e.target.value)}>
                <option value="">All types</option>
                {data?.facets.doc_types.map((d) => (
                  <option key={d}>{d}</option>
                ))}
              </select>
              <input
                type="date"
                className="input !w-auto"
                value={since}
                onChange={(e) => setSince(e.target.value)}
                title="Effective on/after"
              />
            </div>
            {!data ? (
              <div className="flex justify-center p-10">
                <Spinner />
              </div>
            ) : data.documents.length === 0 ? (
              <Empty icon={<FileText className="h-5 w-5" />} title="No documents match" />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[860px]">
                  <thead className="border-b border-slate-100 dark:border-slate-800">
                    <tr>
                      <th className="th">Document</th>
                      <th className="th">Department</th>
                      <th className="th">Classification</th>
                      <th className="th">Owner</th>
                      <th className="th">Last updated</th>
                      <th className="th">Access level</th>
                      <th className="th">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {data.documents.map((d) => (
                      <tr
                        key={d.id}
                        onClick={() => openDoc(d.id)}
                        className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40"
                      >
                        <td className="td">
                          <div className="flex items-center gap-2.5">
                            <div className="rounded-md bg-slate-100 p-1.5 text-slate-500 dark:bg-slate-800">
                              {d.status === "quarantined" ? (
                                <AlertOctagon className="h-4 w-4 text-rose-500" />
                              ) : (
                                <FileText className="h-4 w-4" />
                              )}
                            </div>
                            <div className="min-w-0">
                              <p className="max-w-[360px] truncate font-medium text-slate-800 dark:text-slate-100">
                                {d.title}
                              </p>
                              <p className="text-xs text-slate-500">
                                {d.id} · v{d.version} · {d.doc_type}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="td text-slate-600 dark:text-slate-300">{d.department}</td>
                        <td className="td">
                          <ClassBadge level={d.classification} />
                        </td>
                        <td className="td text-slate-600 dark:text-slate-300">{d.owner}</td>
                        <td className="td whitespace-nowrap text-slate-600 dark:text-slate-300">
                          {fmtDate(d.updated_at ?? d.effective_date)}
                        </td>
                        <td className="td text-xs text-slate-500">
                          {d.allowed_departments.includes("*") ? (
                            "All employees"
                          ) : (
                            d.allowed_departments.join(", ") || (
                              <span className="flex items-center gap-1">
                                <Lock className="h-3 w-3" />
                                Nobody
                              </span>
                            )
                          )}
                          <p className="text-[10.5px] text-emerald-600">✓ {d.access_rule.replace("_", " ")}</p>
                        </td>
                        <td className="td">
                          <span
                            className={cx("rounded px-1.5 py-0.5 text-[11px] font-semibold", STATUS_STYLE[d.status])}
                          >
                            {d.status.replace("_", " ")}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {data && data.pages > 1 && (
              <div className="flex items-center justify-between border-t border-slate-100 px-4 py-2.5 text-sm dark:border-slate-800">
                <span className="text-slate-500">
                  {((data.page - 1) * data.page_size + 1).toLocaleString()}–
                  {Math.min(data.page * data.page_size, data.total).toLocaleString()} of {data.total.toLocaleString()}
                </span>
                <div className="flex items-center gap-1">
                  <Button size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} aria-label="Previous page">
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="px-2 text-xs text-slate-500">
                    Page {data.page} of {data.pages}
                  </span>
                  <Button
                    size="sm"
                    disabled={page >= data.pages}
                    onClick={() => setPage((p) => p + 1)}
                    aria-label="Next page"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </>
      )}

      {section === "repositories" && (
        <div className="space-y-4">
          {repoLoading ? (
            <div className="flex justify-center p-12">
              <Spinner />
            </div>
          ) : repos.length === 0 ? (
            <Empty
              icon={<FolderGit2 className="h-6 w-6 text-slate-400" />}
              title="No code repositories connected"
              action={
                !me.is_guest ? (
                  <Button variant="primary" size="sm" onClick={() => setImportRepo(true)}>
                    <FolderGit2 className="h-4 w-4" />
                    Import Repository
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {repos.map((r) => (
                <Card key={r.id} className="flex flex-col justify-between p-4 transition-all hover:shadow-card">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-2">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-500/10 dark:text-brand-400">
                          <FolderGit2 className="h-5 w-5" />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate font-semibold text-slate-900 dark:text-white">{r.name}</p>
                          <p className="truncate font-mono text-[11px] text-slate-500">{r.repo_name}</p>
                        </div>
                      </div>
                      <ClassBadge level={r.classification} size="xs" />
                    </div>

                    <p className="line-clamp-2 text-xs text-slate-600 dark:text-slate-400">
                      {r.description || "Connected GitHub repository indexed for multi-agent code search."}
                    </p>

                    <div className="grid grid-cols-3 gap-2 rounded-lg bg-slate-50 p-2 text-center text-xs dark:bg-slate-800/50">
                      <div>
                        <p className="font-bold text-slate-900 dark:text-white">{r.total_files}</p>
                        <p className="text-[10px] text-slate-500">Files</p>
                      </div>
                      <div>
                        <p className="font-bold text-slate-900 dark:text-white">{r.total_chunks}</p>
                        <p className="text-[10px] text-slate-500">Chunks</p>
                      </div>
                      <div>
                        <p
                          className={cx(
                            "font-bold",
                            r.secrets_count > 0
                              ? "text-amber-600 dark:text-amber-400"
                              : "text-emerald-600 dark:text-emerald-400"
                          )}
                        >
                          {r.secrets_count}
                        </p>
                        <p className="text-[10px] text-slate-500">Redacted</p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-500">
                      <span className="flex items-center gap-1">
                        <GitBranch className="h-3 w-3" />
                        {r.default_branch}
                      </span>
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                        {r.status}
                      </span>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
                    <Button
                      size="sm"
                      variant="primary"
                      className="flex-1 text-xs"
                      onClick={() => setSelectedRepo(r)}
                    >
                      Inspect Codebase
                    </Button>
                    <a
                      href={r.clone_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                      title="Open in GitHub"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Upload Document Drawer */}
      <Drawer open={upload} onClose={() => setUpload(false)} title="Upload & classify document" width="max-w-xl">
        <UploadPanel onUploaded={load} />
      </Drawer>

      {/* Import Repository Drawer */}
      <ImportRepoDrawer
        open={importRepo}
        onClose={() => setImportRepo(false)}
        onImported={() => {
          loadRepos();
          load();
        }}
      />

      {/* Repository Details Drawer */}
      <RepoDetailsDrawer
        repo={selectedRepo}
        onClose={() => setSelectedRepo(null)}
        onSync={() => {
          loadRepos();
        }}
        onDelete={() => {
          loadRepos();
        }}
      />
    </div>
  );
}

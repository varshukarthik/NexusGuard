import {
  ChevronDown,
  ChevronRight,
  ExternalLink,
  FileCode,
  Folder,
  FolderGit2,
  FolderOpen,
  GitBranch,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import type { RepoTreeItem, RepositoryItem, SecurityFinding } from "../lib/types";
import { Button, ClassBadge, cx, Drawer, fmtDate, Spinner } from "../lib/ui";

interface RepoDetailsDrawerProps {
  repo: RepositoryItem | null;
  onClose: () => void;
  onSync: () => void;
  onDelete: () => void;
}

function FileTreeNode({ item, depth = 0 }: { item: RepoTreeItem; depth?: number }) {
  const [isOpen, setIsOpen] = useState(depth < 2);
  const isDir = item.type === "directory";

  return (
    <div className="text-xs">
      <div
        onClick={() => isDir && setIsOpen(!isOpen)}
        style={{ paddingLeft: `${depth * 14 + 6}px` }}
        className={cx(
          "flex cursor-pointer select-none items-center justify-between rounded-md py-1.5 pr-2 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800/60",
          depth === 0 && "font-medium"
        )}
      >
        <div className="flex items-center gap-1.5 truncate">
          {isDir ? (
            <>
              {isOpen ? <ChevronDown className="h-3.5 w-3.5 text-slate-400" /> : <ChevronRight className="h-3.5 w-3.5 text-slate-400" />}
              {isOpen ? <FolderOpen className="h-3.5 w-3.5 text-amber-500" /> : <Folder className="h-3.5 w-3.5 text-amber-500" />}
            </>
          ) : (
            <>
              <span className="w-3.5" />
              <FileCode className="h-3.5 w-3.5 text-blue-500 dark:text-blue-400" />
            </>
          )}
          <span className="truncate text-slate-800 dark:text-slate-200">{item.name}</span>
        </div>
        {item.size !== undefined && !isDir && (
          <span className="font-mono text-[10px] text-slate-400">
            {item.size > 1024 ? `${(item.size / 1024).toFixed(1)} KB` : `${item.size} B`}
          </span>
        )}
      </div>

      {isDir && isOpen && item.children && (
        <div className="border-l border-slate-200 dark:border-slate-800">
          {item.children.map((child, idx) => (
            <FileTreeNode key={`${child.path}-${idx}`} item={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function RepoDetailsDrawer({ repo, onClose, onSync, onDelete }: RepoDetailsDrawerProps) {
  const { me, notify } = useApp();
  const [activeTab, setActiveTab] = useState<"tree" | "security">("tree");
  const [isSyncing, setIsSyncing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (!repo) return null;

  const canManage = me?.permissions?.includes("repositories:manage") || me?.permissions?.includes("admin:dashboard");
  const scanReport: SecurityFinding[] = repo.security_scan_report || [];

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await api.post(`/repositories/${repo.id}/sync`, {});
      notify(`Repository '${repo.name}' synchronized successfully!`, "ok");
      onSync();
    } catch (err: any) {
      notify(err.message || "Failed to sync repository", "err");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.del(`/repositories/${repo.id}`);
      notify(`Repository '${repo.name}' disconnected.`, "ok");
      setConfirmDelete(false);
      onDelete();
      onClose();
    } catch (err: any) {
      notify(err.message || "Failed to disconnect repository", "err");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Drawer
      open={!!repo}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <FolderGit2 className="h-5 w-5 text-brand-600" />
          <span className="truncate">{repo.name}</span>
        </div>
      }
    >
      <div className="space-y-6 p-5">
        {/* Header Badges & Repo Metadata */}
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <ClassBadge level={repo.classification} />
            <span className="rounded bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300">
              {repo.repo_name}
            </span>
            <span className="flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-400">
              <GitBranch className="h-3 w-3" />
              {repo.default_branch}
            </span>
            <span
              className={cx(
                "rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wider",
                repo.status === "READY"
                  ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
                  : "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
              )}
            >
              {repo.status}
            </span>
          </div>

          <p className="text-xs text-slate-600 dark:text-slate-400">
            {repo.description || "Imported code repository connected to NovaTech intelligence search."}
          </p>

          <a
            href={repo.clone_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:underline dark:text-brand-400"
          >
            <span>View on GitHub</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-2.5">
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-center dark:border-slate-800 dark:bg-slate-900/40">
            <p className="text-lg font-bold text-slate-900 dark:text-white">{repo.total_files}</p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">Source Files</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-center dark:border-slate-800 dark:bg-slate-900/40">
            <p className="text-lg font-bold text-slate-900 dark:text-white">{repo.total_chunks}</p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">Vector Chunks</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 text-center dark:border-slate-800 dark:bg-slate-900/40">
            <p className={cx("text-lg font-bold", scanReport.length > 0 ? "text-amber-600 dark:text-amber-400" : "text-emerald-600 dark:text-emerald-400")}>
              {scanReport.length}
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">Secrets Masked</p>
          </div>
        </div>

        {/* Sync Info */}
        <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3.5 py-2.5 text-xs text-slate-500 dark:bg-slate-800/40 dark:text-slate-400">
          <span>Last synchronized: {repo.last_synced_at ? fmtDate(repo.last_synced_at) : "Never"}</span>
          <span>Sync: {repo.sync_interval || "Manual"}</span>
        </div>

        {/* Tabs */}
        <div className="flex rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
          <button
            type="button"
            onClick={() => setActiveTab("tree")}
            className={cx(
              "flex-1 rounded-md py-1.5 text-xs font-semibold transition-all",
              activeTab === "tree"
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white"
                : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            )}
          >
            File Tree ({repo.tree_structure?.length || 0})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("security")}
            className={cx(
              "flex-1 rounded-md py-1.5 text-xs font-semibold transition-all",
              activeTab === "security"
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white"
                : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            )}
          >
            Security Scan ({scanReport.length})
          </button>
        </div>

        {/* Tab 1: File Tree */}
        {activeTab === "tree" && (
          <div className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-950">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Indexed Codebase Hierarchy
            </p>
            <div className="max-h-72 overflow-y-auto space-y-0.5 pr-1">
              {repo.tree_structure && repo.tree_structure.length > 0 ? (
                repo.tree_structure.map((node, i) => <FileTreeNode key={`${node.path}-${i}`} item={node} />)
              ) : (
                <p className="py-6 text-center text-xs text-slate-400">No files registered in tree.</p>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Security & Secret Findings */}
        {activeTab === "security" && (
          <div className="space-y-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 dark:border-slate-800 dark:bg-slate-900/30">
              <div className="flex items-center gap-2">
                {scanReport.length === 0 ? (
                  <>
                    <ShieldCheck className="h-5 w-5 text-emerald-500" />
                    <div>
                      <p className="text-xs font-semibold text-slate-900 dark:text-white">Clean Security Scan</p>
                      <p className="text-[11px] text-slate-500">No unredacted credentials or API tokens detected.</p>
                    </div>
                  </>
                ) : (
                  <>
                    <ShieldAlert className="h-5 w-5 text-amber-500" />
                    <div>
                      <p className="text-xs font-semibold text-slate-900 dark:text-white">
                        {scanReport.length} Sensitive Secret(s) Automatically Redacted
                      </p>
                      <p className="text-[11px] text-slate-500">
                        Tokens and private keys were masked prior to chunking and vector storage.
                      </p>
                    </div>
                  </>
                )}
              </div>
            </div>

            {scanReport.length > 0 && (
              <div className="divide-y divide-slate-100 rounded-xl border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
                {scanReport.map((f, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 text-xs">
                    <div>
                      <span className="font-mono text-xs font-semibold text-rose-600 dark:text-rose-400">
                        {f.type}
                      </span>
                      <p className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">{f.file}</p>
                    </div>
                    <span className="rounded bg-rose-50 px-2 py-0.5 text-[10px] font-medium text-rose-700 dark:bg-rose-500/10 dark:text-rose-300">
                      [REDACTED]
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Action Controls */}
        <div className="space-y-3 border-t border-slate-100 pt-4 dark:border-slate-800">
          <div className="flex items-center justify-between">
            {confirmDelete ? (
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="danger"
                  disabled={isDeleting}
                  onClick={handleDelete}
                  className="!bg-rose-600 text-white"
                >
                  {isDeleting ? <Spinner className="h-3.5 w-3.5" /> : <Trash2 className="h-3.5 w-3.5" />}
                  Confirm Disconnect
                </Button>
                <Button size="sm" variant="secondary" onClick={() => setConfirmDelete(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                variant="secondary"
                disabled={!canManage}
                onClick={() => setConfirmDelete(true)}
                className="text-rose-600 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-500/10"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Disconnect Repo
              </Button>
            )}

            <Button size="sm" variant="primary" disabled={isSyncing || !canManage} onClick={handleSync}>
              <RefreshCw className={cx("h-3.5 w-3.5", isSyncing && "animate-spin")} />
              Sync Now
            </Button>
          </div>
        </div>
      </div>
    </Drawer>
  );
}

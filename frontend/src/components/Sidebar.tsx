import { BarChart3, Bot, ClipboardCheck, FileText, FlaskConical, Globe2, ListChecks, MessageSquare, MoreHorizontal,
  Pencil, Plus, ScrollText, Search, Settings, Shield, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import type { Conversation, Page } from "../lib/types";
import { cx } from "../lib/ui";
import { BrandLockup } from "./Brand";

interface Props {
  page: Page;
  pages: Page[];
  setPage: (p: Page) => void;
  conversationId: string | null;
  openConversation: (id: string) => void;
  newChat: () => void;
  onDeleted: (id: string) => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

const NAV: { id: Page; label: string; icon: any }[] = [
  { id: "chat", label: "AI Assistant", icon: MessageSquare },
  { id: "work", label: "Work Mode", icon: Bot },
  { id: "tasks", label: "My Work", icon: ListChecks },
  { id: "approvals", label: "Approvals", icon: ClipboardCheck },
  { id: "documents", label: "Knowledge Base", icon: FileText },
  { id: "security", label: "Security Center", icon: Shield },
  { id: "audit", label: "Audit Logs", icon: ScrollText },
  { id: "admin", label: "Admin Dashboard", icon: BarChart3 },
  { id: "lab", label: "Policy Lab", icon: FlaskConical },
  { id: "settings", label: "Settings", icon: Settings },
];

function groupOf(iso: string) {
  const d = new Date(iso), now = new Date();
  const days = Math.floor((now.getTime() - d.getTime()) / 86400000);
  return days < 1 ? "Today" : days < 2 ? "Yesterday" : days < 7 ? "Previous 7 days" : "Older";
}

export default function Sidebar({ page, pages, setPage, conversationId, openConversation, newChat, onDeleted, mobileOpen, onCloseMobile }: Props) {
  const { version, notify, me } = useApp();
  const [convs, setConvs] = useState<Conversation[]>([]);
  const [q, setQ] = useState("");
  const [menu, setMenu] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(0);
  const t = useRef<number>();

  useEffect(() => {
    window.clearTimeout(t.current);
    t.current = window.setTimeout(() => {
      api.get<Conversation[]>(`/conversations?q=${encodeURIComponent(q)}`).then(setConvs).catch(() => {});
    }, q ? 250 : 0);
  }, [q, version, me.user_id]);

  useEffect(() => {
    if (me.is_guest) return;
    api.get<{ inbox: { status: string }[] }>("/approvals")
      .then((r) => setPending(r.inbox.filter((a) => a.status === "pending").length)).catch(() => {});
  }, [version, page, me.user_id, me.is_guest]);

  async function rename(id: string) {
    if (!draft.trim()) return setEditing(null);
    try {
      await api.patch(`/conversations/${id}`, { title: draft.trim() });
      setConvs((c) => c.map((x) => (x.id === id ? { ...x, title: draft.trim() } : x)));
    } catch (e: any) { notify(e.message, "err"); }
    setEditing(null);
  }
  async function remove(id: string) {
    try {
      await api.del(`/conversations/${id}`);
      setConvs((c) => c.filter((x) => x.id !== id));
      onDeleted(id);
      notify("Conversation deleted");
    } catch (e: any) { notify(e.message, "err"); }
  }

  const groups: [string, Conversation[]][] = [];
  for (const c of convs) {
    const g = groupOf(c.updated_at);
    const last = groups[groups.length - 1];
    if (last && last[0] === g) last[1].push(c); else groups.push([g, [c]]);
  }

  return (
    <>
      {mobileOpen && <div className="fixed inset-0 z-40 bg-slate-900/40 md:hidden" onClick={onCloseMobile} aria-hidden="true" />}
      <aside aria-label="Primary navigation"
        className={cx("z-50 w-[272px] shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900",
          mobileOpen ? "fixed inset-y-0 left-0 flex shadow-2xl animate-fade-in" : "hidden md:flex")}>
        <div className="flex items-center justify-between px-4 pb-3 pt-4">
          <BrandLockup size="sm" sub={me.is_guest ? "Guest Mode" : "Intelligence Platform"} />
          <button onClick={onCloseMobile} className="rounded p-1 text-slate-400 hover:bg-slate-100 md:hidden dark:hover:bg-slate-800" aria-label="Close menu"><X className="h-4 w-4" /></button>
        </div>
        <div className="px-3">
          <button onClick={newChat} className="focus-ring flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100">
            <Plus className="h-4 w-4" /> New conversation
          </button>
        </div>
        <nav className="mt-3 space-y-0.5 px-3">
          {NAV.filter((n) => pages.includes(n.id)).map((n) => (
            <button key={n.id} onClick={() => setPage(n.id)} aria-current={page === n.id ? "page" : undefined}
              className={cx("focus-ring flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-sm transition",
                page === n.id ? "bg-brand-50 font-medium text-brand-800 dark:bg-brand-500/10 dark:text-brand-200" : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800")}>
              <n.icon className="h-4 w-4" />
              <span className="flex-1 text-left">{n.id === "documents" && me.is_guest ? "Public Knowledge" : n.label}</span>
              {n.id === "approvals" && !!pending && <span className="rounded-full bg-rose-500 px-1.5 text-[10.5px] font-semibold text-white">{pending}</span>}
            </button>
          ))}
        </nav>
        <div className="mt-4 px-5"><p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Conversations</p></div>
        <div className="px-3 pt-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search conversations" aria-label="Search conversations"
              className="w-full rounded-md border border-slate-200 bg-slate-50 py-1.5 pl-8 pr-2 text-xs focus:border-brand-300 focus:outline-none dark:border-slate-800 dark:bg-slate-950" />
          </div>
        </div>
        <div className="mt-1.5 flex-1 overflow-y-auto px-3 pb-3 scroll-thin" onClick={() => setMenu(null)}>
          {convs.length === 0 && <p className="px-2 py-3 text-xs text-slate-400">{q ? "No matches" : me.is_guest ? "Guest conversations are temporary and end when you sign out." : "No conversations yet"}</p>}
          {groups.map(([g, list]) => (
            <div key={g} className="mb-1">
              <p className="px-2 pb-1 pt-2 text-[10.5px] font-medium text-slate-400">{g}</p>
              {list.map((c) => (
                <div key={c.id} className={cx("group relative flex items-center rounded-md",
                  conversationId === c.id && page === "chat" ? "bg-slate-100 dark:bg-slate-800" : "hover:bg-slate-50 dark:hover:bg-slate-800/60")}>
                  {editing === c.id ? (
                    <input autoFocus value={draft} onChange={(e) => setDraft(e.target.value)} onBlur={() => rename(c.id)} aria-label="Conversation title"
                      onKeyDown={(e) => { if (e.key === "Enter") rename(c.id); if (e.key === "Escape") setEditing(null); }}
                      className="m-0.5 w-full rounded border border-brand-300 px-2 py-1 text-xs focus:outline-none dark:bg-slate-900" />
                  ) : (
                    <button onClick={() => openConversation(c.id)} className="min-w-0 flex-1 truncate px-2.5 py-1.5 text-left text-[13px] text-slate-600 dark:text-slate-300">{c.title}</button>
                  )}
                  {editing !== c.id && (
                    <button onClick={(e) => { e.stopPropagation(); setMenu(menu === c.id ? null : c.id); }}
                      className="mr-1 rounded p-0.5 text-slate-400 opacity-0 hover:bg-slate-200 focus:opacity-100 group-hover:opacity-100 dark:hover:bg-slate-700" aria-label={`Options for ${c.title}`}>
                      <MoreHorizontal className="h-4 w-4" />
                    </button>
                  )}
                  {menu === c.id && (
                    <div className="absolute right-1 top-8 z-20 w-36 rounded-lg border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                      <button className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-xs hover:bg-slate-100 dark:hover:bg-slate-800"
                        onClick={() => { setEditing(c.id); setDraft(c.title); setMenu(null); }}><Pencil className="h-3.5 w-3.5" />Rename</button>
                      <button className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-xs text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10"
                        onClick={() => { setMenu(null); remove(c.id); }}><Trash2 className="h-3.5 w-3.5" />Delete</button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
        <div className="border-t border-slate-200 px-4 py-2.5 text-[10.5px] leading-snug text-slate-400 dark:border-slate-800">
          {me.is_guest ? <span className="flex items-center gap-1.5"><Globe2 className="h-3 w-3" />Guest Mode · public information only</span>
            : "Fictional demo data · NovaTech Solutions"}
        </div>
      </aside>
    </>
  );
}

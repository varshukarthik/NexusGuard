import { AlertCircle, ArrowUp, BarChart3, Bot, BriefcaseBusiness, Download, Eraser, FileSearch, FolderKanban, Globe2,
  Laptop, ListTodo, Lock, RotateCcw, ShieldCheck, Square, Users, Workflow } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NovaMark } from "../components/Brand";
import { AgentActivity, AssistantMessage } from "../components/Message";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import { Markdown } from "../lib/markdown";
import type { ChatMessage, TimelineStep } from "../lib/types";
import { Avatar, Button, cx, Spinner } from "../lib/ui";

type Final = { conversation: { id: string; title: string }; user_message: ChatMessage; assistant_message: ChatMessage };

const CAPABILITIES = [
  { icon: FileSearch, name: "Knowledge", text: "Policies, procedures and guides — cited" },
  { icon: Users, name: "HR", text: "Leave, benefits, onboarding, people" },
  { icon: Laptop, name: "IT", text: "VPN, devices, software, escalations" },
  { icon: FolderKanban, name: "Projects", text: "Status, members, deadlines, risks" },
  { icon: BarChart3, name: "Analytics", text: "Counts and trends from live records" },
  { icon: BriefcaseBusiness, name: "Documents", text: "Summarise, compare, find owners" },
  { icon: Workflow, name: "Workflows", text: "Tickets, leave, access — with confirmation" },
  { icon: ListTodo, name: "Productivity", text: "Priorities, tasks and meeting prep" },
];
const GUEST_CAPS = [
  { icon: Globe2, name: "Company", text: "Products, offices and public announcements" },
  { icon: FileSearch, name: "Public policies", text: "Privacy notice, careers FAQ, sustainability" },
  { icon: FolderKanban, name: "Public initiatives", text: "Open-source, community and green projects" },
  { icon: Bot, name: "AI capabilities", text: "See how the agents plan, retrieve and cite" },
];
const GUEST_GREETING = "Welcome to NovaTech Solutions. You are currently using Guest Mode. I can help you explore publicly available company information and demonstrate our enterprise AI capabilities.";

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export default function Chat({ conversationId, onConversation, onNewChat }:
  { conversationId: string | null; onConversation: (id: string) => void; onNewChat: () => void }) {
  const { me, notify } = useApp();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [convId, setConvId] = useState<string | null>(conversationId);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(!!conversationId);
  const [steps, setSteps] = useState<TimelineStep[]>([]);
  const [partial, setPartial] = useState("");
  const [failed, setFailed] = useState<{ q: string; msg: string; regen?: boolean } | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const ta = useRef<HTMLTextAreaElement>(null);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    setConvId(conversationId);
    if (!conversationId) { setMessages([]); setLoading(false); return; }
    setLoading(true);
    api.get<{ messages: ChatMessage[] }>(`/conversations/${conversationId}`)
      .then((r) => setMessages(r.messages)).catch((e) => notify(e.message, "err")).finally(() => setLoading(false));
  }, [conversationId, notify]);

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages.length, busy, steps.length, failed]);
  useEffect(() => { if (!busy) ta.current?.focus(); }, [busy]);

  async function runStream(path: string, body: unknown, regen = false, q = "") {
    setBusy(true); setSteps([]); setPartial(""); setFailed(null);
    const ctl = new AbortController();
    abort.current = ctl;
    try {
      const r = await api.stream<Final>(path, body, {
        onStep: (s) => setSteps((x) => [...x, s]),
        onDelta: (t) => setPartial((p) => p + t),
      }, ctl.signal);
      setMessages((m) => {
        const base = m.filter((x) => x.id !== "tmp");
        if (regen) {
          const idx = base.map((x) => x.role).lastIndexOf("assistant");
          return idx >= 0 ? [...base.slice(0, idx), r.assistant_message] : [...base, r.assistant_message];
        }
        return [...base, r.user_message, r.assistant_message];
      });
      if (r.conversation.id !== convId) { setConvId(r.conversation.id); onConversation(r.conversation.id); }
    } catch (e: any) {
      if (e.code === "aborted") {
        setMessages((m) => m.filter((x) => x.id !== "tmp"));
        setInput(q);
      } else {
        setFailed({ q, msg: e.message, regen });
      }
    } finally { setBusy(false); setSteps([]); setPartial(""); abort.current = null; }
  }

  function send(text?: string) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setInput("");
    if (ta.current) ta.current.style.height = "auto";
    setMessages((m) => [...m.filter((x) => x.id !== "tmp"), { id: "tmp", role: "user", content: q, meta: {}, created_at: new Date().toISOString() }]);
    runStream("/chat/stream", { message: q, conversation_id: convId }, false, q);
  }
  function regenerate() {
    if (!convId || busy) return;
    runStream(`/conversations/${convId}/regenerate?stream=true`, {}, true);
  }
  function retry() {
    if (!failed) return;
    if (failed.regen) return regenerate();
    setMessages((m) => m.filter((x) => x.id !== "tmp"));
    send(failed.q);
  }
  async function exportChat() {
    if (!convId) return;
    try {
      const { blob, filename } = await api.download(`/conversations/${convId}/export`);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = filename; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    } catch (e: any) { notify(e.message, "err"); }
  }
  async function clearChat() {
    if (!convId || !confirmClear()) return;
    try { await api.post(`/conversations/${convId}/clear`); setMessages([]); notify("Conversation cleared"); }
    catch (e: any) { notify(e.message, "err"); }
  }
  function confirmClear() { return window.confirm("Clear all messages in this conversation? This can't be undone."); }

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant")?.id;
  const empty = !loading && messages.length === 0 && !busy;
  const caps = me.is_guest ? GUEST_CAPS : CAPABILITIES;

  return (
    <div className="flex h-full flex-col">
      {!!messages.length && convId && (
        <div className="flex items-center justify-end gap-1 border-b border-slate-100 px-4 py-1.5 dark:border-slate-800/80">
          <Button size="sm" variant="ghost" onClick={exportChat} title="Export conversation as Markdown"><Download className="h-3.5 w-3.5" />Export</Button>
          <Button size="sm" variant="ghost" onClick={clearChat} title="Clear conversation"><Eraser className="h-3.5 w-3.5" />Clear</Button>
          <Button size="sm" variant="ghost" onClick={onNewChat}>New</Button>
        </div>
      )}
      <div className="flex-1 overflow-y-auto scroll-thin">
        <div className="mx-auto max-w-3xl px-4 pb-6 pt-6 sm:px-6">
          {loading && <div className="flex justify-center py-20"><Spinner className="h-5 w-5 text-slate-400" /></div>}
          {empty && (
            <div className="animate-rise pt-4 sm:pt-12">
              <div className="mb-8 text-center">
                <NovaMark className="mx-auto mb-5 h-12 w-12" />
                {me.is_guest ? (
                  <>
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-semibold text-amber-800 dark:bg-amber-500/15 dark:text-amber-300"><Globe2 className="h-3 w-3" />Guest Mode</span>
                    <p className="mx-auto mt-4 max-w-xl text-[15px] leading-relaxed text-slate-700 dark:text-slate-300">{GUEST_GREETING}</p>
                  </>
                ) : (
                  <>
                    <h2 className="text-[26px] font-semibold tracking-tight text-slate-900 dark:text-white">{greeting()}, {me.full_name.split(" ")[0]}.</h2>
                    <p className="mx-auto mt-2 max-w-lg text-[14px] text-slate-500">
                      Ask anything about NovaTech Solutions — policies, projects, people, data — or ask me to get work done. I only use information your role is allowed to access.
                    </p>
                  </>
                )}
              </div>
              <p className="mb-2 text-center text-[11px] font-semibold uppercase tracking-wider text-slate-400">{me.is_guest ? "What you can explore" : "Specialised agents working for you"}</p>
              <div className={cx("grid gap-2", me.is_guest ? "sm:grid-cols-2" : "grid-cols-2 sm:grid-cols-4")}>
                {caps.map((c) => (
                  <div key={c.name} className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900">
                    <c.icon className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                    <p className="mt-2 text-[13px] font-semibold text-slate-800 dark:text-slate-100">{c.name}</p>
                    <p className="mt-0.5 text-[12px] leading-snug text-slate-500">{c.text}</p>
                  </div>
                ))}
              </div>
              <p className="mt-6 flex items-center justify-center gap-1.5 text-[12px] text-slate-400">
                {me.is_guest ? <><Lock className="h-3.5 w-3.5" />Internal, confidential and personal data are never available in Guest Mode.</>
                  : <><ShieldCheck className="h-3.5 w-3.5" />Access is checked on the server before any data reaches the AI. Actions always ask for your confirmation.</>}
              </p>
            </div>
          )}
          <div className="space-y-7">
            {messages.map((m) => m.role === "user" ? (
              <div key={m.id} className="flex justify-end gap-3 animate-fade-in">
                <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-tr-md bg-slate-900 px-4 py-2.5 text-[14.5px] text-white dark:bg-brand-600">{m.content}</div>
                <Avatar name={me.full_name} />
              </div>
            ) : (
              <AssistantMessage key={m.id} msg={m} latest={m.id === lastAssistant && !busy}
                onRegenerate={regenerate}
                onUpdate={(nm) => setMessages((all) => all.map((x) => (x.id === nm.id ? nm : x)))} />
            ))}
            {busy && (
              <div className="flex gap-3" aria-live="polite">
                <NovaMark className="mt-0.5 h-8 w-8" />
                <div className="min-w-0 flex-1 space-y-3">
                  <AgentActivity steps={steps.length ? steps : [{ key: "start", label: "Analyzing request", status: "active", detail: "", t_ms: 0 }]} live defaultOpen={false} />
                  {partial ? <Markdown text={partial} /> : (
                    <div className="flex items-center gap-1.5 pl-1" aria-label="Generating response">
                      {[0, 1, 2].map((i) => <span key={i} className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-blink" style={{ animationDelay: `${i * 180}ms` }} />)}
                    </div>
                  )}
                </div>
              </div>
            )}
            {failed && !busy && (
              <div role="alert" className="ml-11 flex flex-wrap items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200">
                <AlertCircle className="h-4 w-4 shrink-0" /><span className="flex-1">{failed.msg}</span>
                <Button size="sm" onClick={retry}><RotateCcw className="h-3.5 w-3.5" />Retry</Button>
              </div>
            )}
          </div>
          <div ref={bottom} />
        </div>
      </div>
      <div className="border-t border-slate-200 bg-white/85 px-3 py-3 backdrop-blur sm:px-4 dark:border-slate-800 dark:bg-slate-950/70">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-card focus-within:border-brand-300 focus-within:ring-4 focus-within:ring-brand-500/10 dark:border-slate-700 dark:bg-slate-900">
            <label htmlFor="composer" className="sr-only">Message the NovaTech Solutions assistant</label>
            <textarea id="composer" ref={ta} rows={1} value={input} maxLength={4000} disabled={busy}
              onChange={(e) => { setInput(e.target.value); e.target.style.height = "auto"; e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px"; }}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder={me.is_guest ? "Ask about NovaTech's products, offices or public information…" : "Ask about policies, projects, people or data — or ask me to do something…"}
              className="max-h-40 flex-1 resize-none bg-transparent px-2 py-1.5 text-[14.5px] placeholder:text-slate-400 focus:outline-none disabled:opacity-60" />
            {busy ? (
              <button onClick={() => abort.current?.abort()} aria-label="Stop generating"
                className="focus-ring flex h-9 w-9 items-center justify-center rounded-xl bg-slate-800 text-white hover:bg-slate-700 dark:bg-slate-700"><Square className="h-3.5 w-3.5 fill-current" /></button>
            ) : (
              <button onClick={() => send()} disabled={!input.trim()} aria-label="Send message"
                className="focus-ring flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white transition hover:bg-brand-700 disabled:bg-slate-200 disabled:text-slate-400 dark:disabled:bg-slate-800">
                <ArrowUp className="h-4 w-4" />
              </button>
            )}
          </div>
          <p className="mt-1.5 text-center text-[11px] text-slate-400">
            {me.is_guest ? "Guest Mode · public information only · conversations end when you sign out"
              : `${me.full_name} · ${me.role_name} · ${me.clearance.toLowerCase()} clearance — answers use only data you're authorized to access.`}
          </p>
        </div>
      </div>
    </div>
  );
}

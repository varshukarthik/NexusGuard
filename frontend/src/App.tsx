import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import ContextPanel from "./components/ContextPanel";
import DocumentDrawer from "./components/DocumentDrawer";
import Sidebar from "./components/Sidebar";
import Splash from "./components/Splash";
import Topbar from "./components/Topbar";
import { api, hasToken, setToken, setUnauthorizedHandler } from "./lib/api";
import { Ctx } from "./lib/app";
import type { Me, Page } from "./lib/types";
import Chat from "./pages/Chat";
import Documents from "./pages/Documents";
import LandingPage from "./pages/LandingPage";
import Login from "./pages/Login";
import Tasks from "./pages/Tasks";
import { Spinner, Toast } from "./lib/ui";

// Heavier, less frequently used pages are code-split so sign-in and chat load fast.
const Admin = lazy(() => import("./pages/Admin"));
const Approvals = lazy(() => import("./pages/Approvals"));
const AuditLogs = lazy(() => import("./pages/AuditLogs"));
const PolicyLab = lazy(() => import("./pages/PolicyLab"));
const SecurityCenter = lazy(() => import("./pages/SecurityCenter"));
const Settings = lazy(() => import("./pages/Settings"));
const WorkMode = lazy(() => import("./pages/WorkMode"));

/** Pages a principal may open. The server enforces the same rules — this only avoids dead ends in the UI. */
export function allowedPages(me: Me): Page[] {
  if (me.is_guest) return ["chat", "documents"];
  const pages: Page[] = ["chat", "work", "tasks", "approvals", "documents", "security", "audit", "lab", "settings"];
  if (me.permissions.includes("admin:dashboard")) pages.splice(7, 0, "admin");
  return pages;
}

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [booting, setBooting] = useState(hasToken());
  const [authView, setAuthView] = useState<"landing" | "login">("landing");
  const [page, setPage] = useState<Page>("chat");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [chatKey, setChatKey] = useState(0);
  const [docId, setDocId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; kind: "ok" | "err" } | null>(null);
  const [version, setVersion] = useState(0);
  const [panel, setPanel] = useState(() => window.innerWidth > 1280);
  const [navOpen, setNavOpen] = useState(false);

  const refreshMe = useCallback(async () => {
    try { setMe(await api.get<Me>("/users/me")); } catch { setMe(null); setToken(null); } finally { setBooting(false); }
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => { setToken(null); setMe(null); });
    if (hasToken()) refreshMe();
  }, [refreshMe]);

  useEffect(() => {
    document.title = me
      ? (me.is_guest ? "Guest Mode · Nova Solutions" : "Nova Solutions — Enterprise Intelligence Platform")
      : (authView === "login" ? "Sign in · Nova Solutions" : "Nova Solutions — Enterprise Digital Solutions");
  }, [me, authView]);

  const notify = useCallback((msg: string, kind: "ok" | "err" = "ok") => setToast({ msg, kind }), []);

  const switchUser = useCallback(async (email: string) => {
    try { await api.post("/auth/logout"); } catch { /* ignore */ }
    const r = await api.post<{ token: string }>("/auth/sso/demo", { email });
    setToken(r.token);
    setConversationId(null);
    setChatKey((k) => k + 1);
    setPage("chat");
    await refreshMe();
    setVersion((v) => v + 1);
  }, [refreshMe]);

  const go = useCallback((p: Page) => { setPage(p); setNavOpen(false); }, []);

  if (booting) return <Splash />;
  if (!me) {
    if (authView === "login") {
      return (
        <Login
          onBack={() => setAuthView("landing")}
          onLoggedIn={() => {
            setBooting(true);
            setPage("chat");
            setConversationId(null);
            refreshMe();
          }}
        />
      );
    }
    return <LandingPage onSignIn={() => setAuthView("login")} />;
  }

  const pages = allowedPages(me);
  const current = pages.includes(page) ? page : "chat";
  const ctx = {
    me, refreshMe, notify, openDoc: setDocId, go, switchUser,
    can: (p: string) => me.permissions.includes(p), bump: () => setVersion((v) => v + 1), version,
  };
  const newChat = () => { setConversationId(null); setChatKey((k) => k + 1); go("chat"); };
  const signOut = async () => {
    try { await api.post("/auth/logout"); } catch { /* */ }
    setToken(null); setMe(null); setConversationId(null); setAuthView("landing");
  };

  return (
    <Ctx.Provider value={ctx}>
      <div className="flex h-full overflow-hidden">
        <Sidebar page={current} pages={pages} setPage={go} conversationId={conversationId} mobileOpen={navOpen}
          onCloseMobile={() => setNavOpen(false)}
          openConversation={(id) => { setConversationId(id); go("chat"); }} newChat={newChat}
          onDeleted={(id) => { if (id === conversationId) newChat(); }} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar page={current} panel={panel} togglePanel={() => setPanel((p) => !p)} onMenu={() => setNavOpen(true)}
            onSignOut={signOut} />
          <div className="flex min-h-0 flex-1">
            <main className="min-w-0 flex-1 overflow-y-auto scroll-thin" id="main">
              <Suspense fallback={<div className="flex justify-center p-20"><Spinner className="h-5 w-5 text-slate-400" /></div>}>
              {current === "work" && <WorkMode />}
              {current === "chat" && <Chat key={`${me.user_id}-${chatKey}`} conversationId={conversationId}
                onConversation={(id) => { setConversationId(id); setVersion((v) => v + 1); }} onNewChat={newChat} />}
              {current === "tasks" && <Tasks />}
              {current === "approvals" && <Approvals />}
              {current === "documents" && <Documents />}
              {current === "security" && <SecurityCenter />}
              {current === "audit" && <AuditLogs />}
              {current === "admin" && <Admin />}
              {current === "lab" && <PolicyLab />}
              {current === "settings" && <Settings />}
              </Suspense>
            </main>
            {panel && <ContextPanel onClose={() => setPanel(false)} />}
          </div>
        </div>
      </div>
      <DocumentDrawer id={docId} onClose={() => setDocId(null)} />
      {toast && <Toast msg={toast.msg} kind={toast.kind} onClose={() => setToast(null)} />}
    </Ctx.Provider>
  );
}

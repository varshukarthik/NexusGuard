import { createContext, useContext } from "react";
import type { Me, Page } from "./types";

export interface AppCtx {
  me: Me;
  refreshMe: () => Promise<void>;
  notify: (msg: string, kind?: "ok" | "err") => void;
  openDoc: (id: string) => void;
  go: (p: Page) => void;
  switchUser: (email: string) => Promise<void>;
  can: (perm: string) => boolean;
  bump: () => void; // signals other views (approvals count, conversations) to refresh
  version: number;
}

export const Ctx = createContext<AppCtx>(null as unknown as AppCtx);
export const useApp = () => useContext(Ctx);

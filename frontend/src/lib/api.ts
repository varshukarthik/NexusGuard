// Thin API client. The browser only ever holds a session token — never an LLM key or any other secret.
const BASE = "/api";
const KEY = "novatech-token";
let token: string | null = null;
try { token = sessionStorage.getItem(KEY) ?? localStorage.getItem(KEY); } catch { /* storage unavailable */ }

let onUnauthorized: () => void = () => {};
export const setUnauthorizedHandler = (fn: () => void) => { onUnauthorized = fn; };

/** remember=true keeps the session across browser restarts (until it expires server-side). */
export function setToken(t: string | null, remember = false) {
  token = t;
  try {
    sessionStorage.removeItem(KEY);
    localStorage.removeItem(KEY);
    if (t) (remember ? localStorage : sessionStorage).setItem(KEY, t);
  } catch { /* ignore */ }
}
export const hasToken = () => !!token;

export class ApiError extends Error {
  status: number;
  code: string;
  extra: Record<string, unknown>;
  constructor(status: number, code: string, message: string, extra: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.extra = extra;
  }
}

const FRIENDLY: Record<number, string> = {
  0: "Can't reach the NovaTech Solutions service. Check your connection and try again.",
  429: "You're sending requests too quickly. Please wait a moment and try again.",
  500: "Something went wrong on our side. Please try again.",
  502: "The service is temporarily unavailable. Please try again shortly.",
  503: "The service is temporarily unavailable. Please try again shortly.",
  504: "The request timed out. Please try again.",
};

function headers(json: boolean): Record<string, string> {
  const h: Record<string, string> = {};
  if (token) h.Authorization = `Bearer ${token}`;
  if (json) h["Content-Type"] = "application/json";
  return h;
}

async function request<T>(method: string, path: string, body?: unknown, isForm = false): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      method, headers: headers(body !== undefined && !isForm),
      body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "network", FRIENDLY[0]);
  }
  let data: any = null;
  try { data = await res.json(); } catch { /* non-JSON */ }
  if (!res.ok) {
    if (res.status === 401 && path !== "/auth/login") onUnauthorized();
    const msg = data?.message ?? FRIENDLY[res.status] ?? `Request failed (${res.status})`;
    throw new ApiError(res.status, data?.error ?? "error", msg, data ?? {});
  }
  return data as T;
}

async function download(path: string): Promise<{ blob: Blob; filename: string }> {
  let res: Response;
  try { res = await fetch(BASE + path, { headers: headers(false) }); } catch { throw new ApiError(0, "network", FRIENDLY[0]); }
  if (!res.ok) throw new ApiError(res.status, "error", FRIENDLY[res.status] ?? "Download failed.");
  const cd = res.headers.get("content-disposition") ?? "";
  const filename = /filename="?([^"]+)"?/.exec(cd)?.[1] ?? "export.md";
  return { blob: await res.blob(), filename };
}

export interface StreamHandlers {
  onStep?: (step: any) => void;
  onDelta?: (text: string) => void;
  onConversation?: (conv: { id: string; title: string }) => void;
}

/** Server-sent events over fetch (POST): live agent activity, progressive answer text, then the final message. */
async function stream<T>(path: string, body: unknown, h: StreamHandlers, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, { method: "POST", headers: headers(true), body: JSON.stringify(body), signal });
  } catch (e: any) {
    if (e?.name === "AbortError") throw new ApiError(499, "aborted", "Stopped.");
    throw new ApiError(0, "network", FRIENDLY[0]);
  }
  if (!res.ok || !res.body) {
    let data: any = null;
    try { data = await res.json(); } catch { /* */ }
    if (res.status === 401) onUnauthorized();
    throw new ApiError(res.status, data?.error ?? "error", data?.message ?? FRIENDLY[res.status] ?? "Request failed.");
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  let final: T | null = null;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const ev = /^event: (.*)$/m.exec(chunk)?.[1];
      const raw = /^data: (.*)$/m.exec(chunk)?.[1];
      if (!ev || raw === undefined) continue;
      const data = JSON.parse(raw);
      if (ev === "step") h.onStep?.(data);
      else if (ev === "delta") h.onDelta?.(data.text);
      else if (ev === "conversation") h.onConversation?.(data);
      else if (ev === "done") final = data as T;
      else if (ev === "error") throw new ApiError(500, data.error ?? "error", data.message ?? FRIENDLY[500]);
    }
  }
  if (!final) throw new ApiError(500, "incomplete", "The response was interrupted. Please retry.");
  return final;
}

export const api = {
  get: <T>(p: string) => request<T>("GET", p),
  post: <T>(p: string, b: unknown = {}) => request<T>("POST", p, b),
  patch: <T>(p: string, b: unknown) => request<T>("PATCH", p, b),
  del: <T>(p: string) => request<T>("DELETE", p),
  upload: <T>(p: string, form: FormData) => request<T>("POST", p, form, true),
  download,
  stream,
};

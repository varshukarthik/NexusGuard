import { ChevronRight, Download, ScrollText, Search } from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/app";
import type { AuditRow } from "../lib/types";
import { Button, Card, ClassBadge, cx, Empty, fmtTime, PageHeader, ResultBadge, RiskBadge, Spinner } from "../lib/ui";

export default function AuditLogs() {
  const { version, me } = useApp();
  const [data, setData] = useState<{ scope: string; total: number; items: AuditRow[] } | null>(null);
  const [q, setQ] = useState("");
  const [user, setUser] = useState("");
  const [pr, setPr] = useState("");
  const [risk, setRisk] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const [limit, setLimit] = useState(100);

  useEffect(() => {
    const t = setTimeout(() => {
      const p = new URLSearchParams({ q, user, permission_result: pr, risk, limit: String(limit) });
      api.get<typeof data>(`/audit-logs?${p}`).then(setData).catch(() => {});
    }, 200);
    return () => clearTimeout(t);
  }, [q, user, pr, risk, limit, version, me.user_id]);

  function exportCsv() {
    if (!data) return;
    const cols: (keyof AuditRow)[] = ["ts", "user_name", "action", "query", "resource", "resource_id", "classification", "permission_result", "tool", "result", "reason", "risk", "session_id", "ip"];
    const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const csv = [cols.join(","), ...data.items.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "novatech-audit-log.csv";
    a.click();
  }

  return (
    <div className="mx-auto max-w-7xl p-6">
      <PageHeader icon={<ScrollText className="h-5 w-5" />} title="Audit Logs"
        subtitle={data?.scope === "self" ? "Showing your own activity. Organisation-wide logs require audit:read_all (Security Admin / Executive)." : "Organisation-wide, append-only record of every request, authorization decision and AI action."}
        actions={<Button onClick={exportCsv}><Download className="h-4 w-4" />Export CSV</Button>} />
      <Card>
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 p-3 dark:border-slate-800">
          <div className="relative min-w-[220px] flex-1"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input className="input pl-9" placeholder="Search action, resource, query, reason" value={q} onChange={(e) => setQ(e.target.value)} /></div>
          {data?.scope !== "self" && <input className="input !w-44" placeholder="User" value={user} onChange={(e) => setUser(e.target.value)} />}
          <select className="input !w-auto" value={pr} onChange={(e) => setPr(e.target.value)}>
            <option value="">All results</option>{["ALLOWED", "DENIED", "BLOCKED", "REDACTED"].map((x) => <option key={x}>{x}</option>)}</select>
          <select className="input !w-auto" value={risk} onChange={(e) => setRisk(e.target.value)}>
            <option value="">All risk</option>{["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((x) => <option key={x}>{x}</option>)}</select>
          {data && <span className="text-xs text-slate-500">{data.total.toLocaleString()} events</span>}
        </div>
        {!data ? <div className="flex justify-center p-10"><Spinner /></div> : data.items.length === 0 ? <Empty icon={<ScrollText className="h-5 w-5" />} title="No events" /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px]">
              <thead className="border-b border-slate-100 dark:border-slate-800"><tr>
                <th className="th w-6" /><th className="th">Timestamp</th><th className="th">User</th><th className="th">Action</th><th className="th">Resource</th>
                <th className="th">Classification</th><th className="th">Permission</th><th className="th">AI tool</th><th className="th">Result</th><th className="th">Risk</th>
              </tr></thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {data.items.map((e) => (
                  <Fragment key={e.id}>
                    <tr onClick={() => setOpen(open === e.id ? null : e.id)} className={cx("cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40", e.risk === "HIGH" || e.risk === "CRITICAL" ? "bg-rose-50/30 dark:bg-rose-500/5" : "")}>
                      <td className="td"><ChevronRight className={cx("h-3.5 w-3.5 text-slate-400 transition", open === e.id && "rotate-90")} /></td>
                      <td className="td whitespace-nowrap text-xs text-slate-500">{fmtTime(e.ts)}</td>
                      <td className="td whitespace-nowrap font-medium">{e.user_name || "—"}</td>
                      <td className="td"><p className="font-mono text-xs">{e.action}</p>{e.query && <p className="max-w-[260px] truncate text-xs text-slate-500">“{e.query}”</p>}</td>
                      <td className="td max-w-[220px]"><p className="truncate">{e.resource || "—"}</p>{e.resource_id && <p className="font-mono text-[10.5px] text-slate-400">{e.resource_id}</p>}</td>
                      <td className="td">{e.classification ? <ClassBadge level={e.classification} size="xs" /> : <span className="text-slate-300">—</span>}</td>
                      <td className="td"><ResultBadge value={e.permission_result} /></td>
                      <td className="td font-mono text-[11px] text-slate-500">{e.tool || "—"}</td>
                      <td className="td text-xs font-medium">{e.result}</td>
                      <td className="td"><RiskBadge risk={e.risk} /></td>
                    </tr>
                    {open === e.id && (
                      <tr className="bg-slate-50/70 dark:bg-slate-900/60"><td colSpan={10} className="px-10 py-3 text-xs">
                        <div className="grid gap-x-8 gap-y-1 sm:grid-cols-2">
                          <p><span className="text-slate-500">Reason:</span> {e.reason || "—"}</p>
                          <p><span className="text-slate-500">Session / IP:</span> <span className="font-mono">{e.session_id || "—"} · {e.ip || "—"}</span></p>
                          <p><span className="text-slate-500">Request ID:</span> <span className="font-mono">{e.request_id || "—"}</span></p>
                          <p><span className="text-slate-500">Event ID:</span> <span className="font-mono">{e.id}</span></p>
                        </div>
                        {Object.keys(e.details ?? {}).length > 0 && <pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-slate-950 p-3 font-mono text-[11px] text-slate-200 scroll-thin">{JSON.stringify(e.details, null, 2)}</pre>}
                      </td></tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && data.items.length < data.total && (
          <div className="border-t border-slate-100 p-3 text-center dark:border-slate-800"><Button size="sm" onClick={() => setLimit(limit + 100)}>Load more</Button></div>
        )}
      </Card>
    </div>
  );
}

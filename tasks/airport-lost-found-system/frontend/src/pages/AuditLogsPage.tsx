import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { PageHeader } from "../components/PageHeader";
import type { AuditLog } from "../types";

export function AuditLogsPage() {
  const { data = [] } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: async () => (await api.get<AuditLog[]>("/audit-logs")).data,
  });

  return (
    <section className="space-y-4">
      <PageHeader title="Audit Logs" kicker="Security and operational review" />
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
            <tr>
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Entity</th>
              <th className="px-4 py-3">Actor</th>
              <th className="px-4 py-3">Severity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.map((log) => (
              <tr key={log.id}>
                <td className="px-4 py-3 text-slate-500">{new Date(log.created_at).toLocaleString()}</td>
                <td className="px-4 py-3 font-medium text-slate-950">{log.action}</td>
                <td className="px-4 py-3 text-slate-600">{log.entity_type} {log.entity_id ? `#${log.entity_id}` : ""}</td>
                <td className="px-4 py-3 text-slate-600">{log.actor_role ?? "system"}</td>
                <td className="px-4 py-3"><Badge value={log.severity} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

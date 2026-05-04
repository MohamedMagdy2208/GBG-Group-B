import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Activity, Database, RefreshCw, ServerCog, ShieldCheck } from "lucide-react";
import type React from "react";
import { useState } from "react";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { useToast } from "../components/Toast";
import type { BackgroundJob, DeepHealth, OutboxEvent, ProviderStatus } from "../types";

function describeError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.message) return error.message;
  }
  return fallback;
}

export function AdminOperationsPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [lastAdminAction, setLastAdminAction] = useState<Record<string, unknown> | null>(null);
  const { data: jobs = [] } = useQuery({
    queryKey: ["admin-jobs"],
    queryFn: async () => (await api.get<BackgroundJob[]>("/admin/jobs")).data,
  });
  const { data: outbox = [] } = useQuery({
    queryKey: ["admin-outbox"],
    queryFn: async () => (await api.get<OutboxEvent[]>("/admin/outbox")).data,
  });
  const { data: health } = useQuery({
    queryKey: ["deep-health"],
    queryFn: async () => (await api.get<DeepHealth>("/health/ready/deep")).data,
    refetchInterval: 30000,
  });
  const { data: providers } = useQuery({
    queryKey: ["provider-status"],
    queryFn: async () => (await api.get<ProviderStatus>("/admin/system/providers")).data,
  });

  const retryJob = useMutation({
    mutationFn: async (jobId: number) => (await api.post(`/admin/jobs/${jobId}/retry`)).data,
    onSuccess: (_d, jobId) => {
      queryClient.invalidateQueries({ queryKey: ["admin-jobs"] });
      toast.push(`Job #${jobId} re-queued.`, "success");
    },
    onError: (error, jobId) => toast.push(describeError(error, `Could not retry job #${jobId}.`), "error"),
  });
  const adminAction = useMutation({
    mutationFn: async ({ endpoint }: { endpoint: string; label: string }) => (await api.post<Record<string, unknown>>(endpoint)).data,
    onSuccess: (data, variables) => {
      setLastAdminAction(data);
      queryClient.invalidateQueries({ queryKey: ["deep-health"] });
      queryClient.invalidateQueries({ queryKey: ["provider-status"] });
      queryClient.invalidateQueries({ queryKey: ["admin-jobs"] });
      queryClient.invalidateQueries({ queryKey: ["admin-outbox"] });
      queryClient.invalidateQueries({ queryKey: ["matches"] });
      toast.push(`${variables.label} completed.`, "success");
    },
    onError: (error, variables) => toast.push(describeError(error, `${variables.label} failed.`), "error"),
  });

  const pendingJobs = jobs.filter((job) => job.status === "pending" || job.status === "failed").length;
  const deadJobs = jobs.filter((job) => job.status === "dead_letter").length;
  const pendingOutbox = outbox.filter((event) => event.status === "pending" || event.status === "failed").length;
  const failedChecks = Object.values(health?.checks ?? {}).filter((check) => check.status === "failed").length;

  return (
    <section className="space-y-5">
      <PageHeader title="Operations" kicker="Pilot readiness" />

      <div className="grid gap-3 md:grid-cols-4">
        <StatCard label="Ready State" value={health?.status ?? "checking"} icon={ShieldCheck} accent={health?.status === "ready" ? "radar" : "amber"} />
        <StatCard label="Failed Checks" value={failedChecks} icon={Activity} accent={failedChecks ? "rose" : "sky"} />
        <StatCard label="Queue Backlog" value={pendingJobs} icon={ServerCog} accent={pendingJobs ? "amber" : "radar"} />
        <StatCard label="Outbox Backlog" value={pendingOutbox} icon={Database} accent={pendingOutbox ? "amber" : "radar"} />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-950">Dependency Health</h2>
          </div>
          <div className="divide-y divide-slate-100">
            {Object.entries(health?.checks ?? {}).map(([name, check]) => (
              <div key={name} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                <div>
                  <p className="font-medium capitalize text-slate-950">{name.replaceAll("_", " ")}</p>
                  <p className="text-xs text-slate-500">{compactJson(check)}</p>
                </div>
                <Badge value={String(check.status ?? "unknown")} />
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-950">Configured Providers</h2>
          </div>
          <div className="grid gap-3 p-4 text-sm sm:grid-cols-2">
            <ProviderLine label="Environment" value={providers?.environment ?? "-"} />
            <ProviderLine label="Azure Mode" value={providers?.use_azure_services ? "enabled" : "local"} />
            <ProviderLine label="Cache" value={providers?.cache_backend ?? "-"} />
            <ProviderLine label="Graph RAG" value={providers?.graph_rag_provider ?? "-"} />
            {Object.entries(providers?.azure ?? {})
              .filter(([key]) => key !== "openai_routes")
              .map(([key, value]) => (
              <ProviderLine key={key} label={key.replaceAll("_", " ")} value={value ? "configured" : "missing"} tone={value ? "normal" : "warning"} />
            ))}
            {Object.entries(providers?.azure.openai_routes ?? {}).map(([key, value]) => (
              <ProviderLine key={`openai-${key}`} label={`OpenAI ${key}`} value={value ?? "missing"} tone={value ? "normal" : "warning"} />
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-950">Search And Matching Tools</h2>
        </div>
        <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-5">
          <AdminActionButton label="Recreate Index" endpoint="/admin/search/recreate-index" mutation={adminAction} />
          <AdminActionButton label="Reindex Lost" endpoint="/admin/search/reindex-lost-reports" mutation={adminAction} />
          <AdminActionButton label="Reindex Found" endpoint="/admin/search/reindex-found-items" mutation={adminAction} />
          <AdminActionButton label="Rebuild All" endpoint="/admin/search/reindex-all?recreate_index=true" mutation={adminAction} />
          <AdminActionButton label="Rerun Matching" endpoint="/admin/matching/rerun-all" mutation={adminAction} />
        </div>
        {lastAdminAction ? (
          <div className="border-t border-slate-100 px-4 py-3 text-xs text-slate-600">
            <span className="font-semibold text-slate-950">Last result:</span> {compactAction(lastAdminAction)}
          </div>
        ) : null}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <OperationsTable
          title="Background Jobs"
          rows={jobs}
          columns={["job_type", "status", "attempts", "updated_at"]}
          renderActions={(row) =>
            row.status === "failed" || row.status === "dead_letter" ? (
              <button
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                onClick={() => retryJob.mutate(row.id)}
              >
                <RefreshCw className="h-3 w-3" />
                Retry
              </button>
            ) : null
          }
          deadCount={deadJobs}
        />
        <OperationsTable title="Outbox Events" rows={outbox} columns={["event_type", "status", "attempts", "updated_at"]} />
      </div>
    </section>
  );
}

function AdminActionButton({
  label,
  endpoint,
  mutation,
}: {
  label: string;
  endpoint: string;
  mutation: {
    isPending: boolean;
    variables?: { endpoint: string; label: string };
    mutate: (payload: { endpoint: string; label: string }) => void;
  };
}) {
  const isThisRunning = mutation.isPending && mutation.variables?.endpoint === endpoint;
  return (
    <button
      className="focus-ring inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
      disabled={mutation.isPending}
      onClick={() => mutation.mutate({ endpoint, label })}
    >
      <RefreshCw className={`h-4 w-4 ${isThisRunning ? "animate-spin" : ""}`} />
      {isThisRunning ? "Running..." : label}
    </button>
  );
}

function ProviderLine({ label, value, tone = "normal" }: { label: string; value: string; tone?: "normal" | "warning" }) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2">
      <span className="capitalize text-slate-500">{label}</span>
      <Badge value={tone === "warning" ? "warning" : value} />
    </div>
  );
}

function OperationsTable<T extends { id: number; status: string; attempts: number; updated_at: string; last_error?: string | null }>(
  props: {
    title: string;
    rows: T[];
    columns: Array<keyof T & string>;
    renderActions?: (row: T) => React.ReactNode;
    deadCount?: number;
  },
) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-950">{props.title}</h2>
        {props.deadCount ? <Badge value="dead_letter" /> : null}
      </div>
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            {props.columns.map((column) => (
              <th key={column} className="px-4 py-3 capitalize">
                {column.replaceAll("_", " ")}
              </th>
            ))}
            <th className="px-4 py-3">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {props.rows.slice(0, 12).map((row) => (
            <tr key={row.id}>
              {props.columns.map((column) => (
                <td key={column} className="px-4 py-3 text-slate-600">
                  {column === "status" ? <Badge value={String(row[column])} /> : formatCell(row[column])}
                </td>
              ))}
              <td className="px-4 py-3">{props.renderActions?.(row)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(value: unknown) {
  if (typeof value === "string" && value.includes("T")) {
    return new Date(value).toLocaleString();
  }
  return String(value ?? "-");
}

function compactJson(value: Record<string, unknown>) {
  const entries = Object.entries(value).filter(([key]) => key !== "details");
  return entries
    .map(([key, val]) => `${key}: ${String(val)}`)
    .slice(0, 4)
    .join(" | ");
}

function compactAction(value: Record<string, unknown>) {
  return JSON.stringify(value, (_key, val) => (Array.isArray(val) && val.length > 3 ? [...val.slice(0, 3), "..."] : val));
}

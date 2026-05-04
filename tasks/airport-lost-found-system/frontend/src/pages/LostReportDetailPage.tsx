import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Loader2 } from "lucide-react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { ImageComparePanel } from "../components/ImageComparePanel";
import { PageHeader } from "../components/PageHeader";
import { useToast } from "../components/Toast";
import type { LostReport, MatchCandidate } from "../types";

function describeError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.message) return error.message;
  }
  return fallback;
}

export function LostReportDetailPage() {
  const { id } = useParams();
  const client = useQueryClient();
  const toast = useToast();
  const { data: report, isLoading } = useQuery({
    queryKey: ["lost-report", id],
    queryFn: async () => (await api.get<LostReport>(`/lost-reports/${id}`)).data,
  });
  const runMatching = useMutation({
    mutationFn: async () => (await api.post<MatchCandidate[]>(`/lost-reports/${id}/run-matching`)).data,
    onSuccess: (data) => {
      client.invalidateQueries({ queryKey: ["matches"] });
      toast.push(`Matching ran — ${Array.isArray(data) ? data.length : 0} candidates returned.`, "success");
    },
    onError: (error) => toast.push(describeError(error, "Could not run matching."), "error"),
  });
  if (isLoading) return <p className="text-sm text-slate-500">Loading lost report...</p>;
  if (!report) return <p className="text-sm text-slate-500">Lost report not available.</p>;
  return (
    <section className="space-y-4">
      <PageHeader
        title={report.item_title}
        kicker={report.report_code}
        action={
          <button
            onClick={() => runMatching.mutate()}
            disabled={runMatching.isPending}
            className="focus-ring inline-flex items-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {runMatching.isPending ? <Loader2 size={14} className="animate-spin" /> : null}
            {runMatching.isPending ? "Running..." : "Run matching"}
          </button>
        }
      />
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <Badge value={report.status} />
        <p className="mt-4 text-sm leading-6 text-slate-700">{report.raw_description}</p>
        <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div><dt className="font-semibold text-slate-500">Category</dt><dd>{report.category ?? "—"}</dd></div>
          <div><dt className="font-semibold text-slate-500">Color</dt><dd>{report.color ?? "—"}</dd></div>
          <div><dt className="font-semibold text-slate-500">Location</dt><dd>{report.lost_location ?? "—"}</dd></div>
          <div><dt className="font-semibold text-slate-500">Flight</dt><dd>{report.flight_number ?? "—"}</dd></div>
        </dl>
      </div>
      {report.proof_blob_url ? (
        <ImageComparePanel
          lostImageUrl={report.proof_blob_url}
          foundImageUrl={null}
          lostLabel={`Lost report ${report.report_code}`}
          foundLabel="Run matching to compare against found items"
        />
      ) : null}
    </section>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { PageHeader } from "../components/PageHeader";
import type { LostReport, MatchCandidate } from "../types";

export function LostReportDetailPage() {
  const { id } = useParams();
  const client = useQueryClient();
  const { data: report } = useQuery({
    queryKey: ["lost-report", id],
    queryFn: async () => (await api.get<LostReport>(`/lost-reports/${id}`)).data,
  });
  const runMatching = useMutation({
    mutationFn: async () => (await api.post<MatchCandidate[]>(`/lost-reports/${id}/run-matching`)).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ["matches"] }),
  });
  if (!report) return null;
  return (
    <section className="space-y-4">
      <PageHeader title={report.item_title} kicker={report.report_code} action={<button onClick={() => runMatching.mutate()} className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white">Run matching</button>} />
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <Badge value={report.status} />
        <p className="mt-4 text-sm leading-6 text-slate-700">{report.raw_description}</p>
        <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div><dt className="font-semibold text-slate-500">Category</dt><dd>{report.category}</dd></div>
          <div><dt className="font-semibold text-slate-500">Color</dt><dd>{report.color}</dd></div>
          <div><dt className="font-semibold text-slate-500">Location</dt><dd>{report.lost_location}</dd></div>
          <div><dt className="font-semibold text-slate-500">Flight</dt><dd>{report.flight_number ?? "None"}</dd></div>
        </dl>
      </div>
    </section>
  );
}

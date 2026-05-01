import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { PageHeader } from "../components/PageHeader";
import { ScoreBreakdown } from "../components/ScoreBreakdown";
import type { ClaimVerification, GraphContext, MatchCandidate } from "../types";

export function MatchReviewPage() {
  const client = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("pending");
  const [confidenceFilter, setConfidenceFilter] = useState("all");
  const { data = [] } = useQuery({
    queryKey: ["matches"],
    queryFn: async () => (await api.get<MatchCandidate[]>("/matches")).data,
  });
  const { data: claims = [] } = useQuery({
    queryKey: ["claim-verifications"],
    queryFn: async () => (await api.get<ClaimVerification[]>("/claim-verifications")).data,
  });
  const action = useMutation({
    mutationFn: async ({ id, verb }: { id: number; verb: "approve" | "reject" | "needs-more-info" }) =>
      (await api.post(`/matches/${id}/${verb}`, { review_notes: "Reviewed from dashboard" })).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ["matches"] }),
  });
  const createClaim = useMutation({
    mutationFn: async (id: number) => (await api.post(`/matches/${id}/claim-verification`, {})).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ["claim-verifications"] }),
  });
  const release = useMutation({
    mutationFn: async (claim: ClaimVerification) =>
      (await api.post(`/matches/${claim.match_candidate_id}/release`, {
        released_to_name: claim.match_candidate?.lost_report?.contact_email ?? "Verified passenger",
        released_to_contact: claim.match_candidate?.lost_report?.contact_phone,
        release_checklist_json: {
          identity_checked: true,
          proof_checked: true,
          passenger_signed: true,
          custody_updated: true,
        },
        review_notes: "Released from match review after checklist completion.",
      })).data,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["matches"] });
      client.invalidateQueries({ queryKey: ["claim-verifications"] });
    },
  });
  const filteredMatches = data.filter((match) => {
    const statusMatches = statusFilter === "all" || match.status === statusFilter;
    const confidenceMatches = confidenceFilter === "all" || match.confidence_level === confidenceFilter;
    return statusMatches && confidenceMatches;
  });
  const highRiskCount = data.filter((match) => ["high_value", "sensitive", "dangerous"].includes(match.found_item?.risk_level ?? "")).length;
  return (
    <section>
      <PageHeader title="Match Review" kicker="Manual approval required" action={<button onClick={() => api.post("/matches/run").then(() => client.invalidateQueries({ queryKey: ["matches"] }))} className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white">Run all</button>} />
      <div className="mb-4 grid gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm lg:grid-cols-[1fr_auto_auto]">
        <div>
          <p className="text-sm font-semibold text-slate-950">{filteredMatches.length} matches in view</p>
          <p className="mt-1 text-xs text-slate-500">{highRiskCount} candidates require extra risk attention.</p>
        </div>
        <select className="focus-ring rounded-lg border border-slate-200 px-3 py-2 text-sm" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="Status filter">
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="needs_more_info">Needs more info</option>
          <option value="rejected">Rejected</option>
          <option value="all">All statuses</option>
        </select>
        <select className="focus-ring rounded-lg border border-slate-200 px-3 py-2 text-sm" value={confidenceFilter} onChange={(event) => setConfidenceFilter(event.target.value)} aria-label="Confidence filter">
          <option value="all">All confidence</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>
      <div className="grid gap-4">
        {filteredMatches.map((match) => {
          const claim = claims.find((item) => item.match_candidate_id === match.id);
          const isClosed = match.status === "approved" || match.status === "rejected";
          return (
          <article key={match.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="grid gap-4 lg:grid-cols-[1fr_260px_220px]">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-semibold text-slate-950">{match.lost_report?.item_title} {" -> "} {match.found_item?.item_title}</h2>
                  <Badge value={match.confidence_level} />
                  <Badge value={match.status} />
                  <Badge value={match.found_item?.risk_level} />
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-600">{match.ai_match_summary}</p>
                {claim ? (
                  <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                    Claim verification: <b>{claim.status}</b>, fraud score <b>{claim.fraud_score.toFixed(0)}/100</b>
                  </div>
                ) : null}
                <GraphEvidencePanel matchId={match.id} />
                <p className="mt-2 text-xs font-semibold text-amber-700">Staff approval is required before release.</p>
              </div>
              <ScoreBreakdown match={match} />
              <div className="grid content-start gap-2">
                <p className="text-3xl font-semibold text-slate-950">{match.match_score.toFixed(0)}%</p>
                <button disabled={isClosed} onClick={() => action.mutate({ id: match.id, verb: "approve" })} className="rounded-lg bg-radar px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40">Approve</button>
                <button onClick={() => createClaim.mutate(match.id)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-800">Create claim check</button>
                <button onClick={() => claim && release.mutate(claim)} disabled={claim?.status !== "approved"} className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40">Release</button>
                <button disabled={isClosed} onClick={() => action.mutate({ id: match.id, verb: "needs-more-info" })} className="rounded-lg border border-amber-300 px-3 py-2 text-sm font-semibold text-amber-800 disabled:cursor-not-allowed disabled:opacity-40">More info</button>
                <button disabled={isClosed} onClick={() => action.mutate({ id: match.id, verb: "reject" })} className="rounded-lg border border-rose-300 px-3 py-2 text-sm font-semibold text-rose-800 disabled:cursor-not-allowed disabled:opacity-40">Reject</button>
              </div>
            </div>
          </article>
        )})}
        {filteredMatches.length === 0 ? (
          <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
            No matches meet the current filters.
          </div>
        ) : null}
      </div>
    </section>
  );
}

function GraphEvidencePanel({ matchId }: { matchId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["graph-rag", "match", matchId],
    queryFn: async () => (await api.get<GraphContext>(`/graph-rag/matches/${matchId}`)).data,
  });

  if (isLoading) {
    return <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-500">Loading graph evidence...</div>;
  }
  if (!data) return null;

  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-semibold text-slate-950">Graph RAG evidence</p>
        <Badge value={data.provider} />
        <span className="text-xs font-medium text-slate-500">{data.nodes.length} nodes / {data.edges.length} edges</span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{data.generated_summary}</p>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <MiniList title="Evidence" rows={data.evidence} />
        <MiniList title="Risk signals" rows={data.risk_signals} tone="risk" />
      </div>
    </div>
  );
}

function MiniList({ title, rows, tone = "normal" }: { title: string; rows: string[]; tone?: "normal" | "risk" }) {
  return (
    <div>
      <p className={`text-xs font-semibold uppercase tracking-normal ${tone === "risk" ? "text-rose-700" : "text-slate-500"}`}>{title}</p>
      <ul className="mt-1 space-y-1 text-xs leading-5 text-slate-600">
        {rows.length ? rows.slice(0, 4).map((row) => <li key={row}>{row}</li>) : <li>None detected</li>}
      </ul>
    </div>
  );
}

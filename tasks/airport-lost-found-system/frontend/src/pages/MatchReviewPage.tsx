import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import axios from "axios";
import { Check, Search, Sparkles, X } from "lucide-react";
import { api } from "../api/client";
import { StatusPill } from "../components/ui/Pill";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Section } from "../components/ui/Section";
import { SegmentedControl } from "../components/ui/SegmentedControl";
import { EmptyState } from "../components/EmptyState";
import { GraphCanvas } from "../components/GraphCanvas";
import { ImageComparePanel } from "../components/ImageComparePanel";
import { MatchEvidencePanel } from "../components/MatchEvidencePanel";
import { ScoreBreakdown } from "../components/ScoreBreakdown";
import { SkeletonRows } from "../components/Skeleton";
import { useToast } from "../components/Toast";
import type { ClaimVerification, GraphContext, MatchCandidate } from "../types";

function describeError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.message) return error.message;
  }
  return fallback;
}

export function MatchReviewPage() {
  const client = useQueryClient();
  const toast = useToast();
  const [statusFilter, setStatusFilter] = useState("pending");
  const [confidenceFilter, setConfidenceFilter] = useState("all");
  const [busyMatchId, setBusyMatchId] = useState<number | null>(null);
  const { data = [], isLoading } = useQuery({
    queryKey: ["matches"],
    queryFn: async () => (await api.get<MatchCandidate[]>("/matches")).data,
  });
  const { data: claims = [] } = useQuery({
    queryKey: ["claim-verifications"],
    queryFn: async () => (await api.get<ClaimVerification[]>("/claim-verifications")).data,
  });
  const action = useMutation({
    mutationFn: async ({ id, verb }: { id: number; verb: "approve" | "reject" | "needs-more-info" }) => {
      setBusyMatchId(id);
      return (await api.post(`/matches/${id}/${verb}`, { review_notes: "Reviewed from dashboard" })).data;
    },
    onSuccess: (_data, variables) => {
      client.invalidateQueries({ queryKey: ["matches"] });
      const labels = { approve: "approved", reject: "rejected", "needs-more-info": "marked as needs more info" } as const;
      toast.push(`Match #${variables.id} ${labels[variables.verb]}.`, "success");
      // If the user was on the Pending filter, switch to All so they can see the change.
      if (statusFilter === "pending" && (variables.verb === "approve" || variables.verb === "reject")) {
        setStatusFilter("all");
      }
    },
    onError: (error, variables) => {
      toast.push(describeError(error, `Could not ${variables.verb} match #${variables.id}.`), "error");
    },
    onSettled: () => setBusyMatchId(null),
  });
  const createClaim = useMutation({
    mutationFn: async (id: number) => {
      setBusyMatchId(id);
      return (await api.post(`/matches/${id}/claim-verification`, {})).data;
    },
    onSuccess: (data) => {
      client.invalidateQueries({ queryKey: ["claim-verifications"] });
      const blocked = data?.status === "blocked";
      toast.push(
        blocked
          ? `Claim verification opened but is blocked by fraud rules. Review evidence before approving.`
          : `Claim verification opened. Submit evidence and approve to enable release.`,
        blocked ? "info" : "success",
      );
    },
    onError: (error) => {
      toast.push(describeError(error, "Could not create claim verification."), "error");
    },
    onSettled: () => setBusyMatchId(null),
  });
  const release = useMutation({
    mutationFn: async (claim: ClaimVerification) => {
      setBusyMatchId(claim.match_candidate_id);
      return (await api.post(`/matches/${claim.match_candidate_id}/release`, {
        released_to_name: claim.match_candidate?.lost_report?.contact_email ?? "Verified passenger",
        released_to_contact: claim.match_candidate?.lost_report?.contact_phone,
        release_checklist_json: {
          identity_checked: true,
          proof_checked: true,
          passenger_signed: true,
          custody_updated: true,
        },
        review_notes: "Released from match review after checklist completion.",
      })).data;
    },
    onSuccess: (_data, claim) => {
      client.invalidateQueries({ queryKey: ["matches"] });
      client.invalidateQueries({ queryKey: ["claim-verifications"] });
      toast.push(`Item released for match #${claim.match_candidate_id}.`, "success");
      if (statusFilter === "pending") setStatusFilter("all");
    },
    onError: (error) => {
      toast.push(describeError(error, "Could not release item."), "error");
    },
    onSettled: () => setBusyMatchId(null),
  });
  const runAll = useMutation({
    mutationFn: async () => (await api.post("/matches/run")).data,
    onSuccess: (data: MatchCandidate[]) => {
      client.invalidateQueries({ queryKey: ["matches"] });
      toast.push(`Re-ran matching across all open reports — ${Array.isArray(data) ? data.length : 0} candidates returned.`, "success");
    },
    onError: (error) => toast.push(describeError(error, "Could not run matching."), "error"),
  });
  const filteredMatches = data.filter((match) => {
    const statusMatches = statusFilter === "all" || match.status === statusFilter;
    const confidenceMatches = confidenceFilter === "all" || match.confidence_level === confidenceFilter;
    return statusMatches && confidenceMatches;
  });
  const highRiskCount = data.filter((match) => ["high_value", "sensitive", "dangerous"].includes(match.found_item?.risk_level ?? "")).length;
  return (
    <Section
      kicker="Manual approval required"
      title="Match Review"
      description="Each candidate combines hybrid search, AI re-rank, image similarity, and evidence highlighting. Approve, reject, or request more info — every decision is audited."
      action={
        <Button variant="primary" onClick={() => runAll.mutate()} loading={runAll.isPending} leftIcon={<Sparkles className="h-4 w-4" />}>
          {runAll.isPending ? "Running..." : "Run all"}
        </Button>
      }
    >
      <Card className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-display text-lg font-semibold tracking-tight text-ink-900">
            {filteredMatches.length} <span className="font-normal text-ink-500">{filteredMatches.length === 1 ? "match" : "matches"} in view</span>
          </p>
          <p className="mt-0.5 text-xs text-ink-500">
            {highRiskCount} candidate{highRiskCount === 1 ? "" : "s"} flagged as high-value, sensitive, or dangerous.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <SegmentedControl
            value={statusFilter}
            onChange={setStatusFilter}
            ariaLabel="Status filter"
            options={[
              { value: "pending", label: "Pending" },
              { value: "approved", label: "Approved" },
              { value: "needs_more_info", label: "Need info" },
              { value: "rejected", label: "Rejected" },
              { value: "all", label: "All" },
            ]}
          />
          <SegmentedControl
            value={confidenceFilter}
            onChange={setConfidenceFilter}
            ariaLabel="Confidence filter"
            options={[
              { value: "all", label: "All conf." },
              { value: "high", label: "High" },
              { value: "medium", label: "Medium" },
              { value: "low", label: "Low" },
            ]}
          />
        </div>
      </Card>
      <div className="grid gap-5">
        {filteredMatches.map((match) => {
          const claim = claims.find((item) => item.match_candidate_id === match.id);
          const isClosed = match.status === "approved" || match.status === "rejected";
          const score = Math.round(match.match_score);
          const scoreTone = score >= 85 ? "text-success-700" : score >= 70 ? "text-warn-700" : "text-ink-600";
          const ringTone = score >= 85 ? "ring-success-500/30" : score >= 70 ? "ring-warn-500/30" : "ring-ink-300";
          return (
            <Card key={match.id} className="overflow-hidden p-0" padded={false}>
              {/* Header strip */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink-200/60 bg-ink-50/60 px-5 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-display text-base font-semibold tracking-tight text-ink-900">
                    {match.lost_report?.item_title} <span className="font-normal text-ink-400">→</span> {match.found_item?.item_title}
                  </h2>
                  <StatusPill value={match.confidence_level} />
                  <StatusPill value={match.status} />
                  <StatusPill value={match.found_item?.risk_level} />
                </div>
                <div className={`grid h-12 w-12 place-items-center rounded-2xl bg-white ring-2 ${ringTone}`}>
                  <span className={`font-display text-lg font-bold tabular-nums ${scoreTone}`}>{score}</span>
                </div>
              </div>

              {/* Body */}
              <div className="grid gap-5 p-5 lg:grid-cols-[1fr_280px]">
                <div className="space-y-4">
                  <p className="whitespace-pre-line text-sm leading-relaxed text-ink-700">{match.ai_match_summary}</p>

                  {claim ? (
                    <div className="rounded-2xl border border-warn-500/20 bg-warn-50 px-4 py-3 text-sm text-warn-700">
                      Claim verification: <b className="capitalize">{claim.status.replaceAll("_", " ")}</b> · fraud score <b className="tabular-nums">{claim.fraud_score.toFixed(0)}/100</b>
                    </div>
                  ) : null}

                  <ImageComparePanel
                    lostImageUrl={match.lost_report?.proof_blob_url}
                    foundImageUrl={match.found_item?.image_blob_url}
                    lostLabel={match.lost_report?.report_code ? `Lost report ${match.lost_report.report_code}` : "Lost report (proof)"}
                    foundLabel={match.found_item?.item_title ?? "Found item"}
                  />

                  <MatchEvidencePanel
                    spans={match.evidence_spans_json}
                    lostText={match.lost_report?.ai_clean_description ?? match.lost_report?.raw_description ?? ""}
                    foundText={match.found_item?.ai_clean_description ?? match.found_item?.raw_description ?? ""}
                  />

                  <GraphEvidencePanel matchId={match.id} />
                </div>

                <aside className="space-y-4 rounded-2xl bg-ink-50/60 p-4">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-500">Score breakdown</p>
                    <div className="mt-3">
                      <ScoreBreakdown match={match} />
                    </div>
                  </div>

                  <div className="border-t border-ink-200/60 pt-4">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-500">Actions</p>
                    <div className="mt-2 space-y-2">
                      <Button
                        variant="primary"
                        fullWidth
                        loading={busyMatchId === match.id && action.isPending && action.variables?.verb === "approve"}
                        disabled={isClosed || busyMatchId === match.id}
                        onClick={() => action.mutate({ id: match.id, verb: "approve" })}
                        leftIcon={<Check className="h-4 w-4" />}
                      >
                        Approve
                      </Button>
                      <Button
                        variant="outline"
                        fullWidth
                        loading={busyMatchId === match.id && createClaim.isPending}
                        disabled={busyMatchId === match.id || !!claim}
                        onClick={() => createClaim.mutate(match.id)}
                      >
                        {claim ? "Claim check open" : "Create claim check"}
                      </Button>
                      <Button
                        variant="gold"
                        fullWidth
                        loading={busyMatchId === match.id && release.isPending}
                        disabled={!claim || claim.status !== "approved" || busyMatchId === match.id}
                        onClick={() => claim && release.mutate(claim)}
                      >
                        Release item
                      </Button>
                      <div className="grid grid-cols-2 gap-2">
                        <Button
                          variant="ghost"
                          loading={busyMatchId === match.id && action.isPending && action.variables?.verb === "needs-more-info"}
                          disabled={isClosed || busyMatchId === match.id}
                          onClick={() => action.mutate({ id: match.id, verb: "needs-more-info" })}
                        >
                          More info
                        </Button>
                        <Button
                          variant="ghost"
                          className="text-danger-600 hover:bg-danger-50"
                          loading={busyMatchId === match.id && action.isPending && action.variables?.verb === "reject"}
                          disabled={isClosed || busyMatchId === match.id}
                          onClick={() => action.mutate({ id: match.id, verb: "reject" })}
                          leftIcon={<X className="h-4 w-4" />}
                        >
                          Reject
                        </Button>
                      </div>
                    </div>
                  </div>
                </aside>
              </div>
            </Card>
          );
        })}
        {isLoading ? (
          <SkeletonRows count={3} />
        ) : filteredMatches.length === 0 ? (
          <EmptyState
            icon={<Search size={28} />}
            title="No matches in view"
            description="Try a different status or confidence filter, or click Run all to score open reports against current found items."
            action={
              <Button onClick={() => runAll.mutate()} loading={runAll.isPending} size="sm" leftIcon={<Sparkles className="h-3.5 w-3.5" />}>
                Run all
              </Button>
            }
          />
        ) : null}
      </div>
    </Section>
  );
}

function GraphEvidencePanel({ matchId }: { matchId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["graph-rag", "match", matchId],
    queryFn: async () => (await api.get<GraphContext>(`/graph-rag/matches/${matchId}`)).data,
  });

  if (isLoading) {
    return <div className="rounded-2xl border border-ink-200/60 bg-ink-50/60 px-4 py-3 text-xs text-ink-500">Loading graph evidence…</div>;
  }
  if (!data) return null;

  return (
    <div className="rounded-2xl border border-ink-200/60 bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="font-display text-sm font-semibold tracking-tight text-ink-900">Graph RAG evidence</p>
        <StatusPill value={data.provider} withDot />
        <span className="text-xs font-medium text-ink-500">{data.nodes.length} nodes · {data.edges.length} edges</span>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-ink-700">{data.generated_summary}</p>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <MiniList title="Evidence" rows={data.evidence} />
        <MiniList title="Risk signals" rows={data.risk_signals} tone="risk" />
      </div>
      <div className="mt-3">
        <GraphCanvas graph={data} height={320} />
      </div>
    </div>
  );
}

function MiniList({ title, rows, tone = "normal" }: { title: string; rows: string[]; tone?: "normal" | "risk" }) {
  return (
    <div className="rounded-2xl bg-ink-50/60 p-3">
      <p className={`text-[11px] font-semibold uppercase tracking-wider ${tone === "risk" ? "text-danger-600" : "text-ink-500"}`}>{title}</p>
      <ul className="mt-1.5 space-y-1 text-xs leading-5 text-ink-700">
        {rows.length ? rows.slice(0, 4).map((row) => <li key={row}>{row}</li>) : <li className="text-ink-400">None detected</li>}
      </ul>
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Loader2 } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { SkeletonRows } from "../components/Skeleton";
import { useToast } from "../components/Toast";
import type { ClaimVerification } from "../types";

const releaseChecklist = {
  identity_checked: true,
  proof_checked: true,
  passenger_signed: true,
  custody_updated: true,
};

function describeError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.message) return error.message;
  }
  return fallback;
}

export function ClaimVerificationPage() {
  const client = useQueryClient();
  const toast = useToast();
  const [busy, setBusy] = useState<{ id: number; verb: string } | null>(null);
  const { data = [], isLoading } = useQuery({
    queryKey: ["claim-verifications"],
    queryFn: async () => (await api.get<ClaimVerification[]>("/claim-verifications")).data,
  });
  const approve = useMutation({
    mutationFn: async (id: number) => {
      setBusy({ id, verb: "approve" });
      return (await api.post(`/claim-verifications/${id}/approve`, {
        review_notes: "Evidence reviewed from staff checklist.",
        release_checklist_json: releaseChecklist,
      })).data;
    },
    onSuccess: (_d, id) => {
      client.invalidateQueries({ queryKey: ["claim-verifications"] });
      toast.push(`Claim #${id} approved. You can now release the item.`, "success");
    },
    onError: (error, id) => toast.push(describeError(error, `Could not approve claim #${id}.`), "error"),
    onSettled: () => setBusy(null),
  });
  const reject = useMutation({
    mutationFn: async (id: number) => {
      setBusy({ id, verb: "reject" });
      return (await api.post(`/claim-verifications/${id}/reject`, {
        review_notes: "Claim rejected from staff checklist.",
      })).data;
    },
    onSuccess: (_d, id) => {
      client.invalidateQueries({ queryKey: ["claim-verifications"] });
      toast.push(`Claim #${id} rejected.`, "success");
    },
    onError: (error, id) => toast.push(describeError(error, `Could not reject claim #${id}.`), "error"),
    onSettled: () => setBusy(null),
  });
  const release = useMutation({
    mutationFn: async (claim: ClaimVerification) => {
      setBusy({ id: claim.id, verb: "release" });
      return (await api.post(`/matches/${claim.match_candidate_id}/release`, {
        released_to_name: claim.match_candidate?.lost_report?.contact_email ?? "Verified passenger",
        released_to_contact: claim.match_candidate?.lost_report?.contact_phone,
        release_checklist_json: releaseChecklist,
        review_notes: "Released after completed staff verification checklist.",
      })).data;
    },
    onSuccess: (_d, claim) => {
      client.invalidateQueries({ queryKey: ["claim-verifications"] });
      client.invalidateQueries({ queryKey: ["matches"] });
      toast.push(`Item released for claim #${claim.id}.`, "success");
    },
    onError: (error) => toast.push(describeError(error, "Could not release item."), "error"),
    onSettled: () => setBusy(null),
  });

  return (
    <section className="space-y-4">
      <PageHeader title="Claim Verification" kicker="Evidence, fraud risk, and release checklist" />
      <div className="grid gap-4">
        {isLoading ? (
          <SkeletonRows count={3} />
        ) : data.length === 0 ? (
          <EmptyState title="No claim verifications yet" description="Open a claim from a match to begin verification." />
        ) : null}
        {data.map((claim) => {
          const releaseDisabled = claim.status !== "approved";
          const claimBusy = busy?.id === claim.id;
          return (
            <article key={claim.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="grid gap-4 lg:grid-cols-[1fr_220px]">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-semibold text-slate-950">
                      {claim.match_candidate?.lost_report?.item_title ?? "Lost item"} {" -> "} {claim.match_candidate?.found_item?.item_title ?? "Found item"}
                    </h2>
                    <Badge value={claim.status} />
                    <Badge value={claim.match_candidate?.found_item?.risk_level} />
                  </div>
                  <p className="mt-3 text-sm text-slate-600">Fraud score: <b>{claim.fraud_score.toFixed(0)}/100</b></p>
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    <Panel title="Questions" rows={claim.verification_questions_json.map(String)} />
                    <Panel title="Fraud flags" rows={claim.fraud_flags_json.map(String)} />
                  </div>
                </div>
                <div className="grid content-start gap-2">
                  <ActionButton
                    busy={claimBusy && busy?.verb === "approve"}
                    disabled={claimBusy || claim.status === "approved" || claim.status === "released" || claim.status === "rejected"}
                    onClick={() => approve.mutate(claim.id)}
                    label="Approve claim"
                    busyLabel="Approving..."
                    className="bg-radar text-white"
                  />
                  <ActionButton
                    busy={claimBusy && busy?.verb === "release"}
                    disabled={releaseDisabled || claimBusy}
                    onClick={() => release.mutate(claim)}
                    label="Release item"
                    busyLabel="Releasing..."
                    className="bg-slate-900 text-white"
                  />
                  <ActionButton
                    busy={claimBusy && busy?.verb === "reject"}
                    disabled={claimBusy || claim.status === "rejected" || claim.status === "released"}
                    onClick={() => reject.mutate(claim.id)}
                    label="Reject claim"
                    busyLabel="Rejecting..."
                    className="border border-rose-300 bg-white text-rose-800"
                  />
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function ActionButton({
  busy,
  disabled,
  onClick,
  label,
  busyLabel,
  className,
}: {
  busy: boolean;
  disabled: boolean;
  onClick: () => void;
  label: string;
  busyLabel: string;
  className: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || busy}
      className={`focus-ring inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
    >
      {busy ? <Loader2 size={14} className="animate-spin" /> : null}
      {busy ? busyLabel : label}
    </button>
  );
}

function Panel({ title, rows }: { title: string; rows: string[] }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">{title}</p>
      <ul className="mt-2 space-y-1 text-sm text-slate-700">
        {rows.length ? rows.map((row) => <li key={row}>{row}</li>) : <li>None recorded</li>}
      </ul>
    </div>
  );
}

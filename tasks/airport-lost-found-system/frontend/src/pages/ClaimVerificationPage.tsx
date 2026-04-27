import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { PageHeader } from "../components/PageHeader";
import type { ClaimVerification } from "../types";

const releaseChecklist = {
  identity_checked: true,
  proof_checked: true,
  passenger_signed: true,
  custody_updated: true,
};

export function ClaimVerificationPage() {
  const client = useQueryClient();
  const { data = [] } = useQuery({
    queryKey: ["claim-verifications"],
    queryFn: async () => (await api.get<ClaimVerification[]>("/claim-verifications")).data,
  });
  const approve = useMutation({
    mutationFn: async (id: number) =>
      (await api.post(`/claim-verifications/${id}/approve`, {
        review_notes: "Evidence reviewed from staff checklist.",
        release_checklist_json: releaseChecklist,
      })).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ["claim-verifications"] }),
  });
  const reject = useMutation({
    mutationFn: async (id: number) =>
      (await api.post(`/claim-verifications/${id}/reject`, {
        review_notes: "Claim rejected from staff checklist.",
      })).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ["claim-verifications"] }),
  });
  const release = useMutation({
    mutationFn: async (claim: ClaimVerification) =>
      (await api.post(`/matches/${claim.match_candidate_id}/release`, {
        released_to_name: claim.match_candidate?.lost_report?.contact_email ?? "Verified passenger",
        released_to_contact: claim.match_candidate?.lost_report?.contact_phone,
        release_checklist_json: releaseChecklist,
        review_notes: "Released after completed staff verification checklist.",
      })).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ["claim-verifications"] }),
  });

  return (
    <section className="space-y-4">
      <PageHeader title="Claim Verification" kicker="Evidence, fraud risk, and release checklist" />
      <div className="grid gap-4">
        {data.map((claim) => (
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
                <button onClick={() => approve.mutate(claim.id)} className="rounded-lg bg-radar px-3 py-2 text-sm font-semibold text-white">Approve claim</button>
                <button onClick={() => release.mutate(claim)} disabled={claim.status !== "approved"} className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40">Release item</button>
                <button onClick={() => reject.mutate(claim.id)} className="rounded-lg border border-rose-300 px-3 py-2 text-sm font-semibold text-rose-800">Reject claim</button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
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

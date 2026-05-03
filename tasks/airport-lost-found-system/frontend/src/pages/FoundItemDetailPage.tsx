import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { PageHeader } from "../components/PageHeader";
import type { BarcodeLabel, FoundItem, MatchCandidate } from "../types";

export function FoundItemDetailPage() {
  const { id } = useParams();
  const client = useQueryClient();
  const { data: item } = useQuery({
    queryKey: ["found-item", id],
    queryFn: async () => (await api.get<FoundItem>(`/found-items/${id}`)).data,
  });
  const runMatching = useMutation({
    mutationFn: async () => (await api.post<MatchCandidate[]>(`/found-items/${id}/run-matching`)).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ["matches"] }),
  });
  const label = useMutation({
    mutationFn: async () => (await api.post<BarcodeLabel>(`/found-items/${id}/labels`)).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ["found-item", id] }),
  });
  if (!item) return null;
  return (
    <section className="space-y-4">
      <PageHeader title={item.item_title} kicker="Found item" action={<button onClick={() => runMatching.mutate()} className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white">Run matching</button>} />
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap gap-2"><Badge value={item.status} /><Badge value={item.risk_level} /></div>
          <p className="mt-4 text-sm leading-6 text-slate-700">{item.raw_description}</p>
          <p className="mt-3 text-sm font-medium text-slate-500">AI description</p>
          <p className="text-sm text-slate-800">{item.ai_clean_description}</p>
        </div>
        <aside className="space-y-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm"><b>Category:</b> {item.category}</p>
          <p className="text-sm"><b>Color:</b> {item.color}</p>
          <p className="text-sm"><b>Found:</b> {item.found_location}</p>
          <p className="text-sm"><b>Storage:</b> {item.storage_location}</p>
          <button onClick={() => label.mutate()} className="inline-flex rounded-lg bg-radar px-3 py-2 text-sm font-semibold text-white">Generate QR label</button>
          {label.data ? (
            <div className="rounded-lg border border-slate-200 p-3">
              <img src={`${api.defaults.baseURL}/labels/${label.data.label_code}/qr`} alt={`QR label ${label.data.label_code}`} className="mx-auto h-40 w-40" />
              <p className="mt-2 text-center text-xs font-semibold text-slate-600">{label.data.label_code}</p>
            </div>
          ) : null}
          <Link className="inline-flex rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold" to={`/staff/found/${item.id}/custody`}>Custody timeline</Link>
          <Link className="inline-flex rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold" to="/staff/scan">Open QR scanner</Link>
        </aside>
      </div>
    </section>
  );
}

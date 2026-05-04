import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Loader2 } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { ImageComparePanel } from "../components/ImageComparePanel";
import { PageHeader } from "../components/PageHeader";
import { useToast } from "../components/Toast";
import type { BarcodeLabel, FoundItem, MatchCandidate } from "../types";

function describeError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.message) return error.message;
  }
  return fallback;
}

export function FoundItemDetailPage() {
  const { id } = useParams();
  const client = useQueryClient();
  const toast = useToast();
  const { data: item, isLoading } = useQuery({
    queryKey: ["found-item", id],
    queryFn: async () => (await api.get<FoundItem>(`/found-items/${id}`)).data,
  });
  const runMatching = useMutation({
    mutationFn: async () => (await api.post<MatchCandidate[]>(`/found-items/${id}/run-matching`)).data,
    onSuccess: (data) => {
      client.invalidateQueries({ queryKey: ["matches"] });
      toast.push(`Matching ran — ${Array.isArray(data) ? data.length : 0} candidates returned.`, "success");
    },
    onError: (error) => toast.push(describeError(error, "Could not run matching."), "error"),
  });
  const label = useMutation({
    mutationFn: async () => (await api.post<BarcodeLabel>(`/found-items/${id}/labels`)).data,
    onSuccess: (data) => {
      client.invalidateQueries({ queryKey: ["found-item", id] });
      toast.push(`QR label ${data.label_code} ready.`, "success");
    },
    onError: (error) => toast.push(describeError(error, "Could not generate QR label."), "error"),
  });
  if (isLoading) return <p className="text-sm text-slate-500">Loading found item...</p>;
  if (!item) return <p className="text-sm text-slate-500">Found item not available.</p>;
  return (
    <section className="space-y-4">
      <PageHeader
        title={item.item_title}
        kicker="Found item"
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
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap gap-2"><Badge value={item.status} /><Badge value={item.risk_level} /></div>
            <p className="mt-4 text-sm leading-6 text-slate-700">{item.raw_description}</p>
            <p className="mt-3 text-sm font-medium text-slate-500">AI description</p>
            <p className="text-sm text-slate-800">{item.ai_clean_description}</p>
          </div>
          {item.image_blob_url ? (
            <ImageComparePanel
              foundImageUrl={item.image_blob_url}
              lostImageUrl={null}
              foundLabel={item.item_title}
              lostLabel="No matching lost report image yet"
            />
          ) : null}
        </div>
        <aside className="space-y-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm"><b>Category:</b> {item.category ?? "—"}</p>
          <p className="text-sm"><b>Color:</b> {item.color ?? "—"}</p>
          <p className="text-sm"><b>Found:</b> {item.found_location ?? "—"}</p>
          <p className="text-sm"><b>Storage:</b> {item.storage_location ?? "—"}</p>
          <button
            type="button"
            onClick={() => label.mutate()}
            disabled={label.isPending}
            className="focus-ring inline-flex items-center gap-2 rounded-lg bg-radar px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {label.isPending ? <Loader2 size={14} className="animate-spin" /> : null}
            {label.isPending ? "Generating..." : "Generate QR label"}
          </button>
          {label.data ? (
            <div className="rounded-lg border border-slate-200 p-3">
              <img src={`${api.defaults.baseURL}/labels/${label.data.label_code}/qr`} alt={`QR label ${label.data.label_code}`} className="mx-auto h-40 w-40" />
              <p className="mt-2 text-center text-xs font-semibold text-slate-600">{label.data.label_code}</p>
            </div>
          ) : null}
          <Link className="focus-ring inline-flex rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold" to={`/staff/found/${item.id}/custody`}>Custody timeline</Link>
          <Link className="focus-ring inline-flex rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold" to="/staff/scan">Open QR scanner</Link>
        </aside>
      </div>
    </section>
  );
}

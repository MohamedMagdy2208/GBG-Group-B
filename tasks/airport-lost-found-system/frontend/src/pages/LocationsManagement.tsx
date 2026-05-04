import { FormEvent, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Loader2 } from "lucide-react";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { useToast } from "../components/Toast";

type Location = { id: number; name: string; type: string; parent_location?: string; description?: string };

function describeError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.message) return error.message;
  }
  return fallback;
}

export function LocationsManagement() {
  const client = useQueryClient();
  const toast = useToast();
  const formRef = useRef<HTMLFormElement | null>(null);
  const { data = [], isLoading } = useQuery({ queryKey: ["locations"], queryFn: async () => (await api.get<Location[]>("/locations")).data });
  const create = useMutation({
    mutationFn: async (payload: Record<string, string>) => (await api.post("/locations", payload)).data,
    onSuccess: (data) => {
      client.invalidateQueries({ queryKey: ["locations"] });
      toast.push(`Location "${data?.name ?? ""}" created.`, "success");
      formRef.current?.reset();
    },
    onError: (error) => toast.push(describeError(error, "Could not create location."), "error"),
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    create.mutate({
      name: String(form.get("name") ?? ""),
      type: String(form.get("type") ?? "other"),
      description: String(form.get("description") ?? ""),
    });
  }
  return (
    <section className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <div>
        <PageHeader title="Locations Management" kicker="Admin" />
        {isLoading ? (
          <p className="text-sm text-slate-500">Loading locations...</p>
        ) : data.length === 0 ? (
          <EmptyState title="No locations yet" description="Add the first location from the form on the right." />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {data.map((location) => (
              <div key={location.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <p className="font-semibold text-slate-950">{location.name}</p>
                <p className="text-sm capitalize text-slate-500">{location.type}</p>
              </div>
            ))}
          </div>
        )}
      </div>
      <form ref={formRef} onSubmit={submit} className="space-y-3 self-start rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="name" placeholder="Name" required />
        <select className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="type" defaultValue="other">
          {["terminal", "gate", "lounge", "security", "restroom", "baggage", "aircraft", "other"].map((value) => (
            <option key={value} value={value}>{value}</option>
          ))}
        </select>
        <textarea className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="description" placeholder="Description" />
        <button
          type="submit"
          disabled={create.isPending}
          className="focus-ring inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {create.isPending ? <Loader2 size={14} className="animate-spin" /> : null}
          {create.isPending ? "Creating..." : "Create location"}
        </button>
      </form>
    </section>
  );
}

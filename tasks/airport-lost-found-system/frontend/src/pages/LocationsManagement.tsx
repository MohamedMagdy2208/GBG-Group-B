import { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";

type Location = { id: number; name: string; type: string; parent_location?: string; description?: string };

export function LocationsManagement() {
  const client = useQueryClient();
  const { data = [] } = useQuery({ queryKey: ["locations"], queryFn: async () => (await api.get<Location[]>("/locations")).data });
  const create = useMutation({
    mutationFn: async (payload: Record<string, FormDataEntryValue>) => (await api.post("/locations", payload)).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ["locations"] }),
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    create.mutate({ name: form.get("name")!, type: form.get("type")!, description: form.get("description")! });
    event.currentTarget.reset();
  }
  return (
    <section className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <div>
        <PageHeader title="Locations Management" kicker="Admin" />
        <div className="grid gap-3 sm:grid-cols-2">
          {data.map((location) => (
            <div key={location.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <p className="font-semibold text-slate-950">{location.name}</p>
              <p className="text-sm capitalize text-slate-500">{location.type}</p>
            </div>
          ))}
        </div>
      </div>
      <form onSubmit={submit} className="space-y-3 self-start rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="name" placeholder="Name" required />
        <select className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="type">
          {["terminal", "gate", "lounge", "security", "restroom", "baggage", "aircraft", "other"].map((value) => <option key={value} value={value}>{value}</option>)}
        </select>
        <textarea className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="description" placeholder="Description" />
        <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Create location</button>
      </form>
    </section>
  );
}

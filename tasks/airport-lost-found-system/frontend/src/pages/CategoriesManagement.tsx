import { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";

type Category = { id: number; name: string; related_categories_json: string[]; description?: string };

export function CategoriesManagement() {
  const client = useQueryClient();
  const { data = [] } = useQuery({ queryKey: ["categories"], queryFn: async () => (await api.get<Category[]>("/categories")).data });
  const create = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => (await api.post("/categories", payload)).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ["categories"] }),
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    create.mutate({
      name: form.get("name"),
      related_categories_json: String(form.get("related") || "").split(",").map((value) => value.trim()).filter(Boolean),
      description: form.get("description"),
    });
    event.currentTarget.reset();
  }
  return (
    <section className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <div>
        <PageHeader title="Categories Management" kicker="Admin" />
        <div className="grid gap-3 sm:grid-cols-2">
          {data.map((category) => (
            <div key={category.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <p className="font-semibold text-slate-950">{category.name}</p>
              <p className="text-sm text-slate-500">{category.description}</p>
            </div>
          ))}
        </div>
      </div>
      <form onSubmit={submit} className="space-y-3 self-start rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="name" placeholder="Name" required />
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="related" placeholder="Related categories" />
        <textarea className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="description" placeholder="Description" />
        <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Create category</button>
      </form>
    </section>
  );
}

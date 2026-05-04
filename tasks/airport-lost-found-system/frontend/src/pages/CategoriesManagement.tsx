import { FormEvent, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Loader2 } from "lucide-react";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { useToast } from "../components/Toast";

type Category = { id: number; name: string; related_categories_json: string[]; description?: string };

function describeError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.message) return error.message;
  }
  return fallback;
}

export function CategoriesManagement() {
  const client = useQueryClient();
  const toast = useToast();
  const formRef = useRef<HTMLFormElement | null>(null);
  const { data = [], isLoading } = useQuery({ queryKey: ["categories"], queryFn: async () => (await api.get<Category[]>("/categories")).data });
  const create = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => (await api.post("/categories", payload)).data,
    onSuccess: (data) => {
      client.invalidateQueries({ queryKey: ["categories"] });
      toast.push(`Category "${data?.name ?? ""}" created.`, "success");
      formRef.current?.reset();
    },
    onError: (error) => toast.push(describeError(error, "Could not create category."), "error"),
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    create.mutate({
      name: form.get("name"),
      related_categories_json: String(form.get("related") || "").split(",").map((value) => value.trim()).filter(Boolean),
      description: form.get("description"),
    });
  }
  return (
    <section className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <div>
        <PageHeader title="Categories Management" kicker="Admin" />
        {isLoading ? (
          <p className="text-sm text-slate-500">Loading categories...</p>
        ) : data.length === 0 ? (
          <EmptyState title="No categories yet" description="Add the first category from the form on the right." />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {data.map((category) => (
              <div key={category.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <p className="font-semibold text-slate-950">{category.name}</p>
                {category.description ? <p className="text-sm text-slate-500">{category.description}</p> : null}
                {category.related_categories_json?.length ? (
                  <p className="mt-2 text-xs text-slate-500">Related: {category.related_categories_json.join(", ")}</p>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>
      <form ref={formRef} onSubmit={submit} className="space-y-3 self-start rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="name" placeholder="Name" required />
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="related" placeholder="Related categories (comma separated)" />
        <textarea className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="description" placeholder="Description" />
        <button
          type="submit"
          disabled={create.isPending}
          className="focus-ring inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {create.isPending ? <Loader2 size={14} className="animate-spin" /> : null}
          {create.isPending ? "Creating..." : "Create category"}
        </button>
      </form>
    </section>
  );
}

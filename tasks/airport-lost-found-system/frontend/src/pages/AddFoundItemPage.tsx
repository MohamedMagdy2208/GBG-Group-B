import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, uploadFile } from "../api/client";
import { PageHeader } from "../components/PageHeader";

export function AddFoundItemPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    const form = new FormData(event.currentTarget);
    let image_blob_url = "";
    if (file) {
      image_blob_url = (await uploadFile(file, "found-items")).url;
    }
    const response = await api.post("/found-items", {
      item_title: form.get("item_title"),
      category: form.get("category"),
      raw_description: form.get("raw_description"),
      color: form.get("color"),
      found_location: form.get("found_location"),
      found_datetime: form.get("found_datetime") ? new Date(String(form.get("found_datetime"))).toISOString() : null,
      storage_location: form.get("storage_location"),
      risk_level: form.get("risk_level"),
      image_blob_url,
    });
    setBusy(false);
    navigate(`/staff/found/${response.data.id}`);
  }

  return (
    <section className="max-w-3xl">
      <PageHeader title="Register Found Item" kicker="Staff intake" />
      <form onSubmit={submit} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-2">
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="item_title" placeholder="Item title" required />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="category" placeholder="Category" required />
        <textarea className="focus-ring min-h-28 rounded-lg border border-slate-200 px-3 py-2 sm:col-span-2" name="raw_description" placeholder="Staff notes" required />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="color" placeholder="Color" />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="found_location" placeholder="Found location" />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="found_datetime" type="datetime-local" />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="storage_location" placeholder="Storage location" />
        <select className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="risk_level" defaultValue="normal">
          <option value="normal">Normal</option>
          <option value="high_value">High value</option>
          <option value="sensitive">Sensitive</option>
          <option value="dangerous">Dangerous</option>
        </select>
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2 sm:col-span-2" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        <button disabled={busy} className="focus-ring rounded-lg bg-slate-900 px-4 py-2 font-semibold text-white sm:col-span-2">
          {busy ? "Registering..." : "Register item"}
        </button>
      </form>
    </section>
  );
}

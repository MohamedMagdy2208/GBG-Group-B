import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, uploadFile } from "../api/client";
import { PageHeader } from "../components/PageHeader";

export function LostReportForm() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    const form = new FormData(event.currentTarget);
    let proof_blob_url = "";
    if (file) {
      proof_blob_url = (await uploadFile(file, "proofs")).url;
    }
    const response = await api.post("/lost-reports", {
      item_title: form.get("item_title"),
      category: form.get("category"),
      raw_description: form.get("raw_description"),
      color: form.get("color"),
      lost_location: form.get("lost_location"),
      lost_datetime: form.get("lost_datetime") ? new Date(String(form.get("lost_datetime"))).toISOString() : null,
      flight_number: form.get("flight_number"),
      contact_email: form.get("contact_email"),
      contact_phone: form.get("contact_phone"),
      proof_blob_url,
    });
    setBusy(false);
    navigate(`/status?code=${response.data.report_code}`);
  }

  return (
    <section className="max-w-3xl">
      <PageHeader title="Passenger Lost Report" kicker="Public intake" />
      <form onSubmit={submit} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-2">
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="item_title" placeholder="Item title" required />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="category" placeholder="Category" required />
        <textarea className="focus-ring min-h-28 rounded-lg border border-slate-200 px-3 py-2 sm:col-span-2" name="raw_description" placeholder="Description" required />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="color" placeholder="Color" />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="lost_location" placeholder="Lost location" required />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="lost_datetime" type="datetime-local" />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="flight_number" placeholder="Flight number" />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="contact_email" type="email" placeholder="Contact email" />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="contact_phone" placeholder="Contact phone" />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2 sm:col-span-2" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        <button disabled={busy} className="focus-ring rounded-lg bg-slate-900 px-4 py-2 font-semibold text-white sm:col-span-2">
          {busy ? "Submitting..." : "Submit report"}
        </button>
      </form>
    </section>
  );
}

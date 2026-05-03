import { FormEvent, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { api, uploadFile } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { useCategoryOptions } from "../hooks/useCategoryOptions";

function localDateValue(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function localTimeValue(date = new Date()) {
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
}

function combineLocalDateTime(dateValue: FormDataEntryValue | null, timeValue: FormDataEntryValue | null) {
  const date = String(dateValue ?? "");
  const time = String(timeValue ?? "00:00") || "00:00";
  if (!date) {
    return null;
  }
  return new Date(`${date}T${time}`).toISOString();
}

export function LostReportForm() {
  const navigate = useNavigate();
  const { categories, isLoading: categoriesLoading } = useCategoryOptions();
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
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
        lost_datetime: combineLocalDateTime(form.get("lost_date"), form.get("lost_time")),
        flight_number: form.get("flight_number"),
        contact_email: form.get("contact_email"),
        contact_phone: form.get("contact_phone"),
        proof_blob_url,
      });
      navigate(`/status?code=${response.data.report_code}`);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        setError(typeof detail === "string" ? detail : "We could not submit the report. Check the fields and try again.");
      } else {
        setError("We could not submit the report. Check the fields and try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="max-w-3xl">
      <PageHeader title="Passenger Lost Report" kicker="Public intake" />
      <form onSubmit={submit} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-2">
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="item_title" placeholder="Item title" required />
        <select className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="category" defaultValue="" aria-label="Category" required>
          <option value="" disabled>
            {categoriesLoading ? "Loading categories..." : "Select category"}
          </option>
          {categories.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
        <textarea className="focus-ring min-h-28 rounded-lg border border-slate-200 px-3 py-2 sm:col-span-2" name="raw_description" placeholder="Description" required />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="color" placeholder="Color" />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="lost_location" placeholder="Lost location" required />
        <label className="grid gap-1 text-sm font-medium text-slate-700">
          Last seen date
          <input
            className="focus-ring rounded-lg border border-slate-200 px-3 py-2 text-base font-normal text-slate-950"
            name="lost_date"
            type="date"
            defaultValue={localDateValue()}
            max={localDateValue()}
            required
          />
        </label>
        <label className="grid gap-1 text-sm font-medium text-slate-700">
          Approx. time
          <input
            className="focus-ring rounded-lg border border-slate-200 px-3 py-2 text-base font-normal text-slate-950"
            name="lost_time"
            type="time"
            defaultValue={localTimeValue()}
            required
          />
        </label>
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="flight_number" placeholder="Flight number" />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="contact_email" type="email" placeholder="Contact email" />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2" name="contact_phone" placeholder="Contact phone" />
        <input className="focus-ring rounded-lg border border-slate-200 px-3 py-2 sm:col-span-2" type="file" accept="image/png,image/jpeg,image/webp,application/pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 sm:col-span-2">{error}</p> : null}
        <button disabled={busy} className="focus-ring rounded-lg bg-slate-900 px-4 py-2 font-semibold text-white sm:col-span-2">
          {busy ? "Submitting..." : "Submit report"}
        </button>
      </form>
    </section>
  );
}

import { FormEvent, useState } from "react";
import axios from "axios";
import { Camera, FileUp, Send } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api, uploadFile } from "../api/client";
import { Button, Card, Field, Input, Section, Select, Textarea } from "../components/ui";
import { useToast } from "../components/Toast";
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
  if (!date) return null;
  return new Date(`${date}T${time}`).toISOString();
}

export function LostReportForm() {
  const navigate = useNavigate();
  const toast = useToast();
  const { categories, isLoading: categoriesLoading } = useCategoryOptions();
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    const email = String(form.get("contact_email") || "").trim();
    const phone = String(form.get("contact_phone") || "").trim();
    if (!email && !phone) {
      setError("Please share an email or phone number so staff can reach you.");
      return;
    }
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("That email address looks invalid. Please double-check it.");
      return;
    }
    if (phone && !/^\+?[0-9 .()-]{7,20}$/.test(phone)) {
      setError("That phone number looks invalid. Use international format like +201234567890.");
      return;
    }
    const lostDateValue = String(form.get("lost_date") || "");
    if (lostDateValue) {
      const lost = new Date(`${lostDateValue}T00:00`);
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - 90);
      if (lost > new Date()) {
        setError("Lost date cannot be in the future.");
        return;
      }
      if (lost < cutoff) {
        setError("Lost date is more than 90 days ago. Please contact airport support.");
        return;
      }
    }
    setBusy(true);
    try {
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
        contact_email: email || null,
        contact_phone: phone || null,
        proof_blob_url,
      });
      toast.push(`Report ${response.data.report_code} created.`, "success");
      navigate(`/status?code=${response.data.report_code}`);
    } catch (err) {
      let detail = "We could not submit the report. Check the fields and try again.";
      if (axios.isAxiosError(err) && typeof err.response?.data?.detail === "string") {
        detail = err.response.data.detail;
      }
      setError(detail);
      toast.push(detail, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Section
      kicker="Public intake"
      title="File a lost-item report"
      description="Tell us what you lost. Staff matches it against found items in seconds. The more detail, the better the match."
    >
      <div className="grid gap-5 lg:grid-cols-[1fr_300px]">
        <Card as="form" {...({ onSubmit: submit } as any)}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Item title">
              <Input name="item_title" placeholder="e.g. Black iPhone 14" required />
            </Field>
            <Field label="Category">
              <Select name="category" defaultValue="" required aria-label="Category">
                <option value="" disabled>{categoriesLoading ? "Loading…" : "Select category"}</option>
                {categories.map((category) => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </Select>
            </Field>
            <div className="sm:col-span-2">
              <Field label="Description" hint="Anything that helps staff identify the item — color, brand, marks, contents.">
                <Textarea name="raw_description" placeholder="Describe the item…" required />
              </Field>
            </div>
            <Field label="Color" optional>
              <Input name="color" placeholder="Black, blue, red…" />
            </Field>
            <Field label="Where you lost it">
              <Input name="lost_location" placeholder="Terminal 2 Gate B12" required />
            </Field>
            <Field label="Last seen — date">
              <Input name="lost_date" type="date" defaultValue={localDateValue()} max={localDateValue()} required />
            </Field>
            <Field label="Last seen — time">
              <Input name="lost_time" type="time" defaultValue={localTimeValue()} required />
            </Field>
            <Field label="Flight number" optional>
              <Input name="flight_number" placeholder="MS123" />
            </Field>
            <Field label="Contact email" hint="One of email or phone is required.">
              <Input name="contact_email" type="email" placeholder="you@example.com" />
            </Field>
            <Field label="Contact phone" optional>
              <Input name="contact_phone" placeholder="+20 100 000 0000" />
            </Field>
            <div className="sm:col-span-2">
              <Field label="Proof attachment" hint="Receipt, photo, or boarding pass — helps verification later.">
                <label
                  htmlFor="lost-report-proof"
                  className="focus-ring flex cursor-pointer items-center justify-between gap-3 rounded-2xl border border-dashed border-ink-300 bg-ink-50/40 px-4 py-3 text-sm text-ink-700 hover:border-navy-300 hover:bg-navy-50"
                >
                  <span className="flex items-center gap-2">
                    <FileUp className="h-4 w-4 text-ink-500" />
                    {file ? file.name : "Choose an image or PDF"}
                  </span>
                  <span className="text-xs text-ink-400">PNG · JPG · WEBP · PDF</span>
                </label>
                <input
                  id="lost-report-proof"
                  type="file"
                  className="hidden"
                  accept="image/png,image/jpeg,image/webp,application/pdf"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
              </Field>
            </div>
            {error ? (
              <p className="rounded-2xl border border-danger-500/20 bg-danger-50 px-3 py-2 text-sm text-danger-700 sm:col-span-2">
                {error}
              </p>
            ) : null}
            <div className="sm:col-span-2">
              <Button type="submit" loading={busy} fullWidth size="lg" rightIcon={<Send className="h-4 w-4" />}>
                Submit report
              </Button>
            </div>
          </div>
        </Card>

        <aside className="space-y-4">
          <Card className="bg-gradient-to-br from-navy-50 via-white to-gold-50/40">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gold-700">Pro tip</p>
            <h3 className="mt-1 font-display text-base font-semibold tracking-tight text-ink-900">
              Got a photo of a similar item?
            </h3>
            <p className="mt-1 text-sm text-ink-600">
              Try the photo-only intake — Vision describes it, and image similarity finds visual look-alikes from registered finds.
            </p>
            <Button
              variant="gold"
              size="sm"
              className="mt-3"
              onClick={() => navigate("/lost-report/photo")}
              leftIcon={<Camera className="h-3.5 w-3.5" />}
            >
              Search by photo
            </Button>
          </Card>
          <Card>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-navy-700">What happens next</p>
            <ol className="mt-3 space-y-2 text-sm text-ink-700">
              <li className="flex gap-2"><span className="font-mono text-xs text-navy-700">01</span> AI cleans and indexes your report.</li>
              <li className="flex gap-2"><span className="font-mono text-xs text-navy-700">02</span> Hybrid search matches it against found items.</li>
              <li className="flex gap-2"><span className="font-mono text-xs text-navy-700">03</span> Staff review evidence and contact you.</li>
            </ol>
          </Card>
        </aside>
      </div>
    </Section>
  );
}

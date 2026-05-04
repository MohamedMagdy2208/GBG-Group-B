import { FormEvent, useState } from "react";
import axios from "axios";
import { Camera, ImagePlus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api, uploadFile } from "../api/client";
import { Button, Card, Field, Input, Section } from "../components/ui";
import { useToast } from "../components/Toast";

export function PhotoOnlyLostReportPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!file) {
      setError("Please attach a photo.");
      return;
    }
    const form = new FormData(event.currentTarget);
    const email = String(form.get("contact_email") || "").trim();
    const phone = String(form.get("contact_phone") || "").trim();
    if (!email && !phone) {
      setError("Please share an email or phone number.");
      return;
    }
    setBusy(true);
    try {
      const upload = await uploadFile(file, "proofs");
      const response = await api.post("/lost-reports/photo-only", {
        image_url: upload.url,
        contact_email: email || null,
        contact_phone: phone || null,
        lost_location: form.get("lost_location") || null,
      });
      toast.push(`Report ${response.data.report_code} created.`, "success");
      navigate(`/status?code=${response.data.report_code}`);
    } catch (err) {
      let msg = "Could not submit photo report.";
      if (axios.isAxiosError(err) && typeof err.response?.data?.detail === "string") {
        msg = err.response.data.detail;
      }
      setError(msg);
      toast.push(msg, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Section
      kicker="Public intake"
      title="Search by photo"
      description="Upload a photo of a similar item — Vision describes it and image similarity finds visual look-alikes from registered finds."
    >
      <div className="mx-auto max-w-2xl">
        <Card as="form" {...({ onSubmit: submit } as any)} className="space-y-4">
          <Field label="Photo of a similar item" hint="A photo of the same model from any angle works.">
            <label
              htmlFor="photo-only-input"
              className="focus-ring relative flex aspect-video cursor-pointer flex-col items-center justify-center gap-2 overflow-hidden rounded-2xl border border-dashed border-ink-300 bg-ink-50/40 text-center text-sm text-ink-600 transition hover:border-navy-300 hover:bg-navy-50"
            >
              {previewUrl ? (
                <img src={previewUrl} alt="Preview" className="absolute inset-0 h-full w-full object-contain" />
              ) : (
                <>
                  <ImagePlus className="h-7 w-7 text-ink-400" />
                  <span className="font-medium">Click to upload a photo</span>
                  <span className="text-xs text-ink-400">PNG · JPG · WEBP</span>
                </>
              )}
            </label>
            <input
              id="photo-only-input"
              type="file"
              className="hidden"
              accept="image/png,image/jpeg,image/webp"
              onChange={(event) => {
                const next = event.target.files?.[0] ?? null;
                setFile(next);
                if (previewUrl) URL.revokeObjectURL(previewUrl);
                setPreviewUrl(next ? URL.createObjectURL(next) : null);
              }}
              required
            />
          </Field>
          <Field label="Where you lost it" optional>
            <Input name="lost_location" placeholder="Terminal 3 baggage claim" />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Contact email" hint="One of email or phone is required.">
              <Input name="contact_email" type="email" placeholder="you@example.com" />
            </Field>
            <Field label="Contact phone" optional>
              <Input name="contact_phone" placeholder="+20 100 000 0000" />
            </Field>
          </div>
          {error ? (
            <p className="rounded-2xl border border-danger-500/20 bg-danger-50 px-3 py-2 text-sm text-danger-700">{error}</p>
          ) : null}
          <Button type="submit" loading={busy} fullWidth size="lg" leftIcon={<Camera className="h-4 w-4" />}>
            {busy ? "Searching…" : "Search by photo"}
          </Button>
        </Card>
      </div>
    </Section>
  );
}

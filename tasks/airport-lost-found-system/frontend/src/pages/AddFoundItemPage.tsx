import { FormEvent, useState } from "react";
import axios from "axios";
import { ImagePlus, Save, Sparkles } from "lucide-react";
// (Save icon used inside the page)
import { useNavigate } from "react-router-dom";
import { api, uploadFile } from "../api/client";
import { Button, Card, Field, Input, Section, Select, Textarea } from "../components/ui";
import { Pill } from "../components/ui/Pill";
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

function combineLocalDateTime(date: string, time: string) {
  if (!date) return null;
  const safeTime = time || "00:00";
  return new Date(`${date}T${safeTime}`).toISOString();
}

type DraftFields = {
  item_title: string;
  category: string;
  raw_description: string;
  color: string;
  found_location: string;
  storage_location: string;
  risk_level: "normal" | "high_value" | "sensitive" | "dangerous";
};

const EMPTY_DRAFT: DraftFields = {
  item_title: "",
  category: "",
  raw_description: "",
  color: "",
  found_location: "",
  storage_location: "",
  risk_level: "normal",
};

export function AddFoundItemPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { categories, isLoading: categoriesLoading } = useCategoryOptions();
  const [file, setFile] = useState<File | null>(null);
  const [uploadedImageUrl, setUploadedImageUrl] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftFields>(EMPTY_DRAFT);
  const [foundDate, setFoundDate] = useState(localDateValue());
  const [foundTime, setFoundTime] = useState(localTimeValue());
  const [busy, setBusy] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [aiAssisted, setAiAssisted] = useState(false);
  const [aiHint, setAiHint] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  function update<K extends keyof DraftFields>(key: K, value: DraftFields[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function generateFromPhoto() {
    if (!file) {
      setError("Pick a photo first, then click Generate.");
      return;
    }
    setError("");
    setAiHint(null);
    setGenerating(true);
    try {
      const url = uploadedImageUrl ?? (await uploadFile(file, "found-items")).url;
      if (!uploadedImageUrl) setUploadedImageUrl(url);
      const response = await api.post("/ai/describe-from-image", { image_url: url });
      const ai = response.data as Partial<DraftFields> & { confidence?: number; vision_caption?: string };
      setDraft((current) => ({
        item_title: ai.item_title || current.item_title,
        category: ai.category || current.category,
        raw_description: ai.raw_description || current.raw_description,
        color: ai.color || current.color,
        found_location: current.found_location,
        storage_location: current.storage_location,
        risk_level: (ai.risk_level as DraftFields["risk_level"]) || current.risk_level,
      }));
      setAiAssisted(true);
      const confidencePct = Math.round(((ai.confidence ?? 0.5) as number) * 100);
      setAiHint(
        ai.vision_caption
          ? `AI confidence ${confidencePct}%: "${ai.vision_caption}". Edit before saving.`
          : `AI confidence ${confidencePct}%. Review fields before saving.`,
      );
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        setError(typeof detail === "string" ? detail : "Could not generate from photo.");
      } else {
        setError("Could not generate from photo.");
      }
    } finally {
      setGenerating(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      let image_blob_url = uploadedImageUrl ?? "";
      if (!image_blob_url && file) {
        image_blob_url = (await uploadFile(file, "found-items")).url;
        setUploadedImageUrl(image_blob_url);
      }
      const response = await api.post("/found-items", {
        item_title: draft.item_title,
        category: draft.category || null,
        raw_description: draft.raw_description,
        color: draft.color || null,
        found_location: draft.found_location || null,
        found_datetime: combineLocalDateTime(foundDate, foundTime),
        storage_location: draft.storage_location || null,
        risk_level: draft.risk_level,
        image_blob_url,
      });
      toast.push(`Item #${response.data.id} registered.`, "success");
      navigate(`/staff/found/${response.data.id}`);
    } catch (err) {
      let detail = "We could not register the item. Check the fields and try again.";
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
      kicker="Staff intake"
      title="Register a found item"
      description="Upload a photo and let AI draft the description for you. Review carefully before saving — staff approval gates every release."
    >
      <Card as="form" {...({ onSubmit: submit } as any)}>
        <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
          {/* Photo + AI section */}
          <div className="space-y-3">
            <Field label="Photo" hint="Then click ✨ Generate to auto-fill description.">
              <label
                htmlFor="found-photo-input"
                className="focus-ring relative flex aspect-square cursor-pointer flex-col items-center justify-center gap-2 overflow-hidden rounded-2xl border border-dashed border-ink-300 bg-ink-50/40 text-center text-sm text-ink-600 transition hover:border-navy-300 hover:bg-navy-50"
              >
                {previewUrl ? (
                  <img src={previewUrl} alt="Preview" className="absolute inset-0 h-full w-full object-cover" />
                ) : (
                  <>
                    <ImagePlus className="h-7 w-7 text-ink-400" />
                    <span className="font-medium">Click to upload</span>
                    <span className="text-xs text-ink-400">PNG · JPG · WEBP</span>
                  </>
                )}
              </label>
              <input
                id="found-photo-input"
                type="file"
                className="hidden"
                accept="image/png,image/jpeg,image/webp"
                onChange={(event) => {
                  const next = event.target.files?.[0] ?? null;
                  setFile(next);
                  setUploadedImageUrl(null);
                  setAiHint(null);
                  setAiAssisted(false);
                  if (previewUrl) URL.revokeObjectURL(previewUrl);
                  setPreviewUrl(next ? URL.createObjectURL(next) : null);
                }}
              />
            </Field>
            <Button
              type="button"
              variant="gold"
              size="sm"
              fullWidth
              loading={generating}
              disabled={!file}
              onClick={generateFromPhoto}
              leftIcon={<Sparkles className="h-3.5 w-3.5" />}
            >
              {generating ? "Analyzing photo…" : "Generate from photo"}
            </Button>
            {aiAssisted ? (
              <Pill tone="gold" withDot>AI-drafted — verify</Pill>
            ) : null}
            {aiHint ? <p className="text-xs leading-relaxed text-ink-500">{aiHint}</p> : null}
          </div>

          {/* Form fields */}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Item title">
              <Input
                name="item_title"
                placeholder="e.g. Black iPhone 14"
                value={draft.item_title}
                onChange={(event) => update("item_title", event.target.value)}
                required
              />
            </Field>
            <Field label="Category">
              <Select
                value={draft.category}
                onChange={(event) => update("category", event.target.value)}
                required
                aria-label="Category"
              >
                <option value="" disabled>{categoriesLoading ? "Loading…" : "Select category"}</option>
                {categories.map((category) => (
                  <option key={category} value={category}>{category}</option>
                ))}
                {draft.category && !categories.includes(draft.category) ? (
                  <option value={draft.category}>{draft.category} (AI-suggested)</option>
                ) : null}
              </Select>
            </Field>
            <div className="sm:col-span-2">
              <Field label="Description">
                <Textarea
                  placeholder="Staff notes — describe markings, condition, any damage."
                  value={draft.raw_description}
                  onChange={(event) => update("raw_description", event.target.value)}
                  required
                />
              </Field>
            </div>
            <Field label="Color" optional>
              <Input value={draft.color} onChange={(event) => update("color", event.target.value)} placeholder="Black, blue…" />
            </Field>
            <Field label="Found location" optional>
              <Input value={draft.found_location} onChange={(event) => update("found_location", event.target.value)} placeholder="Terminal 3 Gate F1" />
            </Field>
            <Field label="Found date">
              <Input type="date" value={foundDate} max={localDateValue()} onChange={(event) => setFoundDate(event.target.value)} required />
            </Field>
            <Field label="Found time">
              <Input type="time" value={foundTime} onChange={(event) => setFoundTime(event.target.value)} required />
            </Field>
            <Field label="Storage location" optional>
              <Input value={draft.storage_location} onChange={(event) => update("storage_location", event.target.value)} placeholder="Lost & Found Office T3" />
            </Field>
            <Field label="Risk level" hint="Marks the item for stricter release rules.">
              <Select
                value={draft.risk_level}
                onChange={(event) => update("risk_level", event.target.value as DraftFields["risk_level"])}
              >
                <option value="normal">Normal</option>
                <option value="high_value">High value</option>
                <option value="sensitive">Sensitive</option>
                <option value="dangerous">Dangerous</option>
              </Select>
            </Field>
            {error ? (
              <p className="rounded-2xl border border-danger-500/20 bg-danger-50 px-3 py-2 text-sm text-danger-700 sm:col-span-2">{error}</p>
            ) : null}
            <div className="sm:col-span-2 flex justify-end pt-1">
              <Button type="submit" loading={busy} size="lg" leftIcon={<Save className="h-4 w-4" />}>
                Register item
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </Section>
  );
}

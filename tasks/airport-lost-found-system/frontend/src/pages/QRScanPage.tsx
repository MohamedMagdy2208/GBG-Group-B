import { FormEvent, useEffect, useRef, useState } from "react";
import axios from "axios";
import { Camera, Loader2, Search } from "lucide-react";
import { api } from "../api/client";
import { Button, Card, Section } from "../components/ui";
import { StatusPill } from "../components/ui/Pill";
import { useToast } from "../components/Toast";
import type { LabelScanResponse } from "../types";

function describeError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.message) return error.message;
  }
  return fallback;
}

export function QRScanPage() {
  const toast = useToast();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [code, setCode] = useState("");
  const [result, setResult] = useState<LabelScanResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [cameraStatus, setCameraStatus] = useState("Camera scanner uses the browser BarcodeDetector when available.");

  useEffect(() => {
    let stopped = false;
    let stream: MediaStream | null = null;

    async function start() {
      const BarcodeDetector = (window as any).BarcodeDetector;
      if (!BarcodeDetector || !navigator.mediaDevices?.getUserMedia) return;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        const detector = new BarcodeDetector({ formats: ["qr_code"] });
        const loop = async () => {
          if (stopped || !videoRef.current) return;
          const detections = await detector.detect(videoRef.current).catch(() => []);
          const rawValue = detections[0]?.rawValue;
          if (rawValue) {
            setCode(rawValue);
            await scan(rawValue);
            return;
          }
          requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
      } catch {
        setCameraStatus("Camera scanner is unavailable. Enter the QR code manually.");
      }
    }

    void start();
    return () => {
      stopped = true;
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function scan(value = code) {
    if (!value.trim()) {
      toast.push("Enter or scan a label code first.", "info");
      return;
    }
    setBusy(true);
    try {
      const response = await api.post<LabelScanResponse>("/labels/scan", {
        label_code: value,
        notes: "Scanned from staff QR page",
      });
      setResult(response.data);
      toast.push(`Label ${response.data.label.label_code} scanned.`, "success");
    } catch (error) {
      toast.push(describeError(error, "Could not scan label."), "error");
    } finally {
      setBusy(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await scan();
  }

  return (
    <Section
      kicker="Found item label lookup"
      title="QR custody scan"
      description="Point the camera at a QR label, or enter the code manually. Each scan adds a custody event."
    >
      <div className="grid gap-4 lg:grid-cols-[440px_1fr]">
        <Card>
          <div className="aspect-video overflow-hidden rounded-2xl bg-navy-950">
            <video ref={videoRef} className="h-full w-full object-cover" muted playsInline />
          </div>
          <p className="mt-3 text-xs text-ink-500">{cameraStatus}</p>
          <form onSubmit={submit} className="mt-4 flex items-center gap-2">
            <input
              value={code}
              onChange={(event) => setCode(event.target.value)}
              className="focus-ring flex-1 rounded-2xl border border-ink-200 bg-white px-4 py-2.5 font-mono text-sm text-ink-900 placeholder:text-ink-400 focus:border-navy-500 focus:outline-none focus:ring-4 focus:ring-navy-500/10"
              placeholder="LF-XXXXXXXXXX"
              aria-label="Label code"
            />
            <Button type="submit" loading={busy} leftIcon={<Search className="h-4 w-4" />}>
              {busy ? "Scanning…" : "Scan"}
            </Button>
          </form>
        </Card>
        <Card>
          <div className="flex items-center gap-2">
            <span className="grid h-9 w-9 place-items-center rounded-2xl bg-gold-50 text-gold-700 ring-1 ring-gold-100">
              <Camera className="h-4 w-4" />
            </span>
            <div>
              <p className="font-display text-base font-semibold tracking-tight text-ink-900">Scan result</p>
              <p className="text-xs text-ink-500">Latest label and custody snapshot.</p>
            </div>
          </div>
          {result ? (
            <div className="mt-5 space-y-3">
              <div className="flex flex-wrap gap-2">
                <StatusPill value={result.label.status} />
                <StatusPill value={result.found_item?.status} />
                <StatusPill value={result.found_item?.risk_level} />
              </div>
              <dl className="grid grid-cols-[120px_1fr] gap-2 text-sm">
                <dt className="text-ink-500">Label</dt><dd className="font-mono text-ink-800">{result.label.label_code}</dd>
                <dt className="text-ink-500">Found item</dt><dd className="text-ink-800">{result.found_item?.item_title ?? "—"}</dd>
                <dt className="text-ink-500">Storage</dt><dd className="text-ink-800">{result.found_item?.storage_location ?? "Not assigned"}</dd>
                <dt className="text-ink-500">Scans</dt><dd className="font-semibold tabular-nums text-ink-900">{result.label.scan_count}</dd>
              </dl>
            </div>
          ) : (
            <p className="mt-5 text-sm text-ink-500">Scan a QR label or enter a label code to open the custody context.</p>
          )}
        </Card>
      </div>
    </Section>
  );
}

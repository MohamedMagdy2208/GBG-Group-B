import { PageHeader } from "../components/PageHeader";

const settings = [
  ["Azure services", "Controlled by USE_AZURE_SERVICES"],
  ["Cache backend", "Redis with in-memory fallback"],
  ["Status cache TTL", "60 seconds"],
  ["Analytics cache TTL", "300 seconds"],
  ["Telemetry", "OpenTelemetry and Application Insights"],
  ["Privacy", "PII masking and short-lived blob access"],
];

export function SettingsPage() {
  return (
    <section>
      <PageHeader title="System Settings" kicker="Admin" />
      <div className="grid gap-3 md:grid-cols-2">
        {settings.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm font-semibold text-slate-500">{label}</p>
            <p className="mt-2 font-medium text-slate-950">{value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

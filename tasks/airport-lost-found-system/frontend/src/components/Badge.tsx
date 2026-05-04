import { StatusPill } from "./ui/Pill";

// Legacy wrapper — maps the old <Badge /> API onto the new Apple-style StatusPill.
export function Badge({ value }: { value?: string | null }) {
  return <StatusPill value={value} />;
}

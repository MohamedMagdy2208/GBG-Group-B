import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { PageHeader } from "../components/PageHeader";
import type { FoundItem } from "../types";

export function FoundItemListPage() {
  const { data = [] } = useQuery({
    queryKey: ["found-items"],
    queryFn: async () => (await api.get<FoundItem[]>("/found-items")).data,
  });
  return (
    <section>
      <PageHeader title="Found Item List" kicker="Inventory" action={<Link className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white" to="/staff/found/new">Add found item</Link>} />
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100 text-xs uppercase tracking-normal text-slate-500">
            <tr><th className="p-3">Item</th><th>Category</th><th>Location</th><th>Risk</th><th>Status</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50">
                <td className="p-3 font-semibold"><Link to={`/staff/found/${item.id}`}>{item.item_title}</Link></td>
                <td>{item.category}</td>
                <td>{item.found_location}</td>
                <td><Badge value={item.risk_level} /></td>
                <td><Badge value={item.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

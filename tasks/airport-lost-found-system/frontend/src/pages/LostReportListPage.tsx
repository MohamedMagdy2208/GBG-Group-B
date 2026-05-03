import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { PageHeader } from "../components/PageHeader";
import type { LostReport } from "../types";

export function LostReportListPage() {
  const { data = [] } = useQuery({
    queryKey: ["lost-reports"],
    queryFn: async () => (await api.get<LostReport[]>("/lost-reports")).data,
  });
  return (
    <section>
      <PageHeader title="Lost Report List" kicker="Passenger reports" />
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100 text-xs uppercase tracking-normal text-slate-500">
            <tr><th className="p-3">Code</th><th>Item</th><th>Category</th><th>Location</th><th>Status</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.map((report) => (
              <tr key={report.id} className="hover:bg-slate-50">
                <td className="p-3 font-semibold"><Link to={`/staff/lost/${report.id}`}>{report.report_code}</Link></td>
                <td>{report.item_title}</td>
                <td>{report.category}</td>
                <td>{report.lost_location}</td>
                <td><Badge value={report.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

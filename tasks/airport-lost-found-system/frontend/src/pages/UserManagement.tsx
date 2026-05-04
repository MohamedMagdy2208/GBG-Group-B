import { FormEvent, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Loader2 } from "lucide-react";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { PageHeader } from "../components/PageHeader";
import { useToast } from "../components/Toast";
import type { User } from "../types";

function describeError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.message) return error.message;
  }
  return fallback;
}

export function UserManagement() {
  const client = useQueryClient();
  const toast = useToast();
  const formRef = useRef<HTMLFormElement | null>(null);
  const { data = [] } = useQuery({
    queryKey: ["users"],
    queryFn: async () => (await api.get<User[]>("/users")).data,
  });
  const create = useMutation({
    mutationFn: async (payload: Record<string, string>) => (await api.post("/users", payload)).data,
    onSuccess: (data) => {
      client.invalidateQueries({ queryKey: ["users"] });
      toast.push(`User ${data?.email ?? "created"} added.`, "success");
      formRef.current?.reset();
    },
    onError: (error) => toast.push(describeError(error, "Could not create user."), "error"),
  });
  const disableUser = useMutation({
    mutationFn: async (userId: number) => (await api.post(`/admin/users/${userId}/disable`)).data,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["users"] });
      toast.push("User disabled.", "success");
    },
    onError: (error) => toast.push(describeError(error, "Could not disable user."), "error"),
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    create.mutate({
      name: String(form.get("name") ?? ""),
      email: String(form.get("email") ?? ""),
      phone: String(form.get("phone") ?? ""),
      password: String(form.get("password") ?? ""),
      role: String(form.get("role") ?? "staff"),
    });
  }
  return (
    <section className="grid gap-4 lg:grid-cols-[1fr_340px]">
      <div>
        <PageHeader title="User Management" kicker="Admin" />
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase tracking-normal text-slate-500"><tr><th className="p-3">Name</th><th>Email</th><th>Role</th><th>Status</th><th>Action</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((user) => (
                <tr key={user.id}>
                  <td className="p-3 font-semibold">{user.name}</td>
                  <td>{user.email}</td>
                  <td><Badge value={user.role} /></td>
                  <td><Badge value={user.is_disabled ? "disabled" : "active"} /></td>
                  <td>
                    {!user.is_disabled ? (
                      <button
                        className="focus-ring rounded-lg border border-rose-200 px-2 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                        onClick={() => disableUser.mutate(user.id)}
                        disabled={disableUser.isPending && disableUser.variables === user.id}
                      >
                        {disableUser.isPending && disableUser.variables === user.id ? "Disabling..." : "Disable"}
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <form ref={formRef} onSubmit={submit} className="space-y-3 self-start rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="name" placeholder="Name" required />
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="email" type="email" placeholder="Email" required />
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="phone" placeholder="Phone" />
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="password" type="password" placeholder="Password (min 12 chars, mix of cases, digit, symbol)" required minLength={12} />
        <select className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="role" defaultValue="staff">
          <option value="staff">Staff</option>
          <option value="security">Security</option>
          <option value="admin">Admin</option>
        </select>
        <button
          type="submit"
          disabled={create.isPending}
          className="focus-ring inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {create.isPending ? <Loader2 size={14} className="animate-spin" /> : null}
          {create.isPending ? "Creating..." : "Create user"}
        </button>
      </form>
    </section>
  );
}

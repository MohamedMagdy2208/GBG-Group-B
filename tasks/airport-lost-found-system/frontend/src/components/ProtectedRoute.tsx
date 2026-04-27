import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import type { Role } from "../types";

export function ProtectedRoute({ roles }: { roles: Role[] }) {
  const { user, loading, hasRole } = useAuth();
  if (loading) {
    return <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-500">Loading session...</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (!hasRole(roles)) {
    return <div className="rounded-lg border border-rose-200 bg-rose-50 p-6 text-sm font-medium text-rose-800">Access restricted.</div>;
  }
  return <Outlet />;
}

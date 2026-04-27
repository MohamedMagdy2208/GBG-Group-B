import {
  AlertTriangle,
  BarChart3,
  Bot,
  Boxes,
  ClipboardList,
  Home,
  LogOut,
  MapPin,
  MessageSquare,
  PackagePlus,
  Search,
  ServerCog,
  Settings,
  ShieldCheck,
  ScanLine,
  Tags,
  Users,
} from "lucide-react";
import type React from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import type { Role } from "../types";

type NavItem = {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: Role[];
};

const navItems: NavItem[] = [
  { to: "/", label: "Home", icon: Home },
  { to: "/chat", label: "Chat", icon: Bot },
  { to: "/lost-report", label: "Report", icon: MessageSquare },
  { to: "/status", label: "Status", icon: Search },
  { to: "/staff", label: "Dashboard", icon: ShieldCheck, roles: ["staff", "admin", "security"] },
  { to: "/staff/found/new", label: "Add Found", icon: PackagePlus, roles: ["staff", "admin", "security"] },
  { to: "/staff/found", label: "Found", icon: Boxes, roles: ["staff", "admin", "security"] },
  { to: "/staff/lost", label: "Lost", icon: ClipboardList, roles: ["staff", "admin", "security"] },
  { to: "/staff/matches", label: "Matches", icon: Search, roles: ["staff", "admin", "security"] },
  { to: "/staff/claims", label: "Claims", icon: ShieldCheck, roles: ["staff", "admin", "security"] },
  { to: "/staff/scan", label: "QR Scan", icon: ScanLine, roles: ["staff", "admin", "security"] },
  { to: "/admin/analytics", label: "Analytics", icon: BarChart3, roles: ["admin"] },
  { to: "/admin/audit", label: "Audit", icon: ShieldCheck, roles: ["admin"] },
  { to: "/admin/operations", label: "Operations", icon: ServerCog, roles: ["admin"] },
  { to: "/admin/users", label: "Users", icon: Users, roles: ["admin"] },
  { to: "/admin/locations", label: "Locations", icon: MapPin, roles: ["admin"] },
  { to: "/admin/categories", label: "Categories", icon: Tags, roles: ["admin"] },
  { to: "/admin/settings", label: "Settings", icon: Settings, roles: ["admin"] },
];

export function Shell() {
  const { user, logout, hasRole, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const visible = navItems.filter((item) => !item.roles || hasRole(item.roles));

  return (
    <div className="min-h-screen bg-slate-50">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white lg:block">
        <div className="flex h-16 items-center gap-3 border-b border-slate-200 px-5">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-runway text-white">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-950">Airport Ops</p>
            <p className="text-xs text-slate-500">Lost & Found</p>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {visible.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur lg:px-8">
          <div>
            <p className="text-sm font-semibold text-slate-950">AI-Powered Lost & Found</p>
            <p className="text-xs text-slate-500">Airport operations workspace</p>
          </div>
          <div className="flex items-center gap-2">
            {user ? (
              <>
                <span className="hidden text-sm text-slate-600 sm:inline">
                  {user.name} - {user.role}
                </span>
                <button
                  className="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100"
                  title="Log out"
                  onClick={() => {
                    logout();
                    navigate("/");
                  }}
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </>
            ) : (
              <button
                className="focus-ring rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white"
                onClick={() => navigate("/login")}
              >
                Sign in
              </button>
            )}
          </div>
        </header>
        {sessionExpired ? (
          <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900 lg:px-8">
            <span className="inline-flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              Your session expired. Please sign in again to continue protected work.
            </span>
          </div>
        ) : null}
        <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

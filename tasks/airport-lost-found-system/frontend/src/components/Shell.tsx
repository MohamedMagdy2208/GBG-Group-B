import {
  AlertTriangle,
  BarChart3,
  Bot,
  Boxes,
  ClipboardList,
  Home,
  Languages,
  LogOut,
  MapPin,
  MessageSquare,
  PackagePlus,
  Plane,
  Search,
  ServerCog,
  Settings,
  ShieldCheck,
  ScanLine,
  Sparkles,
  Tags,
  Users,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { type Language, loadLanguage, persistLanguage, translate } from "../i18n";
import type { Role } from "../types";
import { Button } from "./ui/Button";

type NavItem = {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: Role[];
  group: "general" | "staff" | "admin";
};

const navItems: NavItem[] = [
  { to: "/", label: "Home", icon: Home, group: "general" },
  { to: "/chat", label: "Chat", icon: Bot, group: "general" },
  { to: "/lost-report", label: "Report", icon: MessageSquare, group: "general" },
  { to: "/status", label: "Status", icon: Search, group: "general" },
  { to: "/staff", label: "Dashboard", icon: ShieldCheck, roles: ["staff", "admin", "security"], group: "staff" },
  { to: "/staff/found/new", label: "Add Found", icon: PackagePlus, roles: ["staff", "admin", "security"], group: "staff" },
  { to: "/staff/found", label: "Found", icon: Boxes, roles: ["staff", "admin", "security"], group: "staff" },
  { to: "/staff/lost", label: "Lost", icon: ClipboardList, roles: ["staff", "admin", "security"], group: "staff" },
  { to: "/staff/matches", label: "Matches", icon: Search, roles: ["staff", "admin", "security"], group: "staff" },
  { to: "/staff/claims", label: "Claims", icon: ShieldCheck, roles: ["staff", "admin", "security"], group: "staff" },
  { to: "/staff/scan", label: "QR Scan", icon: ScanLine, roles: ["staff", "admin", "security"], group: "staff" },
  { to: "/admin/analytics", label: "Analytics", icon: BarChart3, roles: ["admin"], group: "admin" },
  { to: "/admin/audit", label: "Audit", icon: ShieldCheck, roles: ["admin"], group: "admin" },
  { to: "/admin/operations", label: "Operations", icon: ServerCog, roles: ["admin"], group: "admin" },
  { to: "/admin/demo", label: "Demo", icon: Sparkles, roles: ["admin"], group: "admin" },
  { to: "/admin/users", label: "Users", icon: Users, roles: ["admin"], group: "admin" },
  { to: "/admin/locations", label: "Locations", icon: MapPin, roles: ["admin"], group: "admin" },
  { to: "/admin/categories", label: "Categories", icon: Tags, roles: ["admin"], group: "admin" },
  { to: "/admin/settings", label: "Settings", icon: Settings, roles: ["admin"], group: "admin" },
];

const NAV_KEYS: Record<string, string> = {
  Home: "nav.home",
  Chat: "nav.chat",
  Report: "nav.report",
  Status: "nav.status",
  Dashboard: "nav.dashboard",
  "Add Found": "nav.addFound",
  Found: "nav.found",
  Lost: "nav.lost",
  Matches: "nav.matches",
  Claims: "nav.claims",
  "QR Scan": "nav.qrScan",
  Analytics: "nav.analytics",
  Audit: "nav.audit",
  Operations: "nav.operations",
  Demo: "nav.demo",
  Users: "nav.users",
  Locations: "nav.locations",
  Categories: "nav.categories",
  Settings: "nav.settings",
};

const GROUP_LABELS: Record<NavItem["group"], string> = {
  general: "Public",
  staff: "Staff",
  admin: "Admin",
};

export function Shell() {
  const { user, logout, hasRole, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [language, setLanguage] = useState<Language>(loadLanguage());
  const visible = useMemo(() => navItems.filter((item) => !item.roles || hasRole(item.roles)), [hasRole]);
  const grouped = useMemo(() => {
    const map: Record<NavItem["group"], NavItem[]> = { general: [], staff: [], admin: [] };
    visible.forEach((item) => map[item.group].push(item));
    return map;
  }, [visible]);

  useEffect(() => {
    persistLanguage(language);
  }, [language]);

  const userInitials = (user?.name ?? "")
    .split(" ")
    .map((part) => part.charAt(0))
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="min-h-screen bg-mesh-light bg-ink-50">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-2xl focus:bg-navy-900 focus:px-3 focus:py-1.5 focus:text-white focus:shadow-card"
      >
        Skip to content
      </a>

      <aside className="fixed inset-y-0 start-0 hidden w-72 flex-col border-e border-ink-200/60 bg-white/80 backdrop-blur-xl lg:flex">
        <div className="flex h-16 items-center gap-3 border-b border-ink-200/60 px-6">
          <div className="grid h-10 w-10 place-items-center rounded-2xl bg-gradient-navy text-white shadow-navy">
            <Plane className="h-5 w-5 -rotate-45" />
          </div>
          <div>
            <p className="font-display text-sm font-semibold tracking-tight text-ink-900">Airport Ops</p>
            <p className="text-[11px] font-medium uppercase tracking-wider text-gold-700">Lost &amp; Found</p>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Primary">
          {(Object.keys(grouped) as NavItem["group"][]).map((groupKey) => {
            const items = grouped[groupKey];
            if (!items.length) return null;
            return (
              <div key={groupKey} className="mb-5 last:mb-0">
                <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-ink-400">
                  {GROUP_LABELS[groupKey]}
                </p>
                <div className="space-y-0.5">
                  {items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.to === "/"}
                      className={({ isActive }) =>
                        `group relative flex items-center gap-3 rounded-2xl px-3 py-2 text-[13px] font-medium tracking-tight transition-all duration-150 ease-apple ${
                          isActive
                            ? "bg-navy-50 text-navy-900"
                            : "text-ink-600 hover:bg-ink-100 hover:text-ink-900"
                        }`
                      }
                    >
                      {({ isActive }) => (
                        <>
                          {isActive ? (
                            <span className="absolute inset-y-2 start-0 w-0.5 rounded-full bg-gold-500" aria-hidden />
                          ) : null}
                          <item.icon className={`h-4 w-4 shrink-0 ${isActive ? "text-navy-700" : "text-ink-500 group-hover:text-ink-700"}`} />
                          <span>{translate(language, NAV_KEYS[item.label] ?? item.label)}</span>
                        </>
                      )}
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </nav>

        {user ? (
          <div className="border-t border-ink-200/60 p-4">
            <div className="flex items-center gap-3 rounded-2xl bg-ink-50 px-3 py-2">
              <div className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-navy text-xs font-semibold text-white">
                {userInitials || "OP"}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-ink-900">{user.name}</p>
                <p className="text-xs capitalize text-ink-500">{user.role}</p>
              </div>
              <button
                onClick={() => {
                  logout();
                  navigate("/");
                }}
                className="focus-ring rounded-xl p-1.5 text-ink-500 hover:bg-white hover:text-ink-900"
                title={translate(language, "shell.signOut")}
                aria-label={translate(language, "shell.signOut")}
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        ) : null}
      </aside>

      <div className="lg:ps-72">
        <header className="sticky top-0 z-30 border-b border-ink-200/60 glass">
          <div className="flex h-16 items-center justify-between px-4 lg:px-8">
            <div className="flex items-center gap-3">
              <div className="lg:hidden">
                <div className="grid h-9 w-9 place-items-center rounded-2xl bg-gradient-navy text-white shadow-navy">
                  <Plane className="h-4 w-4 -rotate-45" />
                </div>
              </div>
              <div>
                <p className="hidden text-[11px] font-semibold uppercase tracking-[0.18em] text-gold-700 lg:block">
                  {currentBreadcrumb(location.pathname)}
                </p>
                <p className="font-display text-sm font-semibold tracking-tight text-ink-900">
                  {translate(language, "shell.appName")}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setLanguage((current) => (current === "en" ? "ar" : "en"))}
                className="focus-ring inline-flex h-9 items-center gap-1.5 rounded-full border border-ink-200 bg-white px-3 text-xs font-semibold text-ink-700 hover:border-ink-300"
                aria-label="Toggle language"
              >
                <Languages className="h-3.5 w-3.5" />
                {translate(language, "language.toggle")}
              </button>
              {!user ? (
                <Button size="sm" onClick={() => navigate("/login")}>
                  {translate(language, "shell.signIn")}
                </Button>
              ) : null}
            </div>
          </div>
          {sessionExpired ? (
            <div className="border-t border-warn-500/20 bg-warn-50 px-4 py-2 text-sm text-warn-700 lg:px-8">
              <span className="inline-flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                {translate(language, "shell.sessionExpired")}
              </span>
            </div>
          ) : null}
        </header>

        <main id="main-content" className="mx-auto max-w-7xl px-4 py-8 lg:px-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function currentBreadcrumb(pathname: string): string {
  if (pathname === "/") return "Welcome";
  const segments = pathname.split("/").filter(Boolean);
  return segments.map((segment) => segment.replaceAll("-", " ")).join(" / ");
}

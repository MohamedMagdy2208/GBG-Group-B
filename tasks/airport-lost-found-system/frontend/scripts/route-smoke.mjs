import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const app = read("src/App.tsx");
const shell = read("src/components/Shell.tsx");
const operations = read("src/pages/AdminOperationsPage.tsx");

const expectedRoutes = [
  'path="chat"',
  'path="lost-report"',
  'path="status"',
  'path="staff"',
  'path="staff/found/new"',
  'path="staff/matches"',
  'path="staff/claims"',
  'path="staff/scan"',
  'path="admin/analytics"',
  'path="admin/audit"',
  'path="admin/operations"',
];

for (const route of expectedRoutes) {
  assert(app.includes(route), `Missing route: ${route}`);
}

for (const protectedRoute of ['roles={["staff", "admin", "security"]}', 'roles={["admin"]}']) {
  assert(app.includes(protectedRoute), `Missing protected route guard: ${protectedRoute}`);
}

for (const navLabel of ["Dashboard", "Add Found", "Matches", "Claims", "QR Scan", "Operations", "Audit"]) {
  assert(shell.includes(`label: "${navLabel}"`), `Missing nav label: ${navLabel}`);
}

for (const endpoint of [
  "/admin/search/recreate-index",
  "/admin/search/reindex-lost-reports",
  "/admin/search/reindex-found-items",
  "/admin/search/reindex-all?recreate_index=true",
  "/admin/matching/rerun-all",
]) {
  assert(operations.includes(endpoint), `Missing operations endpoint: ${endpoint}`);
}

console.log("Route smoke tests passed.");

function read(path) {
  return readFileSync(join(root, path), "utf8");
}

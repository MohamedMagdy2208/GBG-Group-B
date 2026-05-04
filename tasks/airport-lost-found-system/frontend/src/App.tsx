import { Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Shell } from "./components/Shell";
import { AddFoundItemPage } from "./pages/AddFoundItemPage";
import { AdminOperationsPage } from "./pages/AdminOperationsPage";
import { AnalyticsDashboard } from "./pages/AnalyticsDashboard";
import { AuditLogsPage } from "./pages/AuditLogsPage";
import { CategoriesManagement } from "./pages/CategoriesManagement";
import { ChatPage } from "./pages/ChatPage";
import { ClaimVerificationPage } from "./pages/ClaimVerificationPage";
import { CustodyTimelinePage } from "./pages/CustodyTimelinePage";
import { DemoConsolePage } from "./pages/DemoConsolePage";
import { FoundItemDetailPage } from "./pages/FoundItemDetailPage";
import { FoundItemListPage } from "./pages/FoundItemListPage";
import { LandingPage } from "./pages/LandingPage";
import { LocationsManagement } from "./pages/LocationsManagement";
import { LoginPage } from "./pages/LoginPage";
import { LostReportDetailPage } from "./pages/LostReportDetailPage";
import { LostReportForm } from "./pages/LostReportForm";
import { LostReportListPage } from "./pages/LostReportListPage";
import { MatchReviewPage } from "./pages/MatchReviewPage";
import { PhotoOnlyLostReportPage } from "./pages/PhotoOnlyLostReportPage";
import { ReportStatusPage } from "./pages/ReportStatusPage";
import { QRScanPage } from "./pages/QRScanPage";
import { SettingsPage } from "./pages/SettingsPage";
import { StaffDashboard } from "./pages/StaffDashboard";
import { UserManagement } from "./pages/UserManagement";

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<LandingPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="lost-report" element={<LostReportForm />} />
        <Route path="lost-report/photo" element={<PhotoOnlyLostReportPage />} />
        <Route path="status" element={<ReportStatusPage />} />
        <Route element={<ProtectedRoute roles={["staff", "admin", "security"]} />}>
          <Route path="staff" element={<StaffDashboard />} />
          <Route path="staff/found/new" element={<AddFoundItemPage />} />
          <Route path="staff/found" element={<FoundItemListPage />} />
          <Route path="staff/found/:id" element={<FoundItemDetailPage />} />
          <Route path="staff/found/:id/custody" element={<CustodyTimelinePage />} />
          <Route path="staff/lost" element={<LostReportListPage />} />
          <Route path="staff/lost/:id" element={<LostReportDetailPage />} />
          <Route path="staff/matches" element={<MatchReviewPage />} />
          <Route path="staff/claims" element={<ClaimVerificationPage />} />
          <Route path="staff/scan" element={<QRScanPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={["admin"]} />}>
          <Route path="admin/analytics" element={<AnalyticsDashboard />} />
          <Route path="admin/audit" element={<AuditLogsPage />} />
          <Route path="admin/users" element={<UserManagement />} />
          <Route path="admin/locations" element={<LocationsManagement />} />
          <Route path="admin/categories" element={<CategoriesManagement />} />
          <Route path="admin/settings" element={<SettingsPage />} />
          <Route path="admin/operations" element={<AdminOperationsPage />} />
          <Route path="admin/demo" element={<DemoConsolePage />} />
        </Route>
      </Route>
    </Routes>
  );
}

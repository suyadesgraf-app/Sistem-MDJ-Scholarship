import React, { useState } from "react";
import DashboardShell from "@/components/DashboardShell";
import StatsOverview from "@/components/StatsOverview";
import ParticipantsPanel from "@/components/ParticipantsPanel";
import AdminUsers from "@/components/AdminUsers";
import SiteManager from "@/components/SiteManager";
import CampusManager from "@/components/CampusManager";
import DisbursementManager from "@/components/DisbursementManager";
import ActiveLetterApprovalManager from "@/components/ActiveLetterApprovalManager";
import SelectionImportManager from "@/components/SelectionImportManager";
import AiAdministrativeVerification from "@/components/AiAdministrativeVerification";
import ApplicantArchiveManager from "@/components/ApplicantArchiveManager";
import AdminRecipientDashboard from "@/components/AdminRecipientDashboard";
import LiveChat from "@/components/LiveChat";
import {
  BarChart3,
  Building2,
  FileSpreadsheet,
  FileCheck2,
  HandCoins,
  Users,
  ShieldCheck,
  LayoutDashboard,
  Sparkles,
  Archive,
  MessageCircleMore,
} from "lucide-react";

const MENU = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "ringkasan", label: "Ringkasan", icon: BarChart3 },
  { id: "peserta", label: "Data Peserta", icon: Users },
  { id: "import-seleksi", label: "Import Seleksi", icon: FileSpreadsheet },
  { id: "verifikasi-ai", label: "Verifikasi AI", icon: Sparkles },
  { id: "surat-aktif", label: "Surat Aktif AI", icon: FileCheck2 },
  { id: "pencairan-dana", label: "Pencairan Dana", icon: HandCoins },
  { id: "kampus", label: "Kampus", icon: Building2 },
  { id: "admin", label: "Admin Wilayah", icon: ShieldCheck },
  { id: "live-chat", label: "Live Chat", icon: MessageCircleMore },
  { id: "arsip-pendaftar", label: "Arsip Pendaftar", icon: Archive },
  { id: "website", label: "Kelola Website", icon: LayoutDashboard },
];

export default function SuperAdminDashboard() {
  const [active, setActive] = useState("dashboard");
  return (
    <DashboardShell menu={MENU} active={active} onSelect={setActive} brandLabel="Super Admin"
      title={MENU.find((m) => m.id === active)?.label} subtitle="Panel kendali MDJ Scholarship">
      {active === "dashboard" && <AdminRecipientDashboard />}
      {active === "ringkasan" && <StatsOverview showAdmins />}
      {active === "peserta" && <ParticipantsPanel />}
      {active === "pencairan-dana" && <DisbursementManager />}
      {active === "admin" && <AdminUsers canManageProvincial />}
      {active === "verifikasi-ai" && <AiAdministrativeVerification />}
      {active === "import-seleksi" && <SelectionImportManager />}
      {active === "kampus" && <CampusManager />}
      {active === "surat-aktif" && <ActiveLetterApprovalManager />}
      {active === "live-chat" && <LiveChat />}
      {active === "arsip-pendaftar" && <ApplicantArchiveManager />}
      {active === "website" && <SiteManager />}
    </DashboardShell>
  );
}

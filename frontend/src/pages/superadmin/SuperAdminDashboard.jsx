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
import {
  Building2,
  FileSpreadsheet,
  FileCheck2,
  HandCoins,
  Home,
  Users,
  ShieldCheck,
  LayoutDashboard,
  Sparkles,
} from "lucide-react";

const MENU = [
  { id: "ringkasan", label: "Ringkasan", icon: Home },
  { id: "peserta", label: "Data Pendaftar", icon: Users },
  { id: "pencairan-dana", label: "Pencairan Dana", icon: HandCoins },
  { id: "admin", label: "Akun Admin", icon: ShieldCheck },
  { id: "verifikasi-ai", label: "Verifikasi AI", icon: Sparkles },
  { id: "import-seleksi", label: "Import Seleksi", icon: FileSpreadsheet },
  { id: "kampus", label: "Kampus", icon: Building2 },
  { id: "surat-aktif", label: "Surat Aktif AI", icon: FileCheck2 },
  { id: "website", label: "Kelola Website", icon: LayoutDashboard },
];

export default function SuperAdminDashboard() {
  const [active, setActive] = useState("ringkasan");
  return (
    <DashboardShell menu={MENU} active={active} onSelect={setActive} brandLabel="Super Admin"
      title={MENU.find((m) => m.id === active)?.label} subtitle="Panel kendali MDJ Scholarship">
      {active === "ringkasan" && <StatsOverview showAdmins />}
      {active === "peserta" && <ParticipantsPanel />}
      {active === "pencairan-dana" && <DisbursementManager />}
      {active === "admin" && <AdminUsers canManageProvincial />}
      {active === "verifikasi-ai" && <AiAdministrativeVerification />}
      {active === "import-seleksi" && <SelectionImportManager />}
      {active === "kampus" && <CampusManager />}
      {active === "surat-aktif" && <ActiveLetterApprovalManager />}
      {active === "website" && <SiteManager />}
    </DashboardShell>
  );
}

import React, { useMemo, useState } from "react";
import DashboardShell from "@/components/DashboardShell";
import AdminRecipientDashboard from "@/components/AdminRecipientDashboard";
import AdminRegistrationSummary from "@/components/AdminRegistrationSummary";
import ParticipantsPanel from "@/components/ParticipantsPanel";
import CampusManager from "@/components/CampusManager";
import DisbursementManager from "@/components/DisbursementManager";
import SelectionImportManager from "@/components/SelectionImportManager";
import AiAdministrativeVerification from "@/components/AiAdministrativeVerification";
import AdminUsers from "@/components/AdminUsers";
import { useAuth } from "@/context/AuthContext";
import {
  Building2,
  HandCoins,
  FileSpreadsheet,
  Home,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";

const BASE_MENU = [
  { id: "dashboard", label: "Dashboard", icon: Home },
  { id: "ringkasan", label: "Ringkasan", icon: Home },
  { id: "peserta", label: "Data Peserta", icon: Users },
  { id: "pencairan-dana", label: "Pencairan Dana", icon: HandCoins },
  { id: "verifikasi-ai", label: "Verifikasi AI", icon: Sparkles },
  { id: "import-seleksi", label: "Import Seleksi", icon: FileSpreadsheet },
];

export default function AdminDashboard() {
  const { user } = useAuth();
  const [active, setActive] = useState("ringkasan");
  const isRegionalAdmin = user?.role === "admin_wilayah";
  const menu = useMemo(() => {
    if (isRegionalAdmin) return BASE_MENU;
    return [
      ...BASE_MENU,
      { id: "kampus", label: "Kampus", icon: Building2 },
      { id: "admin-wilayah", label: "Admin Wilayah", icon: ShieldCheck },
    ];
  }, [isRegionalAdmin]);
  const activeMenu = menu.find((item) => item.id === active);
  const subtitle = isRegionalAdmin
    ? `Kelola data peserta ${user?.region || "wilayah kerja"}`
    : "Kelola data peserta MDJ Scholarship";

  return (
    <DashboardShell
      menu={menu}
      active={active}
      onSelect={setActive}
      brandLabel={isRegionalAdmin ? "Admin Wilayah" : "Admin Provinsi"}
      title={activeMenu?.label}
      subtitle={subtitle}
    >
      {active === "dashboard" && <AdminRecipientDashboard />}
      {active === "ringkasan" && <AdminRegistrationSummary />}
      {active === "peserta" && <ParticipantsPanel />}
      {active === "pencairan-dana" && <DisbursementManager />}
      {active === "verifikasi-ai" && <AiAdministrativeVerification />}
      {active === "import-seleksi" && <SelectionImportManager />}
      {active === "kampus" && <CampusManager />}
      {active === "admin-wilayah" && <AdminUsers canManageProvincial={false} />}
    </DashboardShell>
  );
}

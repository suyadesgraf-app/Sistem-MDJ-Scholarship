import React, { useState } from "react";
import DashboardShell from "@/components/DashboardShell";
import StatsOverview from "@/components/StatsOverview";
import ParticipantsPanel from "@/components/ParticipantsPanel";
import AdminUsers from "@/components/AdminUsers";
import SiteManager from "@/components/SiteManager";
import { Home, Users, ShieldCheck, LayoutDashboard } from "lucide-react";

const MENU = [
  { id: "ringkasan", label: "Ringkasan", icon: Home },
  { id: "peserta", label: "Data Pendaftar", icon: Users },
  { id: "admin", label: "Akun Admin", icon: ShieldCheck },
  { id: "website", label: "Kelola Website", icon: LayoutDashboard },
];

export default function SuperAdminDashboard() {
  const [active, setActive] = useState("ringkasan");
  return (
    <DashboardShell menu={MENU} active={active} onSelect={setActive} brandLabel="Super Admin"
      title={MENU.find((m) => m.id === active)?.label} subtitle="Panel kendali MDJ Scholarship">
      {active === "ringkasan" && <StatsOverview showAdmins />}
      {active === "peserta" && <ParticipantsPanel />}
      {active === "admin" && <AdminUsers />}
      {active === "website" && <SiteManager />}
    </DashboardShell>
  );
}

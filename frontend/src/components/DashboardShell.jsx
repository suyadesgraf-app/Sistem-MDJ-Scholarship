import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  Menu,
  X,
  LogOut,
  ChevronDown,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import HeaderNotifications from "@/components/HeaderNotifications";
import api, { API } from "@/lib/api";

const STATUS_META = {
  draft: { label: "Draft", cls: "bg-gray-100 text-gray-600" },
  submitted: { label: "Terkirim", cls: "bg-blue-50 text-blue-700" },
  perlu_perbaikan: { label: "Perlu Perbaikan Berkas", cls: "bg-[#FFFBEB] text-[#7A5C00]" },
  verifikasi: { label: "Verifikasi Administrasi", cls: "bg-[#FEF9E7] text-[#7a5c00]" },
  lolos_administrasi: { label: "Lolos Administrasi", cls: "bg-[#E8F6EE] text-[#0B6B3A]" },
  wawancara: { label: "Wawancara", cls: "bg-purple-50 text-purple-700" },
  verifikasi_faktual: { label: "Verifikasi Faktual", cls: "bg-orange-50 text-orange-700" },
  lolos: { label: "Lolos / Penerima", cls: "bg-[#E8F6EE] text-[#0B6B3A]" },
  ditolak: { label: "Tidak Lolos", cls: "bg-[#FEE2E2] text-[#DC2626]" },
};

export function StatusBadge({ status }) {
  const m = STATUS_META[status] || STATUS_META.draft;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold ${m.cls}`}
      data-testid={`status-badge-${status}`}
    >
      {m.label}
    </span>
  );
}
export { STATUS_META };

function SidebarTooltip({ children }) {
  return (
    <span
      role="tooltip"
      className={[
        "pointer-events-none absolute left-[calc(100%+10px)] top-1/2 z-[60]",
        "-translate-y-1/2 whitespace-nowrap rounded-lg bg-[#1F2937] px-3 py-2",
        "text-xs font-bold text-white opacity-0 shadow-lg transition-opacity",
        "group-hover:opacity-100 group-focus-within:opacity-100",
      ].join(" ")}
    >
      {children}
    </span>
  );
}

function DashboardSidebar({
  active,
  brandLabel,
  collapsed,
  logoUrl,
  menu,
  mobile = false,
  onLogout,
  onMenuSelect,
  onToggleCollapse,
}) {
  return (
    <div
      className="flex h-full flex-col"
      data-testid={mobile ? "mobile-sidebar" : "sidebar"}
    >
      <div
        className={[
          "flex h-16 items-center border-b border-gray-100",
          collapsed ? "justify-center px-3" : "gap-2.5 px-5",
        ].join(" ")}
      >
        <div className="h-9 w-9 overflow-hidden rounded-lg bg-[#27AE60]">
          {logoUrl ? (
            <img
              src={logoUrl}
              alt="Logo MDJ Scholarship"
              className="h-full w-full object-contain"
              data-testid={mobile ? "mobile-sidebar-brand-logo" : "sidebar-brand-logo"}
            />
          ) : (
            <span
              className="flex h-full w-full items-center justify-center text-xs font-black text-white"
            >
              MDJ
            </span>
          )}
        </div>
        {!collapsed && (
          <div className="min-w-0 leading-tight">
            <p className="truncate font-display text-sm font-extrabold text-[#1F2937]">
              MDJ Scholarship
            </p>
            <p className="truncate text-[10px] font-semibold text-[#6B7280]">{brandLabel}</p>
          </div>
        )}
      </div>
      <nav
        className={[
          "mdj-scrollbar min-h-0 flex-1 space-y-1 overflow-x-hidden overflow-y-auto",
          collapsed ? "px-2 py-3" : "p-3",
        ].join(" ")}
      >
        {menu.map((item) => {
          const isActive = active === item.id;
          return (
            <div key={item.id} className="group relative">
              <button
                type="button"
                onClick={() => onMenuSelect(item.id)}
                data-testid={mobile ? `mobile-menu-${item.id}` : `menu-${item.id}`}
                aria-label={collapsed ? item.label : undefined}
                title={collapsed ? item.label : undefined}
                className={[
                  "flex w-full items-center rounded-lg py-2.5 text-left text-sm font-semibold",
                  "transition-colors",
                  collapsed ? "justify-center px-2" : "gap-3 px-3",
                  isActive
                    ? "border-l-4 border-[#27AE60] bg-[#E8F6EE] text-[#0B6B3A]"
                    : "border-l-4 border-transparent text-[#6B7280] hover:bg-gray-50",
                ].join(" ")}
              >
                <item.icon className="h-5 w-5 shrink-0" />
                {collapsed ? <span className="sr-only">{item.label}</span> : (
                  <span className="whitespace-nowrap">{item.label}</span>
                )}
              </button>
            </div>
          );
        })}
      </nav>
      <div
        className={collapsed ? "border-t border-gray-100 p-2" : "border-t border-gray-100 p-3"}
      >
        <div className={collapsed ? "space-y-1" : "flex items-center gap-2"}>
          <div className={collapsed ? "group relative" : "group relative order-2 shrink-0"}>
            <button
              type="button"
              onClick={onToggleCollapse}
              data-testid={mobile ? "mobile-sidebar-collapse-toggle" : "sidebar-collapse-toggle"}
              aria-label={collapsed ? "Buka sidebar" : "Tutup sidebar"}
              className={[
                "flex items-center rounded-lg text-sm font-semibold text-[#374151]",
                "transition-colors hover:bg-gray-100",
                collapsed ? "w-full justify-center px-2 py-2.5" : "h-10 w-10 justify-center",
              ].join(" ")}
            >
              {collapsed ? (
                <PanelLeftOpen className="h-5 w-5" />
              ) : (
                <PanelLeftClose className="h-5 w-5" />
              )}
              <span className="sr-only">{collapsed ? "Buka sidebar" : "Tutup sidebar"}</span>
            </button>
            <SidebarTooltip>{collapsed ? "Buka sidebar" : "Tutup sidebar"}</SidebarTooltip>
          </div>
          <div
            className={[
              collapsed ? "group relative mt-1" : "group relative order-1 min-w-0 flex-1",
            ].join(" ")}
          >
            <button
              type="button"
              onClick={onLogout}
              data-testid={mobile ? "mobile-logout-btn" : "logout-btn"}
              aria-label={collapsed ? "Keluar" : undefined}
              className={[
                "flex w-full items-center rounded-lg py-2.5 text-sm font-semibold text-[#DC2626]",
                "transition-colors hover:bg-[#FEE2E2]",
                collapsed ? "justify-center px-2" : "justify-center gap-2 px-3",
              ].join(" ")}
            >
              <LogOut className="h-5 w-5 shrink-0" />
              {collapsed ? <span className="sr-only">Keluar</span> : <span>Keluar</span>}
            </button>
            {collapsed && <SidebarTooltip>Keluar</SidebarTooltip>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DashboardShell({
  menu,
  active,
  onSelect,
  title,
  subtitle,
  actions,
  children,
  brandLabel,
  avatarUrl,
  candidateId,
  notifications = [],
  unreadNotificationCount = 0,
  onNotificationClick,
  onReadAllNotifications,
  displayName,
}) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [logoUrl, setLogoUrl] = useState(null);
  const identityUser = displayName?.trim() ? { ...user, name: displayName.trim() } : user;

  useEffect(() => {
    api.get("/site/content")
      .then((response) => {
        const path = response.data.logo_url;
        setLogoUrl(path ? `${API.replace("/api", "")}${path}` : null);
      })
      .catch(() => setLogoUrl(null));
  }, []);

  const doLogout = async () => { await logout(); navigate("/", { replace: true }); };
  const handleMenuSelect = (menuId) => {
    onSelect(menuId);
    setOpen(false);
  };
  const toggleSidebar = () => setCollapsed((isCollapsed) => !isCollapsed);

  return (
    <div className="min-h-screen bg-[#F9FAFB] flex">
      <aside
        data-testid="desktop-sidebar-container"
        className={[
          "fixed inset-y-0 left-0 z-30 hidden border-r border-gray-100 bg-white",
          "transition-[width] duration-300 lg:flex",
          collapsed ? "w-20" : "w-64",
        ].join(" ")}
      >
        <DashboardSidebar
          active={active}
          brandLabel={brandLabel}
          collapsed={collapsed}
          logoUrl={logoUrl}
          menu={menu}
          onLogout={doLogout}
          onMenuSelect={handleMenuSelect}
          onToggleCollapse={toggleSidebar}
        />
      </aside>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          data-testid="mobile-sidebar-overlay"
          onClick={() => setOpen(false)}
        />
      )}
      <aside
        data-testid="mobile-sidebar-container"
        className={[
          "fixed inset-y-0 left-0 z-50 bg-white transition-[transform,width] duration-300",
          "lg:hidden",
          collapsed ? "w-20" : "w-64",
          open ? "translate-x-0" : "-translate-x-full",
        ].join(" ")}
      >
        <DashboardSidebar
          active={active}
          brandLabel={brandLabel}
          collapsed={collapsed}
          logoUrl={logoUrl}
          menu={menu}
          mobile
          onLogout={doLogout}
          onMenuSelect={handleMenuSelect}
          onToggleCollapse={toggleSidebar}
        />
      </aside>

      <div
        className={[
          "min-w-0 flex-1 transition-[margin] duration-300",
          collapsed ? "lg:ml-20" : "lg:ml-64",
        ].join(" ")}
      >
        <header
          className={[
            "sticky top-0 z-20 flex h-16 items-center justify-between border-b",
            "border-gray-100 bg-white/90 px-4 backdrop-blur-xl sm:px-6",
          ].join(" ")}
        >
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              className="-ml-2 p-2 lg:hidden"
              onClick={() => setOpen(true)}
              data-testid="sidebar-toggle"
              aria-label="Buka menu"
            >
              <Menu className="h-6 w-6 text-[#1F2937]" />
            </button>
            <div className="min-w-0">
              <h1 className="font-display font-bold text-lg text-[#1F2937] truncate">{title}</h1>
              {subtitle && <p className="text-xs text-[#6B7280] truncate">{subtitle}</p>}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {actions}
            {candidateId ? (
              <CandidateIdentity
                avatarUrl={avatarUrl}
                candidateId={candidateId}
                user={identityUser}
                notifications={notifications}
                unreadNotificationCount={unreadNotificationCount}
                onNotificationClick={onNotificationClick}
                onReadAllNotifications={onReadAllNotifications}
              />
            ) : (
              <AccountIdentity avatarUrl={avatarUrl} user={identityUser} />
            )}
          </div>
        </header>
        <main className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto">{children}</main>
      </div>
    </div>
  );
}

function Avatar({ avatarUrl, user }) {
  return (
    <div
      className={[
        "relative flex h-9 w-9 items-center justify-center overflow-hidden rounded-full",
        "bg-[#E8F6EE] text-sm font-bold text-[#0B6B3A]",
      ].join(" ")}
      data-testid="header-profile-avatar"
    >
      <span data-testid="header-profile-initial">
        {(user?.name || "?").charAt(0).toUpperCase()}
      </span>
      {avatarUrl && (
        <img
          src={avatarUrl}
          alt={`Foto profil ${user?.name || "mahasiswa"}`}
          className="absolute inset-0 h-full w-full object-cover"
          data-testid="header-profile-photo"
          onError={(event) => {
            event.currentTarget.style.display = "none";
          }}
        />
      )}
    </div>
  );
}

function CandidateIdentity({
  avatarUrl,
  candidateId,
  user,
  notifications,
  unreadNotificationCount,
  onNotificationClick,
  onReadAllNotifications,
}) {
  return (
    <div className="flex items-center gap-3" data-testid="header-candidate-identity">
      <HeaderNotifications
        notifications={notifications}
        unreadCount={unreadNotificationCount}
        onNotificationClick={onNotificationClick}
        onReadAll={onReadAllNotifications}
      />
      <div className="hidden min-w-0 border-l border-gray-200 pl-4 sm:block">
        <p
          className="max-w-[160px] truncate text-sm font-bold text-[#1F2937]"
          data-testid="candidate-display-name"
        >
          {user?.name}
        </p>
        <p className="text-xs font-semibold text-[#6B7280]" data-testid="candidate-role-label">
          Calon Penerima Manfaat
        </p>
        <p className="text-xs text-[#6B7280]" data-testid="candidate-id-value">
          ID: {candidateId}
        </p>
      </div>
      <Avatar avatarUrl={avatarUrl} user={user} />
    </div>
  );
}

function AccountIdentity({ avatarUrl, user }) {
  const roleLabel = {
    admin: "Admin Provinsi",
    admin_wilayah: "Admin Wilayah",
    super_admin: "Super Admin",
    student: "Mahasiswa",
  }[user?.role] || "";
  return (
    <div className="flex items-center gap-2 border-l border-gray-200 pl-3">
      <Avatar avatarUrl={avatarUrl} user={user} />
      <div className="hidden leading-tight sm:block">
        <p className="max-w-[140px] truncate text-sm font-semibold text-[#1F2937]">
          {user?.name}
        </p>
        <p className="text-[11px] text-[#6B7280]" data-testid="header-role-label">
          {roleLabel}
        </p>
      </div>
    </div>
  );
}

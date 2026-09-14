import React, { useState } from "react";
import { Bell, CheckCheck, Inbox, Megaphone, Route } from "lucide-react";

const typeIcon = {
  announcement: Megaphone,
  selection_result: Megaphone,
  selection_progress: Route,
};

export default function HeaderNotifications({
  notifications,
  unreadCount,
  onNotificationClick,
  onReadAll,
}) {
  const [open, setOpen] = useState(false);
  const visibleNotifications = notifications.slice(0, 5);

  const handleNotificationClick = async (notification) => {
    await onNotificationClick(notification);
    setOpen(false);
  };

  return (
    <div className="relative" data-testid="header-notification-indicator">
      <button
        type="button"
        onClick={() => setOpen((previous) => !previous)}
        aria-expanded={open}
        aria-label="Buka notifikasi"
        data-testid="header-notification-button"
        className="relative flex h-9 w-9 items-center justify-center rounded-full text-[#6B7280] transition-colors hover:bg-gray-100"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span
            className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-[#DC2626]"
            data-testid="header-notification-unread-dot"
          />
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 top-11 z-50 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl"
          data-testid="notification-popover"
        >
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <div>
              <p className="text-sm font-bold text-[#1F2937]">Notifikasi</p>
              <p className="text-xs text-[#6B7280]" data-testid="notification-unread-count">
                {unreadCount > 0 ? `${unreadCount} belum dibaca` : "Semua sudah dibaca"}
              </p>
            </div>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={onReadAll}
                data-testid="mark-all-notifications-read"
                className="flex items-center gap-1 text-xs font-bold text-[#0B6B3A] hover:underline"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Tandai dibaca
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto" data-testid="notification-list">
            {visibleNotifications.length === 0 ? (
              <div className="px-4 py-8 text-center" data-testid="empty-notification-state">
                <Inbox className="mx-auto h-6 w-6 text-gray-300" />
                <p className="mt-2 text-sm font-semibold text-[#6B7280]">Belum ada notifikasi</p>
              </div>
            ) : (
              visibleNotifications.map((notification) => {
                const Icon = typeIcon[notification.type] || Bell;
                return (
                  <button
                    key={notification.id}
                    type="button"
                    onClick={() => handleNotificationClick(notification)}
                    data-testid={`notification-item-${notification.id}`}
                    className={[
                      "flex w-full gap-3 border-b border-gray-100 px-4 py-3 text-left",
                      "transition-colors hover:bg-[#F0FBF5]",
                      notification.is_read ? "bg-white" : "bg-[#F7FCF9]",
                    ].join(" ")}
                  >
                    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#E8F6EE]">
                      <Icon className="h-4 w-4 text-[#0B6B3A]" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-bold text-[#1F2937]">
                        {notification.title}
                      </span>
                      <span className="mt-0.5 block line-clamp-2 text-xs leading-relaxed text-[#6B7280]">
                        {notification.message}
                      </span>
                    </span>
                    {!notification.is_read && (
                      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[#27AE60]" />
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
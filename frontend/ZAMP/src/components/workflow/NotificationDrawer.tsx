import type { FC } from 'react';
import { useState, useEffect, useRef } from 'react';
import {
  Bell,
  Check,
  CheckCircle,
  WarningCircle,
  Info,
  ArrowsClockwise,
  X,
  FileArrowUp,
  XCircle,
} from '@phosphor-icons/react';
import {
  getAdminNotifications,
  getVendorNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  type NotificationItem,
} from '../../services/workflowService';

interface NotificationDrawerProps {
  recipientType: 'admin' | 'vendor';
  vendorId?: string | null;
  onSelectApplication?: (applicationId: string) => void;
}

export const NotificationDrawer: FC<NotificationDrawerProps> = ({
  recipientType,
  vendorId,
  onSelectApplication,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const res =
        recipientType === 'admin'
          ? await getAdminNotifications(40)
          : vendorId
          ? await getVendorNotifications(vendorId, 40)
          : { items: [], unread_count: 0, total_count: 0 };

      setNotifications(res.items);
      setUnreadCount(res.unread_count);
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 20_000); // Polling every 20s
    return () => clearInterval(interval);
  }, [recipientType, vendorId]);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleMarkRead = async (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (err) {
      console.error('Error marking notification read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead(recipientType, vendorId || undefined);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('Error marking all notifications read:', err);
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'approval':
        return <CheckCircle size={16} weight="fill" className="text-emerald-500" />;
      case 'rejection':
        return <XCircle size={16} weight="fill" className="text-rose-500" />;
      case 'clarification':
        return <WarningCircle size={16} weight="fill" className="text-amber-500" />;
      case 'resubmission':
        return <FileArrowUp size={16} weight="bold" className="text-indigo-500" />;
      default:
        return <Info size={16} weight="fill" className="text-[#1F211F]" />;
    }
  };

  return (
    <div className="relative" ref={drawerRef}>
      {/* Bell Button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="relative p-2 rounded-xl border border-slate-200/90 bg-white hover:bg-slate-50 text-slate-700 transition-colors cursor-pointer"
        title="Notifications"
        aria-label="Open notifications"
      >
        <Bell size={18} weight="bold" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-rose-500 text-white text-[10px] font-semibold flex items-center justify-center animate-pulse">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Popover Card */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-[32px] shadow-2xl shadow-slate-300/80 border border-slate-200 z-50 overflow-hidden text-left animate-fadeIn">
          {/* Header */}
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider">
                Notifications
              </h3>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 font-semibold text-[10px] border border-rose-200">
                  {unreadCount} new
                </span>
              )}
            </div>

            <div className="flex items-center space-x-1.5">
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={handleMarkAllRead}
                  className="text-[11px] font-semibold text-[#1F211F] hover:text-[#053e70] cursor-pointer flex items-center space-x-1"
                >
                  <Check size={12} weight="bold" />
                  <span>Mark all read</span>
                </button>
              )}
              <button
                type="button"
                onClick={fetchNotifications}
                className="p-1 rounded text-slate-400 hover:text-slate-600 cursor-pointer"
                title="Refresh notifications"
              >
                <ArrowsClockwise size={13} className={loading ? 'animate-spin' : ''} />
              </button>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X size={14} />
              </button>
            </div>
          </div>

          {/* Notification List */}
          <div className="max-h-96 overflow-y-auto divide-y divide-slate-100 text-xs">
            {notifications.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                <Bell size={24} className="mx-auto mb-2 text-slate-300" />
                <p>No notifications yet.</p>
              </div>
            ) : (
              notifications.map((notif) => {
                const formattedTime = new Date(notif.created_at).toLocaleString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                });

                return (
                  <div
                    key={notif.id}
                    onClick={() => {
                      if (!notif.is_read) handleMarkRead(notif.id);
                      if (notif.application_id && onSelectApplication) {
                        onSelectApplication(notif.application_id);
                        setIsOpen(false);
                      }
                    }}
                    className={`p-3.5 hover:bg-slate-50 transition-colors cursor-pointer flex items-start space-x-3 ${
                      !notif.is_read ? 'bg-blue-50/40' : 'bg-white'
                    }`}
                  >
                    <div className="mt-0.5 shrink-0">
                      {getNotificationIcon(notif.notification_type)}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h4
                          className={`text-xs ${
                            !notif.is_read
                              ? 'font-semibold text-slate-900'
                              : 'font-semibold text-slate-700'
                          }`}
                        >
                          {notif.title}
                        </h4>
                        <span className="text-[10px] text-slate-400 font-mono shrink-0 ml-2">
                          {formattedTime}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 mt-0.5 leading-relaxed line-clamp-3">
                        {notif.message}
                      </p>
                    </div>

                    {!notif.is_read && (
                      <button
                        type="button"
                        onClick={(e) => handleMarkRead(notif.id, e)}
                        className="w-2 h-2 rounded-full bg-[#1F211F] hover:scale-125 transition-transform mt-1 shrink-0 cursor-pointer"
                        title="Mark as read"
                      />
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};


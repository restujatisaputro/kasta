import { apiRequest, bearerHeaders } from './client';

export interface KastaNotification {
  id: string;
  business_id: string;
  notification_type: string;
  title: string;
  message: string;
  entity_type: string;
  entity_id: string;
  action_path: string | null;
  available_at: string | null;
  read_at: string | null;
  created_at: string;
}

export interface NotificationPreference {
  category: string;
  label: string;
  enabled: boolean;
  local_enabled: boolean;
  push_enabled: boolean;
  email_enabled: boolean;
  reminder_time: string;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  timezone: string;
}

function base(businessId: string): string {
  return `/businesses/${businessId}/notifications`;
}

export function getNotifications(businessId: string, token: string): Promise<KastaNotification[]> {
  return apiRequest(base(businessId), { headers: bearerHeaders(token) });
}

export function evaluateNotifications(
  businessId: string,
  token: string,
): Promise<{ generated_count: number; skipped_count: number }> {
  return apiRequest(`${base(businessId)}/evaluate`, {
    method: 'POST',
    headers: bearerHeaders(token),
  });
}

export function getUnreadCount(
  businessId: string,
  token: string,
): Promise<{ unread_count: number }> {
  return apiRequest(`${base(businessId)}/unread-count`, { headers: bearerHeaders(token) });
}

export function markNotificationRead(
  businessId: string,
  notificationId: string,
  token: string,
): Promise<KastaNotification> {
  return apiRequest(`${base(businessId)}/${notificationId}/read`, {
    method: 'POST',
    headers: bearerHeaders(token),
  });
}

export function markAllNotificationsRead(businessId: string, token: string): Promise<void> {
  return apiRequest(`${base(businessId)}/read-all`, {
    method: 'POST',
    headers: bearerHeaders(token),
  });
}

export function getNotificationPreferences(
  businessId: string,
  token: string,
): Promise<NotificationPreference[]> {
  return apiRequest(`${base(businessId)}/preferences`, { headers: bearerHeaders(token) });
}

export function updateNotificationPreferences(
  businessId: string,
  token: string,
  items: NotificationPreference[],
): Promise<NotificationPreference[]> {
  return apiRequest(`${base(businessId)}/preferences`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(token) },
    body: JSON.stringify({
      items: items.map((item) => ({
        category: item.category,
        enabled: item.enabled,
        local_enabled: item.local_enabled,
        push_enabled: item.push_enabled,
        email_enabled: item.email_enabled,
        reminder_time: item.reminder_time,
        quiet_hours_start: item.quiet_hours_start,
        quiet_hours_end: item.quiet_hours_end,
        timezone: item.timezone,
      })),
    }),
  });
}

export function notificationHref(businessId: string, actionPath: string | null): string {
  if (!actionPath) return `/usaha/${businessId}`;
  if (actionPath === '/sinkronisasi') return `/usaha/${businessId}/pengaturan`;
  return `/usaha/${businessId}${actionPath}`;
}

import type {
  MentorAggregateReport,
  MentorAuditActivity,
  MentorAccessGrant,
  MentorAccessHistory,
  MentorAccessScope,
  MentorBusinessDetail,
  MentorDashboard,
  MentoringSession,
  MentoringSessionStatus,
  MentorNote,
  MentorRecommendation,
  RecommendationStatus,
  ReportExportFormat,
} from '@kasta/contracts';

import { publicConfig } from '$lib/config/public';

import { ApiError, apiRequest, bearerHeaders } from './client';

function jsonHeaders(token: string): HeadersInit {
  return { 'Content-Type': 'application/json', ...bearerHeaders(token) };
}

export function getMentorDashboard(token: string): Promise<MentorDashboard> {
  return apiRequest('/mentors/me/dashboard', { headers: bearerHeaders(token) });
}

export function getMentorBusiness(
  token: string,
  businessId: string,
): Promise<MentorBusinessDetail> {
  return apiRequest(`/mentors/me/businesses/${businessId}`, { headers: bearerHeaders(token) });
}

export function getMentorReport(token: string): Promise<MentorAggregateReport> {
  return apiRequest('/mentors/me/report', { headers: bearerHeaders(token) });
}

export function getMentorAudit(token: string): Promise<MentorAuditActivity[]> {
  return apiRequest('/mentors/me/audit', { headers: bearerHeaders(token) });
}

export function requestMentorAccess(
  token: string,
  input: { business_id: string; requested_scope: MentorAccessScope[]; message: string | null },
): Promise<MentorAccessGrant> {
  return apiRequest('/mentors/me/access-requests', {
    method: 'POST',
    headers: jsonHeaders(token),
    body: JSON.stringify(input),
  });
}

export function getMyMentorAccess(token: string): Promise<MentorAccessGrant[]> {
  return apiRequest('/mentors/me/access-requests', { headers: bearerHeaders(token) });
}

export function getBusinessMentorAccess(
  token: string,
  businessId: string,
): Promise<MentorAccessGrant[]> {
  return apiRequest(`/businesses/${businessId}/mentor-access`, {
    headers: bearerHeaders(token),
  });
}

export function decideMentorAccess(
  token: string,
  businessId: string,
  accessId: string,
  input: {
    decision: 'APPROVE' | 'REJECT';
    scope: MentorAccessScope[];
    expires_at: string | null;
    reason: string | null;
  },
): Promise<MentorAccessGrant> {
  return apiRequest(`/businesses/${businessId}/mentor-access/${accessId}/decision`, {
    method: 'PATCH',
    headers: jsonHeaders(token),
    body: JSON.stringify(input),
  });
}

export function revokeMentorAccess(
  token: string,
  businessId: string,
  accessId: string,
  reason: string,
): Promise<MentorAccessGrant> {
  return apiRequest(`/businesses/${businessId}/mentor-access/${accessId}/revoke`, {
    method: 'POST',
    headers: jsonHeaders(token),
    body: JSON.stringify({ reason }),
  });
}

export function getMentorAccessHistory(
  token: string,
  businessId: string,
): Promise<MentorAccessHistory[]> {
  return apiRequest(`/businesses/${businessId}/mentor-access/history`, {
    headers: bearerHeaders(token),
  });
}

export function createMentorNote(
  token: string,
  businessId: string,
  input: { content: string; visibility: 'SHARED' | 'PRIVATE' },
): Promise<MentorNote> {
  return apiRequest(`/mentors/me/businesses/${businessId}/notes`, {
    method: 'POST',
    headers: jsonHeaders(token),
    body: JSON.stringify(input),
  });
}

export function createMentorRecommendation(
  token: string,
  businessId: string,
  input: {
    title: string;
    description: string;
    priority: 'LOW' | 'MEDIUM' | 'HIGH';
    due_date: string | null;
  },
): Promise<MentorRecommendation> {
  return apiRequest(`/mentors/me/businesses/${businessId}/recommendations`, {
    method: 'POST',
    headers: jsonHeaders(token),
    body: JSON.stringify(input),
  });
}

export function updateMentorRecommendation(
  token: string,
  businessId: string,
  recommendationId: string,
  input: { status: RecommendationStatus; follow_up_note: string | null },
): Promise<MentorRecommendation> {
  return apiRequest(`/mentors/me/businesses/${businessId}/recommendations/${recommendationId}`, {
    method: 'PATCH',
    headers: jsonHeaders(token),
    body: JSON.stringify(input),
  });
}

export function createMentoringSession(
  token: string,
  businessId: string,
  input: {
    scheduled_at: string;
    duration_minutes: number;
    mode: 'ONSITE' | 'ONLINE' | 'PHONE';
    topic: string;
    location: string | null;
  },
): Promise<MentoringSession> {
  return apiRequest(`/mentors/me/businesses/${businessId}/sessions`, {
    method: 'POST',
    headers: jsonHeaders(token),
    body: JSON.stringify(input),
  });
}

export function updateMentoringSession(
  token: string,
  businessId: string,
  sessionId: string,
  input: {
    status: MentoringSessionStatus;
    outcome: string | null;
    follow_up_date: string | null;
  },
): Promise<MentoringSession> {
  return apiRequest(`/mentors/me/businesses/${businessId}/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: jsonHeaders(token),
    body: JSON.stringify(input),
  });
}

export async function exportMentorReport(token: string, format: ReportExportFormat): Promise<void> {
  const response = await fetch(
    `${publicConfig.apiBaseUrl}/mentors/me/report/export?format=${format}`,
    { headers: bearerHeaders(token), credentials: 'include' },
  );
  if (!response.ok) {
    const problem = (await response.json().catch(() => undefined)) as
      { detail?: string } | undefined;
    throw new ApiError(
      problem?.detail ?? 'Laporan pembinaan belum dapat diunduh.',
      response.status,
    );
  }
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `laporan-pembinaan-kasta.${format.toLowerCase()}`;
  anchor.click();
  URL.revokeObjectURL(url);
}

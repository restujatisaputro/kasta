import type {
  Obligation,
  ObligationAgingReport,
  ObligationDetail,
  ObligationInput,
  ObligationKind,
  ObligationListResponse,
  ObligationPaymentInput,
  ObligationReminderList,
  ObligationStatus,
} from '@kasta/contracts';

import { apiRequest, bearerHeaders } from './client';

function resource(kind: ObligationKind): 'receivables' | 'payables' {
  return kind === 'RECEIVABLE' ? 'receivables' : 'payables';
}

function base(businessId: string): string {
  return `/businesses/${businessId}`;
}

export function getObligations(
  businessId: string,
  token: string,
  kind: ObligationKind,
  filters: {
    q?: string;
    status?: ObligationStatus | '';
    due_from?: string;
    due_to?: string;
    overdue_only?: boolean;
  } = {},
): Promise<ObligationListResponse> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== '' && value !== false) params.set(key, String(value));
  }
  const query = params.size ? `?${params}` : '';
  return apiRequest(`${base(businessId)}/${resource(kind)}${query}`, {
    headers: bearerHeaders(token),
  });
}

export function createObligation(
  businessId: string,
  token: string,
  kind: ObligationKind,
  payload: ObligationInput,
): Promise<Obligation> {
  return apiRequest(`${base(businessId)}/${resource(kind)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(token) },
    body: JSON.stringify(payload),
  });
}

export function getObligation(
  businessId: string,
  token: string,
  kind: ObligationKind,
  obligationId: string,
): Promise<ObligationDetail> {
  return apiRequest(`${base(businessId)}/${resource(kind)}/${obligationId}`, {
    headers: bearerHeaders(token),
  });
}

export function payObligation(
  businessId: string,
  token: string,
  kind: ObligationKind,
  obligationId: string,
  payload: ObligationPaymentInput,
): Promise<ObligationDetail> {
  return apiRequest(`${base(businessId)}/${resource(kind)}/${obligationId}/payments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(token) },
    body: JSON.stringify(payload),
  });
}

export function cancelObligation(
  businessId: string,
  token: string,
  kind: ObligationKind,
  obligationId: string,
  reason: string,
): Promise<Obligation> {
  return apiRequest(`${base(businessId)}/${resource(kind)}/${obligationId}/cancellation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(token) },
    body: JSON.stringify({ reason, cancellation_date: new Date().toISOString().slice(0, 10) }),
  });
}

export function getObligationAging(
  businessId: string,
  token: string,
): Promise<ObligationAgingReport> {
  return apiRequest(`${base(businessId)}/obligations/aging`, {
    headers: bearerHeaders(token),
  });
}

export function getObligationReminders(
  businessId: string,
  token: string,
): Promise<ObligationReminderList> {
  return apiRequest(`${base(businessId)}/obligations/reminders`, {
    headers: bearerHeaders(token),
  });
}

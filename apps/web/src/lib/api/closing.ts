import type { ClosePeriodRequest, CurrentPeriod, PeriodClosing, PeriodClosingList } from '@kasta/contracts';

import { apiRequest, bearerHeaders } from './client';

function base(businessId: string): string {
  return `/businesses/${businessId}/closing`;
}

export function getCurrentPeriod(
  businessId: string,
  token: string,
  asOf?: string,
): Promise<CurrentPeriod> {
  const query = asOf ? `?as_of=${asOf}` : '';
  return apiRequest(`${base(businessId)}/current${query}`, {
    headers: bearerHeaders(token),
  });
}

export function getClosingHistory(
  businessId: string,
  token: string,
  filters: { limit?: number; offset?: number } = {},
): Promise<PeriodClosingList> {
  const params = new URLSearchParams();
  if (filters.limit) params.set('limit', String(filters.limit));
  if (filters.offset) params.set('offset', String(filters.offset));
  const query = params.size ? `?${params}` : '';
  return apiRequest(`${base(businessId)}${query}`, {
    headers: bearerHeaders(token),
  });
}

export function closePeriod(
  businessId: string,
  token: string,
  payload: ClosePeriodRequest,
): Promise<PeriodClosing> {
  return apiRequest(base(businessId), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(token) },
    body: JSON.stringify(payload),
  });
}

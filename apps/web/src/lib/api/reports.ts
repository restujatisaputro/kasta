import type { FinancialReport, ReportExportFormat, ReportFilters } from '@kasta/contracts';

import { ApiError, apiFetch, apiRequest, bearerHeaders } from './client';

function query(filters: ReportFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, String(value));
  }
  return params.toString();
}

export function getFinancialReport(
  businessId: string,
  token: string,
  filters: ReportFilters,
): Promise<FinancialReport> {
  return apiRequest(`/businesses/${businessId}/reports/financial?${query(filters)}`, {
    headers: bearerHeaders(token),
  });
}

export async function exportFinancialReport(
  businessId: string,
  token: string,
  filters: ReportFilters,
  format: ReportExportFormat,
): Promise<void> {
  const params = query(filters);
  const response = await apiFetch(
    `/businesses/${businessId}/reports/financial/export?${params}&format=${format}`,
    { headers: bearerHeaders(token) },
  );
  if (!response.ok) {
    const problem = (await response.json().catch(() => undefined)) as
      { detail?: string } | undefined;
    throw new ApiError(problem?.detail ?? 'Laporan belum dapat diunduh.', response.status);
  }
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `laporan-kasta.${format.toLowerCase()}`;
  anchor.click();
  URL.revokeObjectURL(url);
}

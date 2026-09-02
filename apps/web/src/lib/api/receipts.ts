import type { ConfirmReceiptRequest, ConfirmReceiptResponse, ReceiptReview } from '@kasta/contracts';

import { apiRequest, bearerHeaders } from './client';

function base(businessId: string): string {
  return `/businesses/${businessId}/receipt-scans`;
}

/** Uploads a receipt photo plus the raw text already recognised on-device (OCR runs client-side). */
export function uploadReceiptScan(
  businessId: string,
  token: string,
  photo: File,
  rawOcr: string,
): Promise<ReceiptReview> {
  const form = new FormData();
  form.append('original', photo);
  form.append('raw_ocr', rawOcr);
  return apiRequest(base(businessId), {
    method: 'POST',
    headers: bearerHeaders(token),
    body: form,
  });
}

export function getReceiptScan(
  businessId: string,
  token: string,
  receiptId: string,
): Promise<ReceiptReview> {
  return apiRequest(`${base(businessId)}/${receiptId}`, {
    headers: bearerHeaders(token),
  });
}

export function confirmReceiptScan(
  businessId: string,
  token: string,
  receiptId: string,
  payload: ConfirmReceiptRequest,
): Promise<ConfirmReceiptResponse> {
  return apiRequest(`${base(businessId)}/${receiptId}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(token) },
    body: JSON.stringify(payload),
  });
}

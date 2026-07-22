import type {
  FinancialTransaction,
  SimpleTransactionInput,
  SimpleTransactionResponse,
  TransactionDraft,
  TransactionListResponse,
  TransactionOptions,
} from '@kasta/contracts';

import { apiRequest, bearerHeaders } from './client';

function businessPath(businessId: string, suffix: string): string {
  return `/businesses/${businessId}${suffix}`;
}

export function getTransactionOptions(
  businessId: string,
  token: string,
): Promise<TransactionOptions> {
  return apiRequest(businessPath(businessId, '/transactions/options'), {
    headers: bearerHeaders(token),
  });
}

export function getTransactions(
  businessId: string,
  token: string,
  filters: Record<string, string>,
): Promise<TransactionListResponse> {
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, value]) => value.trim().length > 0),
  );
  const query = params.size > 0 ? `?${params.toString()}` : '';
  return apiRequest(businessPath(businessId, `/transactions${query}`), {
    headers: bearerHeaders(token),
  });
}

export function createTransaction(
  businessId: string,
  token: string,
  payload: SimpleTransactionInput,
): Promise<SimpleTransactionResponse> {
  return apiRequest(businessPath(businessId, '/transactions'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(token) },
    body: JSON.stringify(payload),
  });
}

export function createDraft(
  businessId: string,
  token: string,
  payload: SimpleTransactionInput & { client_reference: string },
): Promise<TransactionDraft> {
  return apiRequest(businessPath(businessId, '/transactions/drafts'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(token) },
    body: JSON.stringify(payload),
  });
}

export function getDrafts(businessId: string, token: string): Promise<TransactionDraft[]> {
  return apiRequest(businessPath(businessId, '/transactions/drafts'), {
    headers: bearerHeaders(token),
  });
}

export function postDraft(
  businessId: string,
  draftId: string,
  token: string,
): Promise<SimpleTransactionResponse> {
  return apiRequest(businessPath(businessId, `/transactions/drafts/${draftId}/post`), {
    method: 'POST',
    headers: bearerHeaders(token),
  });
}

export function reviseTransaction(
  businessId: string,
  transactionId: string,
  token: string,
  payload: SimpleTransactionInput,
  reason: string,
): Promise<SimpleTransactionResponse> {
  return apiRequest(businessPath(businessId, `/transactions/${transactionId}/revision`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(token) },
    body: JSON.stringify({ reason, replacement: payload }),
  });
}

export function reverseTransaction(
  businessId: string,
  transactionId: string,
  token: string,
  reason: string,
): Promise<FinancialTransaction> {
  return apiRequest(businessPath(businessId, `/transactions/${transactionId}/reversal`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(token) },
    body: JSON.stringify({ reason }),
  });
}

export function uploadReceipt(
  businessId: string,
  transactionId: string,
  token: string,
  photo: File,
): Promise<void> {
  const form = new FormData();
  form.append('photo', photo);
  return apiRequest(businessPath(businessId, `/transactions/${transactionId}/receipts`), {
    method: 'POST',
    headers: bearerHeaders(token),
    body: form,
  });
}

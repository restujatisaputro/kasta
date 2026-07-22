import type {
  BusinessCategory,
  BusinessProfile,
  CompleteOnboardingResponse,
} from '@kasta/contracts';

import { apiRequest, bearerHeaders } from './client';
import { publicConfig } from '$lib/config/public';

export interface RegistrationPayload {
  full_name: string;
  email?: string;
  phone?: string;
  password: string;
}

export async function createAccount(payload: RegistrationPayload): Promise<{ user_id: string }> {
  return apiRequest('/onboarding/account', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function verifyAccount(token: string): Promise<{ onboarding_token: string }> {
  return apiRequest('/onboarding/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
}

export async function getBusinessCategories(): Promise<BusinessCategory[]> {
  return apiRequest('/onboarding/categories');
}

export async function completeOnboarding(
  payload: Record<string, unknown>,
  onboardingToken: string,
): Promise<CompleteOnboardingResponse> {
  return apiRequest('/onboarding/complete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(onboardingToken) },
    body: JSON.stringify(payload),
  });
}

export async function getBusinessProfile(
  businessId: string,
  accessToken: string,
): Promise<BusinessProfile> {
  return apiRequest(`/businesses/${businessId}/profile`, {
    headers: bearerHeaders(accessToken),
  });
}

export async function updateBusinessProfile(
  businessId: string,
  accessToken: string,
  payload: Record<string, unknown>,
): Promise<BusinessProfile> {
  return apiRequest(`/businesses/${businessId}/profile`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(accessToken) },
    body: JSON.stringify(payload),
  });
}

export async function uploadBusinessLogo(
  businessId: string,
  accessToken: string,
  logo: File,
): Promise<BusinessProfile> {
  const body = new FormData();
  body.append('logo', logo);
  return apiRequest(`/businesses/${businessId}/profile/logo`, {
    method: 'PUT',
    headers: bearerHeaders(accessToken),
    body,
  });
}

export async function getBusinessLogo(businessId: string, accessToken: string): Promise<string> {
  const response = await fetch(`${publicConfig.apiBaseUrl}/businesses/${businessId}/profile/logo`, {
    headers: bearerHeaders(accessToken),
  });
  if (!response.ok) throw new Error('Logo tidak dapat dimuat.');
  return URL.createObjectURL(await response.blob());
}

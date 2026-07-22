import type { TokenPair } from '@kasta/contracts';
import { apiRequest } from './client';

export interface RegistrationResult {
  user_id: string;
  message: string;
}

export interface MessageResult {
  message: string;
}

export function login(payload: {
  business_id: string;
  identifier: string;
  password: string;
  device_id: string;
  platform: 'WEB';
  device_name: string;
  app_version: string;
}): Promise<TokenPair> {
  return apiRequest('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function register(payload: {
  full_name: string;
  email?: string;
  phone?: string;
  password: string;
}): Promise<RegistrationResult> {
  return apiRequest('/onboarding/account', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function forgotPassword(identifier: string): Promise<MessageResult> {
  return apiRequest('/auth/password/forgot', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier }),
  });
}

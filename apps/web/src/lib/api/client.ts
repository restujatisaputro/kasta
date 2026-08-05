import type { ProblemDetails } from '@kasta/contracts';
import { browser } from '$app/environment';
import { get } from 'svelte/store';

import { publicConfig } from '$lib/config/public';
import { authSession, type AuthSession } from '$lib/stores/auth-session';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly problem?: ProblemDetails,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

let refreshPromise: Promise<AuthSession | null> | null = null;

function bearerToken(init?: RequestInit): string | null {
  const value = new Headers(init?.headers).get('Authorization');
  return value?.startsWith('Bearer ') ? value.slice('Bearer '.length) : null;
}

async function refreshSession(): Promise<AuthSession | null> {
  if (!browser) return null;

  const session = get(authSession);
  if (!session?.refreshToken) return null;

  if (!refreshPromise) {
    refreshPromise = fetch(`${publicConfig.apiBaseUrl}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: session.refreshToken }),
    })
      .then(async (response) => {
        if (!response.ok) {
          authSession.set(null);
          return null;
        }

        const tokens = (await response.json()) as {
          access_token: string;
          refresh_token: string;
        };
        const nextSession = {
          ...session,
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
        };
        authSession.set(nextSession);
        return nextSession;
      })
      .catch(() => {
        authSession.set(null);
        return null;
      });
  }

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

/**
 * Performs an API request and transparently rotates an expired access token.
 * Keeping this in one place also covers non-JSON responses such as exports.
 */
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const requestInit: RequestInit = {
    credentials: 'include',
    ...init,
  };
  let response = await fetch(`${publicConfig.apiBaseUrl}${path}`, requestInit);

  const sentToken = bearerToken(requestInit);
  if (response.status !== 401 || !sentToken || path === '/auth/refresh') return response;

  // Another request may have refreshed the session while this request was in
  // flight. Reuse its token instead of rotating the refresh token twice.
  let session = get(authSession);
  if (session?.accessToken === sentToken) session = await refreshSession();
  if (!session?.accessToken) return response;

  const retryHeaders = new Headers(requestInit.headers);
  retryHeaders.set('Authorization', `Bearer ${session.accessToken}`);
  response = await fetch(`${publicConfig.apiBaseUrl}${path}`, {
    ...requestInit,
    headers: retryHeaders,
  });
  return response;
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, {
    ...init,
    headers: { Accept: 'application/json', ...init?.headers },
  });

  if (!response.ok) {
    const problem = (await response.json().catch(() => undefined)) as ProblemDetails | undefined;
    throw new ApiError(
      problem?.detail ?? problem?.title ?? 'Permintaan tidak dapat diproses',
      response.status,
      problem,
    );
  }

  return (await response.json()) as T;
}

export function bearerHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

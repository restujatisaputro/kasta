import type { ProblemDetails } from '@kasta/contracts';

import { publicConfig } from '$lib/config/public';

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

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${publicConfig.apiBaseUrl}${path}`, {
    credentials: 'include',
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

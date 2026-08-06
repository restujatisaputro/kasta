import { browser } from '$app/environment';
import { writable } from 'svelte/store';

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  businessId: string | null;
}

const STORAGE_KEY = 'kasta-auth-session';

function storedSession(): AuthSession | null {
  if (!browser) return null;
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const value: unknown = JSON.parse(raw);
    if (
      typeof value === 'object' &&
      value !== null &&
      typeof (value as AuthSession).accessToken === 'string' &&
      typeof (value as AuthSession).refreshToken === 'string' &&
      ((value as AuthSession).businessId === null ||
        typeof (value as AuthSession).businessId === 'string')
    ) {
      return value as AuthSession;
    }
  } catch {
    // Invalid or stale browser state is treated as a signed-out session.
  }
  sessionStorage.removeItem(STORAGE_KEY);
  return null;
}

// Keep credentials scoped to the current browser tab. This survives SvelteKit
// navigations and reloads without creating a long-lived localStorage session.
export const authSession = writable<AuthSession | null>(storedSession());

if (browser) {
  authSession.subscribe((session) => {
    if (session) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    else sessionStorage.removeItem(STORAGE_KEY);
  });
}

import { writable } from 'svelte/store';

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  businessId: string;
}

// Sengaja hanya di memori. Token tidak ditaruh di localStorage/sessionStorage.
export const authSession = writable<AuthSession | null>(null);

import { browser } from '$app/environment';

const STORAGE_KEY = 'kasta-onboarding-token';

/**
 * Titipan singkat antara halaman verifikasi tautan dan wizard onboarding.
 * Memakai sessionStorage, bukan URL, agar token pembawa tidak ikut tercatat di
 * riwayat peramban maupun header referrer.
 */
export function saveOnboardingToken(token: string): void {
  if (browser) sessionStorage.setItem(STORAGE_KEY, token);
}

/** Membaca token sekali pakai lalu menghapusnya. */
export function takeOnboardingToken(): string {
  if (!browser) return '';
  const token = sessionStorage.getItem(STORAGE_KEY) ?? '';
  if (token) sessionStorage.removeItem(STORAGE_KEY);
  return token;
}

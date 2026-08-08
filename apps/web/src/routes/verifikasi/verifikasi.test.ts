import { cleanup, render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import VerifikasiPage from './+page.svelte';

const { pageState } = vi.hoisted(() => ({
  pageState: { url: new URL('http://localhost/verifikasi') },
}));

vi.mock('$app/state', () => ({ page: pageState }));
vi.mock('$env/dynamic/public', () => ({
  env: {
    PUBLIC_API_BASE_URL: 'http://testserver/api/v1',
    PUBLIC_APP_ENVIRONMENT: 'test',
  },
}));

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => {
  // AuthShell memuat DarkModeToggle yang membaca preferensi tema peramban.
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockReturnValue({ matches: false, addEventListener: vi.fn() }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('halaman verifikasi lewat tautan', () => {
  it('memverifikasi otomatis memakai token dari tautan email', async () => {
    pageState.url = new URL('http://localhost/verifikasi?token=token-uji-yang-panjang');
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ message: 'Verifikasi berhasil.' }));
    vi.stubGlobal('fetch', fetchMock);

    render(VerifikasiPage);

    expect(await screen.findByRole('heading', { name: 'Akun terverifikasi' })).toBeTruthy();
    const [path, init] = fetchMock.mock.calls[0];
    expect(path).toBe('http://testserver/api/v1/auth/verification/confirm');
    expect(JSON.parse(String(init.body))).toEqual({ token: 'token-uji-yang-panjang' });
  });

  it('menolak tanpa memanggil API bila tautan tidak membawa token', async () => {
    pageState.url = new URL('http://localhost/verifikasi');
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    render(VerifikasiPage);

    expect(await screen.findByRole('heading', { name: 'Verifikasi gagal' })).toBeTruthy();
    expect(screen.getByText(/tidak lengkap/i)).toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('menampilkan alasan dari API ketika tautan sudah kedaluwarsa', async () => {
    pageState.url = new URL('http://localhost/verifikasi?token=token-kedaluwarsa');
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Token tidak valid.' }, 401)),
    );

    render(VerifikasiPage);

    expect(await screen.findByRole('heading', { name: 'Verifikasi gagal' })).toBeTruthy();
    expect(screen.getByText('Token tidak valid.')).toBeTruthy();
  });
});

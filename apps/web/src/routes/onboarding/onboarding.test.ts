import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import ProgressIndicator from '$lib/components/ProgressIndicator.svelte';

import OnboardingPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$env/dynamic/public', () => ({
  env: {
    PUBLIC_API_BASE_URL: 'http://testserver/api/v1',
    PUBLIC_APP_ENVIRONMENT: 'test',
  },
}));

describe('onboarding utama', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify([]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('menampilkan langkah pembuatan akun dengan bahasa sederhana', () => {
    render(OnboardingPage);

    expect(screen.getByRole('heading', { name: 'Buat akun KASTA' })).toBeTruthy();
    expect(screen.getByLabelText('Langkah 1 dari 9')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Buat akun' })).toBeTruthy();
  });

  it('menahan pengguna di langkah pertama ketika data belum lengkap', async () => {
    render(OnboardingPage);

    await fireEvent.click(screen.getByRole('button', { name: 'Buat akun' }));

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Buat akun KASTA' })).toBeTruthy();
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});

describe('indikator progres', () => {
  afterEach(cleanup);

  it('menyebutkan langkah aktif agar dapat dibaca pembaca layar', () => {
    render(ProgressIndicator, { current: 5, total: 9 });
    expect(screen.getByLabelText('Langkah 5 dari 9').textContent).toContain('56%');
  });
});

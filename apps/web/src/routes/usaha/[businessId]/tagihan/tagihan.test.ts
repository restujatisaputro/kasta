import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authSession } from '$lib/stores/auth-session';

import Page from './+page.svelte';

vi.mock('$lib/api/obligations', () => ({
  getObligations: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 }),
  getObligationAging: vi.fn().mockResolvedValue({
    as_of: '2026-07-21',
    receivables: { total_open: '0.00', buckets: [] },
    payables: { total_open: '0.00', buckets: [] },
  }),
  getObligationReminders: vi.fn().mockResolvedValue({ as_of: '2026-07-21', items: [] }),
  createObligation: vi.fn(),
  getObligation: vi.fn(),
  payObligation: vi.fn(),
  cancelObligation: vi.fn(),
}));

describe('halaman utang dan piutang', () => {
  beforeEach(() => {
    authSession.set({ accessToken: 'token', refreshToken: 'refresh', businessId: 'usaha-1' });
  });

  it('menampilkan bahasa status yang mudah dipahami', () => {
    render(Page, { data: { businessId: 'usaha-1' } });
    expect(screen.getByRole('heading', { name: 'Utang dan Piutang' })).toBeTruthy();
    expect(screen.getByRole('option', { name: 'Belum Dibayar' })).toBeTruthy();
    expect(screen.getByRole('option', { name: 'Dibayar Sebagian' })).toBeTruthy();
    expect(screen.getByRole('option', { name: 'Sudah Lunas' })).toBeTruthy();
    expect(screen.getByRole('option', { name: 'Terlambat' })).toBeTruthy();
  });
});

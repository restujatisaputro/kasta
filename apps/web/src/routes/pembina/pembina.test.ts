import type {
  MentorAggregateReport,
  MentorAuditActivity,
  MentorBusinessDetail,
  MentorDashboard,
} from '@kasta/contracts';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authSession } from '$lib/stores/auth-session';

import Page from './+page.svelte';

const business = {
  business_id: 'usaha-1',
  business_name: 'Warung Sejahtera',
  city: 'Bandung',
  province: 'Jawa Barat',
  health_level: 'YELLOW' as const,
  health_label: 'Perlu perhatian',
  health_icon: '!',
  last_recorded_date: '2026-07-20',
  days_since_recording: 1,
  recording_consistency: '37.50',
  month_revenue: '15000000.00',
  month_expense: '10000000.00',
  month_profit: '5000000.00',
  payable_balance: '3000000.00',
  receivable_balance: '2000000.00',
  overdue_receivable: '0.00',
  open_recommendations: 1,
  risk_indicators: [
    {
      code: 'LOW_CONSISTENCY',
      level: 'YELLOW' as const,
      label: 'Pencatatan belum konsisten',
      message: 'Pencatatan dilakukan pada kurang dari separuh delapan minggu terakhir.',
      icon: '!',
    },
  ],
};

const dashboard: MentorDashboard = {
  total_businesses: 1,
  active_businesses: 1,
  stale_businesses: 0,
  expense_over_income: 0,
  high_debt: 0,
  overdue_receivables: 0,
  open_recommendations: 1,
  health_green: 0,
  health_yellow: 1,
  health_red: 0,
  upcoming_sessions: [
    {
      id: 'jadwal-1',
      business_id: 'usaha-1',
      business_name: 'Warung Sejahtera',
      scheduled_at: '2026-07-25T03:00:00Z',
      duration_minutes: 60,
      mode: 'ONLINE',
      topic: 'Evaluasi pencatatan',
    },
  ],
  businesses: [business],
  generated_at: '2026-07-21T10:00:00Z',
};

const detail: MentorBusinessDetail = {
  summary: business,
  revenue_trend: [
    { month: '2026-07', revenue: '15000000.00', expense: '10000000.00', profit: '5000000.00' },
  ],
  notes: [],
  recommendations: [
    {
      id: 'rekomendasi-1',
      business_id: 'usaha-1',
      mentor_id: 'pembina-1',
      title: 'Catat setiap hari',
      description: 'Sisihkan waktu sepuluh menit setelah toko tutup.',
      priority: 'MEDIUM',
      status: 'OPEN',
      due_date: '2026-07-31',
      follow_up_note: null,
      completed_at: null,
      created_at: '2026-07-21T10:00:00Z',
      updated_at: '2026-07-21T10:00:00Z',
    },
  ],
  sessions: [],
  explanation: 'Warung Sejahtera memperoleh omzet Rp15.000.000 bulan ini.',
};

const aggregate: MentorAggregateReport = {
  dashboard,
  total_revenue: '15000000.00',
  total_expense: '10000000.00',
  total_profit: '5000000.00',
  total_payables: '3000000.00',
  total_receivables: '2000000.00',
  explanation: 'Dari 1 UMKM binaan, 1 perlu perhatian.',
};

const audit: MentorAuditActivity[] = [];

const mocks = vi.hoisted(() => ({
  getMentorDashboard: vi.fn(),
  getMentorBusiness: vi.fn(),
  getMentorReport: vi.fn(),
  getMentorAudit: vi.fn(),
  createMentoringSession: vi.fn(),
  createMentorNote: vi.fn(),
  createMentorRecommendation: vi.fn(),
  updateMentoringSession: vi.fn(),
  updateMentorRecommendation: vi.fn(),
  exportMentorReport: vi.fn(),
  chartInit: vi.fn(),
}));

vi.mock('$lib/api/mentors', () => mocks);
vi.mock('echarts', () => ({ init: mocks.chartInit }));

describe('dashboard pembina', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getMentorDashboard.mockResolvedValue(dashboard);
    mocks.getMentorBusiness.mockResolvedValue(detail);
    mocks.getMentorReport.mockResolvedValue(aggregate);
    mocks.getMentorAudit.mockResolvedValue(audit);
    mocks.chartInit.mockReturnValue({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() });
    authSession.set({
      accessToken: 'token-pembina',
      refreshToken: 'refresh',
      businessId: 'usaha-1',
    });
  });

  it('menampilkan indikator dengan ikon dan teks, ringkasan, serta detail UMKM', async () => {
    render(Page);

    expect(screen.getByRole('heading', { name: 'Dashboard Pembina' })).toBeTruthy();
    await waitFor(() => expect(screen.getAllByText('Warung Sejahtera').length).toBeGreaterThan(0));
    expect(screen.getAllByText(/Perlu perhatian/).length).toBeGreaterThan(0);
    await waitFor(() => expect(screen.getByText(/Pencatatan belum konsisten/)).toBeTruthy());
    expect(screen.getByText(/tanpa dapat mengubah\s+transaksi UMKM/)).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Tren omzet dan laba' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Unduh PDF' })).toBeTruthy();
  });

  it('membuka alur rekomendasi dan status tindak lanjut', async () => {
    render(Page);
    await waitFor(() => expect(screen.getByRole('button', { name: /Rekomendasi/ })).toBeTruthy());

    await fireEvent.click(screen.getByRole('button', { name: /Rekomendasi/ }));

    expect(screen.getByRole('heading', { name: 'Buat rekomendasi' })).toBeTruthy();
    expect(screen.getByText('Catat setiap hari')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Mulai tindak lanjut' })).toBeTruthy();
  });
});

import type { FinancialReport } from '@kasta/contracts';
import { render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { authSession } from '$lib/stores/auth-session';

import Page from './+page.svelte';

const report: FinancialReport = {
  context: {
    business_id: 'usaha-1',
    business_name: 'Warung KASTA',
    period: 'MONTH',
    date_from: '2026-07-01',
    date_to: '2026-07-31',
    category: null,
    payment_method: null,
    branch_id: 'usaha-1',
    branch_name: 'Warung KASTA',
    generated_at: '2026-07-21T10:00:00Z',
    source: 'JOURNAL',
  },
  summary: {
    income: '15000000.00',
    expense: '10000000.00',
    estimated_profit: '5000000.00',
    cash_in: '15000000.00',
    cash_out: '10000000.00',
    net_cash_flow: '5000000.00',
    receivables: '500000.00',
    payables: '250000.00',
    inventory_value: '3000000.00',
  },
  profit_loss: {
    revenues: [{ account_key: 'SALES', account_name: 'Penjualan', amount: '15000000.00' }],
    expenses: [{ account_key: 'RENT', account_name: 'Sewa', amount: '10000000.00' }],
    total_revenue: '15000000.00',
    total_expense: '10000000.00',
    profit: '5000000.00',
    explanation:
      'Usaha Anda memperoleh pemasukan Rp15.000.000 dan mengeluarkan Rp10.000.000. Perkiraan laba bulan ini adalah Rp5.000.000.',
  },
  balance_sheet: {
    assets: [{ account_key: 'CASH', account_name: 'Kas', amount: '5000000.00' }],
    liabilities: [],
    equity: [
      { account_key: 'RETAINED_EARNINGS', account_name: 'Laba berjalan', amount: '5000000.00' },
    ],
    total_assets: '5000000.00',
    total_liabilities: '0.00',
    total_equity: '5000000.00',
    difference: '0.00',
    explanation: 'Nilai yang dimiliki usaha seimbang dengan sumber dananya.',
  },
  cash_flow: {
    cash_in: '15000000.00',
    cash_out: '10000000.00',
    net_cash_flow: '5000000.00',
    ending_cash_balance: '5000000.00',
    explanation: 'Kas bertambah Rp5.000.000 selama periode ini.',
  },
  sales: [{ key: 'SALES', label: 'Penjualan', amount: '15000000.00', percentage: '100.00' }],
  expenditures: [{ key: 'RENT', label: 'Sewa', amount: '10000000.00', percentage: '100.00' }],
  receivables: {
    open_count: 1,
    overdue_count: 0,
    total_initial: '500000.00',
    total_paid: '0.00',
    total_remaining: '500000.00',
    journal_value: '500000.00',
    explanation: 'Terdapat satu piutang belum lunas.',
  },
  payables: {
    open_count: 1,
    overdue_count: 0,
    total_initial: '250000.00',
    total_paid: '0.00',
    total_remaining: '250000.00',
    journal_value: '250000.00',
    explanation: 'Terdapat satu utang belum lunas.',
  },
  inventory: {
    product_count: 1,
    low_stock_count: 0,
    total_quantity: '10.00',
    operational_value: '3000000.00',
    journal_value: '3000000.00',
    explanation: 'Nilai stok operasional sesuai dengan jurnal.',
  },
  best_selling_products: [
    {
      product_id: 'produk-1',
      sku: 'SKU-1',
      name: 'Kopi',
      unit: 'pcs',
      quantity_sold: '10.00',
      sales_value: '15000000.00',
    },
  ],
  monthly_comparison: [
    {
      period: '2026-07',
      income: '15000000.00',
      expense: '10000000.00',
      profit: '5000000.00',
      sales: '15000000.00',
    },
  ],
  charts: {
    income_vs_expense: [
      {
        period: '2026-07-21',
        income: '15000000.00',
        expense: '10000000.00',
        profit: '5000000.00',
        sales: '15000000.00',
      },
    ],
    profit_trend: [
      {
        period: '2026-07',
        income: '15000000.00',
        expense: '10000000.00',
        profit: '5000000.00',
        sales: '15000000.00',
      },
    ],
    expense_categories: [
      { key: 'RENT', label: 'Sewa', amount: '10000000.00', percentage: '100.00' },
    ],
    daily_sales: [
      {
        period: '2026-07-21',
        income: '15000000.00',
        expense: '0.00',
        profit: '15000000.00',
        sales: '15000000.00',
      },
    ],
    best_selling_products: [
      {
        product_id: 'produk-1',
        sku: 'SKU-1',
        name: 'Kopi',
        unit: 'pcs',
        quantity_sold: '10.00',
        sales_value: '15000000.00',
      },
    ],
  },
  explanation: 'Usaha Anda memperoleh pemasukan Rp15.000.000 dan mengeluarkan Rp10.000.000.',
};

const mocks = vi.hoisted(() => ({
  getFinancialReport: vi.fn(),
  exportFinancialReport: vi.fn(),
  chartInit: vi.fn(),
}));

vi.mock('$lib/api/reports', () => mocks);
vi.mock('echarts', () => ({
  init: mocks.chartInit,
}));

describe('halaman laporan', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getFinancialReport.mockResolvedValue(report);
    mocks.exportFinancialReport.mockResolvedValue(undefined);
    mocks.chartInit.mockImplementation(() => ({
      setOption: vi.fn(),
      resize: vi.fn(),
      dispose: vi.fn(),
    }));
    authSession.set({ accessToken: 'token', refreshToken: 'refresh', businessId: 'usaha-1' });
  });

  it('menampilkan laporan berbasis jurnal, penjelasan, grafik, dan pilihan ekspor', async () => {
    render(Page, { data: { businessId: 'usaha-1' } });

    expect(screen.getByRole('heading', { name: 'Laporan Keuangan' })).toBeTruthy();
    await waitFor(() => expect(screen.getByText(/Sumber: jurnal double-entry/)).toBeTruthy());
    expect(screen.getByText(/Perkiraan laba bulan ini/)).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Pemasukan versus pengeluaran' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Produk paling laku' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Unduh PDF' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Unduh XLSX' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Unduh CSV' })).toBeTruthy();
    await waitFor(() => expect(mocks.chartInit).toHaveBeenCalledTimes(5));
  });
});

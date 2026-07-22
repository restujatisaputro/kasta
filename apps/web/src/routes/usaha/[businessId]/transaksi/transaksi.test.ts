import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { authSession } from '$lib/stores/auth-session';

import TransactionPage from './+page.svelte';

vi.mock('$env/dynamic/public', () => ({
  env: {
    PUBLIC_API_BASE_URL: 'http://testserver/api/v1',
    PUBLIC_APP_ENVIRONMENT: 'test',
  },
}));

const options = {
  income_sources: [
    { value: 'SALES', label: 'Penjualan' },
    { value: 'SERVICE_REVENUE', label: 'Pendapatan jasa' },
  ],
  expense_categories: [
    { value: 'INTERNET', label: 'Internet' },
    { value: 'RENT', label: 'Sewa' },
  ],
  payment_methods: [
    { value: 'CASH', label: 'Tunai' },
    { value: 'BANK_TRANSFER', label: 'Transfer bank' },
  ],
};

describe('transaksi sederhana', () => {
  beforeEach(() => {
    authSession.set({
      accessToken: 'access-token-test',
      refreshToken: 'refresh-token-test',
      businessId: 'business-test',
    });
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        const body = url.endsWith('/transactions/options')
          ? options
          : url.endsWith('/transactions/drafts')
            ? []
            : url.endsWith('/inventory/products')
              ? {
                  items: [
                    {
                      id: 'product-1',
                      name: 'Kopi Susu',
                      is_active: true,
                      current_stock: '10.000',
                      unit: 'PCS',
                      sale_price: '12000.00',
                      purchase_price: '8000.00',
                    },
                  ],
                  total: 1,
                  limit: 50,
                  offset: 0,
                }
              : { items: [], total: 0, limit: 50, offset: 0 };
        return new Response(JSON.stringify(body), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }),
    );
  });

  afterEach(() => {
    cleanup();
    authSession.set(null);
    vi.unstubAllGlobals();
  });

  it('menyelesaikan form uang masuk dalam tiga langkah dan memformat Rupiah', async () => {
    render(TransactionPage, { data: { businessId: 'business-test' } });

    await waitFor(() => expect(screen.getByTestId('menu-income')).toBeTruthy());
    expect(screen.getByTestId('menu-expense')).toBeTruthy();
    expect(screen.getByTestId('menu-capital')).toBeTruthy();
    expect(screen.getByTestId('menu-owner_draw')).toBeTruthy();

    await fireEvent.click(screen.getByTestId('menu-income'));
    expect(screen.getByRole('heading', { name: 'Langkah 1 dari 3' })).toBeTruthy();

    await fireEvent.input(screen.getByLabelText('Nominal'), { target: { value: '125000' } });
    expect((screen.getByLabelText('Nominal') as HTMLInputElement).value).toBe('125.000');

    await fireEvent.click(screen.getByTestId('transaction-next'));
    expect(screen.getByRole('heading', { name: 'Langkah 2 dari 3' })).toBeTruthy();
    await fireEvent.click(screen.getByTestId('transaction-next'));

    expect(screen.getByRole('heading', { name: 'Langkah 3 dari 3' })).toBeTruthy();
    expect(screen.getByTestId('review-amount').textContent?.replace(/\s/g, '')).toBe('Rp125.000');
    expect(screen.getByRole('button', { name: 'Simpan draft' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Catat transaksi' })).toBeTruthy();
  });

  it('mengirim produk dan jumlah agar penjualan mengurangi stok', async () => {
    render(TransactionPage, { data: { businessId: 'business-test' } });
    await waitFor(() => expect(screen.getByTestId('menu-income')).toBeTruthy());
    await fireEvent.click(screen.getByTestId('menu-income'));
    await fireEvent.input(screen.getByLabelText('Nominal'), { target: { value: '1000' } });
    await fireEvent.click(screen.getByTestId('transaction-next'));

    await fireEvent.change(screen.getByLabelText(/Produk/), { target: { value: 'product-1' } });
    await fireEvent.input(screen.getByLabelText('Jumlah'), { target: { value: '2' } });
    await fireEvent.click(screen.getByTestId('transaction-next'));
    await fireEvent.click(screen.getByRole('button', { name: 'Catat transaksi' }));

    await waitFor(() => {
      const call = vi
        .mocked(fetch)
        .mock.calls.find(
          ([url, init]) => String(url).endsWith('/transactions') && init?.method === 'POST',
        );
      expect(call).toBeTruthy();
      const body = JSON.parse(String(call?.[1]?.body)) as {
        amount: string;
        items: Array<{ product_id: string; quantity: string; unit_price: string }>;
      };
      expect(body.amount).toBe('24000.00');
      expect(body.items).toEqual([
        { product_id: 'product-1', quantity: '2', unit_price: '12000.00' },
      ]);
    });
  });
});

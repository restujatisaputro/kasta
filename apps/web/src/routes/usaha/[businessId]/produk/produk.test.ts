import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { authSession } from '$lib/stores/auth-session';

import ProductPage from './+page.svelte';

vi.mock('$env/dynamic/public', () => ({
  env: {
    PUBLIC_API_BASE_URL: 'http://testserver/api/v1',
    PUBLIC_APP_ENVIRONMENT: 'test',
  },
}));

const product = {
  id: 'product-1',
  business_id: 'business-test',
  sku: 'KOPI-001',
  barcode: '8991234567890',
  name: 'Kopi Susu Botol',
  category: 'Minuman',
  unit: 'PCS',
  purchase_price: '8000.00',
  sale_price: '12000.00',
  opening_stock: '10.000',
  current_stock: '4.000',
  minimum_stock: '5.000',
  is_active: true,
  is_low_stock: true,
  inventory_value: '32000.00',
  created_at: '2026-07-21T00:00:00Z',
  updated_at: '2026-07-21T00:00:00Z',
};

describe('produk dan stok', () => {
  beforeEach(() => {
    authSession.set({
      accessToken: 'access-token-test',
      refreshToken: 'refresh-token-test',
      businessId: 'business-test',
    });
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith('/inventory/summary')) {
          return jsonResponse({
            product_count: 1,
            active_product_count: 1,
            low_stock_count: 1,
            inventory_value: '32000.00',
            best_sellers: [],
          });
        }
        if (init?.method === 'POST' && url.endsWith('/movements')) {
          return jsonResponse({});
        }
        if (url.includes('/inventory/movements')) {
          return jsonResponse({ items: [], total: 0, limit: 50, offset: 0 });
        }
        return jsonResponse({ items: [product], total: 1, limit: 50, offset: 0 });
      }),
    );
  });

  afterEach(() => {
    cleanup();
    authSession.set(null);
    vi.unstubAllGlobals();
  });

  it('menampilkan stok minimum dan mencatat stok masuk', async () => {
    render(ProductPage, { data: { businessId: 'business-test' } });

    await waitFor(() => expect(screen.getByText('Kopi Susu Botol')).toBeTruthy());
    expect(screen.getByText((text) => text.replace(/\s/g, '') === 'Rp32.000')).toBeTruthy();
    expect(screen.getByText('Perlu diisi')).toBeTruthy();

    await fireEvent.click(screen.getByRole('button', { name: 'Ubah stok' }));
    expect(screen.getByRole('heading', { name: 'Ubah stok Kopi Susu Botol' })).toBeTruthy();
    await fireEvent.input(screen.getByLabelText('Jumlah'), { target: { value: '6' } });
    await fireEvent.input(screen.getByLabelText('Alasan'), {
      target: { value: 'Belanja dari pemasok' },
    });
    await fireEvent.click(screen.getByRole('button', { name: 'Catat perubahan' }));

    await waitFor(() => expect(screen.getByText('Perubahan stok berhasil dicatat.')).toBeTruthy());
    const fetchMock = vi.mocked(fetch);
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url).endsWith('/products/product-1/movements') && init?.method === 'POST',
      ),
    ).toBe(true);
  });
});

function jsonResponse(body: object): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

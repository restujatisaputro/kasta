import type {
  CsvImportResponse,
  InventorySummary,
  Product,
  ProductInput,
  ProductListResponse,
  StockHistoryResponse,
  StockMovement,
  StockMovementInput,
} from '@kasta/contracts';

import { publicConfig } from '$lib/config/public';

import { ApiError, apiRequest, bearerHeaders } from './client';

function inventoryPath(businessId: string, suffix: string): string {
  return `/businesses/${businessId}/inventory${suffix}`;
}

export function getProducts(
  businessId: string,
  token: string,
  filters: { q?: string; low_stock?: boolean } = {},
): Promise<ProductListResponse> {
  const params = new URLSearchParams();
  if (filters.q) params.set('q', filters.q);
  if (filters.low_stock) params.set('low_stock', 'true');
  const query = params.size > 0 ? `?${params.toString()}` : '';
  return apiRequest(inventoryPath(businessId, `/products${query}`), {
    headers: bearerHeaders(token),
  });
}

export function getProductByBarcode(
  businessId: string,
  token: string,
  barcode: string,
): Promise<Product> {
  return apiRequest(
    inventoryPath(businessId, `/products/by-barcode/${encodeURIComponent(barcode)}`),
    { headers: bearerHeaders(token) },
  );
}

export function createProduct(
  businessId: string,
  token: string,
  payload: ProductInput,
): Promise<Product> {
  return apiRequest(inventoryPath(businessId, '/products'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(token) },
    body: JSON.stringify(payload),
  });
}

export function updateProduct(
  businessId: string,
  productId: string,
  token: string,
  payload: ProductInput,
): Promise<Product> {
  const update = {
    sku: payload.sku,
    barcode: payload.barcode,
    name: payload.name,
    category: payload.category,
    unit: payload.unit,
    purchase_price: payload.purchase_price,
    sale_price: payload.sale_price,
    minimum_stock: payload.minimum_stock,
    is_active: payload.is_active,
  };
  return apiRequest(inventoryPath(businessId, `/products/${productId}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(token) },
    body: JSON.stringify(update),
  });
}

export function moveStock(
  businessId: string,
  productId: string,
  token: string,
  payload: StockMovementInput,
): Promise<StockMovement> {
  return apiRequest(inventoryPath(businessId, `/products/${productId}/movements`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...bearerHeaders(token) },
    body: JSON.stringify(payload),
  });
}

export function getStockHistory(
  businessId: string,
  token: string,
  productId?: string,
): Promise<StockHistoryResponse> {
  const query = productId ? `?product_id=${encodeURIComponent(productId)}` : '';
  return apiRequest(inventoryPath(businessId, `/movements${query}`), {
    headers: bearerHeaders(token),
  });
}

export function getInventorySummary(businessId: string, token: string): Promise<InventorySummary> {
  return apiRequest(inventoryPath(businessId, '/summary'), {
    headers: bearerHeaders(token),
  });
}

export function importProductsCsv(
  businessId: string,
  token: string,
  file: File,
): Promise<CsvImportResponse> {
  const form = new FormData();
  form.append('file', file);
  return apiRequest(inventoryPath(businessId, '/products/import-csv'), {
    method: 'POST',
    headers: bearerHeaders(token),
    body: form,
  });
}

export async function exportProductsExcel(businessId: string, token: string): Promise<void> {
  const response = await fetch(
    `${publicConfig.apiBaseUrl}${inventoryPath(businessId, '/products/export.xlsx')}`,
    { headers: bearerHeaders(token), credentials: 'include' },
  );
  if (!response.ok) {
    throw new ApiError('Data produk belum dapat diunduh.', response.status);
  }
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'produk-kasta.xlsx';
  anchor.click();
  URL.revokeObjectURL(url);
}

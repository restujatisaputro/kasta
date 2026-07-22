<script lang="ts">
  import type {
    InventorySummary,
    Product,
    ProductInput,
    ProductUnit,
    StockMovement,
    StockMovementInput,
  } from '@kasta/contracts';
  import { resolve } from '$app/paths';
  import { onMount } from 'svelte';

  import {
    createProduct,
    exportProductsExcel,
    getInventorySummary,
    getProductByBarcode,
    getProducts,
    getStockHistory,
    importProductsCsv,
    moveStock,
    updateProduct,
  } from '$lib/api/inventory';
  import { formatRupiah } from '$lib/money/rupiah';
  import { authSession } from '$lib/stores/auth-session';

  let { data }: { data: { businessId: string } } = $props();
  let products = $state<Product[]>([]);
  let history = $state<StockMovement[]>([]);
  let summary = $state<InventorySummary>({
    product_count: 0,
    active_product_count: 0,
    low_stock_count: 0,
    inventory_value: '0.00',
    best_sellers: [],
  });
  let query = $state('');
  let lowStockOnly = $state(false);
  let loading = $state(true);
  let busy = $state(false);
  let errorMessage = $state('');
  let notice = $state('');
  let formOpen = $state(false);
  let editing = $state<Product | null>(null);
  let movementProduct = $state<Product | null>(null);
  let historyProduct = $state<Product | null>(null);
  let scanBarcode = $state('');

  const units: ProductUnit[] = [
    'PCS',
    'BOX',
    'PACK',
    'KG',
    'GRAM',
    'LITER',
    'ML',
    'METER',
    'SET',
    'UNIT',
  ];

  let productForm = $state<ProductInput>(emptyProduct());
  let movementType = $state<'STOCK_IN' | 'STOCK_OUT' | 'ADJUSTMENT' | 'DAMAGED' | 'LOST'>(
    'STOCK_IN',
  );
  let movementQuantity = $state('');
  let movementReason = $state('');
  let movementReference = $state('');

  onMount(() => void loadAll());

  function emptyProduct(): ProductInput {
    return {
      sku: '',
      barcode: null,
      name: '',
      category: '',
      unit: 'PCS',
      purchase_price: '0.00',
      sale_price: '0.00',
      opening_stock: '0.000',
      minimum_stock: '0.000',
      is_active: true,
    };
  }

  async function loadAll(): Promise<void> {
    if (!$authSession || $authSession.businessId !== data.businessId) {
      loading = false;
      return;
    }
    try {
      const [list, overview, movements] = await Promise.all([
        getProducts(data.businessId, $authSession.accessToken, {
          q: query,
          low_stock: lowStockOnly,
        }),
        getInventorySummary(data.businessId, $authSession.accessToken),
        getStockHistory(data.businessId, $authSession.accessToken),
      ]);
      products = list.items;
      summary = overview;
      history = movements.items;
    } catch (error) {
      errorMessage = messageOf(error, 'Produk belum dapat dimuat.');
    } finally {
      loading = false;
    }
  }

  function openCreate(): void {
    editing = null;
    productForm = emptyProduct();
    formOpen = true;
  }

  function openEdit(product: Product): void {
    editing = product;
    productForm = {
      sku: product.sku,
      barcode: product.barcode,
      name: product.name,
      category: product.category,
      unit: product.unit,
      purchase_price: product.purchase_price,
      sale_price: product.sale_price,
      opening_stock: product.opening_stock,
      minimum_stock: product.minimum_stock,
      is_active: product.is_active,
    };
    formOpen = true;
  }

  async function saveProduct(): Promise<void> {
    if (!$authSession) return;
    busy = true;
    errorMessage = '';
    try {
      if (editing) {
        await updateProduct(data.businessId, editing.id, $authSession.accessToken, productForm);
        notice = 'Produk berhasil diperbarui. Stok tidak berubah.';
      } else {
        await createProduct(data.businessId, $authSession.accessToken, productForm);
        notice = 'Produk dan stok awal berhasil disimpan.';
      }
      formOpen = false;
      await loadAll();
    } catch (error) {
      errorMessage = messageOf(error, 'Produk belum dapat disimpan.');
    } finally {
      busy = false;
    }
  }

  function openMovement(product: Product): void {
    movementProduct = product;
    movementType = 'STOCK_IN';
    movementQuantity = '';
    movementReason = '';
    movementReference = '';
  }

  async function saveMovement(): Promise<void> {
    if (!$authSession || !movementProduct) return;
    if (!movementQuantity || movementReason.trim().length < 3) {
      errorMessage = 'Isi jumlah atau stok hasil hitung dan alasan.';
      return;
    }
    const shared = {
      reason: movementReason.trim(),
      reference: movementReference.trim(),
    };
    const payload: StockMovementInput =
      movementType === 'ADJUSTMENT'
        ? { movement_type: 'ADJUSTMENT', target_stock: movementQuantity, ...shared }
        : { movement_type: movementType, quantity: movementQuantity, ...shared };
    busy = true;
    try {
      await moveStock(data.businessId, movementProduct.id, $authSession.accessToken, payload);
      notice = 'Perubahan stok berhasil dicatat.';
      movementProduct = null;
      await loadAll();
    } catch (error) {
      errorMessage = messageOf(error, 'Stok belum dapat diperbarui.');
    } finally {
      busy = false;
    }
  }

  async function showHistory(product: Product): Promise<void> {
    if (!$authSession) return;
    historyProduct = product;
    try {
      history = (await getStockHistory(data.businessId, $authSession.accessToken, product.id))
        .items;
    } catch (error) {
      errorMessage = messageOf(error, 'Riwayat stok belum dapat dimuat.');
    }
  }

  async function findBarcode(): Promise<void> {
    if (!$authSession || !scanBarcode.trim()) return;
    try {
      const product = await getProductByBarcode(
        data.businessId,
        $authSession.accessToken,
        scanBarcode.trim(),
      );
      products = [product];
      notice = `${product.name} ditemukan.`;
    } catch (error) {
      errorMessage = messageOf(error, 'Barcode belum terdaftar.');
    }
  }

  async function importCsv(event: Event): Promise<void> {
    if (!$authSession) return;
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    busy = true;
    try {
      const result = await importProductsCsv(data.businessId, $authSession.accessToken, file);
      notice = `${result.imported_count} produk berhasil diimpor.`;
      await loadAll();
    } catch (error) {
      errorMessage = messageOf(error, 'CSV belum dapat diimpor.');
    } finally {
      busy = false;
      input.value = '';
    }
  }

  function movementLabel(type: string): string {
    return (
      {
        OPENING: 'Stok awal',
        STOCK_IN: 'Stok masuk',
        STOCK_OUT: 'Stok keluar',
        ADJUSTMENT_IN: 'Penyesuaian tambah',
        ADJUSTMENT_OUT: 'Penyesuaian kurang',
        DAMAGED: 'Produk rusak',
        LOST: 'Produk hilang',
        SALE: 'Penjualan',
        PURCHASE: 'Pembelian',
        SALE_REVERSAL: 'Pembatalan penjualan',
        PURCHASE_REVERSAL: 'Pembatalan pembelian',
        REVISION_ADJUSTMENT: 'Perubahan transaksi',
      }[type] ?? type
    );
  }

  function messageOf(error: unknown, fallback: string): string {
    return error instanceof Error ? error.message : fallback;
  }
</script>

<svelte:head>
  <title>Produk dan Stok — KASTA</title>
</svelte:head>

<section class="text-slate-900 dark:text-slate-100">
  <header class="border-b border-slate-200 bg-white">
    <div class="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
      <div>
        <a href={resolve('/')} class="text-xl font-black text-emerald-950">KASTA</a>
        <p class="text-xs font-semibold text-slate-400">Produk dan stok usaha</p>
      </div>
      <a
        href={resolve('/usaha/[businessId]/transaksi', { businessId: data.businessId })}
        class="rounded-xl border border-slate-200 px-4 py-2 text-sm font-bold">Ke transaksi</a
      >
    </div>
  </header>

  <div class="mx-auto max-w-7xl px-5 py-8 sm:px-8">
    {#if notice}<p class="notice">{notice}</p>{/if}
    {#if errorMessage}<p class="error" role="alert">{errorMessage}</p>{/if}

    {#if loading}
      <p class="py-20 text-center text-slate-500">Memuat produk…</p>
    {:else if !$authSession}
      <p class="rounded-3xl bg-amber-50 p-8 text-center">Masuk kembali untuk mengelola stok.</p>
    {:else}
      <section class="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-sm font-bold text-emerald-700">Persediaan usaha</p>
          <h1 class="text-3xl font-black sm:text-4xl">Produk dan stok</h1>
          <p class="mt-2 text-slate-500">Pantau barang masuk, terjual, rusak, atau hilang.</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <label class="button secondary cursor-pointer"
            >Impor CSV<input
              class="sr-only"
              type="file"
              accept=".csv,text/csv"
              onchange={importCsv}
            /></label
          >
          <button
            class="button secondary"
            onclick={() => void exportProductsExcel(data.businessId, $authSession.accessToken)}
            >Ekspor Excel</button
          >
          <button class="button primary" onclick={openCreate}>Tambah produk</button>
        </div>
      </section>

      <section class="mt-7 grid gap-4 sm:grid-cols-3">
        <article class="metric">
          <span>Nilai persediaan</span><strong>{formatRupiah(summary.inventory_value)}</strong>
        </article>
        <article class="metric">
          <span>Produk aktif</span><strong>{summary.active_product_count}</strong>
        </article>
        <article class="metric {summary.low_stock_count > 0 ? '!bg-amber-50' : ''}">
          <span>Stok minimum</span><strong>{summary.low_stock_count} produk</strong>
        </article>
      </section>

      <section class="mt-7 rounded-3xl border border-slate-200 bg-white p-5">
        <div class="grid gap-3 lg:grid-cols-[1fr_1fr_auto_auto]">
          <input bind:value={query} placeholder="Cari nama, SKU, atau barcode" />
          <div class="flex gap-2">
            <input bind:value={scanBarcode} placeholder="Masukkan hasil scan barcode" />
            <button class="button secondary" onclick={() => void findBarcode()}>Cari</button>
          </div>
          <label class="flex items-center gap-2 rounded-xl border border-slate-200 px-4">
            <input class="!m-0 !w-auto" type="checkbox" bind:checked={lowStockOnly} /> Stok minimum
          </label>
          <button class="button primary" onclick={() => void loadAll()}>Terapkan</button>
        </div>

        <div class="mt-5 overflow-x-auto">
          <table>
            <thead
              ><tr><th>Produk</th><th>Harga</th><th>Stok</th><th>Status</th><th></th></tr></thead
            >
            <tbody>
              {#each products as product (product.id)}
                <tr>
                  <td
                    ><strong>{product.name}</strong><small
                      >{product.sku} · {product.barcode ?? 'Tanpa barcode'}</small
                    ></td
                  >
                  <td
                    >{formatRupiah(product.sale_price)}<small
                      >Beli {formatRupiah(product.purchase_price)}</small
                    ></td
                  >
                  <td
                    ><strong>{product.current_stock} {product.unit}</strong><small
                      >Minimum {product.minimum_stock}</small
                    ></td
                  >
                  <td>
                    <span class:warning={product.is_low_stock} class="tag">
                      {product.is_active
                        ? product.is_low_stock
                          ? 'Perlu diisi'
                          : 'Aman'
                        : 'Tidak aktif'}
                    </span>
                  </td>
                  <td
                    ><div class="flex justify-end gap-2">
                      <button class="mini" onclick={() => openMovement(product)}>Ubah stok</button>
                      <button class="mini" onclick={() => void showHistory(product)}>Riwayat</button
                      >
                      <button class="mini" onclick={() => openEdit(product)}>Edit</button>
                    </div></td
                  >
                </tr>
              {:else}
                <tr
                  ><td colspan="5" class="!py-12 text-center text-slate-500">Belum ada produk.</td
                  ></tr
                >
              {/each}
            </tbody>
          </table>
        </div>
      </section>

      <section class="mt-7 grid gap-5 lg:grid-cols-2">
        <article class="panel">
          <h2>Produk paling laku</h2>
          {#each summary.best_sellers as product (product.product_id)}
            <div class="row">
              <span>{product.name}</span><strong>{product.quantity_sold} {product.unit}</strong>
            </div>
          {:else}<p class="empty">Belum ada penjualan produk.</p>{/each}
        </article>
        <article class="panel">
          <h2>{historyProduct ? `Riwayat ${historyProduct.name}` : 'Riwayat stok terakhir'}</h2>
          {#if historyProduct}<button
              class="text-sm font-bold text-emerald-700"
              onclick={() => {
                historyProduct = null;
                void loadAll();
              }}>Lihat semua</button
            >{/if}
          {#each history.slice(0, 10) as movement (movement.id)}
            <div class="row">
              <span
                >{movementLabel(movement.movement_type)}<small>{movement.reason ?? ''}</small></span
              ><strong class:text-rose-600={movement.quantity_delta.startsWith('-')}
                >{movement.quantity_delta.startsWith('-')
                  ? ''
                  : '+'}{movement.quantity_delta}</strong
              >
            </div>
          {:else}<p class="empty">Belum ada perubahan stok.</p>{/each}
        </article>
      </section>
    {/if}
  </div>

  {#if formOpen}
    <div class="overlay" role="presentation">
      <form
        class="modal max-w-2xl"
        onsubmit={(event) => {
          event.preventDefault();
          void saveProduct();
        }}
      >
        <h2>{editing ? 'Edit produk' : 'Tambah produk'}</h2>
        <p>Stok setelah produk dibuat hanya diubah melalui menu Ubah stok.</p>
        <div class="mt-5 grid gap-4 sm:grid-cols-2">
          <label>Nama produk<input required bind:value={productForm.name} /></label>
          <label>SKU<input required bind:value={productForm.sku} /></label>
          <label>Barcode<input bind:value={productForm.barcode} /></label>
          <label>Kategori<input required bind:value={productForm.category} /></label>
          <label
            >Satuan<select bind:value={productForm.unit}
              >{#each units as unit (unit)}<option value={unit}>{unit}</option>{/each}</select
            ></label
          >
          <label
            >Harga beli<input
              required
              min="0"
              step="0.01"
              type="number"
              bind:value={productForm.purchase_price}
            /></label
          >
          <label
            >Harga jual<input
              required
              min="0"
              step="0.01"
              type="number"
              bind:value={productForm.sale_price}
            /></label
          >
          {#if !editing}<label
              >Stok awal<input
                required
                min="0"
                step="0.001"
                type="number"
                bind:value={productForm.opening_stock}
              /></label
            >{/if}
          <label
            >Stok minimum<input
              required
              min="0"
              step="0.001"
              type="number"
              bind:value={productForm.minimum_stock}
            /></label
          >
          <label class="flex items-center gap-3"
            ><input class="!m-0 !w-auto" type="checkbox" bind:checked={productForm.is_active} /> Produk
            aktif</label
          >
        </div>
        <div class="actions">
          <button type="button" class="button secondary" onclick={() => (formOpen = false)}
            >Batal</button
          ><button class="button primary" disabled={busy}>Simpan</button>
        </div>
      </form>
    </div>
  {/if}

  {#if movementProduct}
    <div class="overlay" role="presentation">
      <form
        class="modal max-w-lg"
        onsubmit={(event) => {
          event.preventDefault();
          void saveMovement();
        }}
      >
        <h2>Ubah stok {movementProduct.name}</h2>
        <p>Stok saat ini {movementProduct.current_stock} {movementProduct.unit}</p>
        <label class="mt-5 block"
          >Jenis perubahan<select bind:value={movementType}
            ><option value="STOCK_IN">Stok masuk</option><option value="STOCK_OUT"
              >Stok keluar</option
            ><option value="ADJUSTMENT">Penyesuaian hasil hitung</option><option value="DAMAGED"
              >Produk rusak</option
            ><option value="LOST">Produk hilang</option></select
          ></label
        >
        <label class="mt-4 block"
          >{movementType === 'ADJUSTMENT' ? 'Stok hasil hitung' : 'Jumlah'}<input
            required
            min="0"
            step="0.001"
            type="number"
            bind:value={movementQuantity}
          /></label
        >
        <label class="mt-4 block"
          >Alasan<textarea required minlength="3" rows="2" bind:value={movementReason}
          ></textarea></label
        >
        <label class="mt-4 block"
          >Nomor referensi <span>(opsional)</span><input bind:value={movementReference} /></label
        >
        <div class="actions">
          <button type="button" class="button secondary" onclick={() => (movementProduct = null)}
            >Batal</button
          ><button class="button primary" disabled={busy}>Catat perubahan</button>
        </div>
      </form>
    </div>
  {/if}
</section>

<style>
  input,
  select,
  textarea {
    margin-top: 0.35rem;
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 0.8rem;
    padding: 0.72rem 0.85rem;
    background: white;
  }
  label {
    color: #334155;
    font-size: 0.875rem;
    font-weight: 700;
  }
  label span {
    color: #94a3b8;
    font-weight: 400;
  }
  .button {
    border-radius: 0.8rem;
    padding: 0.75rem 1rem;
    font-size: 0.875rem;
    font-weight: 800;
  }
  .primary {
    background: #047857;
    color: white;
  }
  .secondary {
    border: 1px solid #cbd5e1;
    background: white;
    color: #334155;
  }
  .notice,
  .error {
    margin-bottom: 1rem;
    border-radius: 1rem;
    padding: 1rem 1.25rem;
    font-size: 0.875rem;
    font-weight: 700;
  }
  .notice {
    background: #ecfdf5;
    color: #065f46;
  }
  .error {
    background: #fff1f2;
    color: #be123c;
  }
  .metric,
  .panel {
    border: 1px solid #e2e8f0;
    border-radius: 1.5rem;
    background: white;
    padding: 1.35rem;
  }
  .metric span,
  td small,
  .row small {
    display: block;
    color: #64748b;
    font-size: 0.75rem;
  }
  .metric strong {
    display: block;
    margin-top: 0.4rem;
    font-size: 1.45rem;
  }
  table {
    width: 100%;
    min-width: 800px;
    border-collapse: collapse;
  }
  th,
  td {
    border-bottom: 1px solid #f1f5f9;
    padding: 0.9rem;
    text-align: left;
    font-size: 0.875rem;
  }
  th {
    color: #64748b;
    font-size: 0.72rem;
    text-transform: uppercase;
  }
  .tag {
    display: inline-block;
    border-radius: 999px;
    background: #ecfdf5;
    padding: 0.3rem 0.6rem;
    color: #047857;
    font-size: 0.75rem;
    font-weight: 800;
  }
  .tag.warning {
    background: #fffbeb;
    color: #b45309;
  }
  .mini {
    border: 1px solid #e2e8f0;
    border-radius: 0.6rem;
    padding: 0.45rem 0.65rem;
    font-size: 0.75rem;
    font-weight: 700;
  }
  .panel h2,
  .modal h2 {
    font-size: 1.25rem;
    font-weight: 900;
  }
  .modal > p {
    margin-top: 0.3rem;
    color: #64748b;
    font-size: 0.875rem;
  }
  .row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    border-top: 1px solid #f1f5f9;
    padding: 0.8rem 0;
    font-size: 0.875rem;
  }
  .empty {
    padding: 2rem 0;
    text-align: center;
    color: #64748b;
  }
  .overlay {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: grid;
    place-items: center;
    overflow-y: auto;
    background: rgb(15 23 42 / 0.45);
    padding: 1.25rem;
  }
  .modal {
    width: 100%;
    border-radius: 1.5rem;
    background: white;
    padding: 1.75rem;
    box-shadow: 0 25px 50px rgb(15 23 42 / 0.2);
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    margin-top: 1.5rem;
    border-top: 1px solid #f1f5f9;
    padding-top: 1.25rem;
  }
</style>

<script lang="ts">
  import { onMount } from 'svelte';
  import type { EntryKind, OptionItem, Product, TransactionPaymentMethod } from '@kasta/contracts';
  import { z } from 'zod';
  import { getProducts } from '$lib/api/inventory';
  import { createObligation, payObligation } from '$lib/api/obligations';
  import { getBusinessProfile } from '$lib/api/onboarding';
  import { createTransaction, getTransactionOptions } from '$lib/api/transactions';
  import { authSession } from '$lib/stores/auth-session';
  import Button from './Button.svelte';
  import Card from './Card.svelte';
  import FormField from './FormField.svelte';
  import Icon from './Icon.svelte';
  import SelectField from './SelectField.svelte';
  import Toast from './Toast.svelte';

  interface Props {
    businessId: string;
    kind: 'INCOME' | 'EXPENSE';
  }
  let { businessId, kind }: Props = $props();

  const CREDIT = 'CREDIT' as const;
  type PaymentChoice = TransactionPaymentMethod | typeof CREDIT;

  const today = new Intl.DateTimeFormat('sv-SE').format(new Date());
  const schema = z.object({
    date: z.string().min(1, 'Pilih tanggal transaksi.'),
    amount: z.string().regex(/^\d+(?:[.,]\d{1,2})?$/, 'Masukkan nominal yang benar.'),
    category: z.string().min(1, 'Pilih kategori.'),
    payment: z.string().min(1, 'Pilih cara pembayaran.'),
  });

  let step = $state(1);
  let date = $state(today);
  let amount = $state('');
  let category = $state('');
  let payment = $state<PaymentChoice>('CASH');
  let counterparty = $state('');
  let note = $state('');
  let recurring = $state(false);
  let dueDate = $state(today);
  let settledOnCreate = $state(false);
  let settledPaymentAccount = $state<'CASH' | 'BANK'>('CASH');

  interface ItemRow {
    productId: string;
    quantity: string;
    unitPrice: string;
  }
  let inventoryMode = $state<'SIMPLE' | 'PERPETUAL'>('SIMPLE');
  let products = $state<Product[]>([]);
  let itemRows = $state<ItemRow[]>([]);
  const itemsRequired = $derived(inventoryMode === 'PERPETUAL');

  let categories = $state<OptionItem[]>([]);
  let basePayments = $state<OptionItem[]>([
    { value: 'CASH', label: 'Tunai' },
    { value: 'BANK_TRANSFER', label: 'Transfer bank' },
    { value: 'QRIS', label: 'QRIS' },
    { value: 'E_WALLET', label: 'Dompet digital' },
  ]);
  let errors = $state<Record<string, string>>({});
  let notice = $state('');
  let noticeTone = $state<'success' | 'error'>('success');
  let busy = $state(false);

  const title = $derived(kind === 'INCOME' ? 'Catat Uang Masuk' : 'Catat Uang Keluar');
  const isCredit = $derived(payment === CREDIT);
  const creditLabel = $derived(kind === 'INCOME' ? 'Piutang (terima nanti)' : 'Utang (bayar nanti)');
  const payments = $derived([
    ...basePayments,
    { value: CREDIT, label: creditLabel } satisfies OptionItem,
  ]);
  const counterpartyLabel = $derived(
    isCredit
      ? kind === 'INCOME'
        ? 'Nama pelanggan'
        : 'Nama pemasok'
      : kind === 'INCOME'
        ? 'Nama pelanggan (opsional)'
        : 'Nama pemasok (opsional)',
  );
  const categoryLabel = $derived(kind === 'INCOME' ? 'Sumber pemasukan' : 'Kategori pengeluaran');

  onMount(async () => {
    const fallback =
      kind === 'INCOME'
        ? [
            { value: 'PENJUALAN', label: 'Penjualan' },
            { value: 'PENDAPATAN_JASA', label: 'Pendapatan jasa' },
          ]
        : [
            { value: 'PEMBELIAN', label: 'Pembelian' },
            { value: 'BEBAN_LAIN', label: 'Pengeluaran lain' },
          ];
    if (!$authSession || $authSession.businessId !== businessId) {
      categories = fallback;
      category = fallback[0].value;
      return;
    }
    try {
      const options = await getTransactionOptions(businessId, $authSession.accessToken);
      categories = kind === 'INCOME' ? options.income_sources : options.expense_categories;
      basePayments = options.payment_methods;
      category = categories[0]?.value ?? '';
    } catch {
      categories = fallback;
      category = fallback[0].value;
    }
    try {
      const profile = await getBusinessProfile(businessId, $authSession.accessToken);
      inventoryMode = profile.inventory_mode;
    } catch {
      inventoryMode = 'SIMPLE';
    }
    try {
      const list = await getProducts(businessId, $authSession.accessToken);
      products = list.items.filter((item) => item.is_active);
    } catch {
      products = [];
    }
    if (itemsRequired) itemRows = [{ productId: '', quantity: '1', unitPrice: '' }];
  });

  function addItemRow(): void {
    itemRows = [...itemRows, { productId: '', quantity: '1', unitPrice: '' }];
  }
  function removeItemRow(index: number): void {
    itemRows = itemRows.filter((_, i) => i !== index);
    syncAmountFromItems();
  }
  function onProductPicked(index: number): void {
    const row = itemRows[index];
    const product = products.find((item) => item.id === row.productId);
    if (product) {
      row.unitPrice = kind === 'INCOME' ? product.sale_price : product.purchase_price;
      itemRows = [...itemRows];
    }
    syncAmountFromItems();
  }
  function syncAmountFromItems(): void {
    if (itemRows.length === 0) return;
    const total = itemRows.reduce(
      (sum, row) => sum + (Number(row.quantity) || 0) * (Number(row.unitPrice) || 0),
      0,
    );
    const rounded = Math.round(total * 100) / 100;
    amount = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(2).replace('.', ',');
  }
  function productLabel(product: Product): string {
    return `${product.name} (stok: ${product.current_stock})`;
  }

  function normalizedAmount(): string {
    return amount.replace(/\./g, '').replace(',', '.');
  }
  function rupiah(value: string): string {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      maximumFractionDigits: 0,
    }).format(Number(value.replace(/\D/g, '')) || 0);
  }
  function next() {
    const result = schema
      .pick(step === 1 ? { date: true, amount: true } : { category: true, payment: true })
      .safeParse({ date, amount: normalizedAmount(), category: category || 'n/a', payment });
    const stepErrors: Record<string, string> = result.success
      ? {}
      : Object.fromEntries(result.error.issues.map((item) => [String(item.path[0]), item.message]));
    // When items drive the total (perpetual mode), the amount isn't known until the
    // product rows in step 2 are filled in, so step 1 shouldn't demand it up front.
    if (step === 1 && itemsRequired) delete stepErrors.amount;
    if (step === 2 && !isCredit && (itemsRequired || itemRows.length > 0)) {
      if (itemRows.length === 0) {
        stepErrors.items = 'Pilih minimal satu produk.';
      } else if (
        itemRows.some(
          (row) => !row.productId || !(Number(row.quantity) > 0) || !(Number(row.unitPrice) >= 0),
        )
      ) {
        stepErrors.items = 'Lengkapi produk, jumlah, dan harga setiap baris.';
      } else if (!(Number(normalizedAmount()) > 0)) {
        stepErrors.items = 'Total dari produk harus lebih dari 0.';
      }
    }
    if (step === 2 && isCredit) {
      if (!counterparty.trim()) {
        stepErrors.counterparty = `Isi nama ${kind === 'INCOME' ? 'pelanggan' : 'pemasok'} untuk ${kind === 'INCOME' ? 'piutang' : 'utang'}.`;
      }
      if (!settledOnCreate) {
        if (!dueDate) {
          stepErrors.dueDate = 'Pilih tanggal jatuh tempo.';
        } else if (dueDate < date) {
          stepErrors.dueDate = 'Jatuh tempo tidak boleh sebelum tanggal transaksi.';
        }
      }
    }
    if (Object.keys(stepErrors).length > 0) {
      errors = stepErrors;
      return;
    }
    errors = {};
    step += 1;
  }
  async function save() {
    if (!$authSession || $authSession.businessId !== businessId) {
      noticeTone = 'error';
      notice = 'Silakan masuk kembali sebelum menyimpan transaksi.';
      return;
    }
    busy = true;
    try {
      if (isCredit) {
        const obligationKind = kind === 'INCOME' ? 'RECEIVABLE' : 'PAYABLE';
        const created = await createObligation(businessId, $authSession.accessToken, obligationKind, {
          party_name: counterparty.trim(),
          initial_amount: normalizedAmount(),
          transaction_date: date,
          due_date: settledOnCreate ? date : dueDate,
          note: note.trim(),
          reminder_enabled: true,
          reminder_days_before: 3,
        });
        if (settledOnCreate) {
          await payObligation(businessId, $authSession.accessToken, obligationKind, created.id, {
            amount: created.initial_amount,
            payment_date: date,
            payment_account: settledPaymentAccount,
            note: 'Lunas saat pencatatan',
          });
        }
        noticeTone = 'success';
        notice = settledOnCreate
          ? `${kind === 'INCOME' ? 'Piutang' : 'Utang'} lunas berhasil dicatat.`
          : `${kind === 'INCOME' ? 'Piutang' : 'Utang'} berhasil dicatat.`;
      } else {
        await createTransaction(businessId, $authSession.accessToken, {
          entry_kind: kind as EntryKind,
          transaction_date: date,
          amount: normalizedAmount(),
          category_account: category,
          counterparty_name: counterparty || null,
          payment_method: payment as TransactionPaymentMethod,
          note: note.trim(),
          recurrence_frequency: recurring ? 'MONTHLY' : null,
          recurrence_interval: recurring ? 1 : null,
          idempotency_key: crypto.randomUUID(),
          items: itemRows.map((row) => ({
            product_id: row.productId,
            quantity: row.quantity,
            unit_price: row.unitPrice,
          })),
        });
        noticeTone = 'success';
        notice = `${title} berhasil disimpan.`;
      }
      amount = '';
      counterparty = '';
      note = '';
      recurring = false;
      dueDate = today;
      settledOnCreate = false;
      settledPaymentAccount = 'CASH';
      itemRows = itemsRequired ? [{ productId: '', quantity: '1', unitPrice: '' }] : [];
      step = 1;
    } catch (error) {
      noticeTone = 'error';
      notice = error instanceof Error ? error.message : 'Transaksi belum dapat disimpan.';
    } finally {
      busy = false;
    }
  }
</script>

<Card>
  <div class="mb-6 flex items-center gap-2" aria-label={`Langkah ${step} dari 3`}>
    {#each [1, 2, 3] as item (item)}
      <span
        class="h-2 flex-1 rounded-full {item <= step
          ? 'bg-kasta-600'
          : 'bg-[var(--surface-muted)]'}"
      ></span>
    {/each}
    <span class="ml-2 text-xs font-bold text-[var(--text-muted)]">{step}/3</span>
  </div>

  {#if step === 1}
    <div class="space-y-5">
      <div>
        <label class="kasta-label" for="quick-amount">Nominal</label>
        <div class="relative">
          <span class="absolute left-4 top-3.5 font-black text-[var(--text-muted)]">Rp</span><input
            id="quick-amount"
            class="kasta-field pl-12 text-xl font-black"
            inputmode="numeric"
            placeholder={itemsRequired ? 'Otomatis dari produk' : '0'}
            disabled={itemsRequired}
            bind:value={amount}
            aria-invalid={errors.amount ? 'true' : undefined}
          />
        </div>
        {#if itemsRequired}<p class="mt-1 text-xs text-[var(--text-muted)]">
            Mode pencatatan detail aktif: nominal dihitung otomatis dari produk yang dipilih di
            langkah berikutnya.
          </p>{/if}
        {#if errors.amount}<p class="mt-1 text-xs font-bold text-red-700" role="alert">
            {errors.amount}
          </p>{/if}
      </div>
      <FormField
        id="quick-date"
        label="Tanggal"
        type="date"
        bind:value={date}
        error={errors.date}
        required
      />
    </div>
  {:else if step === 2}
    <div class="space-y-5">
      <SelectField
        id="quick-payment"
        label={kind === 'INCOME' ? 'Diterima melalui' : 'Dibayar melalui'}
        options={payments}
        bind:value={payment}
        error={errors.payment}
        required
      />
      {#if isCredit}
        <p class="rounded-xl bg-amber-50 p-3 text-xs font-semibold text-amber-800">
          {kind === 'INCOME'
            ? 'Dicatat sebagai piutang: uang belum diterima, tapi penjualan tetap tercatat dan bisa dilunasi nanti dari halaman Piutang.'
            : 'Dicatat sebagai utang: barang/jasa diterima sekarang, pembayaran menyusul dan bisa dilunasi nanti dari halaman Utang.'}
        </p>
      {:else}
        <SelectField
          id="quick-category"
          label={categoryLabel}
          options={categories}
          bind:value={category}
          error={errors.category}
          required
        />
        <div>
          <div class="flex items-center justify-between">
            <span class="kasta-label"
              >Produk{itemsRequired ? '' : ' (opsional)'}{#if itemsRequired}<span
                  class="text-red-600">*</span
                >{/if}</span
            >
            <button
              type="button"
              class="text-xs font-bold text-kasta-700"
              onclick={addItemRow}>+ Tambah produk</button
            >
          </div>
          {#if products.length === 0}
            <p class="mt-1 text-xs text-[var(--text-muted)]">
              Belum ada produk aktif. Tambahkan produk di halaman Produk untuk memakainya di sini.
            </p>
          {/if}
          {#each itemRows as row, index (index)}
            <div class="mt-2 grid grid-cols-[1fr_70px_100px_auto] items-start gap-2">
              <select
                class="kasta-field"
                bind:value={row.productId}
                onchange={() => onProductPicked(index)}
                aria-label="Produk"
                ><option value="">Pilih produk</option>{#each products as product (product.id)}<option
                    value={product.id}>{productLabel(product)}</option
                  >{/each}</select
              >
              <input
                class="kasta-field"
                type="number"
                min="0"
                step="0.001"
                placeholder="Jml"
                aria-label="Jumlah"
                bind:value={row.quantity}
                oninput={syncAmountFromItems}
              /><input
                class="kasta-field"
                type="number"
                min="0"
                step="0.01"
                placeholder="Harga satuan"
                aria-label="Harga satuan"
                bind:value={row.unitPrice}
                oninput={syncAmountFromItems}
              /><button
                type="button"
                class="kasta-field grid place-items-center px-3 text-red-600"
                aria-label="Hapus produk"
                onclick={() => removeItemRow(index)}>✕</button
              >
            </div>
          {/each}
          {#if errors.items}<p class="mt-1 text-xs font-bold text-red-700" role="alert">
              {errors.items}
            </p>{/if}
        </div>
      {/if}
      <FormField
        id="quick-party"
        label={counterpartyLabel}
        bind:value={counterparty}
        error={errors.counterparty}
        required={isCredit}
      />
      {#if isCredit}
        <label
          class="flex min-h-12 items-center gap-3 rounded-xl border border-[var(--border)] p-3 text-sm font-bold"
          ><input
            type="checkbox"
            class="h-5 w-5 accent-kasta-700"
            bind:checked={settledOnCreate}
          /> Sudah lunas sejak dicatat</label
        >
        {#if settledOnCreate}
          <SelectField
            id="quick-settled-account"
            label="Dibayar melalui"
            options={[
              { value: 'CASH', label: 'Kas' },
              { value: 'BANK', label: 'Bank' },
            ]}
            bind:value={settledPaymentAccount}
            required
          />
        {:else}
          <FormField
            id="quick-due-date"
            label="Jatuh tempo"
            type="date"
            bind:value={dueDate}
            error={errors.dueDate}
            required
          />
        {/if}
      {/if}
      <div>
        <label class="kasta-label" for="quick-note">Catatan (opsional)</label><textarea
          id="quick-note"
          class="kasta-field min-h-24"
          bind:value={note}
        ></textarea>
      </div>
      {#if !isCredit}
        <label
          class="flex min-h-12 items-center gap-3 rounded-xl border border-[var(--border)] p-3 text-sm font-bold"
          ><input type="checkbox" class="h-5 w-5 accent-kasta-700" bind:checked={recurring} /> Ulangi
          setiap bulan</label
        >
      {/if}
    </div>
  {:else}
    <div class="rounded-2xl bg-[var(--surface-muted)] p-5">
      <p class="text-sm font-bold text-[var(--text-muted)]">Periksa sebelum menyimpan</p>
      <p class="mt-2 text-3xl font-black">{rupiah(amount)}</p>
      <dl class="mt-5 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt class="text-[var(--text-muted)]">Tanggal</dt>
          <dd class="font-bold">{date}</dd>
        </div>
        {#if isCredit}
          <div>
            <dt class="text-[var(--text-muted)]">{settledOnCreate ? 'Status' : 'Jatuh tempo'}</dt>
            <dd class="font-bold">{settledOnCreate ? 'Lunas sejak dicatat' : dueDate}</dd>
          </div>
        {:else}
          <div>
            <dt class="text-[var(--text-muted)]">Kategori</dt>
            <dd class="font-bold">{categories.find((item) => item.value === category)?.label}</dd>
          </div>
        {/if}
        <div>
          <dt class="text-[var(--text-muted)]">Cara</dt>
          <dd class="font-bold">{payments.find((item) => item.value === payment)?.label}</dd>
        </div>
        <div>
          <dt class="text-[var(--text-muted)]">Pihak terkait</dt>
          <dd class="font-bold">{counterparty || 'Tidak diisi'}</dd>
        </div>
      </dl>
      {#if !isCredit && itemRows.length > 0}
        <div class="mt-4 rounded-xl bg-[var(--surface)] p-3 text-sm">
          <p class="font-bold text-[var(--text-muted)]">Produk</p>
          <ul class="mt-1 space-y-1">
            {#each itemRows as row (row.productId)}
              <li class="flex justify-between">
                <span>{products.find((product) => product.id === row.productId)?.name ?? '—'} × {row.quantity}</span>
                <span class="font-bold"
                  >{rupiah(String(Number(row.quantity) * Number(row.unitPrice)))}</span
                >
              </li>
            {/each}
          </ul>
        </div>
      {/if}
      <p class="mt-5 flex gap-2 text-xs leading-5 text-[var(--text-muted)]">
        <Icon name="check" size={17} /> Catatan keuangan dibuat otomatis setelah transaksi disimpan.
      </p>
    </div>
  {/if}

  <div class="mt-7 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
    {#if step > 1}<Button variant="secondary" onclick={() => (step -= 1)}>Kembali</Button>{/if}
    {#if step < 3}<Button onclick={next}>Lanjut</Button>{:else}<Button
        onclick={save}
        disabled={busy}>{busy ? 'Menyimpan…' : 'Simpan transaksi'}</Button
      >{/if}
  </div>
</Card>
<Toast open={Boolean(notice)} message={notice} tone={noticeTone} onClose={() => (notice = '')} />

<script lang="ts">
  import type {
    EntryKind,
    OptionItem,
    Product,
    RecurrenceFrequency,
    SimpleTransactionInput,
    TransactionDraft,
    TransactionListItem,
    TransactionOptions,
    TransactionPaymentMethod,
  } from '@kasta/contracts';
  import { resolve } from '$app/paths';
  import { onMount } from 'svelte';
  import { z } from 'zod';

  import {
    createDraft,
    createTransaction,
    getDrafts,
    getTransactionOptions,
    getTransactions,
    postDraft,
    reverseTransaction,
    reviseTransaction,
    uploadReceipt,
  } from '$lib/api/transactions';
  import { getProducts } from '$lib/api/inventory';
  import { digitsOnly, formatRupiah, formatRupiahDigits } from '$lib/money/rupiah';
  import { authSession } from '$lib/stores/auth-session';

  let { data }: { data: { businessId: string } } = $props();
  let options = $state<TransactionOptions>({
    income_sources: [],
    expense_categories: [],
    payment_methods: [],
  });
  let transactions = $state<TransactionListItem[]>([]);
  let drafts = $state<TransactionDraft[]>([]);
  let loading = $state(true);
  let busy = $state(false);
  let errorMessage = $state('');
  let notice = $state('');
  let step = $state(0);
  let entryKind = $state<EntryKind>('INCOME');
  let transactionDate = $state(new Date().toISOString().slice(0, 10));
  let amountDigits = $state('');
  let categoryAccount = $state('');
  let paymentMethod = $state<TransactionPaymentMethod>('CASH');
  let counterpartyName = $state('');
  let note = $state('');
  let photo = $state<File | null>(null);
  let recurring = $state(false);
  let recurrenceFrequency = $state<RecurrenceFrequency>('MONTHLY');
  let recurrenceInterval = $state(1);
  let idempotencyKey = $state('');
  let editingId = $state<string | null>(null);
  let revisionReason = $state('');
  let query = $state('');
  let filterKind = $state('');
  let filterStatus = $state('');
  let filterMethod = $state('');
  let cancelTarget = $state<TransactionListItem | null>(null);
  let cancelReason = $state('');
  let inventoryProducts = $state<Product[]>([]);
  let selectedProductId = $state('');
  let productQuantity = $state('1');
  let productUnitPrice = $state('0.00');

  const kindMeta: Record<EntryKind, { label: string; hint: string; icon: string; tone: string }> = {
    INCOME: {
      label: 'Uang Masuk',
      hint: 'Penjualan atau pendapatan usaha',
      icon: '↓',
      tone: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    },
    EXPENSE: {
      label: 'Uang Keluar',
      hint: 'Belanja dan biaya usaha',
      icon: '↑',
      tone: 'bg-amber-50 text-amber-800 border-amber-200',
    },
    CAPITAL: {
      label: 'Tambah Modal',
      hint: 'Masukkan uang pemilik ke usaha',
      icon: '+',
      tone: 'bg-sky-50 text-sky-800 border-sky-200',
    },
    OWNER_DRAW: {
      label: 'Ambil Uang Pribadi',
      hint: 'Ambil uang usaha untuk pemilik',
      icon: '−',
      tone: 'bg-violet-50 text-violet-800 border-violet-200',
    },
  };

  let categoryOptions = $derived(
    entryKind === 'INCOME'
      ? options.income_sources
      : entryKind === 'EXPENSE'
        ? options.expense_categories
        : [],
  );
  let availablePayments = $derived(
    entryKind === 'EXPENSE'
      ? options.payment_methods.filter((item) =>
          ['CASH', 'BANK_TRANSFER', 'CARD'].includes(item.value),
        )
      : entryKind === 'CAPITAL' || entryKind === 'OWNER_DRAW'
        ? options.payment_methods.filter((item) => item.value === 'CASH')
        : options.payment_methods,
  );

  onMount(() => void loadAll());

  async function loadAll(): Promise<void> {
    if (!$authSession || $authSession.businessId !== data.businessId) {
      loading = false;
      return;
    }
    try {
      const [loadedOptions, loadedDrafts, loadedProducts] = await Promise.all([
        getTransactionOptions(data.businessId, $authSession.accessToken),
        getDrafts(data.businessId, $authSession.accessToken),
        getProducts(data.businessId, $authSession.accessToken, {}),
      ]);
      options = loadedOptions;
      drafts = loadedDrafts;
      inventoryProducts = loadedProducts.items.filter((product) => product.is_active);
      await loadTransactions();
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Transaksi belum dapat dimuat.';
    } finally {
      loading = false;
    }
  }

  async function loadTransactions(): Promise<void> {
    if (!$authSession) return;
    const response = await getTransactions(data.businessId, $authSession.accessToken, {
      q: query,
      entry_kind: filterKind,
      transaction_status: filterStatus,
      payment_method: filterMethod,
    });
    transactions = response.items;
  }

  function begin(kind: EntryKind): void {
    resetForm();
    entryKind = kind;
    categoryAccount =
      kind === 'INCOME'
        ? (options.income_sources[0]?.value ?? '')
        : kind === 'EXPENSE'
          ? (options.expense_categories[0]?.value ?? '')
          : '';
    paymentMethod = 'CASH';
    step = 1;
  }

  function resetForm(): void {
    transactionDate = new Date().toISOString().slice(0, 10);
    amountDigits = '';
    categoryAccount = '';
    paymentMethod = 'CASH';
    counterpartyName = '';
    note = '';
    photo = null;
    recurring = false;
    recurrenceFrequency = 'MONTHLY';
    recurrenceInterval = 1;
    idempotencyKey = crypto.randomUUID();
    editingId = null;
    revisionReason = '';
    selectedProductId = '';
    productQuantity = '1';
    productUnitPrice = '0.00';
    errorMessage = '';
  }

  function nextStep(): void {
    errorMessage = '';
    if (step === 1) {
      const result = z
        .object({
          transactionDate: z.string().date(),
          amount: z
            .string()
            .regex(/^\d{1,16}$/)
            .refine((value) => BigInt(value) > 0n),
          category: z.string(),
        })
        .safeParse({
          transactionDate,
          amount: amountDigits,
          category: categoryAccount,
        });
      if (
        !result.success ||
        ((entryKind === 'INCOME' || entryKind === 'EXPENSE') && !categoryAccount)
      ) {
        errorMessage = 'Isi tanggal, nominal, dan pilihan transaksi.';
        return;
      }
    }
    if (step < 3) step += 1;
  }

  function payload(): SimpleTransactionInput {
    const selectedProduct = inventoryProducts.find((product) => product.id === selectedProductId);
    return {
      entry_kind: entryKind,
      transaction_date: transactionDate,
      amount: `${digitsOnly(amountDigits)}.00`,
      category_account: categoryAccount || null,
      counterparty_name: counterpartyName.trim() || null,
      payment_method: paymentMethod,
      note: note.trim(),
      recurrence_frequency: recurring ? recurrenceFrequency : null,
      recurrence_interval: recurring ? recurrenceInterval : null,
      idempotency_key: editingId ? null : idempotencyKey,
      items:
        selectedProduct && (entryKind === 'INCOME' || entryKind === 'EXPENSE')
          ? [
              {
                product_id: selectedProduct.id,
                quantity: String(productQuantity),
                unit_price: productUnitPrice,
              },
            ]
          : [],
    };
  }

  async function save(asDraft: boolean): Promise<void> {
    if (!$authSession) return;
    busy = true;
    errorMessage = '';
    try {
      if (asDraft) {
        await createDraft(data.businessId, $authSession.accessToken, {
          ...payload(),
          client_reference: crypto.randomUUID(),
        });
        notice = 'Draft tersimpan. Anda dapat melanjutkannya nanti.';
      } else {
        const response = editingId
          ? await reviseTransaction(
              data.businessId,
              editingId,
              $authSession.accessToken,
              payload(),
              revisionReason || 'Memperbarui catatan transaksi',
            )
          : await createTransaction(data.businessId, $authSession.accessToken, payload());
        if (photo) {
          try {
            await uploadReceipt(
              data.businessId,
              response.transaction.id,
              $authSession.accessToken,
              photo,
            );
          } catch {
            notice = 'Transaksi tercatat, tetapi foto bukti belum berhasil diunggah.';
            step = 0;
            resetForm();
            await loadAll();
            return;
          }
        }
        notice = editingId
          ? 'Transaksi diperbarui dan riwayat lama tetap tersimpan.'
          : 'Transaksi berhasil dicatat.';
      }
      step = 0;
      resetForm();
      await loadAll();
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Transaksi belum dapat disimpan.';
    } finally {
      busy = false;
    }
  }

  function editTransaction(item: TransactionListItem): void {
    resetForm();
    editingId = item.id;
    entryKind = item.entry_kind ?? 'INCOME';
    transactionDate = item.transaction_date;
    amountDigits = item.amount.split('.')[0]?.replace(/\D/g, '') ?? '';
    categoryAccount = item.category_account_key ?? '';
    paymentMethod = item.payment_method_code ?? 'CASH';
    counterpartyName = item.counterparty_name ?? '';
    note = item.description;
    selectedProductId = item.items[0]?.product_id ?? '';
    productQuantity = item.items[0]?.quantity ?? '1';
    productUnitPrice = item.items[0]?.unit_price ?? '0.00';
    step = 1;
  }

  function updateAmountFromProduct(): void {
    const amount = Number(productUnitPrice) * Number(productQuantity || '0');
    if (Number.isFinite(amount) && amount > 0) amountDigits = Math.round(amount).toString();
  }

  function selectProduct(): void {
    const product = inventoryProducts.find((item) => item.id === selectedProductId);
    productUnitPrice = product
      ? entryKind === 'INCOME'
        ? product.sale_price
        : product.purchase_price
      : '0.00';
    updateAmountFromProduct();
  }

  async function postSavedDraft(draft: TransactionDraft): Promise<void> {
    if (!$authSession) return;
    busy = true;
    try {
      await postDraft(data.businessId, draft.id, $authSession.accessToken);
      notice = 'Draft berhasil diposting.';
      await loadAll();
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Draft belum dapat diposting.';
    } finally {
      busy = false;
    }
  }

  async function confirmCancellation(): Promise<void> {
    if (!$authSession || !cancelTarget || cancelReason.trim().length < 3) {
      errorMessage = 'Isi alasan pembatalan.';
      return;
    }
    busy = true;
    try {
      await reverseTransaction(
        data.businessId,
        cancelTarget.id,
        $authSession.accessToken,
        cancelReason,
      );
      notice = 'Transaksi dibatalkan. Catatan pembatalan sudah dibuat otomatis.';
      cancelTarget = null;
      cancelReason = '';
      await loadTransactions();
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Transaksi belum dapat dibatalkan.';
    } finally {
      busy = false;
    }
  }

  function choosePhoto(event: Event): void {
    const selected = (event.currentTarget as HTMLInputElement).files?.[0] ?? null;
    if (selected && selected.size > 8 * 1024 * 1024) {
      photo = null;
      errorMessage = 'Foto bukti paling besar 8 MB.';
      return;
    }
    photo = selected;
  }

  function labelFor(items: OptionItem[], value: string | null): string {
    return items.find((item) => item.value === value)?.label ?? value ?? '—';
  }
</script>

<svelte:head>
  <title>Transaksi — KASTA</title>
  <meta name="description" content="Catat uang masuk dan keluar usaha dengan mudah." />
</svelte:head>

<section class="text-slate-900 dark:text-slate-100">
  <header class="border-b border-slate-200 bg-white">
    <div class="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
      <div>
        <a href={resolve('/')} class="text-xl font-black tracking-tight text-emerald-950">KASTA</a>
        <p class="text-xs font-semibold text-slate-400">Catatan usaha sehari-hari</p>
      </div>
      <nav class="flex gap-2">
        <a
          href={resolve('/usaha/[businessId]/laporan', { businessId: data.businessId })}
          class="rounded-xl bg-emerald-700 px-4 py-2 text-sm font-bold text-white">Laporan</a
        >
        <a
          href={resolve('/usaha/[businessId]/profil', { businessId: data.businessId })}
          class="rounded-xl border border-slate-200 px-4 py-2 text-sm font-bold text-slate-600"
          >Profil usaha</a
        >
      </nav>
    </div>
  </header>

  <div class="mx-auto max-w-7xl px-5 py-8 sm:px-8">
    {#if notice}
      <p
        class="mb-5 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm font-semibold text-emerald-800"
      >
        {notice}
      </p>
    {/if}
    {#if errorMessage}
      <p
        role="alert"
        class="mb-5 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm font-semibold text-rose-700"
      >
        {errorMessage}
      </p>
    {/if}

    {#if loading}
      <p class="py-20 text-center text-slate-500">Memuat transaksi…</p>
    {:else if !$authSession}
      <div class="mx-auto max-w-xl rounded-3xl border border-amber-200 bg-amber-50 p-9 text-center">
        <h1 class="text-2xl font-black">Sesi Anda sudah berakhir</h1>
        <p class="mt-2 text-slate-600">Masuk kembali untuk mencatat transaksi.</p>
      </div>
    {:else if step === 0}
      <section>
        <p class="text-sm font-bold text-emerald-700">Pilih yang ingin dicatat</p>
        <h1 class="mt-1 text-3xl font-black tracking-tight sm:text-4xl">Keuangan usaha hari ini</h1>
        <div class="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {#each Object.entries(kindMeta) as [kind, meta] (kind)}
            <button
              type="button"
              data-testid={`menu-${kind.toLowerCase()}`}
              class={`group rounded-3xl border p-5 text-left transition hover:-translate-y-0.5 hover:shadow-lg ${meta.tone}`}
              onclick={() => begin(kind as EntryKind)}
            >
              <span
                class="grid h-11 w-11 place-items-center rounded-2xl bg-white/80 text-2xl font-black shadow-sm"
                >{meta.icon}</span
              >
              <strong class="mt-5 block text-lg">{meta.label}</strong>
              <small class="mt-1 block leading-5 opacity-75">{meta.hint}</small>
            </button>
          {/each}
        </div>
      </section>

      {#if drafts.length > 0}
        <section class="mt-10 rounded-3xl border border-slate-200 bg-white p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-bold text-amber-700">Belum selesai</p>
              <h2 class="text-xl font-black">Draft transaksi</h2>
            </div>
            <span class="rounded-full bg-amber-50 px-3 py-1 text-sm font-bold text-amber-700"
              >{drafts.length}</span
            >
          </div>
          <div class="mt-4 grid gap-3 sm:grid-cols-2">
            {#each drafts as draft (draft.id)}
              <article class="flex items-center justify-between rounded-2xl bg-slate-50 p-4">
                <div>
                  <strong>{kindMeta[draft.entry_kind].label}</strong>
                  <p class="text-sm text-slate-500">{formatRupiah(draft.amount)} · {draft.note}</p>
                </div>
                <button
                  class="rounded-xl bg-slate-900 px-3 py-2 text-sm font-bold text-white"
                  disabled={busy}
                  onclick={() => void postSavedDraft(draft)}>Posting</button
                >
              </article>
            {/each}
          </div>
        </section>
      {/if}

      <section class="mt-10 rounded-3xl border border-slate-200 bg-white p-5 sm:p-7">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p class="text-sm font-bold text-emerald-700">Riwayat</p>
            <h2 class="text-2xl font-black">Transaksi terakhir</h2>
          </div>
          <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
            <label class="lg:col-span-2"
              ><span class="sr-only">Cari transaksi</span><input
                bind:value={query}
                placeholder="Cari catatan atau nama…"
              /></label
            >
            <select bind:value={filterKind} aria-label="Filter jenis"
              ><option value="">Semua jenis</option><option value="INCOME">Uang Masuk</option
              ><option value="EXPENSE">Uang Keluar</option><option value="CAPITAL"
                >Tambah Modal</option
              ><option value="OWNER_DRAW">Ambil Uang Pribadi</option></select
            >
            <select bind:value={filterStatus} aria-label="Filter status"
              ><option value="">Semua status</option><option value="POSTED">Aktif</option><option
                value="REVERSED">Dibatalkan</option
              ></select
            >
            <select bind:value={filterMethod} aria-label="Filter pembayaran"
              ><option value="">Semua pembayaran</option
              >{#each options.payment_methods as method (method.value)}<option value={method.value}
                  >{method.label}</option
                >{/each}</select
            >
            <button
              class="rounded-xl bg-emerald-700 px-4 py-3 text-sm font-bold text-white"
              onclick={() => void loadTransactions()}>Terapkan</button
            >
          </div>
        </div>
        <div class="mt-6 space-y-3">
          {#each transactions as item (item.id)}
            <article
              class="flex flex-col gap-4 rounded-2xl border border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div class="flex items-center gap-4">
                <span
                  class={`grid h-11 w-11 place-items-center rounded-2xl font-black ${item.entry_kind === 'INCOME' || item.entry_kind === 'CAPITAL' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}
                  >{kindMeta[item.entry_kind ?? 'INCOME'].icon}</span
                >
                <div>
                  <strong>{item.description}</strong>
                  <p class="text-sm text-slate-500">
                    {item.transaction_date} · {item.counterparty_name ??
                      labelFor(options.payment_methods, item.payment_method_code)}
                  </p>
                </div>
              </div>
              <div class="flex items-center justify-between gap-4 sm:justify-end">
                <div class="text-right">
                  <strong class="text-lg">{formatRupiah(item.amount)}</strong>
                  <p
                    class={`text-xs font-bold ${item.status === 'REVERSED' ? 'text-rose-600' : 'text-emerald-700'}`}
                  >
                    {item.status === 'REVERSED'
                      ? 'Dibatalkan'
                      : item.receipt_count > 0
                        ? `${item.receipt_count} foto bukti`
                        : 'Tercatat'}
                  </p>
                </div>
                {#if item.status === 'POSTED'}
                  <div class="flex gap-2">
                    <button
                      class="rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold"
                      onclick={() => editTransaction(item)}>Ubah</button
                    ><button
                      class="rounded-lg border border-rose-200 px-3 py-2 text-xs font-bold text-rose-700"
                      onclick={() => (cancelTarget = item)}>Batalkan</button
                    >
                  </div>
                {/if}
              </div>
            </article>
          {:else}
            <p class="rounded-2xl bg-slate-50 py-10 text-center text-slate-500">
              Belum ada transaksi yang sesuai.
            </p>
          {/each}
        </div>
      </section>
    {:else}
      <section
        class="mx-auto max-w-3xl overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-xl shadow-slate-200/60"
      >
        <div class="border-b border-slate-100 px-6 py-5 sm:px-9">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-bold text-emerald-700">
                {editingId ? 'Ubah transaksi' : kindMeta[entryKind].label}
              </p>
              <h1 class="text-2xl font-black">Langkah {step} dari 3</h1>
            </div>
            <button class="text-sm font-bold text-slate-500" onclick={() => (step = 0)}
              >Tutup</button
            >
          </div>
          <div class="mt-4 grid grid-cols-3 gap-2" aria-label={`Langkah ${step} dari 3`}>
            {#each [1, 2, 3] as position (position)}<span
                class={`h-2 rounded-full ${position <= step ? 'bg-emerald-600' : 'bg-slate-100'}`}
              ></span>{/each}
          </div>
        </div>
        <div class="p-6 sm:p-9">
          {#if step === 1}
            <h2 class="text-xl font-black">Jumlah dan tanggal</h2>
            <div class="mt-6 grid gap-5 sm:grid-cols-2">
              <label>Tanggal<input bind:value={transactionDate} type="date" /></label>
              <label
                >Nominal
                <div class="money-field">
                  <span>Rp</span><input
                    aria-label="Nominal"
                    value={formatRupiahDigits(amountDigits)}
                    inputmode="numeric"
                    placeholder="0"
                    oninput={(event) =>
                      (amountDigits = digitsOnly((event.currentTarget as HTMLInputElement).value))}
                  />
                </div></label
              >
              {#if categoryOptions.length > 0}<label class="sm:col-span-2"
                  >{entryKind === 'INCOME' ? 'Sumber pemasukan' : 'Kategori pengeluaran'}<select
                    bind:value={categoryAccount}
                    >{#each categoryOptions as option (option.value)}<option value={option.value}
                        >{option.label}</option
                      >{/each}</select
                  ></label
                >{/if}
              <label class="sm:col-span-2"
                >{entryKind === 'INCOME' ? 'Metode penerimaan' : 'Metode pembayaran'}<select
                  bind:value={paymentMethod}
                  >{#each availablePayments as option (option.value)}<option value={option.value}
                      >{option.label}</option
                    >{/each}</select
                ></label
              >
            </div>
          {:else if step === 2}
            <h2 class="text-xl font-black">
              Tambahan <span class="text-sm font-medium text-slate-400">(boleh dilewati)</span>
            </h2>
            <div class="mt-6 grid gap-5">
              {#if (entryKind === 'INCOME' || entryKind === 'EXPENSE') && inventoryProducts.length > 0}
                <div class="grid gap-4 rounded-2xl bg-emerald-50 p-4 sm:grid-cols-2">
                  <label
                    >Produk <span class="font-normal text-slate-400">(opsional)</span><select
                      bind:value={selectedProductId}
                      onchange={selectProduct}
                      ><option value="">Tanpa produk</option
                      >{#each inventoryProducts as product (product.id)}<option value={product.id}
                          >{product.name} — stok {product.current_stock} {product.unit}</option
                        >{/each}</select
                    ></label
                  >
                  <label
                    >Jumlah<input
                      type="number"
                      min="0.001"
                      step="0.001"
                      bind:value={productQuantity}
                      oninput={updateAmountFromProduct}
                      disabled={!selectedProductId}
                    /></label
                  >
                  <p class="sm:col-span-2 text-xs leading-5 text-emerald-800">
                    Penjualan mengurangi stok dan pembelian menambah stok setelah transaksi
                    disimpan.
                  </p>
                </div>
              {/if}
              {#if entryKind === 'INCOME'}<label
                  >Pelanggan<input
                    bind:value={counterpartyName}
                    placeholder="Nama pelanggan (opsional)"
                  /></label
                >{:else if entryKind === 'EXPENSE'}<label
                  >Pemasok<input
                    bind:value={counterpartyName}
                    placeholder="Nama pemasok (opsional)"
                  /></label
                >{/if}
              <label
                >Catatan<textarea
                  bind:value={note}
                  rows="3"
                  placeholder="Contoh: Belanja bahan untuk minggu ini"
                ></textarea></label
              >
              <label
                >Foto bukti <span class="font-normal text-slate-400">(opsional)</span><input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onchange={choosePhoto}
                /></label
              >
              {#if !editingId}<label
                  class="flex items-center gap-3 rounded-2xl border border-slate-200 p-4"
                  ><input class="!m-0 !w-5" type="checkbox" bind:checked={recurring} /><span
                    >Jadikan transaksi berulang</span
                  ></label
                >{/if}
              {#if recurring}<div class="grid gap-4 rounded-2xl bg-slate-50 p-4 sm:grid-cols-2">
                  <label
                    >Berulang setiap<select bind:value={recurrenceFrequency}
                      ><option value="WEEKLY">Minggu</option><option value="MONTHLY">Bulan</option
                      ></select
                    ></label
                  ><label
                    >Jarak<input
                      bind:value={recurrenceInterval}
                      type="number"
                      min="1"
                      max="12"
                    /></label
                  >
                </div>{/if}
            </div>
          {:else}
            <h2 class="text-xl font-black">Periksa sebelum menyimpan</h2>
            <dl class="mt-6 grid gap-3 rounded-3xl bg-slate-50 p-5 sm:grid-cols-2">
              <div>
                <dt>Jenis</dt>
                <dd>{kindMeta[entryKind].label}</dd>
              </div>
              <div>
                <dt>Nominal</dt>
                <dd data-testid="review-amount">{formatRupiah(amountDigits)}</dd>
              </div>
              <div>
                <dt>Tanggal</dt>
                <dd>{transactionDate}</dd>
              </div>
              <div>
                <dt>Pembayaran</dt>
                <dd>{labelFor(options.payment_methods, paymentMethod)}</dd>
              </div>
              {#if categoryAccount}<div>
                  <dt>{entryKind === 'INCOME' ? 'Sumber' : 'Kategori'}</dt>
                  <dd>{labelFor(categoryOptions, categoryAccount)}</dd>
                </div>{/if}
              {#if selectedProductId}<div>
                  <dt>Produk</dt>
                  <dd>
                    {inventoryProducts.find((product) => product.id === selectedProductId)?.name} × {productQuantity}
                  </dd>
                </div>{/if}
              <div>
                <dt>Catatan</dt>
                <dd>{note || 'Tidak ada catatan'}</dd>
              </div>
            </dl>
            {#if editingId}<label class="mt-5 block"
                >Alasan perubahan<textarea
                  bind:value={revisionReason}
                  rows="2"
                  placeholder="Contoh: Nominal sebelumnya salah"
                ></textarea></label
              >{/if}
            <p class="mt-5 rounded-2xl bg-emerald-50 p-4 text-sm leading-6 text-emerald-800">
              KASTA akan membuat catatan keuangan berpasangan secara otomatis. Anda tidak perlu
              mengisi debit atau kredit.
            </p>
          {/if}
          <div
            class="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-6"
          >
            <button
              class="rounded-xl px-4 py-3 text-sm font-bold text-slate-500"
              onclick={() => (step = Math.max(1, step - 1))}
              disabled={step === 1}>Kembali</button
            >
            <div class="flex gap-3">
              {#if step === 3 && !editingId}<button
                  class="rounded-xl border border-slate-300 px-4 py-3 text-sm font-bold"
                  disabled={busy}
                  onclick={() => void save(true)}>Simpan draft</button
                >{/if}<button
                data-testid="transaction-next"
                class="rounded-xl bg-emerald-700 px-5 py-3 text-sm font-bold text-white"
                disabled={busy}
                onclick={() => (step === 3 ? void save(false) : nextStep())}
                >{busy
                  ? 'Menyimpan…'
                  : step === 3
                    ? editingId
                      ? 'Simpan perubahan'
                      : 'Catat transaksi'
                    : 'Lanjut'}</button
              >
            </div>
          </div>
        </div>
      </section>
    {/if}
  </div>

  {#if cancelTarget}
    <div class="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-5" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="cancel-title"
        class="w-full max-w-md rounded-3xl bg-white p-7 shadow-2xl"
      >
        <h2 id="cancel-title" class="text-xl font-black">Batalkan transaksi?</h2>
        <p class="mt-2 text-sm text-slate-600">
          Catatan lama tetap tersimpan dan KASTA membuat catatan pembatalan.
        </p>
        <label class="mt-5 block"
          >Alasan<textarea
            bind:value={cancelReason}
            rows="3"
            placeholder="Tuliskan alasan pembatalan"
          ></textarea></label
        >
        <div class="mt-6 flex justify-end gap-3">
          <button
            class="rounded-xl px-4 py-2 font-bold text-slate-500"
            onclick={() => (cancelTarget = null)}>Kembali</button
          ><button
            class="rounded-xl bg-rose-700 px-4 py-2 font-bold text-white"
            disabled={busy}
            onclick={() => void confirmCancellation()}>Ya, batalkan</button
          >
        </div>
      </div>
    </div>
  {/if}
</section>

<style>
  label {
    color: #334155;
    font-size: 0.875rem;
    font-weight: 700;
  }
  input,
  select,
  textarea {
    margin-top: 0.4rem;
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 0.8rem;
    background: white;
    padding: 0.75rem 0.9rem;
    outline: none;
  }
  input:focus,
  select:focus,
  textarea:focus {
    border-color: #059669;
    box-shadow: 0 0 0 3px #d1fae5;
  }
  .money-field {
    margin-top: 0.4rem;
    display: flex;
    align-items: center;
    overflow: hidden;
    border: 1px solid #cbd5e1;
    border-radius: 0.8rem;
    background: white;
  }
  .money-field span {
    padding-left: 0.9rem;
    font-weight: 800;
    color: #047857;
  }
  .money-field input {
    margin: 0;
    border: 0;
    box-shadow: none;
    font-size: 1.1rem;
    font-weight: 800;
  }
  dt {
    color: #64748b;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  dd {
    margin-top: 0.2rem;
    font-weight: 800;
  }
</style>

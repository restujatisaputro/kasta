<script lang="ts">
  import type { EntryKind, OptionItem, ReceiptReview, TransactionPaymentMethod } from '@kasta/contracts';

  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import FormField from '$lib/components/FormField.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import SelectField from '$lib/components/SelectField.svelte';
  import Toast from '$lib/components/Toast.svelte';
  import { confirmReceiptScan, uploadReceiptScan } from '$lib/api/receipts';
  import { getTransactionOptions } from '$lib/api/transactions';
  import { recognizeReceiptText, terminateReceiptOcr, type RecognizeProgress } from '$lib/ocr/receipt-ocr';
  import { authSession } from '$lib/stores/auth-session';
  import { onDestroy } from 'svelte';

  let { data }: { data: { businessId: string } } = $props();

  type Stage = 'empty' | 'processing' | 'review' | 'confirmed' | 'error';

  let file = $state<File | null>(null);
  let stage = $state<Stage>('empty');
  let progressLabel = $state('Menyiapkan pembaca teks…');
  let errorMessage = $state('');
  let message = $state('');

  let receipt = $state<ReceiptReview | null>(null);
  let entryKind = $state<Extract<EntryKind, 'INCOME' | 'EXPENSE'>>('EXPENSE');
  let merchant = $state('');
  let receiptDate = $state(new Intl.DateTimeFormat('sv-SE').format(new Date()));
  let total = $state('');
  let categoryAccount = $state('');
  let paymentMethod = $state('CASH');
  let note = $state('');

  let incomeCategories = $state<OptionItem[]>([]);
  let expenseCategories = $state<OptionItem[]>([]);
  let paymentMethods = $state<OptionItem[]>([{ value: 'CASH', label: 'Tunai' }]);
  const categoryOptions = $derived(entryKind === 'INCOME' ? incomeCategories : expenseCategories);

  let acknowledgeDuplicate = $state(false);
  let showConfirm = $state(false);
  let busy = $state(false);
  let confirmedTransactionId = $state<string | null>(null);

  onDestroy(() => void terminateReceiptOcr());

  function fieldValue(name: string): string {
    return receipt?.fields.find((item) => item.name === name)?.value ?? '';
  }

  async function loadOptions() {
    if (!$authSession || $authSession.businessId !== data.businessId) return;
    try {
      const options = await getTransactionOptions(data.businessId, $authSession.accessToken);
      incomeCategories = options.income_sources;
      expenseCategories = options.expense_categories;
      paymentMethods = options.payment_methods;
    } catch {
      // Keep the built-in fallback; the confirm step still works with it.
    }
  }
  void loadOptions();

  function reset() {
    file = null;
    stage = 'empty';
    receipt = null;
    merchant = '';
    total = '';
    note = '';
    acknowledgeDuplicate = false;
    confirmedTransactionId = null;
  }

  function selectFile(event: Event) {
    const selected = (event.currentTarget as HTMLInputElement).files?.[0] ?? null;
    if (!selected) return;
    if (
      !['image/jpeg', 'image/png', 'image/webp'].includes(selected.type) ||
      selected.size > 10 * 1024 * 1024
    ) {
      errorMessage = 'Gunakan foto JPG, PNG, atau WebP dengan ukuran maksimal 10 MB.';
      return;
    }
    void processFile(selected);
  }

  async function processFile(selected: File) {
    if (!$authSession || $authSession.businessId !== data.businessId) {
      errorMessage = 'Silakan masuk kembali sebelum mengunggah nota.';
      return;
    }
    errorMessage = '';
    file = selected;
    stage = 'processing';
    progressLabel = 'Membaca teks pada nota…';
    try {
      const rawText = await recognizeReceiptText(selected, (update: RecognizeProgress) => {
        if (update.status === 'recognizing text') {
          progressLabel = `Membaca teks pada nota… ${Math.round(update.progress * 100)}%`;
        } else {
          progressLabel = 'Menyiapkan pembaca teks…';
        }
      });
      progressLabel = 'Mengunggah dan menganalisis nota…';
      const review = await uploadReceiptScan(
        data.businessId,
        $authSession.accessToken,
        selected,
        rawText,
      );
      receipt = review;
      entryKind = fieldValue('transaction_kind') === 'INCOME' ? 'INCOME' : 'EXPENSE';
      merchant = fieldValue('merchant_name');
      receiptDate = fieldValue('receipt_date') || receiptDate;
      total = fieldValue('total');
      const parsedCategory = fieldValue('category_account');
      const fallbackCategory = (entryKind === 'INCOME' ? incomeCategories : expenseCategories)[0]?.value ?? '';
      categoryAccount = parsedCategory || fallbackCategory;
      const parsedPayment = fieldValue('payment_method');
      paymentMethod = parsedPayment || 'CASH';
      acknowledgeDuplicate = false;
      stage = 'review';
    } catch (error) {
      errorMessage =
        error instanceof Error
          ? error.message
          : 'Nota belum dapat diproses. Periksa koneksi lalu coba lagi.';
      stage = 'error';
    }
  }

  async function retry() {
    if (!file) {
      reset();
      return;
    }
    await processFile(file);
  }

  function requestConfirm() {
    if (!merchant.trim()) {
      errorMessage = 'Isi nama toko sebelum konfirmasi.';
      return;
    }
    if (!(Number(total) > 0)) {
      errorMessage = 'Isi total belanja yang benar sebelum konfirmasi.';
      return;
    }
    if ((receipt?.duplicate_candidates.length ?? 0) > 0 && !acknowledgeDuplicate) {
      errorMessage = 'Periksa nota serupa di bawah, lalu centang persetujuan sebelum lanjut.';
      return;
    }
    errorMessage = '';
    showConfirm = true;
  }

  async function confirm() {
    if (!$authSession || !receipt) return;
    showConfirm = false;
    busy = true;
    try {
      const result = await confirmReceiptScan(data.businessId, $authSession.accessToken, receipt.id, {
        corrections: {
          merchant_name: merchant.trim(),
          receipt_date: receiptDate,
          total,
        },
        entry_kind: entryKind,
        category_account: categoryAccount || undefined,
        payment_method: paymentMethod as TransactionPaymentMethod,
        note: note.trim(),
        acknowledge_duplicate: acknowledgeDuplicate,
      });
      confirmedTransactionId = result.transaction_id;
      stage = 'confirmed';
      message = 'Nota dikonfirmasi dan transaksi berhasil dibuat.';
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Nota belum dapat dikonfirmasi.';
    } finally {
      busy = false;
    }
  }
</script>

<svelte:head><title>Foto Nota | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Pencatatan lebih cepat"
  title="Foto Nota"
  description="Unggah foto nota, periksa hasil bacaan, lalu konfirmasi sebelum transaksi dibuat."
/>
<div class="mt-6 grid gap-4 lg:grid-cols-[1fr_1.2fr]">
  <Card>
    <h2 class="text-lg font-black">1. Pilih foto nota</h2>
    <label
      for="receipt-file"
      class="mt-4 flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-kasta-300 bg-kasta-50 p-6 text-center transition hover:bg-kasta-100 dark:bg-kasta-950"
    >
      <span class="grid h-14 w-14 place-items-center rounded-2xl bg-kasta-700 text-white"
        ><Icon name="camera" size={28} /></span
      >
      <strong class="mt-4">{file?.name ?? 'Ambil foto atau pilih dari perangkat'}</strong>
      <span class="mt-2 text-sm text-[var(--text-muted)]"
        >Pastikan seluruh nota terlihat dan tidak buram.</span
      >
    </label>
    <input
      id="receipt-file"
      class="sr-only"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      onchange={selectFile}
    />
    <p class="mt-3 text-xs text-[var(--text-muted)]">Format JPG, PNG, WebP. Maksimal 10 MB.</p>
    {#if stage !== 'empty'}
      <div class="mt-3"><Button variant="secondary" onclick={reset}>Pilih foto lain</Button></div>
    {/if}
  </Card>
  <Card>
    <h2 class="text-lg font-black">2. Periksa hasil bacaan</h2>
    {#if stage === 'empty'}<div class="mt-8 text-center text-[var(--text-muted)]">
        <Icon name="note" size={36} />
        <p class="mt-3 text-sm">Hasil foto akan tampil di sini.</p>
      </div>
    {:else if stage === 'processing'}<div class="mt-8" role="status" aria-live="polite">
        <div class="h-2 overflow-hidden rounded-full bg-[var(--surface-muted)]">
          <span class="block h-full w-2/3 animate-pulse rounded-full bg-kasta-600"></span>
        </div>
        <p class="mt-3 text-center text-sm font-bold">{progressLabel}</p>
      </div>
    {:else if stage === 'error'}<div class="mt-6 rounded-2xl bg-red-50 p-5 text-center dark:bg-red-950">
        <Icon name="close" size={32} />
        <h3 class="mt-2 font-black">Nota belum dapat diproses</h3>
        <p class="mt-2 text-sm text-[var(--text-muted)]">{errorMessage}</p>
        <div class="mt-5 flex justify-center gap-2">
          <Button onclick={retry}>Coba lagi</Button><Button variant="secondary" onclick={reset}
            >Pilih foto lain</Button
          >
        </div>
      </div>
    {:else if stage === 'confirmed'}<div
        class="mt-6 rounded-2xl bg-kasta-50 p-5 text-center dark:bg-kasta-950"
      >
        <Icon name="check" size={32} />
        <h3 class="mt-2 font-black">Transaksi berhasil dibuat</h3>
        <p class="mt-2 text-sm text-[var(--text-muted)]">
          Nota dan transaksi sudah tersimpan dan tercatat dalam pembukuan.
        </p>
        <div class="mt-5 grid gap-2 sm:grid-cols-2">
          <Button href={`/usaha/${data.businessId}/transaksi`}>Lihat transaksi</Button><Button
            variant="secondary"
            onclick={reset}>Unggah nota lain</Button
          >
        </div>
      </div>
    {:else}<div class="mt-5 space-y-5">
        {#if receipt?.fields.some((item) => item.value)}
          <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
            <strong>Terbaca otomatis.</strong> Periksa dan perbaiki bila ada yang kurang tepat.
          </div>
        {:else}
          <div class="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <strong>Tidak banyak yang terbaca.</strong> Isi field di bawah secara manual.
          </div>
        {/if}
        {#if receipt && receipt.duplicate_candidates.length > 0}
          <div class="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
            <strong>Mirip dengan nota sebelumnya:</strong>
            <ul class="mt-1 list-disc pl-5">
              {#each receipt.duplicate_candidates as candidate (candidate.id)}
                <li>
                  {candidate.merchant_name ?? 'Toko tidak diketahui'} · {candidate.receipt_date ?? '-'} ·
                  {candidate.total_amount ?? '-'}
                </li>
              {/each}
            </ul>
            <label class="mt-2 flex items-center gap-2 font-semibold"
              ><input type="checkbox" bind:checked={acknowledgeDuplicate} /> Saya sudah periksa, ini bukan
              nota yang sama</label
            >
          </div>
        {/if}
        <div>
          <label class="kasta-label" for="receipt-kind">Jenis transaksi</label><select
            id="receipt-kind"
            class="kasta-field"
            bind:value={entryKind}
            ><option value="EXPENSE">Pembelian / Uang Keluar</option><option value="INCOME"
              >Penjualan / Uang Masuk</option
            ></select
          >
        </div>
        <FormField
          id="merchant"
          label="Nama toko / responden"
          bind:value={merchant}
          placeholder="Contoh: Toko Maju"
          required
        /><FormField id="receipt-date" label="Tanggal" type="date" bind:value={receiptDate} required
        /><FormField
          id="receipt-total"
          label="Total belanja"
          bind:value={total}
          placeholder="Contoh: 25000"
          required
        />
        <SelectField
          id="receipt-category"
          label={entryKind === 'INCOME' ? 'Sumber pemasukan' : 'Kategori pengeluaran'}
          options={categoryOptions}
          bind:value={categoryAccount}
        />
        <SelectField
          id="receipt-payment"
          label={entryKind === 'INCOME' ? 'Diterima melalui' : 'Dibayar melalui'}
          options={paymentMethods}
          bind:value={paymentMethod}
        />
        <div>
          <label class="kasta-label" for="receipt-note">Catatan (opsional)</label><textarea
            id="receipt-note"
            class="kasta-field min-h-20"
            bind:value={note}
          ></textarea>
        </div>
        {#if errorMessage}<p class="text-sm font-bold text-red-700" role="alert">{errorMessage}</p>{/if}
        <Button full onclick={requestConfirm} disabled={busy}
          >{busy ? 'Menyimpan…' : 'Konfirmasi hasil nota'}</Button
        >
      </div>{/if}
  </Card>
</div>
<ConfirmDialog
  open={showConfirm}
  title="Konfirmasi hasil nota?"
  message="Pastikan nama toko, tanggal, dan total sudah sesuai dengan foto. Transaksi akan langsung dibuat."
  confirmLabel="Ya, sudah benar"
  onConfirm={confirm}
  onCancel={() => (showConfirm = false)}
/>
<Toast open={Boolean(message)} {message} tone="success" onClose={() => (message = '')} />

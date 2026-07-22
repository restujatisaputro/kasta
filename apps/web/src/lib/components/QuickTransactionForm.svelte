<script lang="ts">
  import { onMount } from 'svelte';
  import type { EntryKind, OptionItem, TransactionPaymentMethod } from '@kasta/contracts';
  import { z } from 'zod';
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
  let payment = $state<TransactionPaymentMethod>('CASH');
  let counterparty = $state('');
  let note = $state('');
  let recurring = $state(false);
  let categories = $state<OptionItem[]>([]);
  let payments = $state<OptionItem[]>([
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
  const counterpartyLabel = $derived(
    kind === 'INCOME' ? 'Nama pelanggan (opsional)' : 'Nama pemasok (opsional)',
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
      payments = options.payment_methods;
      category = categories[0]?.value ?? '';
    } catch {
      categories = fallback;
      category = fallback[0].value;
    }
  });

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
      .safeParse({ date, amount: normalizedAmount(), category, payment });
    if (!result.success) {
      errors = Object.fromEntries(
        result.error.issues.map((item) => [String(item.path[0]), item.message]),
      );
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
      await createTransaction(businessId, $authSession.accessToken, {
        entry_kind: kind as EntryKind,
        transaction_date: date,
        amount: normalizedAmount(),
        category_account: category,
        counterparty_name: counterparty || null,
        payment_method: payment,
        note: note.trim(),
        recurrence_frequency: recurring ? 'MONTHLY' : null,
        recurrence_interval: recurring ? 1 : null,
        idempotency_key: crypto.randomUUID(),
      });
      noticeTone = 'success';
      notice = `${title} berhasil disimpan.`;
      amount = '';
      counterparty = '';
      note = '';
      recurring = false;
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
            placeholder="0"
            bind:value={amount}
            aria-invalid={errors.amount ? 'true' : undefined}
          />
        </div>
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
        id="quick-category"
        label={categoryLabel}
        options={categories}
        bind:value={category}
        error={errors.category}
        required
      />
      <SelectField
        id="quick-payment"
        label={kind === 'INCOME' ? 'Diterima melalui' : 'Dibayar melalui'}
        options={payments}
        bind:value={payment}
        error={errors.payment}
        required
      />
      <FormField id="quick-party" label={counterpartyLabel} bind:value={counterparty} />
      <div>
        <label class="kasta-label" for="quick-note">Catatan (opsional)</label><textarea
          id="quick-note"
          class="kasta-field min-h-24"
          bind:value={note}
        ></textarea>
      </div>
      <label
        class="flex min-h-12 items-center gap-3 rounded-xl border border-[var(--border)] p-3 text-sm font-bold"
        ><input type="checkbox" class="h-5 w-5 accent-kasta-700" bind:checked={recurring} /> Ulangi setiap
        bulan</label
      >
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
        <div>
          <dt class="text-[var(--text-muted)]">Kategori</dt>
          <dd class="font-bold">{categories.find((item) => item.value === category)?.label}</dd>
        </div>
        <div>
          <dt class="text-[var(--text-muted)]">Cara</dt>
          <dd class="font-bold">{payments.find((item) => item.value === payment)?.label}</dd>
        </div>
        <div>
          <dt class="text-[var(--text-muted)]">Pihak terkait</dt>
          <dd class="font-bold">{counterparty || 'Tidak diisi'}</dd>
        </div>
      </dl>
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

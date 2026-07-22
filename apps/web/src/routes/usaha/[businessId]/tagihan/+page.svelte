<script lang="ts">
  import type {
    Obligation,
    ObligationAgingReport,
    ObligationDetail,
    ObligationInput,
    ObligationKind,
    ObligationStatus,
  } from '@kasta/contracts';
  import { resolve } from '$app/paths';
  import { onMount } from 'svelte';

  import {
    cancelObligation,
    createObligation,
    getObligation,
    getObligationAging,
    getObligationReminders,
    getObligations,
    payObligation,
  } from '$lib/api/obligations';
  import { formatRupiah } from '$lib/money/rupiah';
  import { authSession } from '$lib/stores/auth-session';

  let { data }: { data: { businessId: string } } = $props();
  let kind = $state<ObligationKind>('RECEIVABLE');
  let items = $state<Obligation[]>([]);
  let aging = $state<ObligationAgingReport | null>(null);
  let reminderCount = $state(0);
  let loading = $state(true);
  let busy = $state(false);
  let errorMessage = $state('');
  let notice = $state('');
  let formOpen = $state(false);
  let paymentTarget = $state<Obligation | null>(null);
  let detail = $state<ObligationDetail | null>(null);
  let query = $state('');
  let statusFilter = $state<ObligationStatus | ''>('');
  let dueTo = $state('');
  let overdueOnly = $state(false);
  let form = $state<ObligationInput>(emptyForm());
  let paymentAmount = $state('');
  let paymentAccount = $state<'CASH' | 'BANK'>('CASH');
  let paymentNote = $state('');

  const statuses: Array<{ value: ObligationStatus; label: string }> = [
    { value: 'OPEN', label: 'Belum Dibayar' },
    { value: 'PARTIALLY_PAID', label: 'Dibayar Sebagian' },
    { value: 'PAID', label: 'Sudah Lunas' },
    { value: 'OVERDUE', label: 'Terlambat' },
    { value: 'CANCELLED', label: 'Dibatalkan' },
  ];

  onMount(() => void loadAll());

  function today(): string {
    return new Date().toISOString().slice(0, 10);
  }

  function emptyForm(): ObligationInput {
    return {
      party_name: '',
      initial_amount: '',
      transaction_date: today(),
      due_date: today(),
      note: '',
      reminder_enabled: true,
      reminder_days_before: 3,
    };
  }

  async function loadAll(): Promise<void> {
    if (!$authSession || $authSession.businessId !== data.businessId) {
      loading = false;
      return;
    }
    loading = true;
    errorMessage = '';
    try {
      const [list, report, reminders] = await Promise.all([
        getObligations(data.businessId, $authSession.accessToken, kind, {
          q: query,
          status: statusFilter,
          due_to: dueTo,
          overdue_only: overdueOnly,
        }),
        getObligationAging(data.businessId, $authSession.accessToken),
        getObligationReminders(data.businessId, $authSession.accessToken),
      ]);
      items = list.items;
      aging = report;
      reminderCount = reminders.items.length;
    } catch (error) {
      errorMessage = messageOf(error, 'Utang dan piutang belum dapat dimuat.');
    } finally {
      loading = false;
    }
  }

  async function switchKind(next: ObligationKind): Promise<void> {
    kind = next;
    statusFilter = '';
    await loadAll();
  }

  async function saveClaim(): Promise<void> {
    if (!$authSession) return;
    if (!form.party_name?.trim() || Number(form.initial_amount) <= 0) {
      errorMessage = `Isi nama ${kind === 'RECEIVABLE' ? 'pelanggan' : 'pemasok'} dan nilai tagihan.`;
      return;
    }
    busy = true;
    try {
      await createObligation(data.businessId, $authSession.accessToken, kind, form);
      notice = `${kind === 'RECEIVABLE' ? 'Piutang' : 'Utang'} berhasil dicatat.`;
      formOpen = false;
      form = emptyForm();
      await loadAll();
    } catch (error) {
      errorMessage = messageOf(error, 'Tagihan belum dapat disimpan.');
    } finally {
      busy = false;
    }
  }

  function openPayment(item: Obligation): void {
    paymentTarget = item;
    paymentAmount = item.remaining_amount;
    paymentAccount = 'CASH';
    paymentNote = '';
  }

  async function savePayment(): Promise<void> {
    if (!$authSession || !paymentTarget) return;
    busy = true;
    try {
      await payObligation(data.businessId, $authSession.accessToken, kind, paymentTarget.id, {
        amount: paymentAmount,
        payment_date: today(),
        payment_account: paymentAccount,
        note: paymentNote,
      });
      notice = 'Pembayaran berhasil dicatat dan sisa tagihan diperbarui.';
      paymentTarget = null;
      await loadAll();
    } catch (error) {
      errorMessage = messageOf(error, 'Pembayaran belum dapat dicatat.');
    } finally {
      busy = false;
    }
  }

  async function showHistory(item: Obligation): Promise<void> {
    if (!$authSession) return;
    try {
      detail = await getObligation(data.businessId, $authSession.accessToken, kind, item.id);
    } catch (error) {
      errorMessage = messageOf(error, 'Riwayat pembayaran belum dapat dimuat.');
    }
  }

  async function cancel(item: Obligation): Promise<void> {
    if (!$authSession) return;
    const reason = window.prompt('Tuliskan alasan pembatalan (minimal 3 karakter):');
    if (!reason || reason.trim().length < 3) return;
    try {
      await cancelObligation(
        data.businessId,
        $authSession.accessToken,
        kind,
        item.id,
        reason.trim(),
      );
      notice = 'Tagihan dibatalkan dan jurnal pembalik dibuat.';
      await loadAll();
    } catch (error) {
      errorMessage = messageOf(error, 'Tagihan belum dapat dibatalkan.');
    }
  }

  function canPay(item: Obligation): boolean {
    return !['PAID', 'CANCELLED'].includes(item.status);
  }

  function messageOf(error: unknown, fallback: string): string {
    return error instanceof Error ? error.message : fallback;
  }
</script>

<svelte:head><title>Utang dan Piutang — KASTA</title></svelte:head>

<section class="text-slate-900 dark:text-slate-100">
  <header class="border-b border-slate-200 bg-white">
    <div class="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
      <div>
        <a href={resolve('/')} class="text-xl font-black text-emerald-950">KASTA</a>
        <p class="text-xs font-semibold text-slate-400">Utang dan piutang usaha</p>
      </div>
      <a
        href={resolve('/usaha/[businessId]/transaksi', { businessId: data.businessId })}
        class="rounded-xl border border-slate-200 px-4 py-2 text-sm font-bold">Ke transaksi</a
      >
    </div>
  </header>

  <div class="mx-auto max-w-7xl px-5 py-8 sm:px-8">
    {#if notice}<p class="mb-4 rounded-xl bg-emerald-50 p-3 text-emerald-800">{notice}</p>{/if}
    {#if errorMessage}<p class="mb-4 rounded-xl bg-red-50 p-3 text-red-700" role="alert">
        {errorMessage}
      </p>{/if}

    <section class="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-sm font-bold text-emerald-700">Tagihan usaha</p>
        <h1 class="text-3xl font-black sm:text-4xl">Utang dan Piutang</h1>
        <p class="mt-2 text-slate-500">
          Pantau jatuh tempo, pembayaran, dan sisa tagihan tanpa menghitung manual.
        </p>
      </div>
      <button
        class="rounded-xl bg-emerald-700 px-5 py-3 font-bold text-white"
        onclick={() => {
          form = emptyForm();
          formOpen = true;
        }}>Tambah {kind === 'RECEIVABLE' ? 'piutang' : 'utang'}</button
      >
    </section>

    <div class="mt-7 flex gap-2 rounded-2xl bg-slate-100 p-1" aria-label="Jenis tagihan">
      <button
        class="flex-1 rounded-xl px-4 py-3 font-bold {kind === 'RECEIVABLE'
          ? 'bg-white text-emerald-800 shadow-sm'
          : 'text-slate-500'}"
        onclick={() => void switchKind('RECEIVABLE')}>Piutang pelanggan</button
      >
      <button
        class="flex-1 rounded-xl px-4 py-3 font-bold {kind === 'PAYABLE'
          ? 'bg-white text-emerald-800 shadow-sm'
          : 'text-slate-500'}"
        onclick={() => void switchKind('PAYABLE')}>Utang pemasok</button
      >
    </div>

    <section class="mt-5 grid gap-4 sm:grid-cols-3">
      <article class="rounded-2xl border border-slate-200 bg-white p-5">
        <span class="text-sm text-slate-500">Total belum lunas</span><strong
          class="mt-1 block text-2xl"
          >{formatRupiah(
            kind === 'RECEIVABLE'
              ? (aging?.receivables.total_open ?? '0')
              : (aging?.payables.total_open ?? '0'),
          )}</strong
        >
      </article>
      <article class="rounded-2xl border border-slate-200 bg-white p-5">
        <span class="text-sm text-slate-500">Jumlah catatan</span><strong
          class="mt-1 block text-2xl">{items.length}</strong
        >
      </article>
      <article class="rounded-2xl border border-amber-200 bg-amber-50 p-5">
        <span class="text-sm text-amber-700">Perlu diingatkan</span><strong
          class="mt-1 block text-2xl text-amber-900">{reminderCount}</strong
        >
      </article>
    </section>

    <section class="mt-5 rounded-3xl border border-slate-200 bg-white p-5">
      <div class="grid gap-3 md:grid-cols-[1fr_220px_180px_auto]">
        <input
          class="rounded-xl border border-slate-200 px-4 py-3"
          bind:value={query}
          placeholder="Cari pelanggan, pemasok, atau catatan"
        />
        <select class="rounded-xl border border-slate-200 px-4" bind:value={statusFilter}
          ><option value="">Semua status</option>{#each statuses as status (status.value)}<option
              value={status.value}>{status.label}</option
            >{/each}</select
        >
        <input
          class="rounded-xl border border-slate-200 px-4"
          type="date"
          bind:value={dueTo}
          aria-label="Jatuh tempo sampai"
        />
        <button
          class="rounded-xl bg-emerald-700 px-5 py-3 font-bold text-white"
          onclick={() => void loadAll()}>Terapkan</button
        >
      </div>
      <label class="mt-3 flex items-center gap-2 text-sm font-semibold text-slate-600"
        ><input type="checkbox" bind:checked={overdueOnly} /> Hanya yang terlambat</label
      >

      {#if loading}<p class="py-16 text-center text-slate-500">Memuat tagihan…</p>
      {:else if !$authSession}<p class="py-16 text-center text-slate-500">
          Masuk kembali untuk melihat tagihan.
        </p>
      {:else if items.length === 0}<p class="py-16 text-center text-slate-500">
          Belum ada catatan pada filter ini.
        </p>
      {:else}
        <div class="mt-5 overflow-x-auto">
          <table class="w-full text-left">
            <thead
              ><tr class="border-b text-sm text-slate-500"
                ><th class="p-3">{kind === 'RECEIVABLE' ? 'Pelanggan' : 'Pemasok'}</th><th
                  class="p-3">Sisa tagihan</th
                ><th class="p-3">Jatuh tempo</th><th class="p-3">Status</th><th class="p-3"
                ></th></tr
              ></thead
            ><tbody>
              {#each items as item (item.id)}<tr class="border-b border-slate-100"
                  ><td class="p-3"
                    ><strong>{item.party.name}</strong><small class="block text-slate-400"
                      >Awal {formatRupiah(item.initial_amount)}</small
                    ></td
                  ><td class="p-3 font-bold">{formatRupiah(item.remaining_amount)}</td><td
                    class="p-3">{item.due_date}</td
                  ><td class="p-3"
                    ><span
                      class="rounded-full px-3 py-1 text-xs font-bold {item.status === 'OVERDUE'
                        ? 'bg-red-100 text-red-700'
                        : item.status === 'PAID'
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-amber-100 text-amber-800'}">{item.status_label}</span
                    ></td
                  ><td class="p-3"
                    ><div class="flex flex-wrap justify-end gap-2">
                      {#if canPay(item)}<button
                          class="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-bold text-white"
                          onclick={() => openPayment(item)}>Catat bayar</button
                        >{/if}<button
                        class="rounded-lg border px-3 py-2 text-xs font-bold"
                        onclick={() => void showHistory(item)}>Riwayat</button
                      >{#if item.paid_amount === '0.00' && item.status !== 'CANCELLED'}<button
                          class="rounded-lg px-3 py-2 text-xs font-bold text-red-600"
                          onclick={() => void cancel(item)}>Batalkan</button
                        >{/if}
                    </div></td
                  ></tr
                >{/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>

    {#if aging}<section class="mt-5 rounded-3xl border border-slate-200 bg-white p-5">
        <h2 class="text-lg font-black">Umur tagihan</h2>
        <div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {#each (kind === 'RECEIVABLE' ? aging.receivables : aging.payables).buckets as bucket (bucket.code)}<article
              class="rounded-2xl bg-slate-50 p-4"
            >
              <span class="text-xs font-bold text-slate-500">{bucket.label}</span><strong
                class="mt-2 block">{formatRupiah(bucket.amount)}</strong
              ><small>{bucket.count} catatan</small>
            </article>{/each}
        </div>
      </section>{/if}
  </div>
</section>

{#if formOpen}<div class="fixed inset-0 z-20 grid place-items-center bg-slate-950/45 p-4">
    <form
      class="w-full max-w-xl rounded-3xl bg-white p-6 shadow-xl"
      onsubmit={(event) => {
        event.preventDefault();
        void saveClaim();
      }}
    >
      <h2 class="text-2xl font-black">Tambah {kind === 'RECEIVABLE' ? 'piutang' : 'utang'}</h2>
      <div class="mt-5 grid gap-4 sm:grid-cols-2">
        <label class="sm:col-span-2"
          >Nama {kind === 'RECEIVABLE' ? 'pelanggan' : 'pemasok'}<input
            class="mt-1 w-full rounded-xl border p-3"
            required
            bind:value={form.party_name}
          /></label
        ><label
          >Nilai awal<input
            class="mt-1 w-full rounded-xl border p-3"
            type="number"
            min="0.01"
            step="0.01"
            required
            bind:value={form.initial_amount}
          /></label
        ><label
          >Tanggal transaksi<input
            class="mt-1 w-full rounded-xl border p-3"
            type="date"
            required
            bind:value={form.transaction_date}
          /></label
        ><label
          >Tanggal jatuh tempo<input
            class="mt-1 w-full rounded-xl border p-3"
            type="date"
            required
            bind:value={form.due_date}
          /></label
        ><label
          >Ingatkan sebelum<input
            class="mt-1 w-full rounded-xl border p-3"
            type="number"
            min="0"
            max="90"
            bind:value={form.reminder_days_before}
          /> hari</label
        ><label class="sm:col-span-2"
          >Catatan<input class="mt-1 w-full rounded-xl border p-3" bind:value={form.note} /></label
        >
      </div>
      <div class="mt-6 flex justify-end gap-2">
        <button
          type="button"
          class="rounded-xl border px-5 py-3 font-bold"
          onclick={() => (formOpen = false)}>Kembali</button
        ><button class="rounded-xl bg-emerald-700 px-5 py-3 font-bold text-white" disabled={busy}
          >Simpan</button
        >
      </div>
    </form>
  </div>{/if}

{#if paymentTarget}<div class="fixed inset-0 z-20 grid place-items-center bg-slate-950/45 p-4">
    <form
      class="w-full max-w-md rounded-3xl bg-white p-6"
      onsubmit={(event) => {
        event.preventDefault();
        void savePayment();
      }}
    >
      <h2 class="text-2xl font-black">Catat pembayaran</h2>
      <p class="mt-1 text-slate-500">
        {paymentTarget.party.name} · sisa {formatRupiah(paymentTarget.remaining_amount)}
      </p>
      <label class="mt-5 block"
        >Jumlah dibayar<input
          class="mt-1 w-full rounded-xl border p-3"
          type="number"
          min="0.01"
          max={paymentTarget.remaining_amount}
          step="0.01"
          required
          bind:value={paymentAmount}
        /></label
      ><label class="mt-4 block"
        >Dibayar melalui<select
          class="mt-1 w-full rounded-xl border p-3"
          bind:value={paymentAccount}
          ><option value="CASH">Kas</option><option value="BANK">Bank</option></select
        ></label
      ><label class="mt-4 block"
        >Catatan<input class="mt-1 w-full rounded-xl border p-3" bind:value={paymentNote} /></label
      >
      <div class="mt-6 flex justify-end gap-2">
        <button
          type="button"
          class="rounded-xl border px-5 py-3 font-bold"
          onclick={() => (paymentTarget = null)}>Kembali</button
        ><button class="rounded-xl bg-emerald-700 px-5 py-3 font-bold text-white" disabled={busy}
          >Simpan pembayaran</button
        >
      </div>
    </form>
  </div>{/if}

{#if detail}<div class="fixed inset-0 z-20 grid place-items-center bg-slate-950/45 p-4">
    <section class="w-full max-w-xl rounded-3xl bg-white p-6">
      <div class="flex justify-between">
        <div>
          <h2 class="text-2xl font-black">Riwayat pembayaran</h2>
          <p class="text-slate-500">{detail.party.name}</p>
        </div>
        <button aria-label="Tutup riwayat" onclick={() => (detail = null)}>✕</button>
      </div>
      <div class="mt-5 space-y-3">
        {#if detail.payments.length === 0}<p class="rounded-xl bg-slate-50 p-4">
            Belum ada pembayaran.
          </p>{:else}{#each detail.payments as payment (payment.id)}<article
              class="flex justify-between rounded-xl bg-slate-50 p-4"
            >
              <div>
                <strong>{payment.payment_date}</strong><small class="block text-slate-500"
                  >{payment.payment_account_key === 'CASH' ? 'Kas' : 'Bank'} · {payment.note ||
                    'Tanpa catatan'}</small
                >
              </div>
              <strong>{formatRupiah(payment.amount)}</strong>
            </article>{/each}{/if}
      </div>
    </section>
  </div>{/if}

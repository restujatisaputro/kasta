<script lang="ts">
  import type { CurrentPeriod, PeriodClosing } from '@kasta/contracts';
  import { onMount } from 'svelte';

  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import FormField from '$lib/components/FormField.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import Toast from '$lib/components/Toast.svelte';
  import { closePeriod, getClosingHistory, getCurrentPeriod } from '$lib/api/closing';
  import { formatRupiah } from '$lib/money/rupiah';
  import { authSession } from '$lib/stores/auth-session';

  let { data }: { data: { businessId: string } } = $props();

  const FREQUENCY_LABEL: Record<string, string> = {
    MONTHLY: 'Bulanan',
    SEMIANNUAL: '2 kali setahun',
    TRIANNUAL: '3 kali setahun',
  };

  let loading = $state(true);
  let current = $state<CurrentPeriod | null>(null);
  let history = $state<PeriodClosing[]>([]);
  let periodEnd = $state(new Intl.DateTimeFormat('sv-SE').format(new Date()));
  let note = $state('');
  let acknowledged = $state(false);
  let showConfirm = $state(false);
  let busy = $state(false);
  let errorMessage = $state('');
  let notice = $state('');

  onMount(() => void load());

  async function load(): Promise<void> {
    if (!$authSession || $authSession.businessId !== data.businessId) {
      loading = false;
      return;
    }
    loading = true;
    errorMessage = '';
    try {
      const [period, historyList] = await Promise.all([
        getCurrentPeriod(data.businessId, $authSession.accessToken),
        getClosingHistory(data.businessId, $authSession.accessToken, { limit: 12 }),
      ]);
      current = period;
      history = historyList.items;
      periodEnd = period.as_of;
    } catch (error) {
      errorMessage = messageOf(error, 'Ringkasan periode belum dapat dimuat.');
    } finally {
      loading = false;
    }
  }

  function requestClose(): void {
    if (!current) return;
    if (!acknowledged) {
      errorMessage = 'Centang bahwa Anda sudah memeriksa dan menyesuaikan transaksi periode ini.';
      return;
    }
    if (!periodEnd || periodEnd < current.period_start) {
      errorMessage = `Tanggal tutup tidak boleh sebelum ${current.period_start}.`;
      return;
    }
    errorMessage = '';
    showConfirm = true;
  }

  async function confirmClose(): Promise<void> {
    if (!$authSession) return;
    showConfirm = false;
    busy = true;
    try {
      await closePeriod(data.businessId, $authSession.accessToken, {
        period_end: periodEnd,
        note: note.trim(),
        acknowledge_adjustments: acknowledged,
      });
      notice = 'Periode berhasil ditutup. Laba/rugi periode ini sudah masuk ke Modal Pemilik.';
      note = '';
      acknowledged = false;
      await load();
    } catch (error) {
      errorMessage = messageOf(error, 'Periode belum dapat ditutup.');
    } finally {
      busy = false;
    }
  }

  function messageOf(error: unknown, fallback: string): string {
    return error instanceof Error ? error.message : fallback;
  }
</script>

<svelte:head><title>Tutup Buku | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Akhir periode"
  title="Tutup Buku"
  description="Periksa laba/rugi berjalan, sesuaikan bila perlu, lalu tutup periode agar hasilnya masuk ke Modal Pemilik."
/>

{#if notice}<p class="mt-4 rounded-xl bg-emerald-50 p-3 text-sm font-bold text-emerald-800">
    {notice}
  </p>{/if}
{#if errorMessage}<p class="mt-4 rounded-xl bg-red-50 p-3 text-sm font-bold text-red-700" role="alert">
    {errorMessage}
  </p>{/if}

{#if loading}
  <p class="mt-8 text-center text-[var(--text-muted)]">Memuat ringkasan periode…</p>
{:else if !current}
  <p class="mt-8 text-center text-[var(--text-muted)]">Masuk kembali untuk melihat ringkasan periode.</p>
{:else}
  <div class="mt-6 grid gap-4 lg:grid-cols-[1.2fr_1fr]">
    <Card>
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="text-lg font-black">Periode berjalan</h2>
        {#if current.is_overdue}
          <span class="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800"
            >Sudah lewat jadwal {FREQUENCY_LABEL[current.frequency]}</span
          >
        {/if}
      </div>
      <p class="mt-1 text-sm text-[var(--text-muted)]">
        {current.period_start} sampai {current.as_of} · jadwal tutup buku: {FREQUENCY_LABEL[
          current.frequency
        ]} (atur di Pengaturan)
      </p>

      <div class="mt-5 grid gap-3 sm:grid-cols-3">
        <div class="rounded-2xl bg-[var(--surface-muted)] p-4">
          <span class="text-xs font-bold text-[var(--text-muted)]">Pemasukan</span>
          <strong class="mt-1 block text-xl">{formatRupiah(current.total_revenue)}</strong>
        </div>
        <div class="rounded-2xl bg-[var(--surface-muted)] p-4">
          <span class="text-xs font-bold text-[var(--text-muted)]">Pengeluaran</span>
          <strong class="mt-1 block text-xl">{formatRupiah(current.total_expense)}</strong>
        </div>
        <div
          class="rounded-2xl p-4 {current.is_loss
            ? 'bg-red-50 dark:bg-red-950'
            : 'bg-emerald-50 dark:bg-emerald-950'}"
        >
          <span class="text-xs font-bold text-[var(--text-muted)]"
            >{current.is_loss ? 'Rugi berjalan' : 'Laba berjalan'}</span
          >
          <strong class="mt-1 block text-xl">{formatRupiah(current.net_profit)}</strong>
        </div>
      </div>

      {#if current.revenues.length > 0 || current.expenses.length > 0}
        <div class="mt-5 grid gap-4 sm:grid-cols-2">
          <div>
            <p class="text-xs font-bold text-[var(--text-muted)]">Rincian pemasukan</p>
            <ul class="mt-2 space-y-1 text-sm">
              {#each current.revenues as line (line.account_key)}
                <li class="flex justify-between">
                  <span>{line.account_name}</span><span class="font-bold"
                    >{formatRupiah(line.amount)}</span
                  >
                </li>
              {/each}
            </ul>
          </div>
          <div>
            <p class="text-xs font-bold text-[var(--text-muted)]">Rincian pengeluaran</p>
            <ul class="mt-2 space-y-1 text-sm">
              {#each current.expenses as line (line.account_key)}
                <li class="flex justify-between">
                  <span>{line.account_name}</span><span class="font-bold"
                    >{formatRupiah(line.amount)}</span
                  >
                </li>
              {/each}
            </ul>
          </div>
        </div>
      {/if}
      <p class="mt-5 text-sm leading-6 text-[var(--text-muted)]">{current.explanation}</p>
    </Card>

    <Card>
      <h2 class="text-lg font-black">Tutup periode ini</h2>
      <div class="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
        <strong>Langkah penyesuaian.</strong> Sebelum menutup, periksa ringkasan di samping. Kalau
        ada transaksi yang belum tercatat atau perlu dikoreksi, catat dulu lewat
        <a class="underline" href={`/usaha/${data.businessId}/uang-masuk`}>Uang Masuk</a>
        atau
        <a class="underline" href={`/usaha/${data.businessId}/uang-keluar`}>Uang Keluar</a>
        seperti biasa, lalu kembali ke sini.
      </div>
      <FormField
        id="closing-period-end"
        label="Tutup sampai tanggal"
        type="date"
        bind:value={periodEnd}
        help={`Minimal ${current.period_start}, maksimal hari ini.`}
      />
      <div class="mt-4">
        <label class="kasta-label" for="closing-note">Catatan (opsional)</label><textarea
          id="closing-note"
          class="kasta-field min-h-20"
          bind:value={note}
        ></textarea>
      </div>
      <label class="mt-4 flex items-start gap-3 rounded-xl border border-[var(--border)] p-3 text-sm font-semibold"
        ><input type="checkbox" class="mt-0.5 h-5 w-5 accent-kasta-700" bind:checked={acknowledged} />
        Saya sudah memeriksa dan menyesuaikan seluruh transaksi periode ini.</label
      >
      <div class="mt-5">
        <Button full onclick={requestClose} disabled={busy}
          >{busy ? 'Menutup…' : 'Tutup periode'}</Button
        >
      </div>
    </Card>
  </div>

  <Card class="mt-4">
    <h2 class="text-lg font-black">Riwayat tutup buku</h2>
    {#if history.length === 0}
      <p class="mt-3 text-sm text-[var(--text-muted)]">Belum ada periode yang ditutup.</p>
    {:else}
      <div class="mt-3 overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead
            ><tr class="border-b text-[var(--text-muted)]"
              ><th class="p-2">Periode</th><th class="p-2">Pemasukan</th><th class="p-2"
                >Pengeluaran</th
              ><th class="p-2">Laba/Rugi</th><th class="p-2">Ditutup pada</th></tr
            ></thead
          ><tbody>
            {#each history as row (row.id)}<tr class="border-b border-[var(--border)]"
                ><td class="p-2 font-bold">{row.period_start} – {row.period_end}</td><td class="p-2"
                  >{formatRupiah(row.total_revenue)}</td
                ><td class="p-2">{formatRupiah(row.total_expense)}</td><td
                  class="p-2 font-bold {Number(row.net_profit) < 0 ? 'text-red-600' : ''}"
                  >{formatRupiah(row.net_profit)}</td
                ><td class="p-2 text-[var(--text-muted)]">{row.created_at.slice(0, 10)}</td></tr
              >{/each}
          </tbody>
        </table>
      </div>
    {/if}
  </Card>
{/if}

<ConfirmDialog
  open={showConfirm}
  title="Tutup periode ini?"
  message={current
    ? `Periode ${current.period_start} sampai ${periodEnd} akan ditutup. ${current.is_loss ? 'Rugi' : 'Laba'} sebesar ${formatRupiah(current.net_profit)} akan menambah/mengurangi Modal Pemilik. Transaksi lama tetap bisa diubah kapan saja setelah ini.`
    : ''}
  confirmLabel="Ya, tutup periode"
  onConfirm={confirmClose}
  onCancel={() => (showConfirm = false)}
/>
<Toast open={Boolean(notice)} message={notice} tone="success" onClose={() => (notice = '')} />

<script lang="ts">
  import { onMount } from 'svelte';
  import type { FinancialReport, TransactionListItem } from '@kasta/contracts';
  import { getFinancialReport } from '$lib/api/reports';
  import { getTransactions } from '$lib/api/transactions';
  import { authSession } from '$lib/stores/auth-session';
  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import Chart from '$lib/components/Chart.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import ErrorState from '$lib/components/ErrorState.svelte';
  import Icon, { type IconName } from '$lib/components/Icon.svelte';
  import LoadingState from '$lib/components/LoadingState.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';

  let { data }: { data: { businessId: string } } = $props();
  let report = $state<FinancialReport | null>(null);
  let transactions = $state<TransactionListItem[]>([]);
  let loading = $state(true);
  let error = $state('');

  function rupiah(value: string | number): string {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      maximumFractionDigits: 0,
    }).format(Number(value) || 0);
  }
  async function loadDashboard() {
    if (!$authSession || $authSession.businessId !== data.businessId) {
      loading = false;
      return;
    }
    loading = true;
    error = '';
    try {
      const [nextReport, list] = await Promise.all([
        getFinancialReport(data.businessId, $authSession.accessToken, { period: 'MONTH' }),
        getTransactions(data.businessId, $authSession.accessToken, { limit: '5' }),
      ]);
      report = nextReport;
      transactions = list.items;
    } catch (cause) {
      error = cause instanceof Error ? cause.message : 'Ringkasan belum dapat dimuat.';
    } finally {
      loading = false;
    }
  }
  onMount(loadDashboard);

  const stats = $derived([
    {
      label: 'Uang masuk bulan ini',
      value: rupiah(report?.summary.income ?? 0),
      icon: 'income' as IconName,
      tone: 'bg-kasta-100 text-kasta-800 dark:bg-kasta-950 dark:text-kasta-200',
    },
    {
      label: 'Uang keluar bulan ini',
      value: rupiah(report?.summary.expense ?? 0),
      icon: 'expense' as IconName,
      tone: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200',
    },
    {
      label: 'Perkiraan laba',
      value: rupiah(report?.summary.estimated_profit ?? 0),
      icon: 'chart' as IconName,
      tone: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200',
    },
    {
      label: 'Saldo kas',
      value: rupiah(report?.cash_flow.ending_cash_balance ?? 0),
      icon: 'transaction' as IconName,
      tone: 'bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-200',
    },
  ]);
  const chartOption = $derived({
    tooltip: { trigger: 'axis' },
    legend: { data: ['Uang masuk', 'Uang keluar'], bottom: 0, textStyle: { color: '#64748b' } },
    grid: { left: 8, right: 8, top: 20, bottom: 45, containLabel: true },
    xAxis: {
      type: 'category',
      data: (report?.charts.income_vs_expense ?? []).map((item) => item.period),
      axisLabel: { color: '#64748b' },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748b', formatter: (value: number) => `${value / 1_000_000} jt` },
    },
    series: [
      {
        name: 'Uang masuk',
        type: 'line',
        smooth: true,
        data: (report?.charts.income_vs_expense ?? []).map((item) => Number(item.income)),
        color: '#15803d',
      },
      {
        name: 'Uang keluar',
        type: 'line',
        smooth: true,
        data: (report?.charts.income_vs_expense ?? []).map((item) => Number(item.expense)),
        color: '#d97706',
      },
    ],
  });
</script>

<svelte:head><title>Beranda usaha | KASTA</title></svelte:head>

<PageHeader
  eyebrow="Beranda usaha"
  title="Apa kabar hari ini?"
  description="Ringkasan dibuat dari catatan keuangan usaha Anda."
>
  {#snippet actions()}<Button href={`/usaha/${data.businessId}/uang-masuk`}
      ><Icon name="income" />Catat uang masuk</Button
    >{/snippet}
</PageHeader>

{#if loading}
  <div class="mt-6"><LoadingState label="Menyiapkan ringkasan usaha…" /></div>
{:else if error}
  <div class="mt-6">
    <ErrorState title="Ringkasan belum tersedia" message={error}
      >{#snippet action()}<Button variant="secondary" onclick={loadDashboard}>Coba lagi</Button
        >{/snippet}</ErrorState
    >
  </div>
{:else if !$authSession}
  <div class="mt-6">
    <EmptyState
      title="Masuk untuk melihat data usaha"
      description="Setelah masuk, saldo, transaksi terbaru, dan perkembangan usaha tampil di sini."
      icon="profile"
      >{#snippet action()}<Button href="/login">Masuk ke KASTA</Button>{/snippet}</EmptyState
    >
  </div>
{:else}
  <section class="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Ringkasan keuangan">
    {#each stats as stat (stat.label)}
      <Card padding="small"
        ><div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-xs font-bold text-[var(--text-muted)]">{stat.label}</p>
            <p class="mt-2 text-xl font-black tracking-tight">{stat.value}</p>
          </div>
          <span class={`grid h-10 w-10 place-items-center rounded-xl ${stat.tone}`}
            ><Icon name={stat.icon} /></span
          >
        </div></Card
      >
    {/each}
  </section>

  <section class="mt-6 grid gap-4 lg:grid-cols-[1.6fr_1fr]">
    <Card
      ><div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-black">Perkembangan usaha</h2>
          <p class="text-sm text-[var(--text-muted)]">Uang masuk dibanding uang keluar.</p>
        </div>
        <a class="text-sm font-extrabold text-kasta-700" href={`/usaha/${data.businessId}/laporan`}
          >Lihat laporan</a
        >
      </div>
      {#if report?.charts.income_vs_expense.length}<Chart
          option={chartOption}
          label="Grafik uang masuk dan keluar"
          description="Perbandingan uang masuk dan uang keluar per periode."
        />{:else}<div class="mt-5">
          <EmptyState
            title="Belum ada grafik"
            description="Catat transaksi untuk melihat perkembangan usaha."
            icon="chart"
          />
        </div>{/if}</Card
    >
    <Card
      ><h2 class="text-lg font-black">Tindakan cepat</h2>
      <div class="mt-4 grid gap-2">
        <Button href={`/usaha/${data.businessId}/uang-masuk`} full
          ><Icon name="income" />Uang Masuk</Button
        ><Button href={`/usaha/${data.businessId}/uang-keluar`} variant="secondary" full
          ><Icon name="expense" />Uang Keluar</Button
        ><Button href={`/usaha/${data.businessId}/foto-nota`} variant="secondary" full
          ><Icon name="camera" />Foto Nota</Button
        >
      </div>
      <div class="mt-5 grid grid-cols-2 gap-2 rounded-xl bg-[var(--surface-muted)] p-3 text-sm">
        <div>
          <span class="block text-xs text-[var(--text-muted)]">Utang tersisa</span><strong
            >{rupiah(report?.summary.payables ?? 0)}</strong
          >
        </div>
        <div>
          <span class="block text-xs text-[var(--text-muted)]">Piutang tersisa</span><strong
            >{rupiah(report?.summary.receivables ?? 0)}</strong
          >
        </div>
      </div></Card
    >
  </section>

  <section class="mt-6">
    <Card
      ><div class="flex items-center justify-between">
        <h2 class="text-lg font-black">Transaksi terbaru</h2>
        <a
          class="text-sm font-extrabold text-kasta-700"
          href={`/usaha/${data.businessId}/transaksi`}>Lihat semua</a
        >
      </div>
      {#if transactions.length}<ul class="mt-4 divide-y divide-[var(--border)]">
          {#each transactions as item (item.id)}<li class="flex min-h-16 items-center gap-3 py-3">
              <span
                class="grid h-10 w-10 place-items-center rounded-xl {item.entry_kind === 'INCOME'
                  ? 'bg-kasta-100 text-kasta-800'
                  : 'bg-amber-100 text-amber-800'}"
                ><Icon name={item.entry_kind === 'INCOME' ? 'income' : 'expense'} /></span
              >
              <div class="min-w-0 flex-1">
                <p class="truncate font-bold">{item.description}</p>
                <p class="text-xs text-[var(--text-muted)]">{item.transaction_date}</p>
              </div>
              <strong class={item.entry_kind === 'INCOME' ? 'text-kasta-700' : ''}
                >{item.entry_kind === 'INCOME' ? '+' : '-'}{rupiah(item.amount)}</strong
              >
            </li>{/each}
        </ul>{:else}<div class="mt-4">
          <EmptyState
            title="Belum ada transaksi"
            description="Catatan terbaru akan tampil di bagian ini."
            icon="transaction"
          />
        </div>{/if}</Card
    >
  </section>
{/if}

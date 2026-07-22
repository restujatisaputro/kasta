<script lang="ts">
  import { onMount } from 'svelte';
  import type { MentorBusinessDetail } from '@kasta/contracts';
  import { getMentorBusiness } from '$lib/api/mentors';
  import { authSession } from '$lib/stores/auth-session';
  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import Chart from '$lib/components/Chart.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import LoadingState from '$lib/components/LoadingState.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  let { data }: { data: { businessId: string } } = $props();
  let detail = $state<MentorBusinessDetail | null>(null);
  let loading = $state(true);
  const rupiah = (value: string) =>
    new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      maximumFractionDigits: 0,
    }).format(Number(value) || 0);
  onMount(async () => {
    if (!$authSession) {
      loading = false;
      return;
    }
    try {
      detail = await getMentorBusiness($authSession.accessToken, data.businessId);
    } finally {
      loading = false;
    }
  });
  const chartOption = $derived({
    tooltip: { trigger: 'axis' },
    legend: { data: ['Omzet', 'Laba'], bottom: 0 },
    grid: { left: 8, right: 8, bottom: 45, containLabel: true },
    xAxis: { type: 'category', data: detail?.revenue_trend.map((item) => item.month) ?? [] },
    yAxis: { type: 'value' },
    series: [
      {
        name: 'Omzet',
        type: 'line',
        smooth: true,
        color: '#15803d',
        data: detail?.revenue_trend.map((item) => Number(item.revenue)) ?? [],
      },
      {
        name: 'Laba',
        type: 'line',
        smooth: true,
        color: '#2563eb',
        data: detail?.revenue_trend.map((item) => Number(item.profit)) ?? [],
      },
    ],
  });
</script>

<svelte:head><title>Detail UMKM | KASTA</title></svelte:head>
{#if loading}<LoadingState label="Memuat kondisi UMKM…" />{:else if detail}
  <PageHeader
    eyebrow="Detail UMKM"
    title={detail.summary.business_name}
    description={detail.explanation}
    >{#snippet actions()}<Button href="/pembina">Buat catatan</Button>{/snippet}</PageHeader
  >
  <section class="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    <Card padding="small"
      ><p class="text-xs font-bold text-[var(--text-muted)]">Omzet bulan ini</p>
      <p class="mt-2 text-xl font-black">{rupiah(detail.summary.month_revenue)}</p></Card
    ><Card padding="small"
      ><p class="text-xs font-bold text-[var(--text-muted)]">Perkiraan laba</p>
      <p class="mt-2 text-xl font-black">{rupiah(detail.summary.month_profit)}</p></Card
    ><Card padding="small"
      ><p class="text-xs font-bold text-[var(--text-muted)]">Utang</p>
      <p class="mt-2 text-xl font-black">{rupiah(detail.summary.payable_balance)}</p></Card
    ><Card padding="small"
      ><p class="text-xs font-bold text-[var(--text-muted)]">Piutang terlambat</p>
      <p class="mt-2 text-xl font-black">{rupiah(detail.summary.overdue_receivable)}</p></Card
    >
  </section>
  <div class="mt-4 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
    <Card
      ><h2 class="font-black">Tren omzet dan laba</h2>
      <Chart
        option={chartOption}
        label="Tren omzet dan laba"
        description="Perubahan omzet dan laba UMKM dari bulan ke bulan."
      /></Card
    ><Card
      ><h2 class="font-black">Indikator kondisi</h2>
      {#if detail.summary.risk_indicators.length}<ul class="mt-4 space-y-3">
          {#each detail.summary.risk_indicators as risk (risk.code)}<li
              class="rounded-xl bg-[var(--surface-muted)] p-3 text-sm"
            >
              <strong>{risk.icon} {risk.label}</strong>
              <p class="mt-1 text-[var(--text-muted)]">{risk.message}</p>
            </li>{/each}
        </ul>{:else}<p class="mt-4 text-sm text-[var(--text-muted)]">
          Tidak ada indikator risiko baru.
        </p>{/if}</Card
    >
  </div>
{:else}<EmptyState
    title="Data tidak dapat dilihat"
    description="Pastikan pemilik UMKM masih memberikan izin ringkasan."
    icon="alert"
    >{#snippet action()}<Button href="/pembina/akses">Periksa izin</Button>{/snippet}</EmptyState
  >{/if}

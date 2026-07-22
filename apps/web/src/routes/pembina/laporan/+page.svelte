<script lang="ts">
  import { onMount } from 'svelte';
  import type { MentorAggregateReport } from '@kasta/contracts';
  import { getMentorReport } from '$lib/api/mentors';
  import { authSession } from '$lib/stores/auth-session';
  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import Chart from '$lib/components/Chart.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  let report = $state<MentorAggregateReport | null>(null);
  onMount(async () => {
    if ($authSession) report = await getMentorReport($authSession.accessToken);
  });
  const rupiah = (value: string) =>
    new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      maximumFractionDigits: 0,
    }).format(Number(value) || 0);
  const chartOption = $derived({
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['48%', '72%'],
        data: [
          {
            name: 'Relatif sehat',
            value: report?.dashboard.health_green ?? 0,
            itemStyle: { color: '#15803d' },
          },
          {
            name: 'Perlu perhatian',
            value: report?.dashboard.health_yellow ?? 0,
            itemStyle: { color: '#d97706' },
          },
          {
            name: 'Perlu pendampingan',
            value: report?.dashboard.health_red ?? 0,
            itemStyle: { color: '#dc2626' },
          },
        ],
      },
    ],
  });
</script>

<svelte:head><title>Laporan agregat pembina | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Portofolio binaan"
  title="Laporan agregat"
  description="Ringkasan gabungan tanpa mengubah transaksi UMKM."
  >{#snippet actions()}<Button href="/pembina" variant="secondary">Ekspor laporan</Button
    >{/snippet}</PageHeader
>
{#if report}<section class="mt-6 grid gap-3 sm:grid-cols-3">
    <Card padding="small"
      ><p class="text-xs font-bold text-[var(--text-muted)]">Total omzet</p>
      <p class="mt-2 text-xl font-black">{rupiah(report.total_revenue)}</p></Card
    ><Card padding="small"
      ><p class="text-xs font-bold text-[var(--text-muted)]">Total pengeluaran</p>
      <p class="mt-2 text-xl font-black">{rupiah(report.total_expense)}</p></Card
    ><Card padding="small"
      ><p class="text-xs font-bold text-[var(--text-muted)]">Perkiraan laba</p>
      <p class="mt-2 text-xl font-black">{rupiah(report.total_profit)}</p></Card
    >
  </section>
  <div class="mt-4 grid gap-4 lg:grid-cols-2">
    <Card
      ><h2 class="font-black">Kondisi UMKM</h2>
      <Chart
        option={chartOption}
        label="Komposisi kondisi UMKM"
        description="Jumlah UMKM relatif sehat, perlu perhatian, dan perlu pendampingan."
      /></Card
    ><Card
      ><h2 class="font-black">Penjelasan sederhana</h2>
      <p class="mt-3 leading-7 text-[var(--text-muted)]">{report.explanation}</p></Card
    >
  </div>{:else}<div class="mt-6">
    <EmptyState
      title="Laporan belum tersedia"
      description="Laporan muncul setelah ada UMKM yang memberi izin ringkasan dan laporan."
      icon="chart"
    />
  </div>{/if}

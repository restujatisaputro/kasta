<script lang="ts">
  import { onMount } from 'svelte';
  import type { Obligation, ObligationKind } from '@kasta/contracts';
  import { getObligations } from '$lib/api/obligations';
  import { authSession } from '$lib/stores/auth-session';
  import Button from './Button.svelte';
  import Card from './Card.svelte';
  import DataTable from './DataTable.svelte';
  import EmptyState from './EmptyState.svelte';
  import LoadingState from './LoadingState.svelte';

  interface Props {
    businessId: string;
    kind: ObligationKind;
  }
  let { businessId, kind }: Props = $props();
  let items = $state<Obligation[]>([]);
  let loading = $state(true);
  const noun = $derived(kind === 'PAYABLE' ? 'utang' : 'piutang');
  const party = $derived(kind === 'PAYABLE' ? 'Pemasok' : 'Pelanggan');
  function rupiah(value: string): string {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      maximumFractionDigits: 0,
    }).format(Number(value) || 0);
  }
  onMount(async () => {
    if (!$authSession || $authSession.businessId !== businessId) {
      loading = false;
      return;
    }
    try {
      items = (await getObligations(businessId, $authSession.accessToken, kind)).items;
    } finally {
      loading = false;
    }
  });
  const rows = $derived(
    items.slice(0, 8).map((item) => ({
      party: item.party.name,
      due: item.due_date,
      remaining: rupiah(item.remaining_amount),
      status: item.status_label,
    })),
  );
</script>

<div class="mt-6 grid gap-4 sm:grid-cols-3">
  <Card padding="small"
    ><p class="text-xs font-bold text-[var(--text-muted)]">Total {noun} tersisa</p>
    <p class="mt-2 text-xl font-black">
      {rupiah(String(items.reduce((sum, item) => sum + Number(item.remaining_amount), 0)))}
    </p></Card
  >
  <Card padding="small"
    ><p class="text-xs font-bold text-[var(--text-muted)]">Belum lunas</p>
    <p class="mt-2 text-xl font-black">
      {items.filter((item) => !['PAID', 'CANCELLED'].includes(item.status)).length} tagihan
    </p></Card
  >
  <Card padding="small"
    ><p class="text-xs font-bold text-[var(--text-muted)]">Terlambat</p>
    <p class="mt-2 text-xl font-black text-red-700">
      {items.filter((item) => item.status === 'OVERDUE').length} tagihan
    </p></Card
  >
</div>
<div class="mt-4">
  {#if loading}<LoadingState label={`Memuat ${noun}…`} />
  {:else if rows.length}<DataTable
      columns={[
        { key: 'party', label: party },
        { key: 'due', label: 'Jatuh tempo' },
        { key: 'remaining', label: 'Sisa', align: 'right' },
        { key: 'status', label: 'Status' },
      ]}
      {rows}
      caption={`Daftar ${noun}`}
    />
  {:else}<EmptyState
      title={`Belum ada ${noun}`}
      description={`Catat ${noun} agar jatuh tempo dan pembayaran mudah dipantau.`}
      icon={kind === 'PAYABLE' ? 'payable' : 'receivable'}
      >{#snippet action()}<Button href={`/usaha/${businessId}/tagihan`}
          >Tambah {kind === 'PAYABLE' ? 'utang' : 'piutang'}</Button
        >{/snippet}</EmptyState
    >{/if}
</div>

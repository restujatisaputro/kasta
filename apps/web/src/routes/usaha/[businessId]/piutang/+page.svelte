<script lang="ts">
  import Button from '$lib/components/Button.svelte';
  import ObligationOverview from '$lib/components/ObligationOverview.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  let { data }: { data: { businessId: string } } = $props();
</script>

<svelte:head><title>Piutang | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Tagihan pelanggan"
  title="Piutang"
  description="Pantau pembayaran dari pelanggan dan tagihan yang sudah terlambat."
  >{#snippet actions()}<Button href={`/usaha/${data.businessId}/tagihan`}>Kelola pembayaran</Button
    >{/snippet}</PageHeader
>
<ObligationOverview businessId={data.businessId} kind="RECEIVABLE" />

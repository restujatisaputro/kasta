<script lang="ts">
  import Button from '$lib/components/Button.svelte';
  import ObligationOverview from '$lib/components/ObligationOverview.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  let { data }: { data: { businessId: string } } = $props();
</script>

<svelte:head><title>Utang | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Tagihan usaha"
  title="Utang"
  description="Pantau yang perlu dibayar kepada pemasok dan lihat pengingat jatuh tempo."
  >{#snippet actions()}<Button href={`/usaha/${data.businessId}/tagihan`}>Kelola pembayaran</Button
    >{/snippet}</PageHeader
>
<ObligationOverview businessId={data.businessId} kind="PAYABLE" />

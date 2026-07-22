<script lang="ts">
  import PageHeader from '$lib/components/PageHeader.svelte';
  import QuickTransactionForm from '$lib/components/QuickTransactionForm.svelte';
  let { data }: { data: { businessId: string } } = $props();
</script>

<svelte:head><title>Uang Keluar | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Transaksi sederhana"
  title="Uang Keluar"
  description="Catat belanja dan biaya usaha dalam tiga langkah."
/>
<div class="mt-6 max-w-2xl">
  <QuickTransactionForm businessId={data.businessId} kind="EXPENSE" />
</div>

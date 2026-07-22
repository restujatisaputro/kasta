<script lang="ts">
  import PageHeader from '$lib/components/PageHeader.svelte';
  import QuickTransactionForm from '$lib/components/QuickTransactionForm.svelte';
  let { data }: { data: { businessId: string } } = $props();
</script>

<svelte:head><title>Uang Masuk | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Transaksi sederhana"
  title="Uang Masuk"
  description="Catat penjualan atau pemasukan lain dalam tiga langkah."
/>
<div class="mt-6 max-w-2xl">
  <QuickTransactionForm businessId={data.businessId} kind="INCOME" />
</div>

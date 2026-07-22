<script lang="ts">
  import { onMount } from 'svelte';
  import type { InventorySummary, Product } from '@kasta/contracts';
  import { getInventorySummary, getProducts } from '$lib/api/inventory';
  import { authSession } from '$lib/stores/auth-session';
  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import DataTable from '$lib/components/DataTable.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import LoadingState from '$lib/components/LoadingState.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  let { data }: { data: { businessId: string } } = $props();
  let summary = $state<InventorySummary | null>(null);
  let products = $state<Product[]>([]);
  let loading = $state(true);
  function rupiah(value: string): string {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      maximumFractionDigits: 0,
    }).format(Number(value) || 0);
  }
  onMount(async () => {
    if (!$authSession || $authSession.businessId !== data.businessId) {
      loading = false;
      return;
    }
    try {
      const [info, list] = await Promise.all([
        getInventorySummary(data.businessId, $authSession.accessToken),
        getProducts(data.businessId, $authSession.accessToken, { low_stock: true }),
      ]);
      summary = info;
      products = list.items;
    } finally {
      loading = false;
    }
  });
  const rows = $derived(
    products.map((item) => ({
      sku: item.sku,
      name: item.name,
      stock: `${item.current_stock} ${item.unit}`,
      minimum: item.minimum_stock,
      status: Number(item.current_stock) <= Number(item.minimum_stock) ? 'Perlu ditambah' : 'Aman',
    })),
  );
</script>

<svelte:head><title>Stok | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Persediaan"
  title="Stok"
  description="Lihat barang yang menipis dan nilai barang yang tersedia."
  >{#snippet actions()}<Button href={`/usaha/${data.businessId}/produk`}>Kelola produk</Button
    >{/snippet}</PageHeader
>
<section class="mt-6 grid gap-3 sm:grid-cols-3">
  <Card padding="small"
    ><p class="text-xs font-bold text-[var(--text-muted)]">Produk aktif</p>
    <p class="mt-2 text-xl font-black">{summary?.active_product_count ?? 0}</p></Card
  ><Card padding="small"
    ><p class="text-xs font-bold text-[var(--text-muted)]">Stok minimum</p>
    <p class="mt-2 text-xl font-black text-amber-700">
      {summary?.low_stock_count ?? 0} produk
    </p></Card
  ><Card padding="small"
    ><p class="text-xs font-bold text-[var(--text-muted)]">Nilai persediaan</p>
    <p class="mt-2 text-xl font-black">{rupiah(summary?.inventory_value ?? '0')}</p></Card
  >
</section>
<div class="mt-4">
  {#if loading}<LoadingState label="Memeriksa stok…" />{:else if rows.length}<DataTable
      columns={[
        { key: 'sku', label: 'SKU' },
        { key: 'name', label: 'Produk' },
        { key: 'stock', label: 'Stok', align: 'right' },
        { key: 'minimum', label: 'Minimum', align: 'right' },
        { key: 'status', label: 'Kondisi' },
      ]}
      {rows}
      caption="Produk dengan stok minimum"
    />{:else}<EmptyState
      title="Tidak ada stok yang perlu diperhatikan"
      description="Produk yang mencapai batas minimum akan muncul di sini."
      icon="stock"
    />{/if}
</div>

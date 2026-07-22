<script lang="ts">
  import Button from '$lib/components/Button.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
</script>

<svelte:head><title>Catatan pembina | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Dokumentasi pendampingan"
  title="Catatan"
  description="Catatan dapat dibagikan kepada UMKM atau disimpan khusus untuk pembina."
  >{#snippet actions()}<Button href="/pembina/umkm">Pilih UMKM</Button>{/snippet}</PageHeader
>
<div class="mt-6">
  <EmptyState
    title="Pilih UMKM untuk membuat catatan"
    description="Catatan tersimpan bersama waktu dan pembina yang membuatnya."
    icon="note"
  />
</div>

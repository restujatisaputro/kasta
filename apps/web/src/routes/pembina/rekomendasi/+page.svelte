<script lang="ts">
  import Button from '$lib/components/Button.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
</script>

<svelte:head><title>Rekomendasi | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Tindak lanjut"
  title="Rekomendasi"
  description="Pantau saran yang baru, sedang dikerjakan, dan sudah selesai."
  >{#snippet actions()}<Button href="/pembina/umkm">Buat rekomendasi</Button>{/snippet}</PageHeader
>
<div class="mt-6">
  <EmptyState
    title="Belum ada rekomendasi pada filter ini"
    description="Pilih UMKM binaan untuk memberi saran yang dapat ditindaklanjuti."
    icon="recommendation"
  />
</div>

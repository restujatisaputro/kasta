<script lang="ts">
  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  let { data }: { data: { businessId: string } } = $props();
</script>

<svelte:head><title>Pembina | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Pendampingan"
  title="Pembina usaha"
  description="Anda tetap memegang kendali atas data apa saja yang dapat dilihat pembina."
  >{#snippet actions()}<Button href={`/usaha/${data.businessId}/akses-pembina`}
      >Atur izin akses</Button
    >{/snippet}</PageHeader
>
<section class="mt-6 grid gap-4 md:grid-cols-3">
  <Card
    ><span class="grid h-11 w-11 place-items-center rounded-xl bg-kasta-100 text-kasta-800"
      ><Icon name="mentor" /></span
    >
    <h2 class="mt-4 font-black">Izin terperinci</h2>
    <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">
      Pilih izin ringkasan, laporan, transaksi, nota, stok, atau tagihan.
    </p></Card
  ><Card
    ><span class="grid h-11 w-11 place-items-center rounded-xl bg-blue-100 text-blue-800"
      ><Icon name="calendar" /></span
    >
    <h2 class="mt-4 font-black">Batas waktu</h2>
    <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">
      Tentukan masa berlaku dan cabut izin kapan saja.
    </p></Card
  ><Card
    ><span class="grid h-11 w-11 place-items-center rounded-xl bg-violet-100 text-violet-800"
      ><Icon name="note" /></span
    >
    <h2 class="mt-4 font-black">Riwayat tercatat</h2>
    <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">
      Aktivitas pembina tercatat agar akses tetap transparan.
    </p></Card
  >
</section>
<div class="mt-4">
  <EmptyState
    title="Belum ada rekomendasi baru"
    description="Catatan dan rekomendasi dari pembina akan muncul di sini."
    icon="recommendation"
  />
</div>

<script lang="ts">
  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import FormField from '$lib/components/FormField.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import Toast from '$lib/components/Toast.svelte';
  let { data }: { data: { businessId: string } } = $props();
  let file = $state<File | null>(null);
  let stage = $state<'empty' | 'processing' | 'review' | 'confirmed'>('empty');
  let merchant = $state('');
  let date = $state(new Intl.DateTimeFormat('sv-SE').format(new Date()));
  let total = $state('');
  let showConfirm = $state(false);
  let message = $state('');

  function selectFile(event: Event) {
    const selected = (event.currentTarget as HTMLInputElement).files?.[0] ?? null;
    if (!selected) return;
    if (
      !['image/jpeg', 'image/png', 'image/webp'].includes(selected.type) ||
      selected.size > 10 * 1024 * 1024
    ) {
      message = 'Gunakan foto JPG, PNG, atau WebP dengan ukuran maksimal 10 MB.';
      return;
    }
    file = selected;
    stage = 'processing';
    window.setTimeout(() => {
      merchant = '';
      total = '';
      stage = 'review';
    }, 650);
  }
  function confirmReceipt() {
    showConfirm = false;
    stage = 'confirmed';
    message = 'Hasil nota dikonfirmasi. Lanjutkan untuk membuat transaksi.';
  }
</script>

<svelte:head><title>Foto Nota | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Pencatatan lebih cepat"
  title="Foto Nota"
  description="Unggah foto nota, periksa hasil bacaan, lalu konfirmasi sebelum transaksi dibuat."
/>
<div class="mt-6 grid gap-4 lg:grid-cols-[1fr_1.2fr]">
  <Card>
    <h2 class="text-lg font-black">1. Pilih foto nota</h2>
    <label
      for="receipt-file"
      class="mt-4 flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-kasta-300 bg-kasta-50 p-6 text-center transition hover:bg-kasta-100 dark:bg-kasta-950"
    >
      <span class="grid h-14 w-14 place-items-center rounded-2xl bg-kasta-700 text-white"
        ><Icon name="camera" size={28} /></span
      >
      <strong class="mt-4">{file?.name ?? 'Ambil foto atau pilih dari perangkat'}</strong>
      <span class="mt-2 text-sm text-[var(--text-muted)]"
        >Pastikan seluruh nota terlihat dan tidak buram.</span
      >
    </label>
    <input
      id="receipt-file"
      class="sr-only"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      onchange={selectFile}
    />
    <p class="mt-3 text-xs text-[var(--text-muted)]">Format JPG, PNG, WebP. Maksimal 10 MB.</p>
  </Card>
  <Card>
    <h2 class="text-lg font-black">2. Periksa hasil bacaan</h2>
    {#if stage === 'empty'}<div class="mt-8 text-center text-[var(--text-muted)]">
        <Icon name="note" size={36} />
        <p class="mt-3 text-sm">Hasil foto akan tampil di sini.</p>
      </div>
    {:else if stage === 'processing'}<div class="mt-8" role="status" aria-live="polite">
        <div class="h-2 overflow-hidden rounded-full bg-[var(--surface-muted)]">
          <span class="block h-full w-2/3 animate-pulse rounded-full bg-kasta-600"></span>
        </div>
        <p class="mt-3 text-center text-sm font-bold">Sedang membaca nota…</p>
      </div>
    {:else if stage === 'confirmed'}<div
        class="mt-6 rounded-2xl bg-kasta-50 p-5 text-center dark:bg-kasta-950"
      >
        <Icon name="check" size={32} />
        <h3 class="mt-2 font-black">Nota sudah diperiksa</h3>
        <p class="mt-2 text-sm text-[var(--text-muted)]">
          Transaksi belum dibuat otomatis. Pilih jenis transaksi untuk melanjutkan.
        </p>
        <div class="mt-5 grid gap-2 sm:grid-cols-2">
          <Button href={`/usaha/${data.businessId}/uang-keluar`}>Uang Keluar</Button><Button
            href={`/usaha/${data.businessId}/uang-masuk`}
            variant="secondary">Uang Masuk</Button
          >
        </div>
      </div>
    {:else}<div class="mt-5 space-y-5">
        <div class="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <strong>Perlu diperiksa.</strong> Isi atau perbaiki hasil yang belum tepat.
        </div>
        <FormField
          id="merchant"
          label="Nama toko"
          bind:value={merchant}
          placeholder="Contoh: Toko Maju"
        /><FormField id="receipt-date" label="Tanggal" type="date" bind:value={date} /><FormField
          id="receipt-total"
          label="Total belanja"
          bind:value={total}
          placeholder="Contoh: 25000"
        />
        <div>
          <label class="kasta-label" for="receipt-kind">Jenis transaksi</label><select
            id="receipt-kind"
            class="kasta-field"
            ><option>Pembelian / Uang Keluar</option><option>Penjualan / Uang Masuk</option></select
          >
        </div>
        <Button full onclick={() => (showConfirm = true)}>Konfirmasi hasil nota</Button>
      </div>{/if}
  </Card>
</div>
<ConfirmDialog
  open={showConfirm}
  title="Konfirmasi hasil nota?"
  message="Pastikan nama toko, tanggal, dan total sudah sesuai dengan foto. Transaksi tetap dibuat pada langkah berikutnya."
  confirmLabel="Ya, sudah benar"
  onConfirm={confirmReceipt}
  onCancel={() => (showConfirm = false)}
/>
<Toast open={Boolean(message)} {message} tone="success" onClose={() => (message = '')} />

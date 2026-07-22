<script lang="ts">
  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import Icon, { type IconName } from '$lib/components/Icon.svelte';
  import MarketingShell from '$lib/components/MarketingShell.svelte';
  const groups: Array<{ icon: IconName; title: string; text: string; items: string[] }> = [
    {
      icon: 'transaction',
      title: 'Pencatatan harian',
      text: 'Selesaikan pencatatan utama dalam maksimal tiga langkah.',
      items: [
        'Uang Masuk dan Uang Keluar',
        'Tambah Modal dan Ambil Uang Pribadi',
        'Draft, transaksi berulang, pencarian, dan filter',
      ],
    },
    {
      icon: 'camera',
      title: 'Foto Nota',
      text: 'Baca nota Indonesia dan tetap minta konfirmasi sebelum menjadi transaksi.',
      items: [
        'Crop dan peningkatan gambar',
        'Nama toko, tanggal, barang, dan total',
        'Pemeriksaan duplikat dan confidence',
      ],
    },
    {
      icon: 'chart',
      title: 'Laporan yang menjelaskan',
      text: 'Laporan bersumber dari jurnal, bukan sekadar daftar transaksi.',
      items: [
        'Ringkasan, laba rugi, posisi keuangan',
        'Arus kas, penjualan, pengeluaran',
        'Grafik serta ekspor PDF, XLSX, CSV',
      ],
    },
    {
      icon: 'box',
      title: 'Produk dan kewajiban',
      text: 'Pantau operasional usaha dalam satu tempat.',
      items: [
        'Produk, stok, dan stok minimum',
        'Utang serta pembayaran',
        'Piutang serta pengingat jatuh tempo',
      ],
    },
    {
      icon: 'mentor',
      title: 'Pembina UMKM',
      text: 'Pendampingan yang menghormati persetujuan pemilik.',
      items: [
        'Dashboard kondisi UMKM',
        'Catatan dan rekomendasi',
        'Scope akses serta masa berlaku',
      ],
    },
    {
      icon: 'settings',
      title: 'Aman dan tetap bekerja',
      text: 'Dirancang untuk kondisi lapangan dan banyak perangkat.',
      items: [
        'Offline-first di Android',
        'Riwayat perubahan dan audit log',
        'Isolasi data setiap UMKM',
      ],
    },
  ];
</script>

<svelte:head
  ><title>Fitur KASTA</title><meta
    name="description"
    content="Fitur pencatatan, laporan, Foto Nota, dan pendampingan KASTA."
  /></svelte:head
>
<MarketingShell
  ><section class="px-5 py-14 sm:px-6 sm:py-20">
    <div class="mx-auto max-w-7xl">
      <div class="max-w-3xl">
        <p class="font-extrabold text-kasta-700 dark:text-kasta-300">Fitur KASTA</p>
        <h1 class="mt-2 text-4xl font-black tracking-tight sm:text-5xl">
          Dari transaksi harian hingga pendampingan.
        </h1>
        <p class="mt-5 text-lg leading-8 text-[var(--text-muted)]">
          Setiap fitur dirancang agar mudah digunakan tanpa mengorbankan kerapian data keuangan.
        </p>
      </div>
      <div class="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        {#each groups as group (group.title)}<Card padding="large"
            ><div
              class="grid h-12 w-12 place-items-center rounded-2xl bg-kasta-100 text-kasta-800 dark:bg-kasta-950 dark:text-kasta-200"
            >
              <Icon name={group.icon} />
            </div>
            <h2 class="mt-5 text-xl font-black">{group.title}</h2>
            <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">{group.text}</p>
            <ul class="mt-4 grid gap-2 text-sm">
              {#each group.items as item (item)}<li class="flex gap-2">
                  <span class="text-kasta-600">✓</span>{item}
                </li>{/each}
            </ul></Card
          >{/each}
      </div>
      <div class="mt-10 flex justify-center">
        <Button href="/registrasi">Mulai menggunakan KASTA</Button>
      </div>
    </div>
  </section></MarketingShell
>

<script lang="ts">
  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import BrandLogo from '$lib/components/BrandLogo.svelte';
  import Icon, { type IconName } from '$lib/components/Icon.svelte';
  import MarketingShell from '$lib/components/MarketingShell.svelte';

  const features: Array<{ icon: IconName; title: string; text: string }> = [
    {
      icon: 'income',
      title: 'Uang Masuk',
      text: 'Catat penjualan atau pemasukan tanpa memilih debit dan kredit.',
    },
    {
      icon: 'expense',
      title: 'Uang Keluar',
      text: 'Kelompokkan belanja usaha dengan bahasa yang mudah dipahami.',
    },
    {
      icon: 'camera',
      title: 'Foto Nota',
      text: 'Foto nota, periksa hasil bacaan, lalu simpan sebagai transaksi.',
    },
    {
      icon: 'chart',
      title: 'Laporan sederhana',
      text: 'Pahami kondisi usaha lewat angka, grafik, dan penjelasan singkat.',
    },
    {
      icon: 'mentor',
      title: 'Pendampingan aman',
      text: 'Bagikan data tertentu kepada pembina hanya dengan persetujuan Anda.',
    },
    {
      icon: 'transaction',
      title: 'Tetap bisa offline',
      text: 'Catat dari Android saat tidak ada internet dan sinkronkan kemudian.',
    },
  ];
</script>

<svelte:head>
  <title>KASTA — Keuangan UMKM Lebih Mudah</title>
  <meta
    name="description"
    content="Catat uang masuk, uang keluar, nota, dan perkembangan usaha dengan bahasa Indonesia yang mudah dipahami."
  />
</svelte:head>

<MarketingShell>
  <section class="kasta-brand-hero relative overflow-hidden px-5 py-16 sm:px-6 sm:py-24">
    <div class="mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-[1.08fr_.92fr]">
      <div>
        <div class="mb-8 lg:hidden"><BrandLogo context="Keuangan dan Asistensi UMKM" /></div>
        <div
          class="inline-flex items-center gap-2 rounded-full border border-kasta-200 bg-[color:var(--surface)]/80 px-3 py-1.5 text-xs font-extrabold text-kasta-800 shadow-sm backdrop-blur"
        >
          <span class="h-2 w-2 rounded-full bg-kasta-500"></span>Dibuat untuk UMKM Indonesia
        </div>
        <h1 class="mt-6 max-w-3xl text-4xl leading-[1.08] font-black tracking-tight sm:text-6xl">
          Urus keuangan usaha tanpa harus menjadi ahli.
        </h1>
        <p class="mt-6 max-w-2xl text-lg leading-8 text-[var(--text-muted)]">
          Catat Uang Masuk, Uang Keluar, Utang, Piutang, dan Foto Nota. KASTA merapikan pencatatan
          di belakang layar agar Anda dapat fokus menjalankan usaha.
        </p>
        <div class="mt-8 flex flex-col gap-3 sm:flex-row">
          <Button href="/registrasi">Buat akun gratis <Icon name="arrow-right" /></Button><Button
            href="/fitur"
            variant="secondary">Lihat semua fitur</Button
          >
        </div>
        <div
          class="mt-7 flex flex-wrap gap-x-6 gap-y-2 text-sm font-semibold text-[var(--text-muted)]"
        >
          <span>✓ Bahasa sederhana</span><span>✓ Bisa dari ponsel</span><span
            >✓ Data terpisah per usaha</span
          >
        </div>
      </div>

      <div class="relative mx-auto w-full max-w-xl">
        <div class="kasta-card kasta-hero-card overflow-hidden p-4 sm:p-6">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-bold text-[var(--text-muted)]">Ringkasan bulan ini</p>
              <p class="text-lg font-black">Warung Bahagia</p>
            </div>
            <span
              class="rounded-full bg-kasta-100 px-3 py-1.5 text-xs font-extrabold text-kasta-800"
              >Relatif sehat</span
            >
          </div>
          <div class="mt-5 grid grid-cols-2 gap-3">
            <div class="rounded-2xl bg-kasta-50 p-4">
              <p class="text-xs font-bold text-kasta-700">Uang Masuk</p>
              <p class="mt-1 text-xl font-black text-kasta-950">Rp15,2 jt</p>
              <small class="text-kasta-700">↑ 12% dari lalu</small>
            </div>
            <div class="rounded-2xl bg-amber-50 p-4">
              <p class="text-xs font-bold text-amber-700">Uang Keluar</p>
              <p class="mt-1 text-xl font-black text-amber-950">Rp9,8 jt</p>
              <small class="text-amber-700">64% pemasukan</small>
            </div>
          </div>
          <div class="mt-3 rounded-2xl bg-slate-950 p-5 text-white">
            <p class="text-xs font-bold text-slate-300">Perkiraan laba</p>
            <p class="mt-1 text-3xl font-black">Rp5.400.000</p>
            <p class="mt-2 text-xs leading-5 text-slate-300">
              Usaha memperoleh lebih banyak pemasukan dibanding pengeluaran bulan ini.
            </p>
          </div>
          <div class="mt-4 grid grid-cols-3 gap-2 text-center">
            <div class="rounded-xl border border-[var(--border)] p-3">
              <Icon name="income" /><span class="mt-1 block text-[11px] font-bold">Uang Masuk</span>
            </div>
            <div class="rounded-xl border border-[var(--border)] p-3">
              <Icon name="expense" /><span class="mt-1 block text-[11px] font-bold"
                >Uang Keluar</span
              >
            </div>
            <div class="rounded-xl border border-[var(--border)] p-3">
              <Icon name="camera" /><span class="mt-1 block text-[11px] font-bold">Foto Nota</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="border-y border-[var(--border)] bg-[var(--surface)] px-5 py-12 sm:px-6">
    <div class="mx-auto max-w-7xl text-center">
      <p class="text-sm font-extrabold text-kasta-700 dark:text-kasta-300">
        Satu tempat untuk kegiatan keuangan harian
      </p>
      <h2 class="mt-2 text-3xl font-black tracking-tight sm:text-4xl">
        Mudah di depan, tetap rapi di belakang.
      </h2>
      <p class="mx-auto mt-3 max-w-2xl leading-7 text-[var(--text-muted)]">
        Anda memakai istilah sehari-hari. KASTA membentuk pencatatan berpasangan dan laporan dari
        jurnal secara otomatis.
      </p>
    </div>
    <div class="motion-stagger mx-auto mt-9 grid max-w-7xl gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {#each features as feature (feature.title)}
        <Card
          ><div
            class="kasta-icon-wrap grid h-11 w-11 place-items-center rounded-xl bg-kasta-100 text-kasta-800 dark:bg-kasta-950 dark:text-kasta-200"
          >
            <Icon name={feature.icon} />
          </div>
          <h3 class="mt-4 text-lg font-black">{feature.title}</h3>
          <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">{feature.text}</p></Card
        >
      {/each}
    </div>
  </section>

  <section class="px-5 py-16 sm:px-6 sm:py-22">
    <div class="mx-auto grid max-w-7xl gap-10 lg:grid-cols-2 lg:items-center">
      <div>
        <p class="font-extrabold text-kasta-700 dark:text-kasta-300">Mulai dalam tiga langkah</p>
        <h2 class="mt-2 text-3xl font-black tracking-tight sm:text-4xl">
          Tidak perlu menunggu pembukuan sempurna.
        </h2>
        <p class="mt-4 leading-7 text-[var(--text-muted)]">
          Mulai dari kegiatan hari ini. Anda dapat memperbaiki data dengan riwayat perubahan yang
          jelas.
        </p>
      </div>
      <ol class="motion-stagger grid gap-3">
        {#each [['1', 'Buat profil usaha', 'Isi informasi dasar dan saldo awal usaha.'], ['2', 'Catat kegiatan harian', 'Gunakan Uang Masuk, Uang Keluar, atau Foto Nota.'], ['3', 'Lihat perkembangan', 'Baca laporan sederhana atau bahas bersama pembina.']] as step (step[0])}
          <li class="kasta-card flex gap-4 p-4">
            <span
              class="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-kasta-700 font-black text-white"
              >{step[0]}</span
            >
            <div>
              <h3 class="font-black">{step[1]}</h3>
              <p class="mt-1 text-sm leading-6 text-[var(--text-muted)]">{step[2]}</p>
            </div>
          </li>
        {/each}
      </ol>
    </div>
  </section>

  <section class="px-5 pb-16 sm:px-6 sm:pb-24">
    <div
      class="mx-auto max-w-7xl overflow-hidden rounded-[2rem] bg-kasta-950 px-6 py-10 text-white sm:px-10 sm:py-12"
    >
      <div class="flex flex-col gap-7 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p class="font-extrabold text-kasta-300">Siap mulai?</p>
          <h2 class="mt-2 max-w-2xl text-3xl font-black">Catat transaksi pertama Anda hari ini.</h2>
          <p class="mt-3 text-kasta-100">
            Gratis untuk mencoba. Tidak perlu memahami istilah akuntansi.
          </p>
        </div>
        <Button href="/registrasi" variant="secondary">Buat akun KASTA</Button>
      </div>
    </div>
  </section>
</MarketingShell>

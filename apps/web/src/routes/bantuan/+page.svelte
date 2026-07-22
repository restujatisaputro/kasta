<script lang="ts">
  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import FormField from '$lib/components/FormField.svelte';
  import Icon, { type IconName } from '$lib/components/Icon.svelte';
  import MarketingShell from '$lib/components/MarketingShell.svelte';
  let query = $state('');
  const topics: Array<{ icon: IconName; title: string; text: string }> = [
    {
      icon: 'profile',
      title: 'Akun dan profil usaha',
      text: 'Registrasi, verifikasi, onboarding, dan anggota usaha.',
    },
    {
      icon: 'transaction',
      title: 'Mencatat transaksi',
      text: 'Uang Masuk, Uang Keluar, draft, koreksi, dan pembatalan.',
    },
    {
      icon: 'camera',
      title: 'Foto Nota',
      text: 'Kamera, hasil OCR, koreksi, dan nota gagal diproses.',
    },
    {
      icon: 'chart',
      title: 'Laporan',
      text: 'Membaca grafik, penjelasan, serta mengunduh laporan.',
    },
    {
      icon: 'mentor',
      title: 'Akses pembina',
      text: 'Permintaan, ruang lingkup, masa berlaku, dan pencabutan.',
    },
    {
      icon: 'settings',
      title: 'Sinkronisasi',
      text: 'Status offline, percobaan ulang, dan penyelesaian konflik.',
    },
  ];
</script>

<svelte:head
  ><title>Bantuan KASTA</title><meta
    name="description"
    content="Pusat bantuan penggunaan KASTA."
  /></svelte:head
>
<MarketingShell
  ><section class="bg-kasta-950 px-5 py-14 text-white sm:px-6 sm:py-18">
    <div class="mx-auto max-w-3xl text-center">
      <p class="font-extrabold text-kasta-300">Pusat Bantuan</p>
      <h1 class="mt-2 text-4xl font-black">Apa yang ingin Anda pelajari?</h1>
      <div class="mx-auto mt-7 max-w-xl text-left [&_label]:text-white">
        <FormField
          id="help-search"
          label="Cari panduan"
          placeholder="Contoh: cara mencatat uang masuk"
          type="search"
          bind:value={query}
        />
      </div>
    </div>
  </section>
  <section class="px-5 py-12 sm:px-6">
    <div class="mx-auto max-w-6xl">
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {#each topics.filter((topic) => !query || `${topic.title} ${topic.text}`
              .toLowerCase()
              .includes(query.toLowerCase())) as topic (topic.title)}<Card
            ><Icon name={topic.icon} />
            <h2 class="mt-4 font-black">{topic.title}</h2>
            <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">{topic.text}</p>
            <a
              class="mt-4 inline-block text-sm font-extrabold text-kasta-700 dark:text-kasta-300"
              href={`mailto:dukungan@kasta.id?subject=${encodeURIComponent(topic.title)}`}
              >Minta bantuan →</a
            ></Card
          >{/each}
      </div>
      <div class="mt-10 rounded-3xl bg-kasta-100 p-6 text-center dark:bg-kasta-950">
        <h2 class="text-xl font-black">Masih memerlukan bantuan?</h2>
        <p class="mt-2 text-kasta-900 dark:text-kasta-100">
          Tim dukungan akan membantu tanpa meminta password atau kode verifikasi Anda.
        </p>
        <div class="mt-5"><Button href="mailto:dukungan@kasta.id">Hubungi dukungan</Button></div>
      </div>
    </div>
  </section></MarketingShell
>

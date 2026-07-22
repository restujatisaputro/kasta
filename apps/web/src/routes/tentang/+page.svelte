<script lang="ts">
  import InfoPage from '$lib/components/InfoPage.svelte';
  const sections = [
    {
      title: 'Mengapa KASTA dibuat',
      paragraphs: [
        'Banyak pelaku UMKM menjalankan usaha dengan baik, tetapi pencatatan keuangan masih tersebar di buku, chat, atau ingatan. Istilah akuntansi yang rumit sering membuat pencatatan terasa jauh dari kegiatan sehari-hari.',
      ],
      items: [
        'Menggunakan bahasa Uang Masuk dan Uang Keluar.',
        'Menyusun jurnal berpasangan secara otomatis.',
        'Memberi pemilik kendali atas akses pembina.',
      ],
    },
    {
      title: 'Prinsip produk',
      paragraphs: [
        'KASTA mengutamakan kejelasan, keamanan, dan tindakan yang mudah dilakukan. Informasi penting selalu disertai teks dan tidak hanya mengandalkan warna.',
      ],
      items: [
        'Mobile-first untuk penggunaan di tempat usaha.',
        'Laporan disertai penjelasan sederhana.',
        'Transaksi keuangan tidak dihapus tanpa jejak.',
      ],
    },
    {
      title: 'Untuk ekosistem UMKM',
      paragraphs: [
        'Pemilik dan pegawai dapat mencatat kegiatan harian. Pembina dapat memberikan pendampingan berbasis data setelah pemilik memberi izin yang jelas dan terbatas.',
      ],
    },
  ];
</script>

<svelte:head
  ><title>Tentang KASTA</title><meta
    name="description"
    content="Alasan KASTA dibangun untuk pelaku UMKM Indonesia."
  /></svelte:head
>
<InfoPage
  eyebrow="Tentang KASTA"
  title="Keuangan usaha yang lebih mudah dipahami."
  description="KASTA adalah Keuangan dan Asistensi UMKM—aplikasi pencatatan dan pendampingan yang memakai bahasa sehari-hari."
  {sections}
/>

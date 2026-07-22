<script lang="ts">
  import InfoPage from '$lib/components/InfoPage.svelte';
  const sections = [
    {
      title: 'Data yang diproses',
      paragraphs: [
        'KASTA memproses informasi akun, profil usaha, transaksi, nota, produk, utang-piutang, perangkat, serta aktivitas keamanan yang diperlukan untuk menyediakan layanan.',
      ],
      items: [
        'Password disimpan dalam bentuk hash, bukan teks asli.',
        'Foto nota disimpan pada penyimpanan objek privat.',
        'Audit keamanan mencatat siapa melakukan tindakan dan kapan.',
      ],
    },
    {
      title: 'Penggunaan data',
      paragraphs: [
        'Data digunakan untuk menjalankan fungsi pencatatan, membuat laporan, menyinkronkan perangkat, mencegah penyalahgunaan, dan memberi dukungan yang diminta pengguna.',
      ],
    },
    {
      title: 'Akses pembina dan administrator',
      paragraphs: [
        'Pembina hanya dapat mengakses UMKM setelah pemilik memberikan scope dan masa berlaku. Administrator tidak dapat melewati izin kecuali terdapat grant dukungan yang sah, terbatas, dan tercatat.',
      ],
    },
    {
      title: 'Hak pengguna',
      paragraphs: [
        'Pemilik dapat meninjau akses, mencabut izin pembina, meminta salinan data, memperbarui data, serta mengajukan penghapusan akun sesuai kewajiban retensi hukum dan akuntansi.',
      ],
    },
    {
      title: 'Kontak privasi',
      paragraphs: [
        'Pertanyaan atau permintaan terkait privasi dapat dikirim ke privasi@kasta.id. Jangan mengirim password, token, atau kode verifikasi melalui email.',
      ],
    },
  ];
</script>

<svelte:head><title>Kebijakan Privasi KASTA</title></svelte:head>
<InfoPage
  eyebrow="Kepercayaan"
  title="Kebijakan Privasi"
  description="Ringkasan cara KASTA memproses dan melindungi data pengguna serta data usaha."
  {sections}
  updated="22 Juli 2026"
/>

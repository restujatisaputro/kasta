<script lang="ts">
  import InfoPage from '$lib/components/InfoPage.svelte';
  const sections = [
    {
      title: 'Penggunaan layanan',
      paragraphs: [
        'Pengguna wajib memberikan informasi yang benar, menjaga keamanan akun, dan menggunakan KASTA untuk kegiatan usaha yang sah. Pemilik bertanggung jawab mengatur anggota dan akses pembina pada usahanya.',
      ],
    },
    {
      title: 'Pencatatan keuangan',
      paragraphs: [
        'KASTA membantu pencatatan dan penyajian informasi. Pengguna tetap bertanggung jawab memeriksa data, menyimpan bukti, serta memenuhi kewajiban hukum dan perpajakan yang berlaku.',
      ],
    },
    {
      title: 'Keamanan akun',
      paragraphs: [
        'Jangan membagikan password, token, atau kode verifikasi. Segera cabut sesi perangkat yang tidak dikenal dan hubungi dukungan bila menduga penyalahgunaan.',
      ],
    },
    {
      title: 'Ketersediaan dan perubahan',
      paragraphs: [
        'Kami berupaya menjaga layanan tetap tersedia. Pemeliharaan, gangguan jaringan, atau perubahan fitur dapat terjadi dan akan dikomunikasikan secara wajar.',
      ],
    },
    {
      title: 'Penghentian akun',
      paragraphs: [
        'Akun dapat dibatasi bila digunakan untuk penyalahgunaan. Pengguna dapat mengajukan penutupan akun, dengan tetap memperhatikan retensi catatan keuangan dan audit yang diwajibkan.',
      ],
    },
  ];
</script>

<svelte:head><title>Syarat Penggunaan KASTA</title></svelte:head>
<InfoPage
  eyebrow="Ketentuan layanan"
  title="Syarat Penggunaan"
  description="Ketentuan dasar penggunaan website dan aplikasi KASTA."
  {sections}
  updated="22 Juli 2026"
/>

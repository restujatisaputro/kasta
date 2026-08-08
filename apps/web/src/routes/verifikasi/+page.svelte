<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import AuthShell from '$lib/components/AuthShell.svelte';
  import Button from '$lib/components/Button.svelte';
  import { confirmVerification } from '$lib/api/auth';

  type Status = 'memproses' | 'berhasil' | 'gagal';

  let status = $state<Status>('memproses');
  let message = $state('');

  /* Verifikasi sengaja dijalankan di peramban, bukan saat render server, agar
     pemindai tautan pada layanan email tidak ikut memakai token sekali pakai. */
  onMount(async () => {
    const token = page.url.searchParams.get('token')?.trim() ?? '';
    if (!token) {
      status = 'gagal';
      message = 'Tautan verifikasi tidak lengkap. Buka kembali tautan dari email Anda.';
      return;
    }
    try {
      await confirmVerification(token);
      status = 'berhasil';
    } catch (error) {
      status = 'gagal';
      message =
        error instanceof Error && error.message
          ? error.message
          : 'Tautan sudah kedaluwarsa atau pernah dipakai.';
    }
  });
</script>

<svelte:head><title>Verifikasi akun | KASTA</title></svelte:head>
<AuthShell
  title="Verifikasi akun"
  description="Kami sedang memastikan tautan dari email Anda masih berlaku."
>
  {#if status === 'memproses'}
    <div class="rounded-2xl bg-kasta-50 p-5 text-center dark:bg-kasta-950" role="status">
      <h2 class="text-lg font-black">Memverifikasi…</h2>
      <p class="mt-2 text-sm text-[var(--text-muted)]">Mohon tunggu sebentar.</p>
    </div>
  {:else if status === 'berhasil'}
    <div class="rounded-2xl bg-kasta-50 p-5 text-center dark:bg-kasta-950" role="status">
      <h2 class="text-lg font-black">Akun terverifikasi</h2>
      <p class="mt-2 text-sm text-[var(--text-muted)]">
        Pendaftaran Anda selesai. Silakan masuk untuk mulai memakai KASTA.
      </p>
      <div class="mt-5"><Button href="/login" full>Masuk ke KASTA</Button></div>
    </div>
  {:else}
    <div class="rounded-2xl bg-kasta-50 p-5 text-center dark:bg-kasta-950" role="alert">
      <h2 class="text-lg font-black">Verifikasi gagal</h2>
      <p class="mt-2 text-sm text-[var(--text-muted)]">{message}</p>
      <p class="mt-2 text-sm text-[var(--text-muted)]">
        Tautan hanya berlaku sekali dan untuk waktu terbatas. Daftar ulang atau minta tautan baru
        bila perlu.
      </p>
      <div class="mt-5"><Button href="/login" full>Kembali ke halaman masuk</Button></div>
    </div>
  {/if}
</AuthShell>

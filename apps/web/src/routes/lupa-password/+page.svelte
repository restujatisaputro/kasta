<script lang="ts">
  import { z } from 'zod';
  import AuthShell from '$lib/components/AuthShell.svelte';
  import Button from '$lib/components/Button.svelte';
  import FormField from '$lib/components/FormField.svelte';
  import { forgotPassword } from '$lib/api/auth';

  let identifier = $state('');
  let error = $state('');
  let sent = $state(false);
  let busy = $state(false);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    const result = z.string().min(3, 'Masukkan email atau nomor telepon.').safeParse(identifier);
    if (!result.success) {
      error = result.error.issues[0]?.message ?? 'Data belum lengkap.';
      return;
    }
    error = '';
    busy = true;
    try {
      await forgotPassword(identifier.trim());
    } catch {
      /* Respons selalu dibuat umum untuk melindungi akun. */
    } finally {
      sent = true;
      busy = false;
    }
  }
</script>

<svelte:head><title>Lupa kata sandi | KASTA</title></svelte:head>
<AuthShell
  title="Atur ulang kata sandi"
  description="Kami akan mengirim petunjuk jika data tersebut terdaftar."
>
  {#if sent}
    <div class="rounded-2xl bg-kasta-50 p-5 text-center dark:bg-kasta-950" role="status">
      <h2 class="text-lg font-black">Periksa pesan Anda</h2>
      <p class="mt-2 text-sm text-[var(--text-muted)]">
        Ikuti tautan yang dikirim. Tautan hanya berlaku untuk waktu terbatas.
      </p>
      <div class="mt-5"><Button href="/login" full>Kembali ke halaman masuk</Button></div>
    </div>
  {:else}
    <form class="space-y-5" onsubmit={submit} novalidate>
      <FormField
        id="reset-identifier"
        label="Email atau nomor telepon"
        bind:value={identifier}
        {error}
        autocomplete="username"
        required
      />
      <Button type="submit" full disabled={busy}>{busy ? 'Mengirim…' : 'Kirim petunjuk'}</Button>
    </form>
    <a class="mt-5 block text-center text-sm font-bold text-kasta-700 hover:underline" href="/login"
      >Kembali ke halaman masuk</a
    >
  {/if}
</AuthShell>

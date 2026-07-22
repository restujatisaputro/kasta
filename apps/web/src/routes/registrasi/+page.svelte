<script lang="ts">
  import { z } from 'zod';
  import AuthShell from '$lib/components/AuthShell.svelte';
  import Button from '$lib/components/Button.svelte';
  import FormField from '$lib/components/FormField.svelte';
  import SelectField from '$lib/components/SelectField.svelte';
  import Toast from '$lib/components/Toast.svelte';
  import { register } from '$lib/api/auth';

  const schema = z
    .object({
      fullName: z.string().min(3, 'Nama minimal 3 karakter.'),
      channel: z.enum(['email', 'phone']),
      identifier: z.string().min(6, 'Masukkan email atau nomor telepon yang valid.'),
      password: z.string().min(12, 'Gunakan minimal 12 karakter.'),
      confirmation: z.string(),
    })
    .refine((value) => value.password === value.confirmation, {
      path: ['confirmation'],
      message: 'Kata sandi belum sama.',
    });

  let fullName = $state('');
  let channel = $state<'email' | 'phone'>('email');
  let identifier = $state('');
  let password = $state('');
  let confirmation = $state('');
  let errors = $state<Record<string, string>>({});
  let message = $state('');
  let success = $state(false);
  let busy = $state(false);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    const result = schema.safeParse({ fullName, channel, identifier, password, confirmation });
    if (!result.success) {
      errors = Object.fromEntries(
        result.error.issues.map((issue) => [String(issue.path[0]), issue.message]),
      );
      return;
    }
    errors = {};
    busy = true;
    try {
      const response = await register({
        full_name: fullName.trim(),
        password,
        ...(channel === 'email' ? { email: identifier.trim() } : { phone: identifier.trim() }),
      });
      success = true;
      message = response.message || 'Akun berhasil dibuat. Silakan periksa pesan verifikasi.';
    } catch (error) {
      message = error instanceof Error ? error.message : 'Pendaftaran belum dapat diproses.';
    } finally {
      busy = false;
    }
  }
</script>

<svelte:head><title>Daftar | KASTA</title></svelte:head>
<AuthShell
  title="Mulai catat usaha"
  description="Buat akun, lalu siapkan profil usaha dengan panduan singkat."
>
  {#if success}
    <div class="rounded-2xl bg-kasta-50 p-5 text-center dark:bg-kasta-950" role="status">
      <h2 class="text-lg font-black">Periksa pesan verifikasi</h2>
      <p class="mt-2 text-sm text-[var(--text-muted)]">{message}</p>
      <div class="mt-5"><Button href="/onboarding" full>Lanjut siapkan usaha</Button></div>
    </div>
  {:else}
    <form class="space-y-5" onsubmit={submit} novalidate>
      <FormField
        id="full-name"
        label="Nama lengkap"
        bind:value={fullName}
        error={errors.fullName}
        autocomplete="name"
        required
      />
      <SelectField
        id="channel"
        label="Daftar menggunakan"
        bind:value={channel}
        options={[
          { value: 'email', label: 'Email' },
          { value: 'phone', label: 'Nomor telepon' },
        ]}
      />
      <FormField
        id="identifier"
        label={channel === 'email' ? 'Email' : 'Nomor telepon'}
        type={channel === 'email' ? 'email' : 'tel'}
        bind:value={identifier}
        error={errors.identifier}
        autocomplete={channel === 'email' ? 'email' : 'tel'}
        required
      />
      <FormField
        id="new-password"
        label="Kata sandi"
        type="password"
        bind:value={password}
        error={errors.password}
        help="Minimal 12 karakter agar akun lebih aman."
        autocomplete="new-password"
        required
      />
      <FormField
        id="confirmation"
        label="Ulangi kata sandi"
        type="password"
        bind:value={confirmation}
        error={errors.confirmation}
        autocomplete="new-password"
        required
      />
      <Button type="submit" full disabled={busy}>{busy ? 'Membuat akun…' : 'Buat akun'}</Button>
    </form>
    <p class="mt-6 text-center text-sm text-[var(--text-muted)]">
      Sudah punya akun? <a class="font-extrabold text-kasta-700 hover:underline" href="/login"
        >Masuk</a
      >
    </p>
  {/if}
</AuthShell>
<Toast open={Boolean(message && !success)} {message} tone="error" onClose={() => (message = '')} />

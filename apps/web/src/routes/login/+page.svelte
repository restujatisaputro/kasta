<script lang="ts">
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';
  import { z } from 'zod';
  import AuthShell from '$lib/components/AuthShell.svelte';
  import Button from '$lib/components/Button.svelte';
  import FormField from '$lib/components/FormField.svelte';
  import Toast from '$lib/components/Toast.svelte';
  import { login } from '$lib/api/auth';
  import { authSession } from '$lib/stores/auth-session';

  const schema = z.object({
    identifier: z.string().min(3, 'Masukkan email atau nomor telepon.'),
    password: z.string().min(1, 'Masukkan kata sandi.'),
  });

  let identifier = $state('');
  let password = $state('');
  let errors = $state<Record<string, string>>({});
  let message = $state('');
  let busy = $state(false);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    const result = schema.safeParse({ identifier, password });
    if (!result.success) {
      errors = Object.fromEntries(
        result.error.issues.map((issue) => [String(issue.path[0]), issue.message]),
      );
      return;
    }
    errors = {};
    busy = true;
    message = '';
    try {
      const deviceId = browser
        ? (localStorage.getItem('kasta-device-id') ?? crypto.randomUUID())
        : 'web-browser';
      if (browser) localStorage.setItem('kasta-device-id', deviceId);
      const tokens = await login({
        identifier: identifier.trim(),
        password,
        device_id: deviceId,
        platform: 'WEB',
        device_name: browser ? navigator.platform || 'Browser' : 'Browser',
        app_version: '0.1.0',
      });
      authSession.set({
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        businessId: null,
      });
      if (browser) {
        await goto('/pilih-usaha');
      }
    } catch (error) {
      message = error instanceof Error ? error.message : 'Belum dapat masuk. Coba lagi.';
    } finally {
      busy = false;
    }
  }
</script>

<svelte:head
  ><title>Masuk | KASTA</title><meta
    name="description"
    content="Masuk ke ruang usaha KASTA."
  /></svelte:head
>

<AuthShell
  title="Selamat datang kembali"
  description="Masuk untuk melanjutkan pencatatan usaha Anda."
>
  <form class="space-y-5" onsubmit={submit} novalidate>
    <FormField
      id="identifier"
      label="Email atau nomor telepon"
      bind:value={identifier}
      error={errors.identifier}
      autocomplete="username"
      required
    />
    <FormField
      id="password"
      label="Kata sandi"
      type="password"
      bind:value={password}
      error={errors.password}
      autocomplete="current-password"
      required
    />
    <div class="flex justify-end">
      <a class="text-sm font-bold text-kasta-700 hover:underline" href="/lupa-password"
        >Lupa kata sandi?</a
      >
    </div>
    <Button type="submit" full disabled={busy}>{busy ? 'Sedang masuk…' : 'Masuk'}</Button>
  </form>
  <p class="mt-6 text-center text-sm text-[var(--text-muted)]">
    Belum punya akun? <a class="font-extrabold text-kasta-700 hover:underline" href="/registrasi"
      >Daftar gratis</a
    >
  </p>
</AuthShell>

<Toast open={Boolean(message)} {message} tone="error" onClose={() => (message = '')} />

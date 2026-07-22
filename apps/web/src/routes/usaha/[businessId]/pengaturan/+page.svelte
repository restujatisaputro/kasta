<script lang="ts">
  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import NotificationPreferences from '$lib/components/NotificationPreferences.svelte';
  import { authSession } from '$lib/stores/auth-session';
  let { data }: { data: { businessId: string } } = $props();
  let logoutOpen = $state(false);
  function logout() {
    authSession.set(null);
    logoutOpen = false;
    window.location.assign('/login');
  }
</script>

<svelte:head><title>Pengaturan | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Preferensi"
  title="Pengaturan"
  description="Sesuaikan pengingat, tampilan, dan keamanan akun."
/>
<div class="mt-6 grid gap-4 lg:grid-cols-2">
  <Card><h2 class="mb-4 font-black">Notifikasi</h2><NotificationPreferences businessId={data.businessId} /></Card>
  <Card
    ><h2 class="font-black">Akun dan keamanan</h2>
    <div class="mt-4 grid gap-2">
      <Button href="/lupa-password" variant="secondary" full>Ubah kata sandi</Button><Button
        href="/bantuan"
        variant="secondary"
        full>Pusat bantuan</Button
      ><Button variant="danger" full onclick={() => (logoutOpen = true)}
        >Keluar dari perangkat ini</Button
      >
    </div></Card
  >
  <Card
    ><h2 class="font-black">Tentang data Anda</h2>
    <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">
      Unduh data usaha atau ajukan penghapusan akun melalui dukungan KASTA.
    </p>
    <div class="mt-4 flex flex-wrap gap-2">
      <Button variant="secondary">Unduh data</Button><Button
        href="/kebijakan-privasi"
        variant="ghost">Baca kebijakan privasi</Button
      >
    </div></Card
  >
</div>
<ConfirmDialog
  open={logoutOpen}
  title="Keluar dari perangkat ini?"
  message="Data yang belum tersimpan dapat hilang. Pastikan sinkronisasi sudah selesai."
  confirmLabel="Ya, keluar"
  onConfirm={logout}
  onCancel={() => (logoutOpen = false)}
/>

<script lang="ts">
  import type { BusinessProfile } from '@kasta/contracts';
  import { onMount } from 'svelte';

  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import NotificationPreferences from '$lib/components/NotificationPreferences.svelte';
  import { getBusinessProfile, updateBusinessProfile } from '$lib/api/onboarding';
  import { authSession } from '$lib/stores/auth-session';

  let { data }: { data: { businessId: string } } = $props();
  let logoutOpen = $state(false);
  let profile = $state<BusinessProfile | null>(null);
  let savingMode = $state(false);
  let modeNotice = $state('');
  let modeError = $state('');
  let savingFrequency = $state(false);
  let frequencyNotice = $state('');
  let frequencyError = $state('');

  const FREQUENCY_OPTIONS: Array<{
    value: 'MONTHLY' | 'SEMIANNUAL' | 'TRIANNUAL';
    label: string;
    help: string;
  }> = [
    { value: 'MONTHLY', label: 'Bulanan', help: 'Tutup setiap akhir bulan.' },
    { value: 'SEMIANNUAL', label: '2 kali setahun', help: 'Tutup tiap 6 bulan (Jan–Jun, Jul–Des).' },
    { value: 'TRIANNUAL', label: '3 kali setahun', help: 'Tutup tiap 4 bulan (Jan–Apr, Mei–Ags, Sep–Des).' },
  ];

  function logout() {
    authSession.set(null);
    logoutOpen = false;
    window.location.assign('/login');
  }

  onMount(async () => {
    if (!$authSession || $authSession.businessId !== data.businessId) return;
    try {
      profile = await getBusinessProfile(data.businessId, $authSession.accessToken);
    } catch {
      // The toggle card just stays hidden; the rest of the settings page still works.
    }
  });

  async function setInventoryMode(mode: 'SIMPLE' | 'PERPETUAL'): Promise<void> {
    if (!$authSession || !profile || profile.inventory_mode === mode) return;
    savingMode = true;
    modeError = '';
    try {
      profile = await updateBusinessProfile(data.businessId, $authSession.accessToken, {
        inventory_mode: mode,
      });
      modeNotice = 'Mode pencatatan diperbarui.';
    } catch (error) {
      modeError =
        error instanceof Error ? error.message : 'Mode pencatatan belum dapat disimpan.';
    } finally {
      savingMode = false;
    }
  }

  async function setClosingFrequency(
    frequency: 'MONTHLY' | 'SEMIANNUAL' | 'TRIANNUAL',
  ): Promise<void> {
    if (!$authSession || !profile || profile.closing_frequency === frequency) return;
    savingFrequency = true;
    frequencyError = '';
    try {
      profile = await updateBusinessProfile(data.businessId, $authSession.accessToken, {
        closing_frequency: frequency,
      });
      frequencyNotice = 'Jadwal tutup buku diperbarui.';
    } catch (error) {
      frequencyError =
        error instanceof Error ? error.message : 'Jadwal tutup buku belum dapat disimpan.';
    } finally {
      savingFrequency = false;
    }
  }
</script>

<svelte:head><title>Pengaturan | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Preferensi"
  title="Pengaturan"
  description="Sesuaikan pengingat, tampilan, dan keamanan akun."
/>
<div class="mt-6 grid gap-4 lg:grid-cols-2">
  <Card
    ><h2 class="mb-4 font-black">Notifikasi</h2>
    <NotificationPreferences businessId={data.businessId} /></Card
  >
  {#if profile}
    <Card>
      <h2 class="font-black">Mode pencatatan stok dan keuangan</h2>
      <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">
        Pilih apakah transaksi harus selalu memilih produk agar stok dan harga pokok penjualan
        (HPP) terhubung otomatis ke keuangan.
      </p>
      <div class="mt-4 grid gap-2 sm:grid-cols-2">
        <button
          type="button"
          class="rounded-2xl border-2 p-4 text-left transition {profile.inventory_mode === 'SIMPLE'
            ? 'border-kasta-600 bg-kasta-50 dark:bg-kasta-950'
            : 'border-[var(--border)]'}"
          disabled={savingMode}
          onclick={() => setInventoryMode('SIMPLE')}
        >
          <strong>Sederhana</strong>
          <p class="mt-1 text-xs text-[var(--text-muted)]">
            Uang Masuk/Keluar dicatat bebas, produk opsional. Cocok untuk pencatatan kas harian.
          </p>
        </button>
        <button
          type="button"
          class="rounded-2xl border-2 p-4 text-left transition {profile.inventory_mode ===
          'PERPETUAL'
            ? 'border-kasta-600 bg-kasta-50 dark:bg-kasta-950'
            : 'border-[var(--border)]'}"
          disabled={savingMode}
          onclick={() => setInventoryMode('PERPETUAL')}
        >
          <strong>Detail (Perpetual)</strong>
          <p class="mt-1 text-xs text-[var(--text-muted)]">
            Setiap transaksi wajib memilih produk. Stok dan HPP diperbarui otomatis ke jurnal saat
            terjual.
          </p>
        </button>
      </div>
      {#if modeNotice}<p class="mt-3 text-sm font-bold text-emerald-700">{modeNotice}</p>{/if}
      {#if modeError}<p class="mt-3 text-sm font-bold text-red-700" role="alert">{modeError}</p>{/if}
    </Card>
    <Card>
      <h2 class="font-black">Jadwal tutup buku</h2>
      <p class="mt-2 text-sm leading-6 text-[var(--text-muted)]">
        Seberapa sering usaha ini biasanya menutup periode di halaman Tutup Buku. Ini cuma
        pengingat jadwal &mdash; Anda tetap bisa menutup periode kapan saja.
      </p>
      <div class="mt-4 grid gap-2 sm:grid-cols-3">
        {#each FREQUENCY_OPTIONS as option (option.value)}
          <button
            type="button"
            class="rounded-2xl border-2 p-4 text-left transition {profile.closing_frequency ===
            option.value
              ? 'border-kasta-600 bg-kasta-50 dark:bg-kasta-950'
              : 'border-[var(--border)]'}"
            disabled={savingFrequency}
            onclick={() => setClosingFrequency(option.value)}
          >
            <strong>{option.label}</strong>
            <p class="mt-1 text-xs text-[var(--text-muted)]">{option.help}</p>
          </button>
        {/each}
      </div>
      {#if frequencyNotice}<p class="mt-3 text-sm font-bold text-emerald-700">{frequencyNotice}</p>{/if}
      {#if frequencyError}<p class="mt-3 text-sm font-bold text-red-700" role="alert">
          {frequencyError}
        </p>{/if}
    </Card>
  {/if}
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

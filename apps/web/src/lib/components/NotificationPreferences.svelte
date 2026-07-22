<script lang="ts">
  import { onMount } from 'svelte';

  import {
    getNotificationPreferences,
    updateNotificationPreferences,
    type NotificationPreference,
  } from '$lib/api/notifications';
  import { authSession } from '$lib/stores/auth-session';

  import Button from './Button.svelte';
  import EmptyState from './EmptyState.svelte';
  import ErrorState from './ErrorState.svelte';
  import LoadingState from './LoadingState.svelte';
  import Toast from './Toast.svelte';

  interface Props {
    businessId: string;
  }

  let { businessId }: Props = $props();
  let items = $state<NotificationPreference[]>([]);
  let loading = $state(true);
  let saving = $state(false);
  let error = $state('');
  let saved = $state(false);

  async function load() {
    if (!$authSession?.accessToken) {
      loading = false;
      error = 'Silakan masuk kembali untuk mengatur notifikasi.';
      return;
    }
    loading = true;
    error = '';
    try {
      items = await getNotificationPreferences(businessId, $authSession.accessToken);
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Pengaturan belum dapat dimuat.';
    } finally {
      loading = false;
    }
  }

  function change(index: number, values: Partial<NotificationPreference>) {
    items[index] = { ...items[index], ...values };
  }

  async function save() {
    if (!$authSession?.accessToken) return;
    saving = true;
    error = '';
    try {
      items = await updateNotificationPreferences(businessId, $authSession.accessToken, items);
      saved = true;
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Pengaturan belum dapat disimpan.';
    } finally {
      saving = false;
    }
  }

  onMount(load);
</script>

{#if loading}
  <LoadingState label="Memuat pengaturan notifikasi…" />
{:else if error && items.length === 0}
  <ErrorState title="Pengaturan belum dapat dibuka" message={error}>
    {#snippet action()}<Button variant="secondary" onclick={load}>Coba lagi</Button>{/snippet}
  </ErrorState>
{:else if items.length === 0}
  <EmptyState title="Belum ada pengaturan" description="Coba muat ulang halaman ini." />
{:else}
  <div class="grid gap-3">
    {#each items as item, index (item.category)}
      <label
        class="flex min-h-16 items-center justify-between gap-4 rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3"
      >
        <span>
          <strong class="block text-sm">{item.label}</strong>
          <small class="text-[var(--text-muted)]">Notifikasi dalam aplikasi dan perangkat</small>
        </span>
        <input
          class="h-6 w-6 accent-kasta-700"
          type="checkbox"
          checked={item.enabled}
          onchange={(event) =>
            change(index, {
              enabled: event.currentTarget.checked,
              local_enabled: event.currentTarget.checked,
            })}
        />
      </label>
    {/each}
    <div class="grid gap-3 rounded-2xl border border-[var(--border)] p-4 sm:grid-cols-3">
      <label class="grid gap-1 text-sm font-bold">
        Waktu pengingat
        <input
          class="min-h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3"
          type="time"
          value={items[0]?.reminder_time.slice(0, 5)}
          onchange={(event) => {
            const value = `${event.currentTarget.value}:00`;
            items = items.map((item) => ({ ...item, reminder_time: value }));
          }}
        />
      </label>
      <label class="grid gap-1 text-sm font-bold">
        Jam tenang mulai
        <input
          class="min-h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3"
          type="time"
          value={items[0]?.quiet_hours_start?.slice(0, 5) ?? ''}
          onchange={(event) => {
            const value = event.currentTarget.value ? `${event.currentTarget.value}:00` : null;
            items = items.map((item) => ({ ...item, quiet_hours_start: value }));
          }}
        />
      </label>
      <label class="grid gap-1 text-sm font-bold">
        Jam tenang selesai
        <input
          class="min-h-11 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3"
          type="time"
          value={items[0]?.quiet_hours_end?.slice(0, 5) ?? ''}
          onchange={(event) => {
            const value = event.currentTarget.value ? `${event.currentTarget.value}:00` : null;
            items = items.map((item) => ({ ...item, quiet_hours_end: value }));
          }}
        />
      </label>
    </div>
    {#if error}<p class="text-sm font-bold text-red-700" role="alert">{error}</p>{/if}
    <Button onclick={save} disabled={saving}>{saving ? 'Menyimpan…' : 'Simpan pengaturan'}</Button>
  </div>
{/if}

<Toast
  open={saved}
  message="Pengaturan notifikasi sudah disimpan."
  onClose={() => (saved = false)}
/>

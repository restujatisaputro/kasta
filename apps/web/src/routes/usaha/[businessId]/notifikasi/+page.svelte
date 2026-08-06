<script lang="ts">
  import { onMount } from 'svelte';

  import {
    evaluateNotifications,
    getNotifications,
    getUnreadCount,
    markAllNotificationsRead,
    markNotificationRead,
    notificationHref,
    type KastaNotification,
  } from '$lib/api/notifications';
  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import ErrorState from '$lib/components/ErrorState.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import LoadingState from '$lib/components/LoadingState.svelte';
  import NotificationPreferences from '$lib/components/NotificationPreferences.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { authSession } from '$lib/stores/auth-session';

  let { data }: { data: { businessId: string } } = $props();
  let items = $state<KastaNotification[]>([]);
  let unread = $state(0);
  let loading = $state(true);
  let error = $state('');

  async function load() {
    if (!$authSession?.accessToken) {
      loading = false;
      error = 'Silakan masuk kembali untuk melihat notifikasi.';
      return;
    }
    loading = true;
    error = '';
    try {
      const token = $authSession.accessToken;
      await evaluateNotifications(data.businessId, token);
      const [result, count] = await Promise.all([
        getNotifications(data.businessId, token),
        getUnreadCount(data.businessId, token),
      ]);
      items = result;
      unread = count.unread_count;
    } catch (reason) {
      error = reason instanceof Error ? reason.message : 'Notifikasi belum dapat dimuat.';
    } finally {
      loading = false;
    }
  }

  async function open(item: KastaNotification) {
    if (!$authSession?.accessToken) return;
    if (!item.read_at) {
      await markNotificationRead(data.businessId, item.id, $authSession.accessToken).catch(
        () => null,
      );
    }
    window.location.assign(notificationHref(data.businessId, item.action_path));
  }

  async function markAll() {
    if (!$authSession?.accessToken) return;
    await markAllNotificationsRead(data.businessId, $authSession.accessToken);
    items = items.map((item) => ({ ...item, read_at: item.read_at ?? new Date().toISOString() }));
    unread = 0;
  }

  onMount(load);
</script>

<svelte:head><title>Notifikasi | KASTA</title></svelte:head>

<PageHeader
  eyebrow="Pengingat usaha"
  title="Notifikasi"
  description="Lihat hal penting dan buka langsung halaman yang perlu ditindaklanjuti."
>
  {#snippet actions()}
    {#if unread > 0}<Button variant="secondary" onclick={markAll}>Tandai semua dibaca</Button>{/if}
  {/snippet}
</PageHeader>

<div class="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
  <section aria-labelledby="notification-inbox-title">
    <h2 id="notification-inbox-title" class="sr-only">Kotak masuk notifikasi</h2>
    {#if loading}
      <LoadingState label="Memuat notifikasi…" />
    {:else if error}
      <ErrorState title="Notifikasi belum dapat dibuka" message={error}>
        {#snippet action()}<Button variant="secondary" onclick={load}>Coba lagi</Button>{/snippet}
      </ErrorState>
    {:else if items.length === 0}
      <EmptyState
        title="Belum ada notifikasi"
        description="Pengingat transaksi, tagihan, stok, nota, dan pembina akan tampil di sini."
      />
    {:else}
      <div class="grid gap-3">
        {#each items as item (item.id)}
          <button class="w-full text-left" onclick={() => open(item)}>
            <Card padding="small">
              <div class="flex items-start gap-3">
                <span
                  class="grid h-11 w-11 shrink-0 place-items-center rounded-xl {item.read_at
                    ? 'bg-[var(--surface-muted)] text-[var(--text-muted)]'
                    : 'bg-kasta-100 text-kasta-800 dark:bg-kasta-950 dark:text-kasta-200'}"
                >
                  <Icon name="notification" />
                </span>
                <span class="min-w-0 flex-1">
                  <span class="flex items-center justify-between gap-3">
                    <strong>{item.title}</strong>
                    {#if !item.read_at}
                      <span
                        class="rounded-full bg-kasta-700 px-2 py-1 text-[10px] font-black text-white"
                        >BARU</span
                      >
                    {/if}
                  </span>
                  <span class="mt-1 block text-sm leading-6 text-[var(--text-muted)]"
                    >{item.message}</span
                  >
                  <span class="mt-2 block text-xs font-bold text-kasta-700 dark:text-kasta-300"
                    >Buka detail →</span
                  >
                </span>
              </div>
            </Card>
          </button>
        {/each}
      </div>
    {/if}
  </section>

  <aside>
    <h2 class="mb-3 text-lg font-black">Atur pengingat</h2>
    <NotificationPreferences businessId={data.businessId} />
  </aside>
</div>

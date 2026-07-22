<script lang="ts">
  import { onMount } from 'svelte';

  import { evaluateNotifications, getUnreadCount } from '$lib/api/notifications';
  import { authSession } from '$lib/stores/auth-session';

  import Icon from './Icon.svelte';

  interface Props {
    businessId: string;
  }

  let { businessId }: Props = $props();
  let unread = $state(0);

  onMount(async () => {
    if (!$authSession?.accessToken) return;
    await evaluateNotifications(businessId, $authSession.accessToken).catch(() => null);
    const result = await getUnreadCount(businessId, $authSession.accessToken).catch(() => null);
    unread = result?.unread_count ?? 0;
  });
</script>

<a
  href={`/usaha/${businessId}/notifikasi`}
  class="relative grid h-11 w-11 place-items-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] hover:text-[var(--text)]"
  aria-label={unread > 0 ? `Buka notifikasi, ${unread} belum dibaca` : 'Buka notifikasi'}
>
  <Icon name="notification" />
  {#if unread > 0}
    <span
      class="absolute -top-1 -right-1 grid min-h-5 min-w-5 place-items-center rounded-full bg-red-600 px-1 text-[10px] font-black text-white"
      aria-hidden="true">{unread > 99 ? '99+' : unread}</span
    >
  {/if}
</a>

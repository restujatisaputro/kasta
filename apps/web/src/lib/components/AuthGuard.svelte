<script lang="ts">
  import { goto } from '$app/navigation';
  import { afterNavigate } from '$app/navigation';
  import { onMount } from 'svelte';
  import type { Snippet } from 'svelte';
  import { get } from 'svelte/store';
  import { authSession } from '$lib/stores/auth-session';

  interface Props {
    children: Snippet;
    businessId?: string;
  }

  let { children, businessId }: Props = $props();
  let authorized = $state(false);

  async function enforce() {
    const session = get(authSession);
    authorized = false;
    if (!session) {
      await goto('/login');
      return;
    }
    if (!session.businessId) {
      await goto('/pilih-usaha');
      return;
    }
    if (businessId && session.businessId !== businessId) {
      await goto(`/usaha/${session.businessId}`);
      return;
    }
    authorized = true;
  }

  onMount(() => {
    const unsubscribe = authSession.subscribe(() => void enforce());
    afterNavigate(() => void enforce());
    return unsubscribe;
  });
</script>

{#if authorized}
  {@render children()}
{:else}
  <div class="flex min-h-[50vh] items-center justify-center px-6 text-sm text-[var(--text-muted)]">
    Memeriksa sesi…
  </div>
{/if}

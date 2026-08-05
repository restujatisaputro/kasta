<script lang="ts">
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { onMount } from 'svelte';
  import type { BusinessAccess } from '@kasta/contracts';
  import Button from '$lib/components/Button.svelte';
  import AuthShell from '$lib/components/AuthShell.svelte';
  import Toast from '$lib/components/Toast.svelte';
  import { listBusinesses, selectBusiness as chooseBusiness } from '$lib/api/auth';
  import { authSession } from '$lib/stores/auth-session';
  import { get } from 'svelte/store';

  let businesses = $state<BusinessAccess[]>([]);
  let busy = $state(true);
  let selectedId = $state('');
  let message = $state('');

  onMount(() => {
    void loadBusinesses();
  });

  async function loadBusinesses() {
    if (!browser) return;
    const session = get(authSession);
    if (!session) {
      await goto('/login');
      return;
    }
    if (session.businessId) {
      await goto(resolve('/usaha/[businessId]', { businessId: session.businessId }));
      return;
    }
    try {
      businesses = await listBusinesses(session.accessToken);
    } catch (error) {
      message = error instanceof Error ? error.message : 'Daftar usaha belum dapat dimuat.';
    } finally {
      busy = false;
    }
  }

  async function selectBusiness(business: BusinessAccess) {
    const session = get(authSession);
    if (!session) {
      await goto('/login');
      return;
    }
    selectedId = business.business_id;
    message = '';
    try {
      const token = await chooseBusiness(business.business_id, session.accessToken);
      authSession.set({
        ...session,
        accessToken: token.access_token,
        businessId: business.business_id,
      });
      await goto(resolve('/usaha/[businessId]', { businessId: business.business_id }));
    } catch (error) {
      message = error instanceof Error ? error.message : 'Usaha belum dapat dipilih.';
    } finally {
      selectedId = '';
    }
  }
</script>

<svelte:head>
  <title>Pilih Usaha | KASTA</title>
  <meta name="description" content="Pilih usaha yang ingin Anda kelola di KASTA." />
</svelte:head>

<AuthShell title="Pilih usaha" description="Pilih ruang usaha yang ingin Anda buka.">
  {#if busy}
    <p class="text-center text-[var(--text-muted)]">Memuat daftar usaha…</p>
  {:else if businesses.length === 0}
    <div class="space-y-4 text-center">
      <p class="text-[var(--text-muted)]">Belum ada usaha aktif yang dapat Anda akses.</p>
      <Button href="/registrasi" variant="secondary" full>Buat akun atau usaha baru</Button>
    </div>
  {:else}
    <div class="space-y-3">
      {#each businesses as business (business.business_id)}
        <button
          type="button"
          class="w-full rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 text-left transition hover:border-kasta-500 hover:bg-kasta-50 disabled:cursor-wait disabled:opacity-60"
          disabled={Boolean(selectedId)}
          onclick={() => void selectBusiness(business)}
        >
          <span class="block font-black">{business.name}</span>
          <span class="mt-1 block text-sm text-[var(--text-muted)]"
            >{business.code} · {business.role}</span
          >
        </button>
      {/each}
    </div>
  {/if}
</AuthShell>

<Toast open={Boolean(message)} {message} tone="error" onClose={() => (message = '')} />

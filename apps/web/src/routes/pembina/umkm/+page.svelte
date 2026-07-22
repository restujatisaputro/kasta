<script lang="ts">
  import { onMount } from 'svelte';
  import type { MentorBusinessSummary } from '@kasta/contracts';
  import { getMentorDashboard } from '$lib/api/mentors';
  import { authSession } from '$lib/stores/auth-session';
  import Button from '$lib/components/Button.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import LoadingState from '$lib/components/LoadingState.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  let businesses = $state<MentorBusinessSummary[]>([]);
  let loading = $state(true);
  let filter = $state('ALL');
  onMount(async () => {
    if (!$authSession) {
      loading = false;
      return;
    }
    try {
      businesses = (await getMentorDashboard($authSession.accessToken)).businesses;
    } finally {
      loading = false;
    }
  });
  const visible = $derived(
    filter === 'ALL' ? businesses : businesses.filter((item) => item.health_level === filter),
  );
  const statusClass = (level: string) =>
    level === 'GREEN'
      ? 'bg-kasta-100 text-kasta-900'
      : level === 'YELLOW'
        ? 'bg-amber-100 text-amber-900'
        : 'bg-red-100 text-red-900';
</script>

<svelte:head><title>UMKM binaan | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Pendampingan"
  title="UMKM binaan"
  description="Pilih UMKM untuk melihat kondisi dan tindak lanjut sesuai izin yang diberikan."
  >{#snippet actions()}<Button href="/pembina/akses">Minta akses UMKM</Button>{/snippet}</PageHeader
>
<div class="mt-6 flex gap-2 overflow-x-auto pb-2" aria-label="Filter kondisi">
  {#each [{ value: 'ALL', label: 'Semua' }, { value: 'GREEN', label: 'Relatif sehat' }, { value: 'YELLOW', label: 'Perlu perhatian' }, { value: 'RED', label: 'Perlu pendampingan' }] as item (item.value)}<button
      class="min-h-11 shrink-0 rounded-xl border px-4 text-sm font-extrabold {filter === item.value
        ? 'border-kasta-700 bg-kasta-700 text-white'
        : 'border-[var(--border)] bg-[var(--surface)]'}"
      onclick={() => (filter = item.value)}>{item.label}</button
    >{/each}
</div>
{#if loading}<LoadingState label="Memuat UMKM binaan…" />{:else if visible.length}<div
    class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3"
  >
    {#each visible as item (item.business_id)}<a
        class="kasta-card block p-5 transition hover:-translate-y-0.5 hover:shadow-lg"
        href={`/pembina/umkm/${item.business_id}`}
        ><div class="flex items-start justify-between gap-3">
          <div>
            <h2 class="font-black">{item.business_name}</h2>
            <p class="mt-1 text-xs text-[var(--text-muted)]">{item.city ?? 'Lokasi belum diisi'}</p>
          </div>
          <span
            class={`rounded-full px-3 py-1 text-xs font-black ${statusClass(item.health_level)}`}
            >{item.health_icon} {item.health_label}</span
          >
        </div>
        <div class="mt-5 grid grid-cols-2 gap-3 text-sm">
          <div>
            <span class="text-xs text-[var(--text-muted)]">Pencatatan</span>
            <p class="font-bold">{item.recording_consistency}%</p>
          </div>
          <div>
            <span class="text-xs text-[var(--text-muted)]">Tindak lanjut</span>
            <p class="font-bold">{item.open_recommendations} terbuka</p>
          </div>
        </div></a
      >{/each}
  </div>{:else}<div class="mt-5">
    <EmptyState
      title="Belum ada UMKM binaan"
      description="Kirim permintaan akses, lalu tunggu persetujuan pemilik UMKM."
      icon="mentor"
      >{#snippet action()}<Button href="/pembina/akses">Kirim permintaan</Button
        >{/snippet}</EmptyState
    >
  </div>{/if}

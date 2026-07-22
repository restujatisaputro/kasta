<script lang="ts">
  import { onMount } from 'svelte';
  import type { MentorScheduleItem } from '@kasta/contracts';
  import { getMentorDashboard } from '$lib/api/mentors';
  import { authSession } from '$lib/stores/auth-session';
  import Button from '$lib/components/Button.svelte';
  import DataTable from '$lib/components/DataTable.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  let items = $state<MentorScheduleItem[]>([]);
  onMount(async () => {
    if ($authSession)
      items = (await getMentorDashboard($authSession.accessToken)).upcoming_sessions;
  });
  const rows = $derived(
    items.map((item) => ({
      date: new Date(item.scheduled_at).toLocaleString('id-ID'),
      business: item.business_name,
      topic: item.topic,
      mode: item.mode,
    })),
  );
</script>

<svelte:head><title>Jadwal pendampingan | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Agenda pembina"
  title="Jadwal"
  description="Pertemuan dan tindak lanjut UMKM binaan."
  >{#snippet actions()}<Button href="/pembina/umkm">Buat jadwal</Button>{/snippet}</PageHeader
>
<div class="mt-6">
  {#if rows.length}<DataTable
      columns={[
        { key: 'date', label: 'Waktu' },
        { key: 'business', label: 'UMKM' },
        { key: 'topic', label: 'Topik' },
        { key: 'mode', label: 'Cara' },
      ]}
      {rows}
      caption="Jadwal pendampingan"
    />{:else}<EmptyState
      title="Belum ada jadwal mendatang"
      description="Pertemuan yang direncanakan akan muncul di sini."
      icon="calendar"
    />{/if}
</div>

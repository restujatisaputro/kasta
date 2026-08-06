<script lang="ts">
  import type { Snippet } from 'svelte';
  import AuthGuard from '$lib/components/AuthGuard.svelte';
  import AppShell from '$lib/components/AppShell.svelte';

  let { data, children }: { data: { businessId: string }; children: Snippet } = $props();
</script>

<AuthGuard businessId={data.businessId}>
  <AppShell businessId={data.businessId}>{@render children()}</AppShell>
</AuthGuard>

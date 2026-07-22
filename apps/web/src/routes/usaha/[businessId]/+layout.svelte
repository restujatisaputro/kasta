<script lang="ts">
  import type { Snippet } from 'svelte';
  import AppShell from '$lib/components/AppShell.svelte';

  let { data, children }: { data: { businessId: string }; children: Snippet } = $props();
</script>

<AppShell businessId={data.businessId}>{@render children()}</AppShell>

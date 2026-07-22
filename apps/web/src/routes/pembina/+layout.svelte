<script lang="ts">
  import type { Snippet } from 'svelte';
  import MentorShell from '$lib/components/MentorShell.svelte';
  let { children }: { children: Snippet } = $props();
</script>

<MentorShell>{@render children()}</MentorShell>

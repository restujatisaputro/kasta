<script lang="ts">
  import type { Snippet } from 'svelte';
  import AuthGuard from '$lib/components/AuthGuard.svelte';
  import MentorShell from '$lib/components/MentorShell.svelte';
  let { children }: { children: Snippet } = $props();
</script>

<AuthGuard><MentorShell>{@render children()}</MentorShell></AuthGuard>

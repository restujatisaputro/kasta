<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    children: Snippet;
    padding?: 'none' | 'small' | 'normal' | 'large';
    class?: string;
  }

  let { children, padding = 'normal', class: className = '' }: Props = $props();
  const spaces = { none: '', small: 'p-4', normal: 'p-5 sm:p-6', large: 'p-6 sm:p-8' };
</script>

<section class="kasta-card {spaces[padding]} {className}">
  {@render children()}
</section>

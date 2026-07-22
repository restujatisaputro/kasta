<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    eyebrow?: string;
    title: string;
    description?: string;
    actions?: Snippet;
  }

  let { eyebrow, title, description, actions }: Props = $props();
</script>

<header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
  <div class="max-w-3xl">
    {#if eyebrow}<p class="mb-1 text-sm font-extrabold text-kasta-700 dark:text-kasta-300">
        {eyebrow}
      </p>{/if}
    <h1 class="text-2xl font-black tracking-tight text-[var(--text)] sm:text-3xl">{title}</h1>
    {#if description}<p class="mt-2 leading-7 text-[var(--text-muted)]">{description}</p>{/if}
  </div>
  {#if actions}<div class="flex flex-wrap gap-2">{@render actions()}</div>{/if}
</header>

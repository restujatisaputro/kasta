<script lang="ts">
  import type { Snippet } from 'svelte';
  import MarketingShell from './MarketingShell.svelte';

  interface Props {
    title: string;
    description: string;
    children: Snippet;
    footer?: Snippet;
  }
  let { title, description, children, footer }: Props = $props();
</script>

<MarketingShell>
  <section class="relative overflow-hidden px-4 py-12 sm:px-6 sm:py-18">
    <div
      class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,#d8f3e3,transparent_34%),radial-gradient(circle_at_bottom_right,#fff3d6,transparent_28%)] dark:opacity-20"
    ></div>
    <div class="relative mx-auto max-w-md">
      <div class="mb-7 text-center">
        <p class="text-sm font-extrabold text-kasta-700 dark:text-kasta-300">KASTA</p>
        <h1 class="mt-2 text-3xl font-black tracking-tight">{title}</h1>
        <p class="mt-2 leading-7 text-[var(--text-muted)]">{description}</p>
      </div>
      <div class="kasta-card p-5 sm:p-7">{@render children()}</div>
      {#if footer}<div class="mt-6 text-center text-sm text-[var(--text-muted)]">
          {@render footer()}
        </div>{/if}
    </div>
  </section>
</MarketingShell>

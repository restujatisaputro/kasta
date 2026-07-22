<script lang="ts">
  import type { Snippet } from 'svelte';
  import Icon, { type IconName } from './Icon.svelte';

  interface Props {
    title: string;
    description: string;
    icon?: IconName;
    action?: Snippet;
  }

  let { title, description, icon = 'note', action }: Props = $props();
</script>

<div
  class="rounded-2xl border border-dashed border-[var(--border)] bg-[var(--surface-subtle)] px-5 py-10 text-center"
>
  <div
    class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-kasta-100 text-kasta-800 dark:bg-kasta-950 dark:text-kasta-200"
  >
    <Icon name={icon} size={24} />
  </div>
  <h2 class="mt-4 font-black text-[var(--text)]">{title}</h2>
  <p class="mx-auto mt-2 max-w-md text-sm leading-6 text-[var(--text-muted)]">{description}</p>
  {#if action}<div class="mt-5 flex justify-center">{@render action()}</div>{/if}
</div>

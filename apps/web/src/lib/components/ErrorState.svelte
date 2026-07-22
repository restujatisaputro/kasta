<script lang="ts">
  import type { Snippet } from 'svelte';
  import Icon from './Icon.svelte';

  interface Props {
    title?: string;
    message: string;
    action?: Snippet;
  }
  let { title = 'Data belum dapat dimuat', message, action }: Props = $props();
</script>

<div class="rounded-2xl border border-red-200 bg-red-50 p-5 text-red-900" role="alert">
  <div class="flex gap-3">
    <Icon name="alert" />
    <div>
      <h2 class="font-black">{title}</h2>
      <p class="mt-1 text-sm leading-6">{message}</p>
      {#if action}<div class="mt-4">{@render action()}</div>{/if}
    </div>
  </div>
</div>

<script lang="ts">
  import { fade, scale } from 'svelte/transition';
  import Button from './Button.svelte';

  interface Props {
    open?: boolean;
    title: string;
    message: string;
    confirmLabel?: string;
    danger?: boolean;
    onConfirm: () => void;
    onCancel: () => void;
  }

  let {
    open = false,
    title,
    message,
    confirmLabel = 'Ya, lanjutkan',
    danger = false,
    onConfirm,
    onCancel,
  }: Props = $props();

  let dialog = $state<HTMLDivElement>();
  $effect(() => {
    if (open) queueMicrotask(() => dialog?.focus());
  });

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') onCancel();
  }
</script>

{#if open}
  <div
    transition:fade={{ duration: 180 }}
    class="fixed inset-0 z-50 grid place-items-center bg-slate-950/55 p-4"
    role="presentation"
    onclick={(event) => event.target === event.currentTarget && onCancel()}
    onkeydown={handleKeydown}
  >
    <div
      bind:this={dialog}
      tabindex="-1"
      transition:scale={{ start: 0.96, duration: 220 }}
      class="kasta-card w-full max-w-md p-6 outline-none"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      aria-describedby="confirm-message"
    >
      <h2 id="confirm-title" class="text-xl font-black">{title}</h2>
      <p id="confirm-message" class="mt-2 leading-7 text-[var(--text-muted)]">{message}</p>
      <div class="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button variant="secondary" onclick={onCancel}>Batal</Button>
        <Button variant={danger ? 'danger' : 'primary'} onclick={onConfirm}>{confirmLabel}</Button>
      </div>
    </div>
  </div>
{/if}

<script lang="ts">
  import { fly } from 'svelte/transition';
  import Icon from './Icon.svelte';

  interface Props {
    open?: boolean;
    message: string;
    tone?: 'success' | 'error' | 'info';
    onClose?: () => void;
  }

  let { open = false, message, tone = 'success', onClose }: Props = $props();
  const styles = {
    success: 'border-kasta-300 bg-kasta-950 text-white',
    error: 'border-red-300 bg-red-950 text-white',
    info: 'border-blue-300 bg-slate-950 text-white',
  };
</script>

{#if open}
  <div
    transition:fly={{ y: 14, duration: 240 }}
    class="fixed right-4 bottom-24 z-50 max-w-sm rounded-2xl border px-4 py-3 shadow-2xl sm:bottom-6 {styles[
      tone
    ]}"
    role="status"
    aria-live="polite"
  >
    <div class="flex items-start gap-3">
      <Icon name={tone === 'error' ? 'alert' : 'check'} />
      <p class="flex-1 text-sm font-semibold leading-6">{message}</p>
      <button
        class="rounded-lg p-1 hover:bg-white/10"
        aria-label="Tutup notifikasi"
        onclick={onClose}
      >
        <Icon name="close" size={18} />
      </button>
    </div>
  </div>
{/if}

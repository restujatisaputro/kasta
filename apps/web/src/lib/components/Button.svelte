<script lang="ts">
  import type { Snippet } from 'svelte';

  type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

  interface Props {
    children: Snippet;
    href?: string;
    variant?: Variant;
    type?: 'button' | 'submit' | 'reset';
    disabled?: boolean;
    full?: boolean;
    ariaLabel?: string;
    onclick?: (event: MouseEvent) => void;
  }

  let {
    children,
    href,
    variant = 'primary',
    type = 'button',
    disabled = false,
    full = false,
    ariaLabel,
    onclick,
  }: Props = $props();

  const tones: Record<Variant, string> = {
    primary: 'border-kasta-700 bg-kasta-700 text-white hover:border-kasta-800 hover:bg-kasta-800',
    secondary:
      'border-[var(--border)] bg-[var(--surface)] text-[var(--text)] hover:border-kasta-300 hover:bg-kasta-50 dark:hover:bg-kasta-950',
    ghost:
      'border-transparent bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-muted)]',
    danger: 'border-red-700 bg-red-700 text-white hover:bg-red-800',
  };

  let classes = $derived(
    `kasta-button inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-extrabold transition disabled:pointer-events-none disabled:opacity-50 ${tones[variant]} ${full ? 'w-full' : ''}`,
  );
</script>

{#if href}
  <a class={classes} {href} aria-label={ariaLabel} {onclick}>
    {@render children()}
  </a>
{:else}
  <button class={classes} {type} {disabled} aria-label={ariaLabel} {onclick}>
    {@render children()}
  </button>
{/if}

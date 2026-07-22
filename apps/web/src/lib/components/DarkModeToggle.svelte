<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from './Icon.svelte';

  let dark = $state(false);

  onMount(() => {
    const saved = localStorage.getItem('kasta-theme');
    dark = saved === 'dark' || (!saved && matchMedia('(prefers-color-scheme: dark)').matches);
    apply();
  });

  function toggle(): void {
    dark = !dark;
    localStorage.setItem('kasta-theme', dark ? 'dark' : 'light');
    apply();
  }

  function apply(): void {
    document.documentElement.classList.toggle('dark', dark);
  }
</script>

<button
  class="grid h-11 w-11 place-items-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] transition hover:bg-[var(--surface-muted)]"
  aria-label={dark ? 'Gunakan tampilan terang' : 'Gunakan tampilan gelap'}
  title={dark ? 'Tampilan terang' : 'Tampilan gelap'}
  onclick={toggle}
>
  <Icon name={dark ? 'sun' : 'moon'} />
</button>

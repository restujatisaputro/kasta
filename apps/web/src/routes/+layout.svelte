<script lang="ts">
  import { navigating, page } from '$app/state';
  import '../app.css';

  let { children } = $props();
  const isNavigating = $derived(navigating.to !== null);
  const routeKey = $derived(`${page.url.pathname}${page.url.search}`);
</script>

<a class="skip-link" href="#main-content">Lewati ke isi utama</a>
{#if isNavigating}
  <div class="navigation-progress" role="status" aria-live="polite">
    <span class="navigation-progress__bar"></span>
    <span class="sr-only">Memuat halaman berikutnya...</span>
  </div>
{/if}

{#key routeKey}
  <div class="page-transition">{@render children()}</div>
{/key}

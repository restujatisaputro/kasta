<script lang="ts">
  interface Props {
    context?: string;
    href?: string;
    compact?: boolean;
  }

  let { context = 'Keuangan dan Asistensi UMKM', href = '/', compact = false }: Props = $props();
</script>

<a
  class="brand-logo {compact ? 'brand-logo--compact' : ''}"
  {href}
  aria-label={context ? `KASTA, ${context}` : 'KASTA'}
>
  <span class="brand-logo__mark" aria-hidden="true">
    <picture>
      <source srcset="/brand/logo-kasta-mark-transparent.webp" type="image/webp" />
      <img src="/brand/logo-kasta-mark-transparent.png" alt="" />
    </picture>
  </span>
  {#if !compact}
    <span class="brand-logo__copy">
      <strong>KASTA</strong>
      <small>{context}</small>
    </span>
  {/if}
</a>

<script lang="ts">
  interface Props {
    label?: string;
    rows?: number;
  }
  let { label = 'Memuat data...', rows = 3 }: Props = $props();
</script>

<div aria-busy="true" aria-live="polite">
  <span class="sr-only">{label}</span>
  <div class="space-y-3" aria-hidden="true">
    {#each Array(rows)
      .fill(0)
      .map((value, index) => value + index) as index (index)}
      <div class="kasta-skeleton h-20 rounded-2xl bg-[var(--surface-muted)]"></div>
    {/each}
  </div>
</div>

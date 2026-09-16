<script lang="ts">
  let { current, total }: { current: number; total: number } = $props();
  let percentage = $derived(Math.round((current / total) * 100));
</script>

<div aria-label={`Langkah ${current} dari ${total}`} class="space-y-2">
  <div class="flex items-center justify-between text-sm font-semibold">
    <span class="text-kasta-700 dark:text-kasta-300">Langkah {current} dari {total}</span>
    <span class="text-[var(--text-muted)]">{percentage}%</span>
  </div>
  <div class="h-2 overflow-hidden rounded-full bg-kasta-100 dark:bg-kasta-950">
    <div
      class="h-full rounded-full bg-kasta-600 transition-all duration-500"
      style={`width: ${percentage}%`}
    ></div>
  </div>
</div>

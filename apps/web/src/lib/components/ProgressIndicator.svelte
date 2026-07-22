<script lang="ts">
  let { current, total }: { current: number; total: number } = $props();
  let percentage = $derived(Math.round((current / total) * 100));
</script>

<div aria-label={`Langkah ${current} dari ${total}`} class="space-y-2">
  <div class="flex items-center justify-between text-sm font-semibold">
    <span class="text-emerald-800">Langkah {current} dari {total}</span>
    <span class="text-slate-500">{percentage}%</span>
  </div>
  <div class="h-2 overflow-hidden rounded-full bg-emerald-100">
    <div
      class="h-full rounded-full bg-emerald-600 transition-all duration-300"
      style={`width: ${percentage}%`}
    ></div>
  </div>
</div>

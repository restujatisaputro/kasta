<script lang="ts">
  import { onMount } from 'svelte';

  interface ChartLike {
    setOption: (option: unknown, notMerge?: boolean) => void;
    resize: () => void;
    dispose: () => void;
  }

  interface Props {
    option: unknown;
    label: string;
    description: string;
    height?: string;
  }

  let { option, label, description, height = '18rem' }: Props = $props();
  let element = $state<HTMLDivElement>();
  let chart: ChartLike | null = null;

  $effect(() => {
    const currentOption = option;
    chart?.setOption(currentOption, true);
  });

  onMount(() => {
    let observer: ResizeObserver | undefined;
    let active = true;
    void import('echarts').then((echarts) => {
      if (!active || !element) return;
      chart = echarts.init(element);
      chart.setOption(option);
      observer = new ResizeObserver(() => chart?.resize());
      observer.observe(element);
    });
    return () => {
      active = false;
      observer?.disconnect();
      chart?.dispose();
    };
  });
</script>

<figure aria-label={label}>
  <div bind:this={element} style:height class="w-full" aria-hidden="true"></div>
  <figcaption class="sr-only">{description}</figcaption>
</figure>

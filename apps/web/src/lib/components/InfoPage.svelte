<script lang="ts" module>
  export interface InfoSection {
    title: string;
    paragraphs: string[];
    items?: string[];
  }
</script>

<script lang="ts">
  import MarketingShell from './MarketingShell.svelte';

  interface Props {
    eyebrow: string;
    title: string;
    description: string;
    sections: InfoSection[];
    updated?: string;
  }
  let { eyebrow, title, description, sections, updated }: Props = $props();
</script>

<MarketingShell>
  <section
    class="border-b border-[var(--border)] bg-[linear-gradient(145deg,#effbf4_0%,#fff_60%,#fff7e8_100%)] px-5 py-14 dark:bg-none sm:px-6 sm:py-20"
  >
    <div class="mx-auto max-w-4xl">
      <p class="font-extrabold text-kasta-700 dark:text-kasta-300">{eyebrow}</p>
      <h1 class="mt-3 text-4xl font-black tracking-tight sm:text-5xl">{title}</h1>
      <p class="mt-5 max-w-3xl text-lg leading-8 text-[var(--text-muted)]">{description}</p>
      {#if updated}<p class="mt-4 text-sm font-semibold text-[var(--text-muted)]">
          Terakhir diperbarui: {updated}
        </p>{/if}
    </div>
  </section>
  <div class="mx-auto grid max-w-4xl gap-5 px-5 py-10 sm:px-6 sm:py-14">
    {#each sections as section (section.title)}
      <article class="kasta-card p-5 sm:p-7">
        <h2 class="text-xl font-black">{section.title}</h2>
        {#each section.paragraphs as paragraph (paragraph)}
          <p class="mt-3 leading-7 text-[var(--text-muted)]">{paragraph}</p>
        {/each}
        {#if section.items}
          <ul class="mt-4 grid gap-3">
            {#each section.items as item (item)}
              <li class="flex gap-3 leading-7 text-[var(--text-muted)]">
                <span class="mt-2.5 h-2 w-2 shrink-0 rounded-full bg-kasta-500"></span><span
                  >{item}</span
                >
              </li>
            {/each}
          </ul>
        {/if}
      </article>
    {/each}
  </div>
</MarketingShell>

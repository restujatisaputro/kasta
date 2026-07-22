<script lang="ts" module>
  export interface DataColumn {
    key: string;
    label: string;
    align?: 'left' | 'right';
  }
</script>

<script lang="ts">
  interface Props {
    columns: DataColumn[];
    rows: Array<Record<string, unknown>>;
    caption: string;
  }
  let { columns, rows, caption }: Props = $props();
</script>

<div class="overflow-x-auto rounded-2xl border border-[var(--border)]">
  <table class="w-full min-w-[620px] border-collapse text-sm">
    <caption class="sr-only">{caption}</caption>
    <thead class="bg-[var(--surface-muted)] text-left text-xs text-[var(--text-muted)] uppercase">
      <tr>
        {#each columns as column (column.key)}
          <th
            class="px-4 py-3 font-extrabold {column.align === 'right' ? 'text-right' : ''}"
            scope="col">{column.label}</th
          >
        {/each}
      </tr>
    </thead>
    <tbody class="divide-y divide-[var(--border)] bg-[var(--surface)]">
      {#each rows as row, index (index)}
        <tr class="hover:bg-[var(--surface-subtle)]">
          {#each columns as column (column.key)}
            <td class="px-4 py-3 {column.align === 'right' ? 'text-right font-bold' : ''}"
              >{String(row[column.key] ?? '—')}</td
            >
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

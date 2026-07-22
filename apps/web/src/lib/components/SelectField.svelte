<script lang="ts">
  export interface SelectOption {
    value: string;
    label: string;
  }

  interface Props {
    id: string;
    label: string;
    options: SelectOption[];
    value?: string;
    help?: string;
    error?: string;
    required?: boolean;
  }

  let {
    id,
    label,
    options,
    value = $bindable(''),
    help,
    error,
    required = false,
  }: Props = $props();
</script>

<div>
  <label class="kasta-label" for={id}>{label}{required ? ' *' : ''}</label>
  <select
    class="kasta-field"
    {id}
    {required}
    aria-invalid={error ? 'true' : undefined}
    aria-describedby={error ? `${id}-error` : help ? `${id}-help` : undefined}
    bind:value
  >
    {#each options as option (option.value)}
      <option value={option.value}>{option.label}</option>
    {/each}
  </select>
  {#if error}
    <p id={`${id}-error`} class="mt-1.5 text-xs font-semibold text-red-700" role="alert">
      {error}
    </p>
  {:else if help}
    <p id={`${id}-help`} class="kasta-help">{help}</p>
  {/if}
</div>

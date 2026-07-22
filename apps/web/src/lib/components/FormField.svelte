<script lang="ts">
  import type { HTMLInputAttributes } from 'svelte/elements';

  interface Props {
    id: string;
    label: string;
    value?: string;
    type?: 'text' | 'email' | 'tel' | 'password' | 'date' | 'number' | 'search';
    placeholder?: string;
    help?: string;
    error?: string;
    autocomplete?: HTMLInputAttributes['autocomplete'];
    required?: boolean;
    disabled?: boolean;
  }

  let {
    id,
    label,
    value = $bindable(''),
    type = 'text',
    placeholder,
    help,
    error,
    autocomplete,
    required = false,
    disabled = false,
  }: Props = $props();

  let descriptionId = $derived(error ? `${id}-error` : help ? `${id}-help` : undefined);
</script>

<div>
  <label class="kasta-label" for={id}>{label}{required ? ' *' : ''}</label>
  <input
    class="kasta-field"
    {id}
    {type}
    {placeholder}
    {autocomplete}
    {required}
    {disabled}
    aria-invalid={error ? 'true' : undefined}
    aria-describedby={descriptionId}
    bind:value
  />
  {#if error}
    <p id={`${id}-error`} class="mt-1.5 text-xs font-semibold text-red-700" role="alert">
      {error}
    </p>
  {:else if help}
    <p id={`${id}-help`} class="kasta-help">{help}</p>
  {/if}
</div>

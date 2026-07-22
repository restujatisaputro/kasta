<script lang="ts">
  import type { MentorAccessGrant, MentorAccessHistory, MentorAccessScope } from '@kasta/contracts';
  import { onMount } from 'svelte';

  import {
    decideMentorAccess,
    getBusinessMentorAccess,
    getMentorAccessHistory,
    revokeMentorAccess,
  } from '$lib/api/mentors';
  import { authSession } from '$lib/stores/auth-session';

  let { data } = $props();
  const scopeOptions: Array<{ value: MentorAccessScope; label: string }> = [
    { value: 'SUMMARY', label: 'Melihat ringkasan' },
    { value: 'REPORTS', label: 'Melihat laporan' },
    { value: 'TRANSACTIONS', label: 'Melihat transaksi' },
    { value: 'RECEIPTS', label: 'Melihat nota' },
    { value: 'INVENTORY', label: 'Melihat stok' },
    { value: 'OBLIGATIONS', label: 'Melihat utang dan piutang' },
    { value: 'EXPORT_REPORTS', label: 'Mengunduh laporan' },
  ];
  let accesses = $state<MentorAccessGrant[]>([]);
  let history = $state<MentorAccessHistory[]>([]);
  let selected = $state<Record<string, MentorAccessScope[]>>({});
  let expiry = $state<Record<string, string>>({});
  let reason = $state<Record<string, string>>({});
  let loading = $state(true);
  let saving = $state('');
  let message = $state('');
  let error = $state('');

  onMount(() => void load());

  async function load(): Promise<void> {
    if (!$authSession) {
      loading = false;
      return;
    }
    try {
      [accesses, history] = await Promise.all([
        getBusinessMentorAccess($authSession.accessToken, data.businessId),
        getMentorAccessHistory($authSession.accessToken, data.businessId),
      ]);
      for (const access of accesses) {
        selected[access.id] = [...access.scope];
      }
    } catch (cause) {
      error = cause instanceof Error ? cause.message : 'Izin pembina belum dapat dimuat.';
    } finally {
      loading = false;
    }
  }

  function toggle(accessId: string, scope: MentorAccessScope): void {
    const values = selected[accessId] ?? [];
    selected[accessId] = values.includes(scope)
      ? values.filter((item) => item !== scope)
      : [...values, scope];
  }

  async function decide(access: MentorAccessGrant, decision: 'APPROVE' | 'REJECT'): Promise<void> {
    if (!$authSession) return;
    error = '';
    message = '';
    saving = access.id;
    try {
      const expiresAt = expiry[access.id]
        ? new Date(`${expiry[access.id]}T23:59:59`).toISOString()
        : null;
      await decideMentorAccess($authSession.accessToken, data.businessId, access.id, {
        decision,
        scope: decision === 'APPROVE' ? (selected[access.id] ?? []) : [],
        expires_at: decision === 'APPROVE' ? expiresAt : null,
        reason: reason[access.id] || null,
      });
      message = decision === 'APPROVE' ? 'Izin pembina sudah aktif.' : 'Permintaan ditolak.';
      await load();
    } catch (cause) {
      error = cause instanceof Error ? cause.message : 'Keputusan belum dapat disimpan.';
    } finally {
      saving = '';
    }
  }

  async function revoke(access: MentorAccessGrant): Promise<void> {
    if (!$authSession) return;
    const value = reason[access.id]?.trim();
    if (!value) {
      error = 'Isi alasan pencabutan terlebih dahulu.';
      return;
    }
    saving = access.id;
    try {
      await revokeMentorAccess($authSession.accessToken, data.businessId, access.id, value);
      message = 'Izin dicabut. Pembina tidak dapat mengakses data lagi.';
      await load();
    } catch (cause) {
      error = cause instanceof Error ? cause.message : 'Izin belum dapat dicabut.';
    } finally {
      saving = '';
    }
  }
</script>

<svelte:head><title>Akses Pembina | KASTA</title></svelte:head>

<section class="page-shell">
  <header class="page-header">
    <div>
      <p class="eyebrow">Privasi usaha</p>
      <h1>Akses Pembina</h1>
      <p>Pilih dengan jelas data yang boleh dilihat dan sampai kapan.</p>
    </div>
    <a class="button secondary" href={`/usaha/${data.businessId}/profil`}>Kembali</a>
  </header>

  {#if error}<p class="alert error" role="alert">{error}</p>{/if}
  {#if message}<p class="alert success" role="status">{message}</p>{/if}
  {#if loading}
    <p>Memuat izin pembina…</p>
  {:else if accesses.length === 0}
    <section class="panel"><p>Belum ada permintaan akses pembina.</p></section>
  {:else}
    <section class="stack" aria-label="Daftar izin pembina">
      {#each accesses as access (access.id)}
        <article class="panel">
          <div class="row between">
            <div>
              <h2>Pembina {access.mentor_id.slice(0, 8)}</h2>
              <p>Status: <strong>{access.status}</strong></p>
            </div>
            {#if access.last_accessed_at}
              <small
                >Terakhir melihat: {new Date(access.last_accessed_at).toLocaleString(
                  'id-ID',
                )}</small
              >
            {/if}
          </div>
          {#if access.request_message}<p>“{access.request_message}”</p>{/if}
          {#if access.status === 'REQUESTED'}
            <fieldset>
              <legend>Data yang boleh dilihat</legend>
              <div class="scope-grid">
                {#each scopeOptions as option (option.value)}
                  <label>
                    <input
                      type="checkbox"
                      checked={(selected[access.id] ?? []).includes(option.value)}
                      onchange={() => toggle(access.id, option.value)}
                    />
                    {option.label}
                  </label>
                {/each}
              </div>
            </fieldset>
            <label>Masa berlaku <input type="date" bind:value={expiry[access.id]} /></label>
            <label
              >Alasan penolakan (bila ditolak)<textarea bind:value={reason[access.id]}
              ></textarea></label
            >
            <div class="row">
              <button disabled={saving === access.id} onclick={() => decide(access, 'APPROVE')}
                >Setujui</button
              >
              <button
                class="danger"
                disabled={saving === access.id}
                onclick={() => decide(access, 'REJECT')}>Tolak</button
              >
            </div>
          {:else if access.status === 'ACTIVE'}
            <p>
              {access.scope
                .map((scope) => scopeOptions.find((item) => item.value === scope)?.label)
                .join(' · ')}
            </p>
            <p>
              Berlaku sampai {access.expires_at
                ? new Date(access.expires_at).toLocaleDateString('id-ID')
                : '-'}
            </p>
            <label>Alasan pencabutan<textarea bind:value={reason[access.id]}></textarea></label>
            <button class="danger" disabled={saving === access.id} onclick={() => revoke(access)}
              >Cabut izin</button
            >
          {/if}
        </article>
      {/each}
    </section>
  {/if}

  <section class="panel">
    <h2>Riwayat akses</h2>
    {#each history as item (item.id)}
      <p>
        <strong>{item.action}</strong> · {new Date(item.accessed_at).toLocaleString('id-ID')}
        {item.reason ?? ''}
      </p>
    {:else}
      <p>Belum ada aktivitas akses.</p>
    {/each}
  </section>
</section>

<style>
  .page-shell {
    max-width: 1100px;
    margin: auto;
    padding: 2rem;
  }
  .page-header,
  .row {
    display: flex;
    gap: 1rem;
    align-items: center;
  }
  .page-header,
  .between {
    justify-content: space-between;
  }
  .stack {
    display: grid;
    gap: 1rem;
  }
  .panel {
    margin: 1rem 0;
    padding: 1.25rem;
    border: 1px solid #d8e0dc;
    border-radius: 1rem;
    background: white;
  }
  .scope-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 0.75rem;
    margin: 0.75rem 0;
  }
  label {
    display: grid;
    gap: 0.35rem;
    margin: 0.75rem 0;
  }
  .scope-grid label {
    display: flex;
  }
  input,
  textarea {
    padding: 0.7rem;
    border: 1px solid #aebcb5;
    border-radius: 0.5rem;
  }
  button,
  .button {
    padding: 0.7rem 1rem;
    border: 0;
    border-radius: 0.6rem;
    background: #176b4d;
    color: white;
    text-decoration: none;
  }
  .danger {
    background: #a62b2b;
  }
  .secondary {
    background: #eef4f1;
    color: #164b39;
  }
  .alert {
    padding: 0.8rem;
    border-radius: 0.6rem;
  }
  .error {
    background: #ffe9e9;
  }
  .success {
    background: #e5f6ed;
  }
  .eyebrow {
    color: #176b4d;
    font-weight: 700;
    text-transform: uppercase;
  }
  @media (max-width: 650px) {
    .page-header,
    .between {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>

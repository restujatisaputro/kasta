<script lang="ts">
  import type { MentorAccessGrant, MentorAccessScope } from '@kasta/contracts';
  import { onMount } from 'svelte';

  import { getMyMentorAccess, requestMentorAccess } from '$lib/api/mentors';
  import { authSession } from '$lib/stores/auth-session';

  const options: Array<{ value: MentorAccessScope; label: string }> = [
    { value: 'SUMMARY', label: 'Ringkasan' },
    { value: 'REPORTS', label: 'Laporan' },
    { value: 'TRANSACTIONS', label: 'Transaksi' },
    { value: 'RECEIPTS', label: 'Nota' },
    { value: 'INVENTORY', label: 'Stok' },
    { value: 'OBLIGATIONS', label: 'Utang dan piutang' },
    { value: 'EXPORT_REPORTS', label: 'Unduh laporan' },
  ];
  let items = $state<MentorAccessGrant[]>([]);
  let businessId = $state('');
  let scopes = $state<MentorAccessScope[]>(['SUMMARY']);
  let requestMessage = $state('');
  let loading = $state(true);
  let saving = $state(false);
  let notice = $state('');
  let error = $state('');

  onMount(() => void load());

  async function load(): Promise<void> {
    if (!$authSession) {
      loading = false;
      return;
    }
    try {
      items = await getMyMentorAccess($authSession.accessToken);
    } catch (cause) {
      error = cause instanceof Error ? cause.message : 'Daftar izin belum dapat dimuat.';
    } finally {
      loading = false;
    }
  }

  function toggle(scope: MentorAccessScope): void {
    scopes = scopes.includes(scope) ? scopes.filter((item) => item !== scope) : [...scopes, scope];
  }

  async function submit(): Promise<void> {
    if (!$authSession || !businessId || scopes.length === 0) {
      error = 'Isi ID UMKM dan pilih kebutuhan akses.';
      return;
    }
    saving = true;
    error = '';
    try {
      await requestMentorAccess($authSession.accessToken, {
        business_id: businessId.trim(),
        requested_scope: scopes,
        message: requestMessage.trim() || null,
      });
      businessId = '';
      requestMessage = '';
      notice = 'Permintaan dikirim. Pemilik UMKM akan memilih izin dan masa berlaku.';
      await load();
    } catch (cause) {
      error = cause instanceof Error ? cause.message : 'Permintaan belum dapat dikirim.';
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head><title>Permintaan Akses | KASTA</title></svelte:head>

<section class="shell">
  <header>
    <p class="eyebrow">Privasi UMKM</p>
    <h1>Permintaan Akses</h1>
    <p>Pemilik UMKM tetap menentukan data yang dapat Anda lihat.</p>
    <a href="/pembina">Kembali ke dashboard</a>
  </header>
  {#if error}<p class="message error" role="alert">{error}</p>{/if}
  {#if notice}<p class="message success" role="status">{notice}</p>{/if}
  <section class="panel">
    <h2>Kirim permintaan</h2>
    <label>ID UMKM <input bind:value={businessId} placeholder="UUID usaha" /></label>
    <fieldset>
      <legend>Data yang dibutuhkan</legend>
      <div class="grid">
        {#each options as option (option.value)}
          <label class="check"
            ><input
              type="checkbox"
              checked={scopes.includes(option.value)}
              onchange={() => toggle(option.value)}
            />
            {option.label}</label
          >
        {/each}
      </div>
    </fieldset>
    <label
      >Pesan untuk pemilik <textarea bind:value={requestMessage} maxlength="500"></textarea></label
    >
    <button disabled={saving} onclick={submit}>{saving ? 'Mengirim…' : 'Kirim permintaan'}</button>
  </section>
  <section class="panel">
    <h2>Status izin</h2>
    {#if loading}<p>Memuat…</p>{/if}
    {#each items as item (item.id)}
      <article>
        <strong>{item.business_id}</strong>
        <span class={`status ${item.status.toLowerCase()}`}>{item.status}</span>
        <p>{item.scope.join(' · ')}</p>
        {#if item.expires_at}<small
            >Berlaku sampai {new Date(item.expires_at).toLocaleDateString('id-ID')}</small
          >{/if}
      </article>
    {:else}
      {#if !loading}<p>Belum ada permintaan akses.</p>{/if}
    {/each}
  </section>
</section>

<style>
  .shell {
    max-width: 900px;
    margin: auto;
    padding: 2rem;
  }
  .panel {
    margin: 1rem 0;
    padding: 1.25rem;
    border: 1px solid #d8e0dc;
    border-radius: 1rem;
    background: white;
  }
  label {
    display: grid;
    gap: 0.35rem;
    margin: 0.75rem 0;
  }
  input,
  textarea {
    padding: 0.7rem;
    border: 1px solid #aebcb5;
    border-radius: 0.5rem;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }
  .check {
    display: flex;
  }
  button {
    padding: 0.75rem 1rem;
    border: 0;
    border-radius: 0.6rem;
    color: white;
    background: #176b4d;
  }
  article {
    padding: 0.8rem 0;
    border-bottom: 1px solid #e2e8e5;
  }
  .status {
    margin-left: 1rem;
    font-weight: 700;
  }
  .message {
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
</style>

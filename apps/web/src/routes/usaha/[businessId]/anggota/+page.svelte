<script lang="ts">
  import Button from '$lib/components/Button.svelte';
  import Card from '$lib/components/Card.svelte';
  import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
  import DataTable from '$lib/components/DataTable.svelte';
  import FormField from '$lib/components/FormField.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import Toast from '$lib/components/Toast.svelte';
  let inviteOpen = $state(false);
  let email = $state('');
  let removeOpen = $state(false);
  let message = $state('');
  const rows = [{ name: 'Pemilik usaha', contact: 'Akun Anda', role: 'Pemilik', status: 'Aktif' }];
</script>

<svelte:head><title>Anggota usaha | KASTA</title></svelte:head>
<PageHeader
  eyebrow="Tim usaha"
  title="Anggota usaha"
  description="Atur pegawai yang boleh membantu pencatatan."
  >{#snippet actions()}<Button onclick={() => (inviteOpen = !inviteOpen)}>Undang pegawai</Button
    >{/snippet}</PageHeader
>
{#if inviteOpen}<div class="mt-6 max-w-xl">
    <Card
      ><h2 class="font-black">Undang pegawai</h2>
      <div class="mt-4">
        <FormField id="member-email" label="Email atau nomor telepon" bind:value={email} />
      </div>
      <div class="mt-4 flex gap-2">
        <Button
          onclick={() => {
            message = 'Undangan berhasil disiapkan.';
            inviteOpen = false;
            email = '';
          }}>Kirim undangan</Button
        ><Button variant="secondary" onclick={() => (inviteOpen = false)}>Batal</Button>
      </div></Card
    >
  </div>{/if}
<div class="mt-6">
  <DataTable
    columns={[
      { key: 'name', label: 'Nama' },
      { key: 'contact', label: 'Kontak' },
      { key: 'role', label: 'Peran' },
      { key: 'status', label: 'Status' },
    ]}
    {rows}
    caption="Anggota usaha"
  />
</div>
<div class="mt-4 text-right">
  <button class="text-sm font-bold text-red-700 hover:underline" onclick={() => (removeOpen = true)}
    >Contoh dialog hapus akses</button
  >
</div>
<ConfirmDialog
  open={removeOpen}
  danger
  title="Hapus akses pegawai?"
  message="Pegawai tidak dapat lagi membuka data usaha setelah akses dihapus."
  confirmLabel="Hapus akses"
  onConfirm={() => {
    removeOpen = false;
    message = 'Akses pegawai dihapus.';
  }}
  onCancel={() => (removeOpen = false)}
/>
<Toast open={Boolean(message)} {message} onClose={() => (message = '')} />

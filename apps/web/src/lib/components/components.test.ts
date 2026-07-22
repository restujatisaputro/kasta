import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

import ConfirmDialog from './ConfirmDialog.svelte';
import DataTable from './DataTable.svelte';
import EmptyState from './EmptyState.svelte';

afterEach(cleanup);

describe('komponen antarmuka KASTA', () => {
  it('memberi nama yang dapat dibaca pembaca layar pada tabel', () => {
    render(DataTable, {
      columns: [{ key: 'name', label: 'Nama usaha' }],
      rows: [{ name: 'Warung Contoh' }],
      caption: 'Daftar UMKM binaan',
    });

    expect(screen.getByRole('table', { name: 'Daftar UMKM binaan' })).toBeTruthy();
    expect(screen.getByText('Warung Contoh')).toBeTruthy();
  });

  it('menampilkan empty state dengan penjelasan yang jelas', () => {
    render(EmptyState, {
      title: 'Belum ada transaksi',
      description: 'Transaksi baru akan muncul di sini.',
    });

    expect(screen.getByRole('heading', { name: 'Belum ada transaksi' })).toBeTruthy();
    expect(screen.getByText('Transaksi baru akan muncul di sini.')).toBeTruthy();
  });

  it('dapat menutup dialog konfirmasi dengan tombol Escape', async () => {
    const cancel = vi.fn();
    render(ConfirmDialog, {
      open: true,
      title: 'Batalkan transaksi?',
      message: 'Transaksi akan dibalik dengan catatan baru.',
      onConfirm: vi.fn(),
      onCancel: cancel,
    });

    await fireEvent.keyDown(screen.getByRole('alertdialog'), { key: 'Escape' });
    expect(cancel).toHaveBeenCalledOnce();
  });
});

<script lang="ts">
  import type { Snippet } from 'svelte';
  import Button from './Button.svelte';
  import DarkModeToggle from './DarkModeToggle.svelte';

  interface Props {
    children: Snippet;
  }

  let { children }: Props = $props();

  const nav = [
    { href: '/tentang', label: 'Tentang' },
    { href: '/fitur', label: 'Fitur' },
    { href: '/bantuan', label: 'Bantuan' },
  ];
</script>

<div class="min-h-screen bg-[var(--surface-subtle)] text-[var(--text)]">
  <header
    class="sticky top-0 z-40 border-b border-[var(--border)] bg-[color:var(--surface)]/95 backdrop-blur"
  >
    <div class="mx-auto flex h-18 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
      <a href="/" class="flex items-center gap-2" aria-label="KASTA, kembali ke beranda">
        <span
          class="grid h-10 w-10 place-items-center rounded-xl bg-kasta-700 text-lg font-black text-white"
          >K</span
        >
        <span
          ><strong class="block text-lg leading-5 text-kasta-950 dark:text-kasta-100">KASTA</strong
          ><small class="hidden text-[11px] text-[var(--text-muted)] sm:block"
            >Keuangan dan Asistensi UMKM</small
          ></span
        >
      </a>

      <nav class="hidden items-center gap-1 md:flex" aria-label="Navigasi utama">
        {#each nav as item (item.href)}
          <a
            class="rounded-xl px-4 py-2.5 text-sm font-bold text-[var(--text-muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--text)]"
            href={item.href}>{item.label}</a
          >
        {/each}
      </nav>

      <div class="hidden items-center gap-2 md:flex">
        <DarkModeToggle />
        <Button href="/login" variant="ghost">Masuk</Button>
        <Button href="/registrasi">Daftar gratis</Button>
      </div>

      <details class="relative md:hidden">
        <summary
          class="flex min-h-11 cursor-pointer list-none items-center rounded-xl border border-[var(--border)] px-3 text-sm font-extrabold"
          >Menu</summary
        >
        <nav
          class="absolute right-0 mt-2 w-64 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-3 shadow-2xl"
          aria-label="Navigasi seluler"
        >
          {#each nav as item (item.href)}
            <a
              class="block rounded-xl px-3 py-3 font-bold hover:bg-[var(--surface-muted)]"
              href={item.href}>{item.label}</a
            >
          {/each}
          <div class="my-2 border-t border-[var(--border)]"></div>
          <a class="block rounded-xl px-3 py-3 font-bold" href="/login">Masuk</a>
          <a
            class="block rounded-xl bg-kasta-700 px-3 py-3 text-center font-bold text-white"
            href="/registrasi">Daftar gratis</a
          >
        </nav>
      </details>
    </div>
  </header>

  <main id="main-content">{@render children()}</main>

  <footer class="border-t border-[var(--border)] bg-[var(--surface)]">
    <div class="mx-auto grid max-w-7xl gap-8 px-5 py-12 sm:px-6 md:grid-cols-[1.2fr_.8fr_.8fr]">
      <div>
        <strong class="text-xl text-kasta-900 dark:text-kasta-100">KASTA</strong>
        <p class="mt-3 max-w-sm text-sm leading-6 text-[var(--text-muted)]">
          Pencatatan keuangan yang mudah dipahami pelaku UMKM dan tetap rapi di belakang layar.
        </p>
      </div>
      <div>
        <h2 class="text-sm font-black">KASTA</h2>
        <div class="mt-3 grid gap-2 text-sm text-[var(--text-muted)]">
          <a href="/tentang">Tentang KASTA</a><a href="/fitur">Fitur</a><a href="/bantuan"
            >Pusat bantuan</a
          >
        </div>
      </div>
      <div>
        <h2 class="text-sm font-black">Kepercayaan</h2>
        <div class="mt-3 grid gap-2 text-sm text-[var(--text-muted)]">
          <a href="/kebijakan-privasi">Kebijakan privasi</a><a href="/syarat-penggunaan"
            >Syarat penggunaan</a
          ><a href="mailto:dukungan@kasta.id">dukungan@kasta.id</a>
        </div>
      </div>
    </div>
    <div
      class="border-t border-[var(--border)] px-5 py-5 text-center text-xs text-[var(--text-muted)]"
    >
      © 2026 KASTA. Dibuat untuk UMKM Indonesia.
    </div>
  </footer>
</div>

<script lang="ts">
  import { page } from '$app/state';
  import type { Snippet } from 'svelte';
  import DarkModeToggle from './DarkModeToggle.svelte';
  import Icon, { type IconName } from './Icon.svelte';

  interface Props {
    children: Snippet;
  }
  let { children }: Props = $props();

  const nav: Array<{ href: string; label: string; icon: IconName }> = [
    { href: '/pembina', label: 'Dashboard', icon: 'home' },
    { href: '/pembina/umkm', label: 'UMKM binaan', icon: 'mentor' },
    { href: '/pembina/catatan', label: 'Catatan', icon: 'note' },
    { href: '/pembina/rekomendasi', label: 'Rekomendasi', icon: 'recommendation' },
    { href: '/pembina/jadwal', label: 'Jadwal', icon: 'calendar' },
    { href: '/pembina/laporan', label: 'Laporan agregat', icon: 'chart' },
    { href: '/pembina/akses', label: 'Permintaan akses', icon: 'users' },
  ];

  function active(href: string): boolean {
    return href === '/pembina'
      ? page.url.pathname === href || page.url.pathname === `${href}/`
      : page.url.pathname.startsWith(href);
  }
</script>

<div
  class="min-h-screen bg-[var(--surface-subtle)] text-[var(--text)] lg:grid lg:grid-cols-[17rem_minmax(0,1fr)]"
>
  <aside
    class="fixed inset-y-0 left-0 z-30 hidden w-68 border-r border-[var(--border)] bg-[var(--surface)] lg:flex lg:flex-col"
  >
    <a href="/" class="flex h-18 items-center gap-3 border-b border-[var(--border)] px-5"
      ><span class="relative grid h-10 w-14 place-items-center overflow-hidden rounded-xl border border-[#eadfc8] bg-[#fff8e7]"
        ><img
          src="/images/kasta-logo.png"
          alt=""
          class="absolute left-1/2 top-1/2 w-[300%] max-w-none -translate-x-1/2 -translate-y-1/2"
        /></span
      ><span
        ><strong class="block">KASTA</strong><small class="text-[11px] text-[var(--text-muted)]"
          >Ruang pembina</small
        ></span
      ></a
    >
    <nav class="flex-1 p-3" aria-label="Menu pembina">
      {#each nav as item (item.href)}
        <a
          href={item.href}
          aria-current={active(item.href) ? 'page' : undefined}
          class="mb-1 flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-bold {active(
            item.href,
          )
            ? 'bg-kasta-100 text-kasta-900 dark:bg-kasta-950 dark:text-kasta-100'
            : 'text-[var(--text-muted)] hover:bg-[var(--surface-muted)]'}"
          ><Icon name={item.icon} />{item.label}</a
        >
      {/each}
    </nav>
    <p class="border-t border-[var(--border)] p-4 text-xs leading-5 text-[var(--text-muted)]">
      Pembina hanya dapat melihat data yang telah diizinkan pemilik UMKM.
    </p>
  </aside>
  <div class="min-w-0 lg:col-start-2">
    <header
      class="sticky top-0 z-20 flex h-18 items-center justify-between border-b border-[var(--border)] bg-[color:var(--surface)]/95 px-4 backdrop-blur sm:px-6"
    >
      <div>
        <p class="text-xs font-bold text-[var(--text-muted)]">Ruang kerja</p>
        <p class="font-black">Pembina UMKM</p>
      </div>
      <div class="flex items-center gap-2">
        <DarkModeToggle /><span
          class="grid h-11 w-11 place-items-center rounded-xl bg-kasta-100 text-sm font-black text-kasta-900"
          >PB</span
        >
      </div>
    </header>
    <main id="main-content" class="mx-auto max-w-[1600px] px-4 py-6 pb-24 sm:px-6 lg:pb-8">
      {@render children()}
    </main>
  </div>
  <nav
    class="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-[var(--border)] bg-[var(--surface)] px-1 pb-[max(.35rem,env(safe-area-inset-bottom))] pt-1 lg:hidden"
    aria-label="Menu pembina seluler"
  >
    {#each nav.slice(0, 5) as item (item.href)}
      <a
        href={item.href}
        class="flex min-h-14 flex-col items-center justify-center gap-1 text-[10px] font-extrabold {active(
          item.href,
        )
          ? 'text-kasta-700'
          : 'text-[var(--text-muted)]'}"
        ><Icon name={item.icon} size={20} />{item.label.replace('UMKM binaan', 'UMKM')}</a
      >
    {/each}
  </nav>
</div>

<script lang="ts">
  import { page } from '$app/state';
  import type { Snippet } from 'svelte';
  import DarkModeToggle from './DarkModeToggle.svelte';
  import Icon, { type IconName } from './Icon.svelte';
  import NotificationBell from './NotificationBell.svelte';

  interface Props {
    businessId: string;
    children: Snippet;
  }

  let { businessId, children }: Props = $props();

  const navigation: Array<{ slug: string; label: string; icon: IconName }> = [
    { slug: '', label: 'Beranda', icon: 'home' },
    { slug: 'transaksi', label: 'Transaksi', icon: 'transaction' },
    { slug: 'uang-masuk', label: 'Uang Masuk', icon: 'income' },
    { slug: 'uang-keluar', label: 'Uang Keluar', icon: 'expense' },
    { slug: 'foto-nota', label: 'Foto Nota', icon: 'camera' },
    { slug: 'produk', label: 'Produk', icon: 'box' },
    { slug: 'stok', label: 'Stok', icon: 'stock' },
    { slug: 'utang', label: 'Utang', icon: 'payable' },
    { slug: 'piutang', label: 'Piutang', icon: 'receivable' },
    { slug: 'laporan', label: 'Laporan', icon: 'chart' },
    { slug: 'pembina', label: 'Pembina', icon: 'mentor' },
    { slug: 'anggota', label: 'Anggota usaha', icon: 'users' },
    { slug: 'profil', label: 'Profil', icon: 'profile' },
    { slug: 'pengaturan', label: 'Pengaturan', icon: 'settings' },
    { slug: 'notifikasi', label: 'Notifikasi', icon: 'notification' },
  ];

  const mobile = navigation.filter((item) =>
    ['', 'transaksi', 'foto-nota', 'laporan', 'pengaturan'].includes(item.slug),
  );

  function href(slug: string): string {
    return `/usaha/${businessId}${slug ? `/${slug}` : ''}`;
  }

  function active(slug: string): boolean {
    const target = href(slug);
    return slug
      ? page.url.pathname.startsWith(target)
      : page.url.pathname === target || page.url.pathname === `${target}/`;
  }
</script>

<div
  class="min-h-screen bg-[var(--surface-subtle)] text-[var(--text)] lg:grid lg:grid-cols-[17rem_minmax(0,1fr)]"
>
  <aside
    class="fixed inset-y-0 left-0 z-30 hidden w-68 border-r border-[var(--border)] bg-[var(--surface)] lg:flex lg:flex-col"
  >
    <a href="/" class="flex h-18 items-center gap-3 border-b border-[var(--border)] px-5">
      <span
        class="relative grid h-10 w-14 place-items-center overflow-hidden rounded-xl border border-[#eadfc8] bg-[#fff8e7]"
      >
        <img
          src="/images/kasta-logo.png"
          alt=""
          class="absolute left-1/2 top-1/2 w-[300%] max-w-none -translate-x-1/2 -translate-y-1/2"
        />
      </span>
      <span
        ><strong class="block text-lg leading-5">KASTA</strong><small
          class="text-[11px] text-[var(--text-muted)]">Ruang usaha</small
        ></span
      >
    </a>
    <nav class="flex-1 overflow-y-auto p-3" aria-label="Menu UMKM">
      {#each navigation as item (item.slug)}
        <a
          href={href(item.slug)}
          aria-current={active(item.slug) ? 'page' : undefined}
          class="mb-1 flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-bold transition {active(
            item.slug,
          )
            ? 'bg-kasta-100 text-kasta-900 dark:bg-kasta-950 dark:text-kasta-100'
            : 'text-[var(--text-muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--text)]'}"
          ><Icon name={item.icon} />{item.label}</a
        >
      {/each}
    </nav>
    <div class="border-t border-[var(--border)] p-4 text-xs text-[var(--text-muted)]">
      Data usaha terlindungi dan dipisahkan per UMKM.
    </div>
  </aside>

  <div class="min-w-0 lg:col-start-2">
    <header
      class="sticky top-0 z-20 flex h-18 items-center justify-between border-b border-[var(--border)] bg-[color:var(--surface)]/95 px-4 backdrop-blur sm:px-6"
    >
      <div>
        <p class="text-xs font-bold text-[var(--text-muted)]">Usaha aktif</p>
        <p class="max-w-[13rem] truncate font-black sm:max-w-none">Usaha Saya</p>
      </div>
      <div class="flex items-center gap-2">
        <a
          href="/bantuan"
          class="hidden min-h-11 items-center rounded-xl px-3 text-sm font-bold text-[var(--text-muted)] hover:bg-[var(--surface-muted)] sm:flex"
          >Bantuan</a
        >
        <DarkModeToggle />
        <NotificationBell {businessId} />
        <a
          href={href('profil')}
          class="grid h-11 w-11 place-items-center rounded-xl bg-kasta-100 font-black text-kasta-900"
          aria-label="Buka profil usaha">US</a
        >
      </div>
    </header>

    <main id="main-content" class="mx-auto max-w-[1500px] px-4 py-6 pb-28 sm:px-6 lg:pb-8">
      {@render children()}
    </main>
  </div>

  <nav
    class="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-[var(--border)] bg-[color:var(--surface)]/98 px-1 pb-[max(.35rem,env(safe-area-inset-bottom))] pt-1 backdrop-blur lg:hidden"
    aria-label="Menu utama seluler"
  >
    {#each mobile as item (item.slug)}
      <a
        href={href(item.slug)}
        aria-current={active(item.slug) ? 'page' : undefined}
        class="flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-[10px] font-extrabold {active(
          item.slug,
        )
          ? 'text-kasta-700 dark:text-kasta-300'
          : 'text-[var(--text-muted)]'}"
      >
        <Icon name={item.icon} size={21} />{item.slug === 'pengaturan' ? 'Lainnya' : item.label}
      </a>
    {/each}
  </nav>
</div>

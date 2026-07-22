<script lang="ts">
  import type {
    BusinessCategory,
    BusinessProfile,
    BusinessScale,
    BusinessType,
  } from '@kasta/contracts';
  import { resolve } from '$app/paths';
  import { onMount } from 'svelte';

  import {
    getBusinessLogo,
    getBusinessCategories,
    getBusinessProfile,
    updateBusinessProfile,
    uploadBusinessLogo,
  } from '$lib/api/onboarding';
  import { authSession } from '$lib/stores/auth-session';

  let { data }: { data: { businessId: string } } = $props();
  let profile = $state<BusinessProfile | null>(null);
  let loading = $state(true);
  let editing = $state(false);
  let errorMessage = $state('');
  let notice = $state('');
  let logoUrl = $state<string | null>(null);
  let categories = $state<BusinessCategory[]>([]);
  let name = $state('');
  let businessType = $state<BusinessType>('TRADE');
  let categoryId = $state('');
  let scale = $state<BusinessScale>('MICRO');
  let establishedYear = $state<number | undefined>();
  let address = $state('');
  let village = $state('');
  let district = $state('');
  let city = $state('');
  let province = $state('');
  let phone = $state('');
  let email = $state('');
  let employeeCount = $state(0);
  let currency = $state<'IDR' | 'USD' | 'SGD' | 'MYR'>('IDR');
  let timezone = $state<'Asia/Jakarta' | 'Asia/Makassar' | 'Asia/Jayapura'>('Asia/Jakarta');
  let recordingMethod = $state<'CASH' | 'ACCRUAL'>('CASH');
  let status = $state<'ACTIVE' | 'INACTIVE'>('ACTIVE');
  let hasProducts = $state(false);
  let filteredCategories = $derived(
    categories.filter((category) => category.business_type === businessType),
  );

  const scaleLabels = { MICRO: 'Mikro', SMALL: 'Kecil', MEDIUM: 'Menengah' } as const;

  onMount(() => {
    void loadProfile();
    return () => {
      if (logoUrl) URL.revokeObjectURL(logoUrl);
    };
  });

  async function loadProfile(): Promise<void> {
    const session = $authSession;
    if (!session || session.businessId !== data.businessId) {
      loading = false;
      return;
    }
    try {
      [profile, categories] = await Promise.all([
        getBusinessProfile(data.businessId, session.accessToken),
        getBusinessCategories(),
      ]);
      syncForm();
      if (profile.logo_path) logoUrl = await getBusinessLogo(data.businessId, session.accessToken);
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Profil belum dapat dimuat.';
    } finally {
      loading = false;
    }
  }

  function syncForm(): void {
    if (!profile) return;
    name = profile.name;
    businessType = profile.business_type;
    categoryId = profile.category_id;
    scale = profile.scale;
    establishedYear = profile.established_year ?? undefined;
    address = profile.address ?? '';
    village = profile.village ?? '';
    district = profile.district ?? '';
    city = profile.city;
    province = profile.province;
    phone = profile.phone ?? '';
    email = profile.email ?? '';
    employeeCount = profile.employee_count;
    currency = profile.currency;
    timezone = profile.timezone;
    recordingMethod = profile.recording_method;
    status = profile.status;
    hasProducts = profile.has_products_and_stock;
  }

  function chooseBusinessType(value: BusinessType): void {
    businessType = value;
    categoryId = '';
  }

  async function saveProfile(): Promise<void> {
    if (!$authSession || !profile) return;
    errorMessage = '';
    try {
      profile = await updateBusinessProfile(data.businessId, $authSession.accessToken, {
        name,
        business_type: businessType,
        category_id: categoryId,
        scale,
        established_year: establishedYear ?? null,
        address: address || null,
        village: village || null,
        district: district || null,
        city,
        province,
        phone: phone || null,
        email: email || null,
        employee_count: employeeCount,
        currency,
        timezone,
        recording_method: recordingMethod,
        status,
        has_products_and_stock: hasProducts,
      });
      editing = false;
      notice = 'Profil usaha berhasil diperbarui.';
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Profil belum dapat disimpan.';
    }
  }

  async function changeLogo(event: Event): Promise<void> {
    const file = (event.currentTarget as HTMLInputElement).files?.[0];
    if (!file || !$authSession) return;
    errorMessage = '';
    try {
      profile = await uploadBusinessLogo(data.businessId, $authSession.accessToken, file);
      if (logoUrl) URL.revokeObjectURL(logoUrl);
      logoUrl = await getBusinessLogo(data.businessId, $authSession.accessToken);
      notice = 'Logo usaha berhasil diperbarui.';
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Logo belum dapat disimpan.';
    }
  }
</script>

<svelte:head><title>Profil Usaha — KASTA</title></svelte:head>

<section class="text-slate-900 dark:text-slate-100">
  <header class="border-b border-slate-200 bg-white">
    <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
      <a href={resolve('/')} class="text-2xl font-black text-emerald-950">KASTA</a>
      <div class="flex items-center gap-3">
        <a
          href={resolve('/usaha/[businessId]/transaksi', { businessId: data.businessId })}
          class="rounded-full bg-emerald-700 px-4 py-2 text-sm font-bold text-white"
          >Catat transaksi</a
        >
        <span class="rounded-full bg-emerald-50 px-4 py-2 text-sm font-bold text-emerald-800"
          >Profil Usaha</span
        >
      </div>
    </div>
  </header>

  <div class="mx-auto max-w-5xl px-6 py-10">
    {#if loading}
      <p class="text-slate-500">Memuat profil usaha…</p>
    {:else if !$authSession}
      <section class="rounded-3xl border border-amber-200 bg-amber-50 p-8 text-center">
        <h1 class="text-2xl font-black text-slate-900">Sesi Anda sudah berakhir</h1>
        <p class="mt-3 text-slate-600">Masuk kembali untuk melihat profil usaha.</p>
        <a
          href={resolve('/onboarding')}
          class="mt-6 inline-block rounded-2xl bg-emerald-700 px-6 py-3 font-bold text-white"
          >Kembali ke awal</a
        >
      </section>
    {:else if profile}
      {#if notice}<p class="mb-6 rounded-2xl bg-emerald-50 p-4 text-emerald-800">{notice}</p>{/if}
      {#if errorMessage}<p role="alert" class="mb-6 rounded-2xl bg-rose-50 p-4 text-rose-700">
          {errorMessage}
        </p>{/if}
      <section class="rounded-[2rem] border border-slate-200 bg-white p-7 shadow-sm sm:p-10">
        <div class="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex items-center gap-5">
            <div class="grid h-24 w-24 overflow-hidden rounded-3xl bg-emerald-100 text-3xl">
              {#if logoUrl}<img
                  class="h-full w-full object-cover"
                  src={logoUrl}
                  alt={`Logo ${profile.name}`}
                />{:else}<span class="m-auto">🏪</span>{/if}
            </div>
            <div>
              <p class="text-sm font-bold text-emerald-700">
                {profile.status === 'ACTIVE' ? 'Usaha aktif' : 'Usaha tidak aktif'}
              </p>
              <h1 class="mt-1 text-3xl font-black text-slate-950">{profile.name}</h1>
              <p class="mt-1 text-slate-500">
                {profile.category_name} · {scaleLabels[profile.scale]}
              </p>
            </div>
          </div>
          <div class="flex flex-wrap gap-2">
            <a
              class="rounded-2xl bg-emerald-100 px-5 py-3 font-bold text-emerald-800"
              href={`/usaha/${data.businessId}/akses-pembina`}>Akses pembina</a
            >
            <button
              class="rounded-2xl bg-slate-900 px-5 py-3 font-bold text-white"
              onclick={() => (editing = !editing)}
              >{editing ? 'Batal mengubah' : 'Ubah profil'}</button
            >
          </div>
        </div>

        <label
          class="mt-6 inline-flex cursor-pointer items-center gap-2 text-sm font-bold text-emerald-700"
          >Ganti logo<input
            class="sr-only"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onchange={(event) => void changeLogo(event)}
          /></label
        >

        {#if editing}
          <div class="mt-8 grid gap-5 border-t border-slate-100 pt-8 sm:grid-cols-2">
            <label class="sm:col-span-2">Nama usaha<input bind:value={name} /></label>
            <label
              >Jenis usaha<select
                value={businessType}
                onchange={(event) =>
                  chooseBusinessType(
                    (event.currentTarget as HTMLSelectElement).value as BusinessType,
                  )}
                ><option value="TRADE">Jual beli</option><option value="CULINARY"
                  >Makanan & minuman</option
                ><option value="SERVICE">Jasa</option><option value="PRODUCTION">Produksi</option
                ><option value="CREATIVE">Kreatif</option><option value="AGRICULTURE"
                  >Tani & ternak</option
                ><option value="OTHER">Lainnya</option></select
              ></label
            >
            <label
              >Kategori usaha<select bind:value={categoryId}
                ><option value="">Pilih kategori</option
                >{#each filteredCategories as category (category.id)}<option value={category.id}
                    >{category.name}</option
                  >{/each}</select
              ></label
            >
            <label
              >Skala usaha<select bind:value={scale}
                ><option value="MICRO">Mikro</option><option value="SMALL">Kecil</option><option
                  value="MEDIUM">Menengah</option
                ></select
              ></label
            >
            <label
              >Tahun berdiri<input
                bind:value={establishedYear}
                type="number"
                min="1800"
                max="9999"
              /></label
            >
            <label class="sm:col-span-2">Alamat<input bind:value={address} /></label>
            <label>Kelurahan/desa<input bind:value={village} /></label><label
              >Kecamatan<input bind:value={district} /></label
            >
            <label>Kota/kabupaten<input bind:value={city} /></label><label
              >Provinsi<input bind:value={province} /></label
            >
            <label>Telepon usaha<input bind:value={phone} /></label><label
              >Email usaha<input bind:value={email} type="email" /></label
            >
            <label>Jumlah pegawai<input bind:value={employeeCount} type="number" min="0" /></label>
            <label
              >Mata uang<select bind:value={currency}
                ><option value="IDR">Rupiah (IDR)</option><option value="USD">Dolar AS (USD)</option
                ><option value="SGD">Dolar Singapura (SGD)</option><option value="MYR"
                  >Ringgit (MYR)</option
                ></select
              ></label
            >
            <label
              >Zona waktu<select bind:value={timezone}
                ><option value="Asia/Jakarta">WIB</option><option value="Asia/Makassar">WITA</option
                ><option value="Asia/Jayapura">WIT</option></select
              ></label
            >
            <label
              >Kapan catatan dibuat?<select bind:value={recordingMethod}
                ><option value="CASH">Saat uang diterima atau dibayar</option><option
                  value="ACCRUAL">Saat jual beli terjadi</option
                ></select
              ></label
            >
            <label
              >Status usaha<select bind:value={status}
                ><option value="ACTIVE">Aktif</option><option value="INACTIVE">Tidak aktif</option
                ></select
              ></label
            >
            <label class="check-card sm:col-span-2"
              ><input type="checkbox" bind:checked={hasProducts} /><span
                >Usaha menggunakan produk dan stok</span
              ></label
            >
            <div class="sm:col-span-2">
              <button
                class="rounded-2xl bg-emerald-700 px-6 py-3 font-bold text-white"
                onclick={() => void saveProfile()}>Simpan perubahan</button
              >
            </div>
          </div>
        {:else}
          <dl class="mt-9 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div class="info">
              <dt>Status</dt>
              <dd>{profile.status === 'ACTIVE' ? 'Aktif' : 'Tidak aktif'}</dd>
            </div>
            <div class="info">
              <dt>Tahun berdiri</dt>
              <dd>{profile.established_year ?? 'Belum diisi'}</dd>
            </div>
            <div class="info">
              <dt>Lokasi</dt>
              <dd>
                {[
                  profile.address,
                  profile.village,
                  profile.district,
                  profile.city,
                  profile.province,
                ]
                  .filter(Boolean)
                  .join(', ')}
              </dd>
            </div>
            <div class="info">
              <dt>Kontak</dt>
              <dd>{[profile.phone, profile.email].filter(Boolean).join(' · ') || 'Belum diisi'}</dd>
            </div>
            <div class="info">
              <dt>Jumlah pegawai</dt>
              <dd>{profile.employee_count} orang</dd>
            </div>
            <div class="info">
              <dt>Cara pembayaran</dt>
              <dd>
                {profile.payment_methods
                  .map((method) =>
                    method === 'CASH'
                      ? 'Tunai'
                      : method === 'BANK_TRANSFER'
                        ? 'Transfer bank'
                        : method === 'E_WALLET'
                          ? 'Dompet digital'
                          : method === 'CARD'
                            ? 'Kartu'
                            : method,
                  )
                  .join(', ')}
              </dd>
            </div>
            <div class="info">
              <dt>Mata uang</dt>
              <dd>{profile.currency}</dd>
            </div>
            <div class="info">
              <dt>Waktu usaha</dt>
              <dd>
                {profile.timezone === 'Asia/Jakarta'
                  ? 'WIB'
                  : profile.timezone === 'Asia/Makassar'
                    ? 'WITA'
                    : 'WIT'}
              </dd>
            </div>
            <div class="info">
              <dt>Cara mencatat</dt>
              <dd>
                {profile.recording_method === 'CASH'
                  ? 'Saat uang berpindah'
                  : 'Saat transaksi terjadi'}
              </dd>
            </div>
            <div class="info">
              <dt>Produk dan stok</dt>
              <dd>{profile.has_products_and_stock ? 'Digunakan' : 'Belum digunakan'}</dd>
            </div>
            <div class="info sm:col-span-2 lg:col-span-3">
              <dt>Saldo awal</dt>
              <dd class="text-xl">
                {new Intl.NumberFormat('id-ID', {
                  style: 'currency',
                  currency: profile.currency,
                }).format(Number(profile.opening_balance))}
              </dd>
            </div>
          </dl>
        {/if}
      </section>
    {/if}
  </div>
</section>

<style>
  label {
    color: #334155;
    font-size: 0.875rem;
    font-weight: 700;
  }
  input,
  select {
    margin-top: 0.45rem;
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 0.85rem;
    padding: 0.75rem 0.9rem;
    outline: none;
  }
  input:focus,
  select:focus {
    border-color: #059669;
    box-shadow: 0 0 0 3px #d1fae5;
  }
  .check-card {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    border: 1px solid #cbd5e1;
    border-radius: 0.9rem;
    padding: 0.8rem 1rem;
  }
  .check-card input {
    margin: 0;
    width: 1.1rem;
    accent-color: #047857;
  }
  .info {
    border-radius: 1rem;
    background: #f8fafc;
    padding: 1rem;
  }
  .info dt {
    color: #64748b;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .info dd {
    margin-top: 0.35rem;
    color: #0f172a;
    font-weight: 800;
  }
</style>

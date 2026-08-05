<script lang="ts">
  import type {
    BusinessCategory,
    BusinessScale,
    BusinessType,
    PaymentMethodCode,
  } from '@kasta/contracts';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { onMount } from 'svelte';
  import { z } from 'zod';

  import ProgressIndicator from '$lib/components/ProgressIndicator.svelte';
  import {
    completeOnboarding,
    createAccount,
    getBusinessCategories,
    requestVerification,
    uploadBusinessLogo,
    verifyAccount,
  } from '$lib/api/onboarding';
  import { businessScales, businessTypes, paymentOptions } from '$lib/onboarding/options';
  import { authSession } from '$lib/stores/auth-session';

  const TOTAL_STEPS = 9;
  const requiredText = z.string().trim().min(2, 'Isi paling sedikit 2 huruf.');
  const deviceId = `web-${crypto.randomUUID()}`;

  let step = $state(1);
  let busy = $state(false);
  let errorMessage = $state('');
  let notice = $state('');
  let accountType = $state<'email' | 'phone'>('email');
  let fullName = $state('');
  let identifier = $state('');
  let password = $state('');
  let verificationToken = $state('');
  let onboardingToken = $state('');
  let categories = $state<BusinessCategory[]>([]);
  let logo = $state<File | null>(null);
  let businessName = $state('');
  let businessType = $state<BusinessType>('TRADE');
  let categoryId = $state('');
  let scale = $state<BusinessScale>('MICRO');
  let establishedYear = $state<number | undefined>();
  let employeeCount = $state(0);
  let address = $state('');
  let village = $state('');
  let district = $state('');
  let city = $state('');
  let province = $state('');
  let businessPhone = $state('');
  let businessEmail = $state('');
  let currency = $state<'IDR' | 'USD' | 'SGD' | 'MYR'>('IDR');
  let timezone = $state<'Asia/Jakarta' | 'Asia/Makassar' | 'Asia/Jayapura'>('Asia/Jakarta');
  let recordingMethod = $state<'CASH' | 'ACCRUAL'>('CASH');
  let paymentMethods = $state<PaymentMethodCode[]>(['CASH']);
  let openingBalance = $state(0);
  let hasProducts = $state(false);
  let tutorialDone = $state(false);
  let filteredCategories = $derived(
    categories.filter((category) => category.business_type === businessType),
  );

  onMount(async () => {
    try {
      categories = await getBusinessCategories();
    } catch {
      notice = 'Daftar kategori belum dapat dimuat. Coba lagi sebentar.';
    }
  });

  function firstIssue(result: z.SafeParseReturnType<unknown, unknown>): string {
    return result.success ? '' : (result.error.issues[0]?.message ?? 'Periksa kembali data Anda.');
  }

  function nextStep(): void {
    errorMessage = '';
    if (step === 3) step = 4;
    else if (step === 4) {
      const result = z
        .object({
          businessName: requiredText,
          categoryId: z.string().uuid('Pilih kategori usaha.'),
        })
        .safeParse({ businessName, categoryId });
      errorMessage = firstIssue(result);
      if (!result.success) return;
      step = 5;
    } else if (step === 5) step = 6;
    else if (step === 6) {
      const result = z
        .object({ city: requiredText, province: requiredText })
        .safeParse({ city, province });
      errorMessage = firstIssue(result);
      if (!result.success) return;
      step = 7;
    } else if (step === 7) {
      if (paymentMethods.length === 0) {
        errorMessage = 'Pilih sedikitnya satu cara menerima pembayaran.';
        return;
      }
      step = 8;
    } else if (step === 8) step = 9;
  }

  function previousStep(): void {
    errorMessage = '';
    if (step > 1) step -= 1;
  }

  async function submitAccount(): Promise<void> {
    const identifierSchema =
      accountType === 'email'
        ? z.string().email('Masukkan alamat email yang benar.')
        : z.string().min(8, 'Masukkan nomor telepon yang benar.');
    const result = z
      .object({
        fullName: requiredText,
        identifier: identifierSchema,
        password: z.string().min(12),
      })
      .safeParse({ fullName, identifier, password });
    errorMessage =
      firstIssue(result) || (password.length < 12 ? 'Password minimal 12 karakter.' : '');
    if (!result.success || errorMessage) return;
    busy = true;
    try {
      await createAccount({
        full_name: fullName,
        password,
        ...(accountType === 'email' ? { email: identifier } : { phone: identifier }),
      });
      notice = `Petunjuk verifikasi dikirim ke ${identifier}.`;
      step = 2;
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Akun belum dapat dibuat.';
    } finally {
      busy = false;
    }
  }

  async function submitVerification(): Promise<void> {
    if (verificationToken.trim().length < 20) {
      errorMessage = 'Masukkan kode verifikasi dari email atau SMS.';
      return;
    }
    busy = true;
    errorMessage = '';
    try {
      const response = await verifyAccount(verificationToken.trim());
      onboardingToken = response.onboarding_token;
      notice = 'Akun sudah terverifikasi.';
      step = 3;
    } catch (error) {
      errorMessage =
        error instanceof Error ? error.message : 'Kode verifikasi tidak dapat digunakan.';
    } finally {
      busy = false;
    }
  }

  async function resendVerification(): Promise<void> {
    if (!identifier.trim()) {
      errorMessage = 'Kembali ke langkah pendaftaran dan masukkan email atau nomor telepon.';
      return;
    }
    busy = true;
    errorMessage = '';
    try {
      const response = await requestVerification(identifier.trim());
      notice = response.message || `Kode verifikasi dikirim ulang ke ${identifier.trim()}.`;
    } catch (error) {
      errorMessage =
        error instanceof Error ? error.message : 'Kode verifikasi belum dapat dikirim ulang.';
    } finally {
      busy = false;
    }
  }

  function chooseBusinessType(value: BusinessType): void {
    businessType = value;
    categoryId = '';
  }

  function togglePayment(value: PaymentMethodCode): void {
    paymentMethods = paymentMethods.includes(value)
      ? paymentMethods.filter((method) => method !== value)
      : [...paymentMethods, value];
  }

  function pickLogo(event: Event): void {
    const input = event.currentTarget as HTMLInputElement;
    logo = input.files?.[0] ?? null;
  }

  async function finishOnboarding(): Promise<void> {
    if (!tutorialDone) {
      errorMessage = 'Tandai bahwa tutorial singkat sudah dipahami.';
      return;
    }
    busy = true;
    errorMessage = '';
    try {
      const result = await completeOnboarding(
        {
          role_selection: 'BUSINESS_OWNER',
          business_name: businessName,
          business_type: businessType,
          category_id: categoryId,
          scale,
          established_year: establishedYear || null,
          address: address || null,
          village: village || null,
          district: district || null,
          city,
          province,
          phone: businessPhone || null,
          email: businessEmail || null,
          employee_count: employeeCount,
          currency,
          timezone,
          recording_method: recordingMethod,
          payment_methods: paymentMethods,
          opening_balance: openingBalance.toFixed(2),
          has_products_and_stock: hasProducts,
          tutorial_completed: true,
          device: {
            device_id: deviceId,
            platform: 'WEB',
            device_name: navigator.userAgent.slice(0, 100),
            app_version: '0.1.0',
          },
        },
        onboardingToken,
      );
      authSession.set({
        accessToken: result.tokens.access_token,
        refreshToken: result.tokens.refresh_token,
        businessId: result.business_id,
      });
      if (logo) {
        await uploadBusinessLogo(result.business_id, result.tokens.access_token, logo);
      }
      await goto(resolve('/usaha/[businessId]/profil', { businessId: result.business_id }));
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Data usaha belum dapat disimpan.';
    } finally {
      busy = false;
    }
  }
</script>

<svelte:head>
  <title>Mulai menggunakan KASTA</title>
  <meta name="description" content="Siapkan akun dan profil usaha KASTA." />
</svelte:head>

<main class="min-h-screen bg-emerald-50/60 px-4 py-8 sm:px-6 sm:py-12">
  <div class="mx-auto max-w-3xl">
    <a href={resolve('/')} class="mb-7 inline-flex text-xl font-black text-emerald-950">KASTA</a>
    <section
      class="overflow-hidden rounded-[2rem] border border-emerald-100 bg-white shadow-xl shadow-emerald-100/60"
    >
      <div class="border-b border-slate-100 px-6 py-6 sm:px-10">
        <ProgressIndicator current={step} total={TOTAL_STEPS} />
      </div>

      <div class="p-6 sm:p-10">
        {#if notice}
          <p class="mb-6 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{notice}</p>
        {/if}
        {#if errorMessage}
          <p
            role="alert"
            class="mb-6 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700"
          >
            {errorMessage}
          </p>
        {/if}

        {#if step === 1}
          <form
            onsubmit={(event) => {
              event.preventDefault();
              void submitAccount();
            }}
          >
            <p class="eyebrow">Selamat datang</p>
            <h1 class="title">Buat akun KASTA</h1>
            <p class="subtitle">Gunakan email atau nomor telepon yang aktif.</p>
            <div class="mt-7 grid grid-cols-2 gap-2 rounded-2xl bg-slate-100 p-1">
              <button
                type="button"
                class:choice-active={accountType === 'email'}
                class="choice-tab"
                onclick={() => (accountType = 'email')}>Email</button
              >
              <button
                type="button"
                class:choice-active={accountType === 'phone'}
                class="choice-tab"
                onclick={() => (accountType = 'phone')}>Nomor telepon</button
              >
            </div>
            <div class="form-grid mt-6">
              <label
                >Nama lengkap<input
                  bind:value={fullName}
                  autocomplete="name"
                  placeholder="Contoh: Sari Wulandari"
                /></label
              >
              <label
                >{accountType === 'email' ? 'Email' : 'Nomor telepon'}<input
                  bind:value={identifier}
                  autocomplete={accountType === 'email' ? 'email' : 'tel'}
                  placeholder={accountType === 'email' ? 'sari@email.com' : '0812 3456 7890'}
                /></label
              >
              <label
                >Password<input
                  bind:value={password}
                  type="password"
                  autocomplete="new-password"
                  placeholder="Minimal 12 karakter"
                /></label
              >
            </div>
            <button class="primary-button mt-8" disabled={busy}
              >{busy ? 'Membuat akun…' : 'Buat akun'}</button
            >
          </form>
        {:else if step === 2}
          <form
            onsubmit={(event) => {
              event.preventDefault();
              void submitVerification();
            }}
          >
            <p class="eyebrow">Periksa pesan Anda</p>
            <h1 class="title">Verifikasi akun</h1>
            <p class="subtitle">Buka pesan dari KASTA, lalu tempel kode verifikasinya di bawah.</p>
            <label class="mt-7 block"
              >Kode verifikasi<textarea
                bind:value={verificationToken}
                rows="3"
                placeholder="Tempel kode verifikasi"
              ></textarea></label
            >
            <button class="primary-button mt-8" disabled={busy}
              >{busy ? 'Memeriksa…' : 'Verifikasi akun'}</button
            >
            <button
              type="button"
              class="mt-4 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700"
              disabled={busy}
              onclick={() => void resendVerification()}
            >
              {busy ? 'Mengirim…' : 'Kirim ulang kode verifikasi'}
            </button>
          </form>
        {:else if step === 3}
          <p class="eyebrow">Peran Anda</p>
          <h1 class="title">Bagaimana Anda menggunakan KASTA?</h1>
          <button
            type="button"
            class="mt-8 flex w-full items-center gap-5 rounded-3xl border-2 border-emerald-600 bg-emerald-50 p-6 text-left"
            onclick={nextStep}
          >
            <span
              class="grid h-14 w-14 place-items-center rounded-2xl bg-emerald-700 text-2xl text-white"
              >🏪</span
            >
            <span
              ><strong class="block text-lg text-slate-950">Saya Pemilik UMKM</strong><span
                class="mt-1 block text-slate-600"
                >Saya ingin mencatat dan melihat perkembangan usaha.</span
              ></span
            >
          </button>
        {:else if step === 4}
          <p class="eyebrow">Tentang usaha</p>
          <h1 class="title">Ceritakan usaha Anda</h1>
          <div class="form-grid mt-7">
            <label
              >Nama usaha<input bind:value={businessName} placeholder="Contoh: Dapur Sari" /></label
            >
            <fieldset>
              <legend>Jenis usaha</legend>
              <div class="option-grid">
                {#each businessTypes as option (option.value)}<button
                    type="button"
                    class:option-active={businessType === option.value}
                    class="option-card"
                    onclick={() => chooseBusinessType(option.value)}
                    ><strong>{option.label}</strong><small>{option.hint}</small></button
                  >{/each}
              </div>
            </fieldset>
            <label
              >Kategori usaha<select bind:value={categoryId}
                ><option value="">Pilih kategori</option
                >{#each filteredCategories as category (category.id)}<option value={category.id}
                    >{category.name}</option
                  >{/each}</select
              ></label
            >
          </div>
        {:else if step === 5}
          <p class="eyebrow">Ukuran usaha</p>
          <h1 class="title">Seperti apa usaha Anda sekarang?</h1>
          <fieldset class="mt-7">
            <legend>Skala usaha</legend>
            <div class="option-grid sm:grid-cols-3">
              {#each businessScales as option (option.value)}<button
                  type="button"
                  class:option-active={scale === option.value}
                  class="option-card"
                  onclick={() => (scale = option.value)}
                  ><strong>{option.label}</strong><small>{option.hint}</small></button
                >{/each}
            </div>
          </fieldset>
          <div class="mt-6 grid gap-5 sm:grid-cols-2">
            <label
              >Tahun berdiri<input
                bind:value={establishedYear}
                type="number"
                min="1800"
                max="9999"
                placeholder="2024"
              /></label
            >
            <label>Jumlah pegawai<input bind:value={employeeCount} type="number" min="0" /></label>
            <label class="sm:col-span-2"
              >Logo usaha <span class="label-note">(boleh nanti)</span><input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onchange={pickLogo}
              /></label
            >
          </div>
        {:else if step === 6}
          <p class="eyebrow">Lokasi usaha</p>
          <h1 class="title">Di mana usaha Anda berjalan?</h1>
          <p class="subtitle">Alamat umum sudah cukup. Tidak perlu menuliskan patokan pribadi.</p>
          <div class="mt-7 grid gap-5 sm:grid-cols-2">
            <label class="sm:col-span-2"
              >Alamat<input bind:value={address} placeholder="Nama jalan atau area usaha" /></label
            >
            <label>Kelurahan/desa<input bind:value={village} /></label><label
              >Kecamatan<input bind:value={district} /></label
            >
            <label>Kota/kabupaten<input bind:value={city} /></label><label
              >Provinsi<input bind:value={province} /></label
            >
            <label>Telepon usaha<input bind:value={businessPhone} placeholder="Opsional" /></label
            ><label
              >Email usaha<input
                bind:value={businessEmail}
                type="email"
                placeholder="Opsional"
              /></label
            >
          </div>
        {:else if step === 7}
          <p class="eyebrow">Pengaturan harian</p>
          <h1 class="title">Sesuaikan dengan cara usaha Anda</h1>
          <div class="mt-7 grid gap-5 sm:grid-cols-2">
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
            <label class="sm:col-span-2"
              >Kapan catatan dibuat?<select bind:value={recordingMethod}
                ><option value="CASH">Saat uang diterima atau dibayar</option><option
                  value="ACCRUAL">Saat penjualan atau pembelian terjadi</option
                ></select
              ></label
            >
          </div>
          <fieldset class="mt-7">
            <legend>Cara menerima pembayaran</legend>
            <div class="grid gap-3 sm:grid-cols-2">
              {#each paymentOptions as option (option.value)}<label class="check-card"
                  ><input
                    type="checkbox"
                    checked={paymentMethods.includes(option.value)}
                    onchange={() => togglePayment(option.value)}
                  /><span>{option.label}</span></label
                >{/each}
            </div>
          </fieldset>
        {:else if step === 8}
          <p class="eyebrow">Titik awal</p>
          <h1 class="title">Berapa uang usaha yang tersedia?</h1>
          <p class="subtitle">
            Isi jumlah yang benar-benar menjadi uang usaha saat ini. Boleh diisi 0.
          </p>
          <label class="mt-7 block"
            >Saldo awal
            <div class="money-input">
              <span>{currency}</span><input
                bind:value={openingBalance}
                type="number"
                min="0"
                step="0.01"
              />
            </div></label
          >
          <fieldset class="mt-7">
            <legend>Apakah usaha memiliki produk dan stok?</legend>
            <div class="grid grid-cols-2 gap-3">
              <button
                type="button"
                class:option-active={hasProducts}
                class="option-card"
                onclick={() => (hasProducts = true)}
                ><strong>Ya, ada</strong><small>KASTA akan menyiapkan menu produk</small></button
              ><button
                type="button"
                class:option-active={!hasProducts}
                class="option-card"
                onclick={() => (hasProducts = false)}
                ><strong>Belum/tidak</strong><small>Menu produk bisa diaktifkan nanti</small
                ></button
              >
            </div>
          </fieldset>
        {:else}
          <p class="eyebrow">Hampir selesai</p>
          <h1 class="title">Tiga hal penting di KASTA</h1>
          <div class="mt-7 space-y-3">
            <div class="tutorial-card">
              <span>1</span>
              <div>
                <strong>Catat uang setiap hari</strong>
                <p>Gunakan Uang Masuk dan Uang Keluar agar tidak ada yang terlupa.</p>
              </div>
            </div>
            <div class="tutorial-card">
              <span>2</span>
              <div>
                <strong>Foto nota bila ada</strong>
                <p>Nota membantu Anda mengecek kembali catatan.</p>
              </div>
            </div>
            <div class="tutorial-card">
              <span>3</span>
              <div>
                <strong>Lihat ringkasan secara rutin</strong>
                <p>KASTA akan membantu menunjukkan keadaan usaha dengan sederhana.</p>
              </div>
            </div>
          </div>
          <label class="check-card mt-6"
            ><input type="checkbox" bind:checked={tutorialDone} /><span
              >Saya sudah memahami tutorial singkat ini.</span
            ></label
          >
        {/if}

        {#if step >= 3}
          <div class="mt-9 flex items-center justify-between gap-3 border-t border-slate-100 pt-6">
            <button type="button" class="secondary-button" onclick={previousStep}>Kembali</button>
            {#if step !== 3 && step < TOTAL_STEPS}<button
                type="button"
                class="primary-button max-w-48"
                onclick={nextStep}>Lanjut</button
              >{/if}
            {#if step === TOTAL_STEPS}<button
                type="button"
                class="primary-button max-w-56"
                disabled={busy}
                onclick={() => void finishOnboarding()}
                >{busy ? 'Menyiapkan usaha…' : 'Selesaikan pengaturan'}</button
              >{/if}
          </div>
        {/if}
      </div>
    </section>
    <p class="mt-6 text-center text-xs leading-5 text-slate-500">
      Data Anda digunakan untuk menyiapkan KASTA dan tidak ditampilkan kepada pengguna lain tanpa
      izin.
    </p>
  </div>
</main>

<style>
  :global(label),
  fieldset {
    color: #334155;
    font-size: 0.9rem;
    font-weight: 700;
  }
  :global(input:not([type='checkbox']):not([type='file'])),
  :global(select),
  :global(textarea) {
    margin-top: 0.5rem;
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 0.9rem;
    background: white;
    padding: 0.8rem 1rem;
    color: #0f172a;
    font-weight: 500;
    outline: none;
  }
  :global(input:focus),
  :global(select:focus),
  :global(textarea:focus) {
    border-color: #059669;
    box-shadow: 0 0 0 3px #d1fae5;
  }
  :global(input[type='file']) {
    margin-top: 0.6rem;
    display: block;
    width: 100%;
    border: 1px dashed #94a3b8;
    border-radius: 0.9rem;
    padding: 0.8rem;
    font-weight: 500;
  }
  legend {
    margin-bottom: 0.65rem;
  }
  .eyebrow {
    color: #047857;
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }
  .title {
    margin-top: 0.45rem;
    color: #0f172a;
    font-size: clamp(1.75rem, 5vw, 2.4rem);
    font-weight: 900;
    line-height: 1.15;
    letter-spacing: -0.025em;
  }
  .subtitle {
    margin-top: 0.75rem;
    color: #64748b;
    line-height: 1.65;
  }
  .form-grid {
    display: grid;
    gap: 1.25rem;
  }
  .choice-tab {
    border-radius: 0.75rem;
    padding: 0.65rem;
    color: #64748b;
    font-weight: 700;
  }
  .choice-active {
    background: white;
    color: #065f46;
    box-shadow: 0 1px 4px #cbd5e1;
  }
  .primary-button {
    width: 100%;
    border-radius: 1rem;
    background: #047857;
    padding: 0.9rem 1.25rem;
    color: white;
    font-weight: 800;
    transition: 0.2s;
  }
  .primary-button:hover {
    background: #065f46;
  }
  .primary-button:disabled {
    cursor: wait;
    opacity: 0.6;
  }
  .secondary-button {
    border-radius: 1rem;
    padding: 0.85rem 1.1rem;
    color: #475569;
    font-weight: 800;
  }
  .option-grid {
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .option-card {
    display: flex;
    min-height: 5.5rem;
    flex-direction: column;
    align-items: flex-start;
    border: 1px solid #cbd5e1;
    border-radius: 1rem;
    padding: 0.9rem;
    text-align: left;
  }
  .option-card strong {
    color: #0f172a;
  }
  .option-card small {
    margin-top: 0.25rem;
    color: #64748b;
    font-weight: 500;
    line-height: 1.35;
  }
  .option-active {
    border-color: #059669;
    background: #ecfdf5;
    box-shadow: 0 0 0 1px #059669;
  }
  .check-card {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    border: 1px solid #cbd5e1;
    border-radius: 1rem;
    padding: 0.9rem 1rem;
  }
  .check-card input {
    width: 1.1rem;
    height: 1.1rem;
    accent-color: #047857;
  }
  .money-input {
    margin-top: 0.5rem;
    display: flex;
    align-items: center;
    border: 1px solid #cbd5e1;
    border-radius: 1rem;
    overflow: hidden;
  }
  .money-input span {
    padding-left: 1rem;
    color: #047857;
    font-weight: 900;
  }
  .money-input input {
    margin: 0 !important;
    border: 0 !important;
    box-shadow: none !important;
    font-size: 1.2rem;
  }
  .tutorial-card {
    display: flex;
    gap: 1rem;
    border-radius: 1.1rem;
    background: #f8fafc;
    padding: 1rem;
  }
  .tutorial-card > span {
    display: grid;
    width: 2rem;
    height: 2rem;
    flex: none;
    place-items: center;
    border-radius: 999px;
    background: #d1fae5;
    color: #047857;
    font-weight: 900;
  }
  .tutorial-card strong {
    color: #0f172a;
  }
  .tutorial-card p {
    margin-top: 0.25rem;
    color: #64748b;
    font-size: 0.875rem;
    line-height: 1.5;
  }
  .label-note {
    color: #94a3b8;
    font-weight: 500;
  }
  @media (max-width: 520px) {
    .option-grid {
      grid-template-columns: 1fr;
    }
  }
</style>

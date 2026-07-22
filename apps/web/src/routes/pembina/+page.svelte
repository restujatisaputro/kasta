<script lang="ts">
  import type {
    MentorAggregateReport,
    MentorAuditActivity,
    MentorBusinessDetail,
    MentorDashboard,
    MentorHealthLevel,
    MentoringSessionStatus,
    RecommendationStatus,
    ReportExportFormat,
  } from '@kasta/contracts';
  import { onMount, tick } from 'svelte';
  import { z } from 'zod';

  import {
    createMentoringSession,
    createMentorNote,
    createMentorRecommendation,
    exportMentorReport,
    getMentorAudit,
    getMentorBusiness,
    getMentorDashboard,
    getMentorReport,
    updateMentoringSession,
    updateMentorRecommendation,
  } from '$lib/api/mentors';
  import { formatRupiah } from '$lib/money/rupiah';
  import { authSession } from '$lib/stores/auth-session';
  import BrandLogo from '$lib/components/BrandLogo.svelte';

  const noteSchema = z.object({ content: z.string().trim().min(3).max(3000) });
  const recommendationSchema = z.object({
    title: z.string().trim().min(3).max(200),
    description: z.string().trim().min(3).max(3000),
  });
  const sessionSchema = z.object({
    topic: z.string().trim().min(3).max(300),
    scheduledAt: z.string().min(1),
  });

  let dashboard = $state<MentorDashboard | null>(null);
  let aggregate = $state<MentorAggregateReport | null>(null);
  let audit = $state<MentorAuditActivity[]>([]);
  let detail = $state<MentorBusinessDetail | null>(null);
  let selectedBusinessId = $state('');
  let search = $state('');
  let healthFilter = $state<MentorHealthLevel | 'ALL'>('ALL');
  let section = $state<'OVERVIEW' | 'NOTES' | 'RECOMMENDATIONS' | 'SESSIONS'>('OVERVIEW');
  let loading = $state(true);
  let detailLoading = $state(false);
  let saving = $state(false);
  let exporting = $state<ReportExportFormat | null>(null);
  let errorMessage = $state('');
  let successMessage = $state('');
  let trendElement = $state<HTMLDivElement>();
  let trendChart: { dispose: () => void; resize: () => void } | null = null;

  let noteContent = $state('');
  let noteVisibility = $state<'SHARED' | 'PRIVATE'>('SHARED');
  let recommendationTitle = $state('');
  let recommendationDescription = $state('');
  let recommendationPriority = $state<'LOW' | 'MEDIUM' | 'HIGH'>('MEDIUM');
  let recommendationDueDate = $state('');
  let sessionTopic = $state('');
  let sessionScheduledAt = $state('');
  let sessionDuration = $state(60);
  let sessionMode = $state<'ONSITE' | 'ONLINE' | 'PHONE'>('ONLINE');
  let sessionLocation = $state('');

  let filteredBusinesses = $derived(
    (dashboard?.businesses ?? []).filter((item) => {
      const location = `${item.city ?? ''} ${item.province ?? ''}`.toLowerCase();
      const query = search.trim().toLowerCase();
      return (
        (healthFilter === 'ALL' || item.health_level === healthFilter) &&
        (!query || item.business_name.toLowerCase().includes(query) || location.includes(query))
      );
    }),
  );

  onMount(() => {
    void loadWorkspace();
    const resize = () => trendChart?.resize();
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      trendChart?.dispose();
    };
  });

  async function loadWorkspace(): Promise<void> {
    if (!$authSession) {
      loading = false;
      return;
    }
    loading = true;
    errorMessage = '';
    try {
      [dashboard, aggregate, audit] = await Promise.all([
        getMentorDashboard($authSession.accessToken),
        getMentorReport($authSession.accessToken),
        getMentorAudit($authSession.accessToken),
      ]);
      const firstBusiness = dashboard.businesses[0];
      if (firstBusiness) await selectBusiness(firstBusiness.business_id);
    } catch (error) {
      errorMessage = message(error, 'Dashboard pembina belum dapat dimuat.');
    } finally {
      loading = false;
    }
  }

  async function selectBusiness(businessId: string): Promise<void> {
    if (!$authSession) return;
    selectedBusinessId = businessId;
    detailLoading = true;
    errorMessage = '';
    try {
      detail = await getMentorBusiness($authSession.accessToken, businessId);
      detailLoading = false;
      await tick();
      await drawTrend();
    } catch (error) {
      errorMessage = message(error, 'Detail UMKM belum dapat dimuat.');
    } finally {
      detailLoading = false;
    }
  }

  async function refreshSelected(): Promise<void> {
    if (!$authSession || !selectedBusinessId) return;
    [dashboard, aggregate, audit, detail] = await Promise.all([
      getMentorDashboard($authSession.accessToken),
      getMentorReport($authSession.accessToken),
      getMentorAudit($authSession.accessToken),
      getMentorBusiness($authSession.accessToken, selectedBusinessId),
    ]);
    await tick();
    await drawTrend();
  }

  async function submitNote(): Promise<void> {
    if (!$authSession || !selectedBusinessId) return;
    const parsed = noteSchema.safeParse({ content: noteContent });
    if (!parsed.success) {
      errorMessage = 'Catatan perlu berisi sedikitnya 3 karakter.';
      return;
    }
    await runSave(async () => {
      await createMentorNote($authSession!.accessToken, selectedBusinessId, {
        content: parsed.data.content,
        visibility: noteVisibility,
      });
      noteContent = '';
      successMessage =
        noteVisibility === 'SHARED'
          ? 'Catatan disimpan dan UMKM menerima notifikasi.'
          : 'Catatan pribadi disimpan.';
    });
  }

  async function submitRecommendation(): Promise<void> {
    if (!$authSession || !selectedBusinessId) return;
    const parsed = recommendationSchema.safeParse({
      title: recommendationTitle,
      description: recommendationDescription,
    });
    if (!parsed.success) {
      errorMessage = 'Judul dan isi rekomendasi perlu berisi sedikitnya 3 karakter.';
      return;
    }
    await runSave(async () => {
      await createMentorRecommendation($authSession!.accessToken, selectedBusinessId, {
        ...parsed.data,
        priority: recommendationPriority,
        due_date: recommendationDueDate || null,
      });
      recommendationTitle = '';
      recommendationDescription = '';
      recommendationDueDate = '';
      successMessage = 'Rekomendasi dikirim dan UMKM menerima notifikasi.';
    });
  }

  async function changeRecommendation(
    recommendationId: string,
    status: RecommendationStatus,
  ): Promise<void> {
    if (!$authSession || !selectedBusinessId) return;
    await runSave(async () => {
      await updateMentorRecommendation(
        $authSession!.accessToken,
        selectedBusinessId,
        recommendationId,
        {
          status,
          follow_up_note:
            status === 'DONE'
              ? 'Tindak lanjut telah dikonfirmasi melalui dashboard pembina.'
              : null,
        },
      );
      successMessage = status === 'DONE' ? 'Tindak lanjut ditandai selesai.' : 'Status diperbarui.';
    });
  }

  async function submitSession(): Promise<void> {
    if (!$authSession || !selectedBusinessId) return;
    const parsed = sessionSchema.safeParse({
      topic: sessionTopic,
      scheduledAt: sessionScheduledAt,
    });
    if (!parsed.success) {
      errorMessage = 'Isi topik dan waktu pertemuan terlebih dahulu.';
      return;
    }
    await runSave(async () => {
      await createMentoringSession($authSession!.accessToken, selectedBusinessId, {
        topic: parsed.data.topic,
        scheduled_at: new Date(parsed.data.scheduledAt).toISOString(),
        duration_minutes: sessionDuration,
        mode: sessionMode,
        location: sessionLocation.trim() || null,
      });
      sessionTopic = '';
      sessionScheduledAt = '';
      sessionLocation = '';
      successMessage = 'Jadwal disimpan dan UMKM menerima notifikasi.';
    });
  }

  async function changeSession(sessionId: string, status: MentoringSessionStatus): Promise<void> {
    if (!$authSession || !selectedBusinessId) return;
    await runSave(async () => {
      await updateMentoringSession($authSession!.accessToken, selectedBusinessId, sessionId, {
        status,
        outcome: status === 'COMPLETED' ? 'Kegiatan pendampingan telah dilaksanakan.' : null,
        follow_up_date: null,
      });
      successMessage = 'Kegiatan pendampingan diperbarui.';
    });
  }

  async function runSave(action: () => Promise<void>): Promise<void> {
    saving = true;
    errorMessage = '';
    successMessage = '';
    try {
      await action();
      await refreshSelected();
    } catch (error) {
      errorMessage = message(error, 'Perubahan belum dapat disimpan.');
    } finally {
      saving = false;
    }
  }

  async function download(format: ReportExportFormat): Promise<void> {
    if (!$authSession) return;
    exporting = format;
    errorMessage = '';
    try {
      await exportMentorReport($authSession.accessToken, format);
    } catch (error) {
      errorMessage = message(error, 'Laporan pembinaan belum dapat diunduh.');
    } finally {
      exporting = null;
    }
  }

  async function drawTrend(): Promise<void> {
    if (!detail || !trendElement) return;
    const echarts = await import('echarts');
    trendChart?.dispose();
    const chart = echarts.init(trendElement);
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['Omzet', 'Laba'] },
      grid: { left: 60, right: 24, bottom: 40 },
      xAxis: { type: 'category', data: detail.revenue_trend.map((item) => item.month) },
      yAxis: { type: 'value' },
      series: [
        {
          name: 'Omzet',
          type: 'line',
          smooth: true,
          lineStyle: { color: '#047857', width: 3 },
          data: detail.revenue_trend.map((item) => Number(item.revenue)),
        },
        {
          name: 'Laba',
          type: 'bar',
          itemStyle: { color: '#f59e0b' },
          data: detail.revenue_trend.map((item) => Number(item.profit)),
        },
      ],
    });
    trendChart = chart;
  }

  function healthClass(level: MentorHealthLevel): string {
    if (level === 'RED') return 'border-red-200 bg-red-50 text-red-800';
    if (level === 'YELLOW') return 'border-amber-200 bg-amber-50 text-amber-800';
    return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  }

  function statusLabel(status: RecommendationStatus | MentoringSessionStatus): string {
    return (
      {
        OPEN: 'Belum dimulai',
        IN_PROGRESS: 'Sedang ditindaklanjuti',
        DONE: 'Selesai',
        CANCELLED: 'Dibatalkan',
        SCHEDULED: 'Terjadwal',
        COMPLETED: 'Selesai',
      } as Record<string, string>
    )[status];
  }

  function priorityLabel(priority: 'LOW' | 'MEDIUM' | 'HIGH'): string {
    return { LOW: 'Rendah', MEDIUM: 'Sedang', HIGH: 'Tinggi' }[priority];
  }

  function sessionModeLabel(mode: string): string {
    return { ONLINE: 'Daring', ONSITE: 'Datang langsung', PHONE: 'Telepon' }[mode] ?? mode;
  }

  function auditLabel(action: string): string {
    return (
      (
        {
          MENTOR_NOTE_CREATED: 'Membuat catatan',
          MENTOR_RECOMMENDATION_CREATED: 'Membuat rekomendasi',
          MENTOR_RECOMMENDATION_UPDATED: 'Memperbarui tindak lanjut',
          MENTOR_SESSION_SCHEDULED: 'Menjadwalkan pendampingan',
          MENTOR_SESSION_UPDATED: 'Memperbarui kegiatan pendampingan',
        } as Record<string, string>
      )[action] ?? action.replaceAll('_', ' ')
    );
  }

  function dateLabel(value: string | null): string {
    if (!value) return 'Belum ada';
    return new Intl.DateTimeFormat('id-ID', { dateStyle: 'medium' }).format(new Date(value));
  }

  function dateTimeLabel(value: string): string {
    return new Intl.DateTimeFormat('id-ID', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value));
  }

  function message(error: unknown, fallback: string): string {
    return error instanceof Error ? error.message : fallback;
  }
</script>

<svelte:head>
  <title>Dashboard Pembina - KASTA</title>
  <meta name="description" content="Pantau UMKM binaan dan tindak lanjut pendampingan." />
</svelte:head>

<section class="bg-[var(--surface-subtle)] text-[var(--text)]">
  <header class="border-b border-[var(--border)] bg-[var(--surface)]">
    <div class="mx-auto flex max-w-[1500px] items-center justify-between px-5 py-4 sm:px-8">
      <div>
        <BrandLogo context="Ruang kerja pembina UMKM" />
      </div>
      <div class="flex flex-wrap gap-2">
        {#each ['PDF', 'XLSX', 'CSV'] as format (format)}
          <button
            class="rounded-xl border border-slate-200 px-3 py-2 text-xs font-bold hover:bg-slate-50"
            disabled={exporting !== null}
            onclick={() => void download(format as ReportExportFormat)}
          >
            {exporting === format ? 'Menyiapkan...' : `Unduh ${format}`}
          </button>
        {/each}
      </div>
    </div>
  </header>

  <div class="mx-auto max-w-[1500px] px-5 py-8 sm:px-8">
    <section class="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
      <div>
        <p class="text-sm font-bold text-kasta-700">Pendampingan berbasis data</p>
        <h1 class="mt-1 text-3xl font-black tracking-tight sm:text-4xl">Dashboard Pembina</h1>
        <p class="mt-2 max-w-3xl text-slate-600">
          Pantau kondisi usaha, beri rekomendasi, dan catat pendampingan tanpa dapat mengubah
          transaksi UMKM.
        </p>
        <a class="mt-3 inline-block font-bold text-kasta-700" href="/pembina/akses">
          Atur permintaan akses →
        </a>
      </div>
      <div class="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
        <strong class="text-slate-900">Petunjuk status:</strong> ✓ Relatif sehat &nbsp; ! Perlu perhatian
        &nbsp; !! Perlu pendampingan
      </div>
    </section>

    {#if errorMessage}
      <p class="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-800" role="alert">
        {errorMessage}
      </p>
    {/if}
    {#if successMessage}
      <p
        class="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-800"
        role="status"
      >
        {successMessage}
      </p>
    {/if}

    {#if loading}
      <p class="py-24 text-center text-slate-500">Menyiapkan ringkasan UMKM binaan...</p>
    {:else if !$authSession}
      <p class="py-24 text-center text-slate-600">
        Masuk sebagai pembina untuk membuka halaman ini.
      </p>
    {:else if dashboard}
      <section class="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        {#each [['UMKM binaan', dashboard.total_businesses, 'Semua akses aktif'], ['UMKM aktif', dashboard.active_businesses, 'Mencatat 7 hari terakhir'], ['Tidak mencatat', dashboard.stale_businesses, 'Lebih dari 7 hari'], ['Pengeluaran tinggi', dashboard.expense_over_income, 'Melebihi pemasukan'], ['Utang tinggi', dashboard.high_debt, 'Perlu ditinjau'], ['Piutang terlambat', dashboard.overdue_receivables, 'Lewat jatuh tempo'], ['Tindak lanjut', dashboard.open_recommendations, 'Belum selesai'], ['Jadwal', dashboard.upcoming_sessions.length, 'Pertemuan mendatang']] as metric (metric[0])}
          <article class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p class="text-xs font-bold text-slate-500">{metric[0]}</p>
            <p class="mt-2 text-3xl font-black text-slate-950">{metric[1]}</p>
            <p class="mt-1 text-[11px] leading-4 text-slate-500">{metric[2]}</p>
          </article>
        {/each}
      </section>

      {#if aggregate}
        <section class="mt-5 rounded-3xl bg-kasta-950 p-6 text-white sm:p-7">
          <div class="grid gap-6 lg:grid-cols-[1.3fr_.7fr] lg:items-center">
            <div>
              <p class="text-sm font-bold text-emerald-300">Laporan agregat bulan ini</p>
              <p class="mt-2 text-xl font-bold leading-8">{aggregate.explanation}</p>
            </div>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div class="rounded-2xl bg-white/10 p-3">
                <span class="text-emerald-200">Omzet</span><strong class="mt-1 block"
                  >{formatRupiah(aggregate.total_revenue)}</strong
                >
              </div>
              <div class="rounded-2xl bg-white/10 p-3">
                <span class="text-emerald-200">Perkiraan laba</span><strong class="mt-1 block"
                  >{formatRupiah(aggregate.total_profit)}</strong
                >
              </div>
            </div>
          </div>
        </section>
      {/if}

      <section class="mt-5 grid gap-5 xl:grid-cols-[390px_minmax(0,1fr)]">
        <aside
          class="self-start rounded-3xl border border-slate-200 bg-white p-4 xl:sticky xl:top-5"
        >
          <div class="flex items-center justify-between gap-3">
            <h2 class="text-xl font-black">UMKM Binaan</h2>
            <span class="text-xs font-bold text-slate-500">{filteredBusinesses.length} usaha</span>
          </div>
          <label class="mt-4 block text-xs font-bold text-slate-600">
            Cari nama atau wilayah
            <input
              class="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm"
              placeholder="Contoh: Warung Maju"
              bind:value={search}
            />
          </label>
          <div class="mt-3 flex flex-wrap gap-2" aria-label="Saring status UMKM">
            {#each [['ALL', 'Semua'], ['GREEN', '✓ Sehat'], ['YELLOW', '! Perhatian'], ['RED', '!! Pendampingan']] as item (item[0])}
              <button
                class="rounded-full border px-3 py-1.5 text-xs font-bold {healthFilter === item[0]
                  ? 'border-emerald-700 bg-emerald-700 text-white'
                  : 'border-slate-200 text-slate-600'}"
                onclick={() => (healthFilter = item[0] as MentorHealthLevel | 'ALL')}
                >{item[1]}</button
              >
            {/each}
          </div>
          <div class="mt-4 max-h-[720px] space-y-3 overflow-auto pr-1">
            {#each filteredBusinesses as item (item.business_id)}
              <button
                class="w-full rounded-2xl border p-4 text-left transition hover:border-emerald-300 {selectedBusinessId ===
                item.business_id
                  ? 'border-emerald-600 bg-emerald-50/60 ring-2 ring-emerald-100'
                  : 'border-slate-200 bg-white'}"
                onclick={() => void selectBusiness(item.business_id)}
              >
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <strong class="block text-sm">{item.business_name}</strong>
                    <span class="text-xs text-slate-500"
                      >{[item.city, item.province].filter(Boolean).join(', ') ||
                        'Lokasi belum diisi'}</span
                    >
                  </div>
                  <span
                    class="rounded-full border px-2 py-1 text-[11px] font-bold {healthClass(
                      item.health_level,
                    )}">{item.health_icon} {item.health_label}</span
                  >
                </div>
                <div class="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <span>Omzet <b class="block">{formatRupiah(item.month_revenue)}</b></span>
                  <span>Laba <b class="block">{formatRupiah(item.month_profit)}</b></span>
                </div>
              </button>
            {:else}
              <p class="rounded-2xl bg-slate-50 p-5 text-center text-sm text-slate-500">
                Tidak ada UMKM sesuai penyaring.
              </p>
            {/each}
          </div>
        </aside>

        <div class="min-w-0">
          {#if detailLoading}
            <p class="rounded-3xl bg-white py-24 text-center text-slate-500">
              Memuat detail UMKM...
            </p>
          {:else if detail}
            <article class="rounded-3xl border border-slate-200 bg-white p-5 sm:p-7">
              <div class="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p class="text-sm font-bold text-emerald-700">Detail UMKM</p>
                  <h2 class="text-2xl font-black">{detail.summary.business_name}</h2>
                  <p class="mt-1 text-sm text-slate-500">
                    Terakhir mencatat: {dateLabel(detail.summary.last_recorded_date)} · Konsistensi
                    {detail.summary.recording_consistency}%
                  </p>
                </div>
                <span
                  class="rounded-full border px-3 py-2 text-sm font-bold {healthClass(
                    detail.summary.health_level,
                  )}">{detail.summary.health_icon} {detail.summary.health_label}</span
                >
              </div>
              <p class="mt-5 rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">
                {detail.explanation}
              </p>

              <nav class="mt-5 flex gap-2 overflow-auto border-b border-slate-200 pb-3">
                {#each [['OVERVIEW', 'Ringkasan'], ['NOTES', `Catatan (${detail.notes.length})`], ['RECOMMENDATIONS', `Rekomendasi (${detail.recommendations.length})`], ['SESSIONS', `Pendampingan (${detail.sessions.length})`]] as item (item[0])}
                  <button
                    class="whitespace-nowrap rounded-xl px-3 py-2 text-sm font-bold {section ===
                    item[0]
                      ? 'bg-emerald-700 text-white'
                      : 'text-slate-600 hover:bg-slate-100'}"
                    onclick={() =>
                      (section = item[0] as 'OVERVIEW' | 'NOTES' | 'RECOMMENDATIONS' | 'SESSIONS')}
                    >{item[1]}</button
                  >
                {/each}
              </nav>

              {#if section === 'OVERVIEW'}
                <div class="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {#each [['Omzet bulan ini', detail.summary.month_revenue], ['Pengeluaran bulan ini', detail.summary.month_expense], ['Perkiraan laba', detail.summary.month_profit], ['Utang', detail.summary.payable_balance], ['Piutang', detail.summary.receivable_balance], ['Piutang terlambat', detail.summary.overdue_receivable]] as money (money[0])}
                    <div class="rounded-2xl border border-slate-200 p-4">
                      <span class="text-xs font-bold text-slate-500">{money[0]}</span>
                      <strong class="mt-1 block text-lg">{formatRupiah(money[1])}</strong>
                    </div>
                  {/each}
                </div>
                <div class="mt-5 grid gap-5 lg:grid-cols-[1.2fr_.8fr]">
                  <section class="rounded-2xl border border-slate-200 p-4">
                    <h3 class="font-black">Tren omzet dan laba</h3>
                    <div class="mt-3 h-72 w-full" bind:this={trendElement}></div>
                  </section>
                  <section class="rounded-2xl border border-slate-200 p-4">
                    <h3 class="font-black">Indikator risiko</h3>
                    <div class="mt-3 space-y-3">
                      {#each detail.summary.risk_indicators as risk (risk.code)}
                        <div class="rounded-xl border p-3 {healthClass(risk.level)}">
                          <strong class="text-sm">{risk.icon} {risk.label}</strong>
                          <p class="mt-1 text-xs leading-5">{risk.message}</p>
                        </div>
                      {/each}
                    </div>
                  </section>
                </div>
              {:else if section === 'NOTES'}
                <div class="mt-5 grid gap-5 lg:grid-cols-[.8fr_1.2fr]">
                  <form
                    class="rounded-2xl bg-slate-50 p-4"
                    onsubmit={(event) => {
                      event.preventDefault();
                      void submitNote();
                    }}
                  >
                    <h3 class="font-black">Buat catatan pembina</h3>
                    <label class="mt-3 block text-sm font-bold"
                      >Isi catatan<textarea class="field" rows="5" bind:value={noteContent}
                      ></textarea></label
                    >
                    <label class="mt-3 block text-sm font-bold"
                      >Siapa yang dapat melihat<select class="field" bind:value={noteVisibility}
                        ><option value="SHARED">Bagikan kepada UMKM</option><option value="PRIVATE"
                          >Hanya saya</option
                        ></select
                      ></label
                    >
                    <button class="primary" disabled={saving}>Simpan catatan</button>
                  </form>
                  <section>
                    <h3 class="font-black">Riwayat catatan</h3>
                    <div class="mt-3 space-y-3">
                      {#each detail.notes as note (note.id)}
                        <article class="rounded-2xl border border-slate-200 p-4">
                          <div class="flex justify-between gap-3 text-xs text-slate-500">
                            <span
                              >{note.visibility === 'SHARED'
                                ? 'Dibagikan kepada UMKM'
                                : 'Catatan pribadi'}</span
                            ><time>{dateTimeLabel(note.created_at)}</time>
                          </div>
                          <p class="mt-2 whitespace-pre-wrap text-sm leading-6">{note.content}</p>
                        </article>
                      {:else}<p class="empty">Belum ada catatan pembina.</p>{/each}
                    </div>
                  </section>
                </div>
              {:else if section === 'RECOMMENDATIONS'}
                <div class="mt-5 grid gap-5 lg:grid-cols-[.8fr_1.2fr]">
                  <form
                    class="rounded-2xl bg-slate-50 p-4"
                    onsubmit={(event) => {
                      event.preventDefault();
                      void submitRecommendation();
                    }}
                  >
                    <h3 class="font-black">Buat rekomendasi</h3>
                    <label class="label"
                      >Judul<input class="field" bind:value={recommendationTitle} /></label
                    >
                    <label class="label"
                      >Penjelasan<textarea
                        class="field"
                        rows="4"
                        bind:value={recommendationDescription}
                      ></textarea></label
                    >
                    <div class="grid grid-cols-2 gap-3">
                      <label class="label"
                        >Prioritas<select class="field" bind:value={recommendationPriority}
                          ><option value="LOW">Rendah</option><option value="MEDIUM">Sedang</option
                          ><option value="HIGH">Tinggi</option></select
                        ></label
                      ><label class="label"
                        >Target selesai<input
                          class="field"
                          type="date"
                          bind:value={recommendationDueDate}
                        /></label
                      >
                    </div>
                    <button class="primary" disabled={saving}>Kirim rekomendasi</button>
                  </form>
                  <section>
                    <h3 class="font-black">Status tindak lanjut</h3>
                    <div class="mt-3 space-y-3">
                      {#each detail.recommendations as item (item.id)}
                        <article class="rounded-2xl border border-slate-200 p-4">
                          <div class="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <strong>{item.title}</strong>
                              <p class="mt-1 text-sm text-slate-600">{item.description}</p>
                            </div>
                            <span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold"
                              >{statusLabel(item.status)}</span
                            >
                          </div>
                          <p class="mt-2 text-xs text-slate-500">
                            Prioritas {priorityLabel(item.priority)} · Target {dateLabel(
                              item.due_date,
                            )}
                          </p>
                          {#if item.follow_up_note}<p
                              class="mt-2 rounded-xl bg-emerald-50 p-3 text-xs text-emerald-800"
                            >
                              {item.follow_up_note}
                            </p>{/if}
                          {#if item.status === 'OPEN'}<button
                              class="small"
                              disabled={saving}
                              onclick={() => void changeRecommendation(item.id, 'IN_PROGRESS')}
                              >Mulai tindak lanjut</button
                            >{:else if item.status === 'IN_PROGRESS'}<button
                              class="small"
                              disabled={saving}
                              onclick={() => void changeRecommendation(item.id, 'DONE')}
                              >Tandai selesai</button
                            >{/if}
                        </article>
                      {:else}<p class="empty">Belum ada rekomendasi.</p>{/each}
                    </div>
                  </section>
                </div>
              {:else}
                <div class="mt-5 grid gap-5 lg:grid-cols-[.8fr_1.2fr]">
                  <form
                    class="rounded-2xl bg-slate-50 p-4"
                    onsubmit={(event) => {
                      event.preventDefault();
                      void submitSession();
                    }}
                  >
                    <h3 class="font-black">Jadwalkan pertemuan</h3>
                    <label class="label"
                      >Topik<input class="field" bind:value={sessionTopic} /></label
                    >
                    <label class="label"
                      >Tanggal dan waktu<input
                        class="field"
                        type="datetime-local"
                        bind:value={sessionScheduledAt}
                      /></label
                    >
                    <div class="grid grid-cols-2 gap-3">
                      <label class="label"
                        >Durasi (menit)<input
                          class="field"
                          type="number"
                          min="15"
                          max="480"
                          bind:value={sessionDuration}
                        /></label
                      ><label class="label"
                        >Cara pertemuan<select class="field" bind:value={sessionMode}
                          ><option value="ONLINE">Daring</option><option value="ONSITE"
                            >Datang langsung</option
                          ><option value="PHONE">Telepon</option></select
                        ></label
                      >
                    </div>
                    <label class="label"
                      >Tempat atau tautan<input class="field" bind:value={sessionLocation} /></label
                    >
                    <button class="primary" disabled={saving}>Simpan jadwal</button>
                  </form>
                  <section>
                    <h3 class="font-black">Kegiatan pendampingan</h3>
                    <div class="mt-3 space-y-3">
                      {#each detail.sessions as item (item.id)}
                        <article class="rounded-2xl border border-slate-200 p-4">
                          <div class="flex flex-wrap justify-between gap-3">
                            <div>
                              <strong>{item.topic}</strong>
                              <p class="text-sm text-slate-500">
                                {dateTimeLabel(item.scheduled_at)} · {item.duration_minutes} menit · {sessionModeLabel(
                                  item.mode,
                                )}
                              </p>
                            </div>
                            <span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold"
                              >{statusLabel(item.status)}</span
                            >
                          </div>
                          {#if item.location}<p class="mt-2 text-sm">
                              Tempat/tautan: {item.location}
                            </p>{/if}
                          {#if item.outcome}<p class="mt-2 rounded-xl bg-slate-50 p-3 text-sm">
                              Hasil: {item.outcome}
                            </p>{/if}
                          {#if item.status === 'SCHEDULED'}<div class="flex gap-2">
                              <button
                                class="small"
                                disabled={saving}
                                onclick={() => void changeSession(item.id, 'COMPLETED')}
                                >Tandai selesai</button
                              ><button
                                class="small muted"
                                disabled={saving}
                                onclick={() => void changeSession(item.id, 'CANCELLED')}
                                >Batalkan jadwal</button
                              >
                            </div>{/if}
                        </article>
                      {:else}<p class="empty">Belum ada kegiatan pendampingan.</p>{/each}
                    </div>
                  </section>
                </div>
              {/if}
            </article>
          {:else}
            <p class="rounded-3xl bg-white py-24 text-center text-slate-500">
              Pilih UMKM untuk melihat detail.
            </p>
          {/if}
        </div>
      </section>

      <section class="mt-5 grid gap-5 lg:grid-cols-2">
        <article class="rounded-3xl border border-slate-200 bg-white p-5">
          <h2 class="text-xl font-black">Jadwal pendampingan</h2>
          <div class="mt-4 space-y-3">
            {#each dashboard.upcoming_sessions as item (item.id)}
              <button
                class="flex w-full items-center gap-3 rounded-2xl bg-slate-50 p-3 text-left"
                onclick={() => {
                  section = 'SESSIONS';
                  void selectBusiness(item.business_id);
                }}
                ><span
                  class="grid h-10 w-10 place-items-center rounded-xl bg-emerald-100 font-black text-emerald-800"
                  >J</span
                ><span
                  ><strong class="block text-sm">{item.business_name}</strong><small
                    class="text-slate-500">{dateTimeLabel(item.scheduled_at)} · {item.topic}</small
                  ></span
                ></button
              >
            {:else}<p class="empty">Belum ada jadwal mendatang.</p>{/each}
          </div>
        </article>
        <article class="rounded-3xl border border-slate-200 bg-white p-5">
          <h2 class="text-xl font-black">Audit aktivitas pembina</h2>
          <div class="mt-4 max-h-80 space-y-3 overflow-auto">
            {#each audit as item (item.id)}
              <div class="border-l-2 border-emerald-300 pl-3">
                <strong class="block text-sm">{item.business_name}</strong>
                <p class="text-xs text-slate-600">
                  {auditLabel(item.action)}{item.reason ? ` · ${item.reason}` : ''}
                </p>
                <time class="text-[11px] text-slate-400">{dateTimeLabel(item.created_at)}</time>
              </div>
            {:else}<p class="empty">Belum ada aktivitas pembina.</p>{/each}
          </div>
        </article>
      </section>
    {/if}
  </div>
</section>

<style>
  .field {
    margin-top: 0.35rem;
    width: 100%;
    border-radius: 0.75rem;
    border: 1px solid #cbd5e1;
    background: white;
    padding: 0.65rem 0.75rem;
    font-size: 0.875rem;
    font-weight: 500;
  }
  .label {
    margin-top: 0.75rem;
    display: block;
    font-size: 0.875rem;
    font-weight: 700;
  }
  .primary {
    margin-top: 1rem;
    border-radius: 0.75rem;
    background: #047857;
    padding: 0.7rem 1rem;
    color: white;
    font-size: 0.875rem;
    font-weight: 800;
  }
  .primary:disabled,
  .small:disabled {
    opacity: 0.55;
  }
  .small {
    margin-top: 0.75rem;
    margin-right: 0.5rem;
    border-radius: 0.65rem;
    background: #047857;
    padding: 0.5rem 0.75rem;
    color: white;
    font-size: 0.75rem;
    font-weight: 800;
  }
  .small.muted {
    background: #e2e8f0;
    color: #334155;
  }
  .empty {
    border-radius: 0.9rem;
    background: #f8fafc;
    padding: 1rem;
    text-align: center;
    font-size: 0.875rem;
    color: #64748b;
  }
</style>

<script lang="ts">
  import type {
    FinancialReport,
    ReportExportFormat,
    ReportFilters,
    ReportPeriod,
  } from '@kasta/contracts';
  import { resolve } from '$app/paths';
  import { onMount, tick } from 'svelte';

  import { exportFinancialReport, getFinancialReport } from '$lib/api/reports';
  import { formatRupiah } from '$lib/money/rupiah';
  import { authSession } from '$lib/stores/auth-session';

  let { data }: { data: { businessId: string } } = $props();
  let report = $state<FinancialReport | null>(null);
  let loading = $state(true);
  let exporting = $state<ReportExportFormat | null>(null);
  let errorMessage = $state('');
  let period = $state<ReportPeriod>('MONTH');
  let referenceDate = $state(new Date().toISOString().slice(0, 10));
  let dateFrom = $state(new Date().toISOString().slice(0, 8) + '01');
  let dateTo = $state(new Date().toISOString().slice(0, 10));
  let category = $state('');
  let paymentMethod = $state('');

  let incomeExpenseChart = $state<HTMLDivElement>();
  let profitChart = $state<HTMLDivElement>();
  let expenseChart = $state<HTMLDivElement>();
  let salesChart = $state<HTMLDivElement>();
  let productChart = $state<HTMLDivElement>();
  let chartInstances: Array<{ resize: () => void; dispose: () => void }> = [];

  const periods: Array<{ value: ReportPeriod; label: string }> = [
    { value: 'DAY', label: 'Hari' },
    { value: 'WEEK', label: 'Minggu' },
    { value: 'MONTH', label: 'Bulan' },
    { value: 'QUARTER', label: 'Kuartal' },
    { value: 'YEAR', label: 'Tahun' },
    { value: 'CUSTOM', label: 'Rentang tanggal' },
  ];
  const categories = [
    ['SALES', 'Penjualan'],
    ['SERVICE_REVENUE', 'Pendapatan Jasa'],
    ['OTHER_REVENUE', 'Pendapatan Lain'],
    ['PURCHASES', 'Pembelian'],
    ['RAW_MATERIALS', 'Bahan Baku'],
    ['TRANSPORTATION', 'Transportasi'],
    ['ELECTRICITY', 'Listrik'],
    ['INTERNET', 'Internet'],
    ['SALARY', 'Gaji'],
    ['RENT', 'Sewa'],
    ['PROMOTION', 'Promosi'],
    ['ADMINISTRATION', 'Administrasi'],
    ['OTHER_EXPENSE', 'Beban Lain'],
  ];

  onMount(() => {
    void loadReport();
    const resize = () => chartInstances.forEach((chart) => chart.resize());
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      chartInstances.forEach((chart) => chart.dispose());
    };
  });

  function filters(): ReportFilters {
    return {
      period,
      reference_date: referenceDate,
      date_from: period === 'CUSTOM' ? dateFrom : undefined,
      date_to: period === 'CUSTOM' ? dateTo : undefined,
      category: category || undefined,
      payment_method: paymentMethod || undefined,
      branch_id: data.businessId,
    };
  }

  async function loadReport(): Promise<void> {
    if (!$authSession || $authSession.businessId !== data.businessId) {
      loading = false;
      return;
    }
    loading = true;
    errorMessage = '';
    let shouldDraw = false;
    try {
      report = await getFinancialReport(data.businessId, $authSession.accessToken, filters());
      shouldDraw = true;
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Laporan belum dapat dimuat.';
    } finally {
      loading = false;
    }
    if (shouldDraw) {
      await tick();
      await drawCharts();
    }
  }

  async function download(format: ReportExportFormat): Promise<void> {
    if (!$authSession) return;
    exporting = format;
    try {
      await exportFinancialReport(data.businessId, $authSession.accessToken, filters(), format);
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Laporan belum dapat diunduh.';
    } finally {
      exporting = null;
    }
  }

  async function drawCharts(): Promise<void> {
    if (
      !report ||
      !incomeExpenseChart ||
      !profitChart ||
      !expenseChart ||
      !salesChart ||
      !productChart
    )
      return;
    const echarts = await import('echarts');
    chartInstances.forEach((chart) => chart.dispose());
    chartInstances = [];
    const axis = report.charts.income_vs_expense.map((item) => item.period.slice(5));
    const tooltip = { trigger: 'axis' };

    const incomeExpense = echarts.init(incomeExpenseChart);
    incomeExpense.setOption({
      tooltip,
      legend: { data: ['Pemasukan', 'Pengeluaran'] },
      xAxis: { type: 'category', data: axis },
      yAxis: { type: 'value' },
      series: [
        {
          name: 'Pemasukan',
          type: 'bar',
          data: report.charts.income_vs_expense.map((item) => Number(item.income)),
          itemStyle: { color: '#047857' },
        },
        {
          name: 'Pengeluaran',
          type: 'bar',
          data: report.charts.income_vs_expense.map((item) => Number(item.expense)),
          itemStyle: { color: '#f59e0b' },
        },
      ],
    });
    const profit = echarts.init(profitChart);
    profit.setOption({
      tooltip,
      xAxis: { type: 'category', data: report.charts.profit_trend.map((item) => item.period) },
      yAxis: { type: 'value' },
      series: [
        {
          name: 'Laba',
          type: 'line',
          smooth: true,
          areaStyle: { color: '#d1fae5' },
          lineStyle: { color: '#047857' },
          data: report.charts.profit_trend.map((item) => Number(item.profit)),
        },
      ],
    });
    const expense = echarts.init(expenseChart);
    expense.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [
        {
          type: 'pie',
          radius: ['35%', '68%'],
          data: report.charts.expense_categories.map((item) => ({
            name: item.label,
            value: Number(item.amount),
          })),
        },
      ],
    });
    const sales = echarts.init(salesChart);
    sales.setOption({
      tooltip,
      xAxis: {
        type: 'category',
        data: report.charts.daily_sales.map((item) => item.period.slice(5)),
      },
      yAxis: { type: 'value' },
      series: [
        {
          name: 'Penjualan',
          type: 'bar',
          data: report.charts.daily_sales.map((item) => Number(item.sales)),
          itemStyle: { color: '#0f766e' },
        },
      ],
    });
    const product = echarts.init(productChart);
    product.setOption({
      tooltip,
      grid: { left: 120 },
      xAxis: { type: 'value' },
      yAxis: {
        type: 'category',
        data: report.charts.best_selling_products.map((item) => item.name).reverse(),
      },
      series: [
        {
          name: 'Jumlah terjual',
          type: 'bar',
          data: report.charts.best_selling_products
            .map((item) => Number(item.quantity_sold))
            .reverse(),
          itemStyle: { color: '#059669' },
        },
      ],
    });
    chartInstances = [incomeExpense, profit, expense, sales, product];
  }
</script>

<svelte:head>
  <title>Laporan Keuangan — KASTA</title>
  <meta name="description" content="Laporan usaha sederhana yang dihitung dari jurnal KASTA." />
</svelte:head>

<section class="text-slate-900 dark:text-slate-100">
  <header class="border-b border-slate-200 bg-white">
    <div class="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
      <div>
        <a href={resolve('/')} class="text-xl font-black text-emerald-950">KASTA</a>
        <p class="text-xs font-semibold text-slate-400">Laporan keuangan usaha</p>
      </div>
      <a
        href={resolve('/usaha/[businessId]/transaksi', { businessId: data.businessId })}
        class="rounded-xl border border-slate-200 px-4 py-2 text-sm font-bold">Ke transaksi</a
      >
    </div>
  </header>

  <div class="mx-auto max-w-7xl px-5 py-8 sm:px-8">
    <section>
      <p class="text-sm font-bold text-emerald-700">Dihitung dari jurnal usaha</p>
      <h1 class="text-3xl font-black sm:text-4xl">Laporan Keuangan</h1>
      <p class="mt-2 text-slate-500">
        Lihat kondisi usaha dalam bahasa sederhana, lengkap dengan grafik dan penjelasan.
      </p>
    </section>

    <section class="mt-6 rounded-3xl border border-slate-200 bg-white p-5">
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label
          >Periode<select class="field" bind:value={period}>
            {#each periods as item (item.value)}<option value={item.value}>{item.label}</option
              >{/each}
          </select></label
        >
        {#if period === 'CUSTOM'}
          <label>Tanggal mulai<input class="field" type="date" bind:value={dateFrom} /></label>
          <label>Tanggal akhir<input class="field" type="date" bind:value={dateTo} /></label>
        {:else}
          <label>Tanggal acuan<input class="field" type="date" bind:value={referenceDate} /></label>
        {/if}
        <label
          >Kategori<select class="field" bind:value={category}>
            <option value="">Semua kategori</option>
            {#each categories as item (item[0])}<option value={item[0]}>{item[1]}</option>{/each}
          </select></label
        >
        <label
          >Metode pembayaran<select class="field" bind:value={paymentMethod}>
            <option value="">Semua metode</option><option value="CASH">Tunai</option><option
              value="BANK_TRANSFER">Transfer bank</option
            ><option value="QRIS">QRIS</option><option value="E_WALLET">Dompet digital</option
            ><option value="CARD">Kartu</option>
          </select></label
        >
        <label>Cabang<select class="field" disabled><option>Usaha ini</option></select></label>
      </div>
      <div class="mt-4 flex flex-wrap gap-2">
        <button class="primary" onclick={() => void loadReport()}>Tampilkan laporan</button>
        {#each ['PDF', 'XLSX', 'CSV'] as format (format)}
          <button
            class="secondary"
            disabled={exporting !== null}
            onclick={() => void download(format as ReportExportFormat)}
            >{exporting === format ? 'Menyiapkan…' : `Unduh ${format}`}</button
          >
        {/each}
      </div>
    </section>

    {#if errorMessage}<p class="mt-5 rounded-2xl bg-red-50 p-4 text-red-700" role="alert">
        {errorMessage}
      </p>{/if}
    {#if loading}<p class="py-24 text-center text-slate-500">Menghitung laporan dari jurnal…</p>
    {:else if !$authSession}<p class="py-24 text-center">Masuk kembali untuk melihat laporan.</p>
    {:else if report}
      <section class="mt-6 rounded-3xl bg-emerald-950 p-6 text-white sm:p-8">
        <p class="text-sm font-bold text-emerald-300">Ringkasan keuangan</p>
        <p class="mt-2 max-w-4xl text-xl font-bold sm:text-2xl">{report.explanation}</p>
        <p class="mt-3 text-sm text-emerald-200">
          {report.context.date_from} sampai {report.context.date_to} · Sumber: jurnal double-entry
        </p>
      </section>

      <section class="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <article class="metric">
          <span>Pemasukan</span><strong>{formatRupiah(report.summary.income)}</strong>
        </article>
        <article class="metric">
          <span>Pengeluaran</span><strong>{formatRupiah(report.summary.expense)}</strong>
        </article>
        <article class="metric">
          <span>Perkiraan laba</span><strong
            class={Number(report.summary.estimated_profit) < 0
              ? 'text-red-600'
              : 'text-emerald-700'}>{formatRupiah(report.summary.estimated_profit)}</strong
          >
        </article>
        <article class="metric">
          <span>Arus kas bersih</span><strong>{formatRupiah(report.summary.net_cash_flow)}</strong>
        </article>
        <article class="metric">
          <span>Piutang</span><strong>{formatRupiah(report.summary.receivables)}</strong>
        </article>
        <article class="metric">
          <span>Utang</span><strong>{formatRupiah(report.summary.payables)}</strong>
        </article>
        <article class="metric">
          <span>Nilai persediaan</span><strong
            >{formatRupiah(report.summary.inventory_value)}</strong
          >
        </article>
        <article class="metric">
          <span>Saldo kas dan rekening</span><strong
            >{formatRupiah(report.cash_flow.ending_cash_balance)}</strong
          >
        </article>
      </section>

      <section class="mt-5 grid gap-5 lg:grid-cols-2">
        <article class="panel">
          <h2>Pemasukan versus pengeluaran</h2>
          <div class="chart" bind:this={incomeExpenseChart}></div>
        </article>
        <article class="panel">
          <h2>Tren laba</h2>
          <div class="chart" bind:this={profitChart}></div>
        </article>
        <article class="panel">
          <h2>Kategori pengeluaran</h2>
          <div class="chart" bind:this={expenseChart}></div>
        </article>
        <article class="panel">
          <h2>Penjualan harian</h2>
          <div class="chart" bind:this={salesChart}></div>
        </article>
        <article class="panel lg:col-span-2">
          <h2>Produk terlaris</h2>
          <div class="chart" bind:this={productChart}></div>
        </article>
      </section>

      <section class="mt-5 grid gap-5 lg:grid-cols-2">
        <article class="panel">
          <h2>Laporan laba rugi</h2>
          <table>
            <tbody>
              {#each report.profit_loss.revenues as row (row.account_key)}<tr
                  ><td>{row.account_name}</td><td>{formatRupiah(row.amount)}</td></tr
                >{/each}
              {#each report.profit_loss.expenses as row (row.account_key)}<tr
                  ><td>{row.account_name}</td><td class="text-amber-700"
                    >({formatRupiah(row.amount)})</td
                  ></tr
                >{/each}
              <tr class="total"
                ><td>Perkiraan laba</td><td>{formatRupiah(report.profit_loss.profit)}</td></tr
              >
            </tbody>
          </table>
          <p class="explanation">{report.profit_loss.explanation}</p>
        </article>

        <article class="panel">
          <h2>Laporan posisi keuangan</h2>
          <h3>Aset</h3>
          {#each report.balance_sheet.assets as row (row.account_key)}<div class="line">
              <span>{row.account_name}</span><strong>{formatRupiah(row.amount)}</strong>
            </div>{/each}
          <h3>Utang</h3>
          {#each report.balance_sheet.liabilities as row (row.account_key)}<div class="line">
              <span>{row.account_name}</span><strong>{formatRupiah(row.amount)}</strong>
            </div>{/each}
          <h3>Modal dan laba</h3>
          {#each report.balance_sheet.equity as row (row.account_key)}<div class="line">
              <span>{row.account_name}</span><strong>{formatRupiah(row.amount)}</strong>
            </div>{/each}
          <p class="explanation">{report.balance_sheet.explanation}</p>
        </article>

        <article class="panel">
          <h2>Arus kas sederhana</h2>
          <div class="line">
            <span>Uang masuk</span><strong>{formatRupiah(report.cash_flow.cash_in)}</strong>
          </div>
          <div class="line">
            <span>Uang keluar</span><strong>{formatRupiah(report.cash_flow.cash_out)}</strong>
          </div>
          <div class="line total">
            <span>Perubahan bersih</span><strong
              >{formatRupiah(report.cash_flow.net_cash_flow)}</strong
            >
          </div>
          <p class="explanation">{report.cash_flow.explanation}</p>
        </article>

        <article class="panel">
          <h2>Utang dan piutang</h2>
          <div class="line">
            <span>Piutang menurut jurnal</span><strong
              >{formatRupiah(report.receivables.journal_value)}</strong
            >
          </div>
          <div class="line">
            <span>Sisa daftar piutang ({report.receivables.open_count})</span><strong
              >{formatRupiah(report.receivables.total_remaining)}</strong
            >
          </div>
          <div class="line">
            <span>Utang menurut jurnal</span><strong
              >{formatRupiah(report.payables.journal_value)}</strong
            >
          </div>
          <div class="line">
            <span>Sisa daftar utang ({report.payables.open_count})</span><strong
              >{formatRupiah(report.payables.total_remaining)}</strong
            >
          </div>
          <p class="explanation">{report.receivables.explanation}</p>
          <p class="explanation">{report.payables.explanation}</p>
        </article>

        <article class="panel">
          <h2>Penjualan dan pengeluaran</h2>
          <h3>Penjualan</h3>
          {#each report.sales as row (row.key)}<div class="line">
              <span>{row.label} · {row.percentage}%</span><strong>{formatRupiah(row.amount)}</strong
              >
            </div>{/each}
          <h3>Pengeluaran</h3>
          {#each report.expenditures as row (row.key)}<div class="line">
              <span>{row.label} · {row.percentage}%</span><strong>{formatRupiah(row.amount)}</strong
              >
            </div>{/each}
        </article>

        <article class="panel">
          <h2>Persediaan</h2>
          <div class="line">
            <span>Produk aktif</span><strong>{report.inventory.product_count}</strong>
          </div>
          <div class="line">
            <span>Produk stok minimum</span><strong>{report.inventory.low_stock_count}</strong>
          </div>
          <div class="line">
            <span>Nilai stok operasional</span><strong
              >{formatRupiah(report.inventory.operational_value)}</strong
            >
          </div>
          <div class="line">
            <span>Nilai akun persediaan di jurnal</span><strong
              >{formatRupiah(report.inventory.journal_value)}</strong
            >
          </div>
          <p class="explanation">{report.inventory.explanation}</p>
        </article>
      </section>

      <section class="panel mt-5 overflow-x-auto">
        <h2>Produk paling laku</h2>
        <table>
          <thead><tr><th>Produk</th><th>Jumlah terjual</th><th>Nilai penjualan</th></tr></thead
          ><tbody>
            {#each report.best_selling_products as item (item.product_id)}<tr
                ><td>{item.name}<small>{item.sku}</small></td><td
                  >{item.quantity_sold} {item.unit}</td
                ><td>{formatRupiah(item.sales_value)}</td></tr
              >{/each}
          </tbody>
        </table>
      </section>

      <section class="panel mt-5 overflow-x-auto">
        <h2>Perbandingan bulanan</h2>
        <table>
          <thead><tr><th>Bulan</th><th>Pemasukan</th><th>Pengeluaran</th><th>Laba</th></tr></thead
          ><tbody>
            {#each report.monthly_comparison as item (item.period)}<tr
                ><td>{item.period}</td><td>{formatRupiah(item.income)}</td><td
                  >{formatRupiah(item.expense)}</td
                ><td>{formatRupiah(item.profit)}</td></tr
              >{/each}
          </tbody>
        </table>
      </section>
    {/if}
  </div>
</section>

<style>
  :global(.field) {
    margin-top: 0.35rem;
    width: 100%;
    border: 1px solid #e2e8f0;
    border-radius: 0.75rem;
    padding: 0.7rem 0.85rem;
    background: white;
  }
  :global(.primary),
  :global(.secondary) {
    border-radius: 0.75rem;
    padding: 0.7rem 1rem;
    font-weight: 800;
  }
  :global(.primary) {
    background: #047857;
    color: white;
  }
  :global(.secondary) {
    border: 1px solid #cbd5e1;
    background: white;
  }
  :global(.metric),
  :global(.panel) {
    border: 1px solid #e2e8f0;
    border-radius: 1.25rem;
    background: white;
    padding: 1.25rem;
  }
  :global(.metric span) {
    display: block;
    color: #64748b;
    font-size: 0.875rem;
  }
  :global(.metric strong) {
    display: block;
    margin-top: 0.35rem;
    font-size: 1.35rem;
  }
  :global(.panel h2) {
    font-size: 1.15rem;
    font-weight: 900;
    margin-bottom: 0.8rem;
  }
  :global(.panel h3) {
    margin-top: 0.9rem;
    color: #047857;
    font-size: 0.8rem;
    font-weight: 900;
    text-transform: uppercase;
  }
  :global(.chart) {
    width: 100%;
    height: 310px;
  }
  :global(.line) {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.55rem 0;
    border-bottom: 1px solid #f1f5f9;
  }
  :global(.total) {
    font-weight: 900;
    border-top: 2px solid #cbd5e1;
  }
  :global(.explanation) {
    margin-top: 1rem;
    border-radius: 0.75rem;
    background: #ecfdf5;
    padding: 0.85rem;
    color: #065f46;
    font-size: 0.875rem;
  }
  :global(table) {
    width: 100%;
    border-collapse: collapse;
  }
  :global(th),
  :global(td) {
    padding: 0.7rem;
    text-align: left;
    border-bottom: 1px solid #e2e8f0;
  }
  :global(td:last-child),
  :global(th:last-child) {
    text-align: right;
  }
  :global(td small) {
    display: block;
    color: #94a3b8;
  }
</style>

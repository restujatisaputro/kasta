import csv
from io import StringIO

from kasta_api.modules.mentors.schemas import MentorAggregateReport
from kasta_api.modules.reports.export import CellRow, _pdf, _rupiah, _xlsx


def build_mentor_csv(report: MentorAggregateReport) -> bytes:
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Laporan Pembinaan KASTA"])
    writer.writerow(["Dibuat pada", report.dashboard.generated_at.isoformat()])
    writer.writerow(["Keterangan", report.explanation])
    writer.writerow([])
    writer.writerow(
        [
            "UMKM",
            "Status",
            "Ikon",
            "Omzet bulan ini",
            "Pengeluaran bulan ini",
            "Perkiraan laba",
            "Utang",
            "Piutang",
            "Piutang terlambat",
            "Konsistensi pencatatan (%)",
            "Terakhir mencatat",
            "Rekomendasi terbuka",
        ]
    )
    for item in report.dashboard.businesses:
        writer.writerow(
            [
                item.business_name,
                item.health_label,
                item.health_icon,
                item.month_revenue,
                item.month_expense,
                item.month_profit,
                item.payable_balance,
                item.receivable_balance,
                item.overdue_receivable,
                item.recording_consistency,
                item.last_recorded_date or "Belum ada",
                item.open_recommendations,
            ]
        )
    return output.getvalue().encode("utf-8-sig")


def build_mentor_xlsx(report: MentorAggregateReport) -> bytes:
    summary: list[CellRow] = [
        ["Laporan Pembinaan KASTA"],
        ["Dibuat pada", report.dashboard.generated_at.isoformat()],
        ["Keterangan", report.explanation],
        [],
        ["UMKM binaan", report.dashboard.total_businesses],
        ["UMKM aktif", report.dashboard.active_businesses],
        ["Tidak mencatat > 7 hari", report.dashboard.stale_businesses],
        ["Pengeluaran melebihi pemasukan", report.dashboard.expense_over_income],
        ["Utang tinggi", report.dashboard.high_debt],
        ["Piutang terlambat", report.dashboard.overdue_receivables],
        ["Rekomendasi belum selesai", report.dashboard.open_recommendations],
        ["Perlu pendampingan", report.dashboard.health_red],
    ]
    businesses: list[CellRow] = [
        [
            "UMKM",
            "Status",
            "Omzet",
            "Pengeluaran",
            "Laba",
            "Utang",
            "Piutang",
            "Piutang terlambat",
            "Konsistensi (%)",
            "Terakhir mencatat",
        ]
    ]
    for business_item in report.dashboard.businesses:
        business_row: list[object] = [
            business_item.business_name,
            f"{business_item.health_icon} {business_item.health_label}",
            business_item.month_revenue,
            business_item.month_expense,
            business_item.month_profit,
            business_item.payable_balance,
            business_item.receivable_balance,
            business_item.overdue_receivable,
            business_item.recording_consistency,
            business_item.last_recorded_date or "Belum ada",
        ]
        businesses.append(business_row)
    schedule: list[CellRow] = [["UMKM", "Jadwal", "Durasi (menit)", "Cara", "Topik"]]
    for schedule_item in report.dashboard.upcoming_sessions:
        schedule_row: list[object] = [
            schedule_item.business_name,
            schedule_item.scheduled_at.isoformat(),
            schedule_item.duration_minutes,
            schedule_item.mode,
            schedule_item.topic,
        ]
        schedule.append(schedule_row)
    return _xlsx([("Ringkasan", summary), ("UMKM Binaan", businesses), ("Jadwal", schedule)])


def build_mentor_pdf(report: MentorAggregateReport) -> bytes:
    lines = [
        "LAPORAN PEMBINAAN KASTA",
        f"Dibuat pada: {report.dashboard.generated_at.isoformat()}",
        "",
        report.explanation,
        "",
        "RINGKASAN",
        f"Jumlah UMKM binaan: {report.dashboard.total_businesses}",
        f"UMKM aktif: {report.dashboard.active_businesses}",
        f"Tidak mencatat lebih dari 7 hari: {report.dashboard.stale_businesses}",
        f"Pengeluaran melebihi pemasukan: {report.dashboard.expense_over_income}",
        f"Utang tinggi: {report.dashboard.high_debt}",
        f"Piutang terlambat: {report.dashboard.overdue_receivables}",
        f"Rekomendasi belum selesai: {report.dashboard.open_recommendations}",
        "",
        "UMKM BINAAN",
    ]
    lines.extend(
        (
            f"{item.health_icon} {item.business_name} - {item.health_label}; omzet "
            f"{_rupiah(item.month_revenue)}; laba {_rupiah(item.month_profit)}; "
            f"utang {_rupiah(item.payable_balance)}; piutang "
            f"{_rupiah(item.receivable_balance)}"
        )
        for item in report.dashboard.businesses
    )
    lines.extend(["", "JADWAL PENDAMPINGAN"])
    lines.extend(
        f"{item.scheduled_at.isoformat()} - {item.business_name}: {item.topic}"
        for item in report.dashboard.upcoming_sessions
    )
    return _pdf(lines)

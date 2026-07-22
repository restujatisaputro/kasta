from collections import defaultdict
from datetime import UTC, date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException

from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.security import utc_now
from kasta_api.modules.businesses.models import Business, BusinessProfile
from kasta_api.modules.mentors.constants import (
    HEALTH_PRESENTATION,
    HealthLevel,
    MentorAccessScope,
    RecommendationStatus,
    SessionStatus,
)
from kasta_api.modules.mentors.models import (
    Mentor,
    MentorBusinessAccess,
    MentoringSession,
    MentorNote,
    Recommendation,
)
from kasta_api.modules.mentors.repository import MentorRepository
from kasta_api.modules.mentors.schemas import (
    MentorAggregateReport,
    MentorAuditResponse,
    MentorBusinessDetail,
    MentorBusinessSummary,
    MentorDashboard,
    MentoringSessionCreate,
    MentoringSessionResponse,
    MentoringSessionUpdate,
    MentorNoteCreate,
    MentorNoteResponse,
    MentorScheduleItem,
    MentorTrendPoint,
    RecommendationCreate,
    RecommendationResponse,
    RecommendationUpdate,
    RiskIndicator,
)
from kasta_api.modules.obligations.models import Notification
from kasta_api.modules.reports.repository import LedgerRow, ReportRepository

ZERO = Decimal("0.00")
MONEY = Decimal("0.01")
OPEN_RECOMMENDATIONS = {"OPEN", "IN_PROGRESS"}


class MentorService:
    def __init__(self, repository: MentorRepository, reports: ReportRepository) -> None:
        self.repository = repository
        self.reports = reports

    async def dashboard(
        self,
        mentor: Mentor,
        required_scopes: set[MentorAccessScope] | None = None,
    ) -> MentorDashboard:
        required_scopes = required_scopes or {MentorAccessScope.SUMMARY}
        rows = await self._visible_businesses(mentor.id, required_scopes)
        summaries = [
            await self._summary(mentor.id, access, business, profile)
            for access, business, profile in rows
        ]
        upcoming = [
            MentorScheduleItem(
                id=session.id,
                business_id=session.business_id,
                business_name=business_name,
                scheduled_at=session.scheduled_at,
                duration_minutes=session.duration_minutes,
                mode=session.mode,
                topic=session.topic,
            )
            for session, business_name in await self.repository.upcoming_sessions(
                mentor.id, utc_now()
            )
        ]
        result = MentorDashboard(
            total_businesses=len(summaries),
            active_businesses=sum(1 for item in summaries if self._is_active(item)),
            stale_businesses=sum(1 for item in summaries if not self._is_active(item)),
            expense_over_income=sum(
                1 for item in summaries if item.month_expense > item.month_revenue
            ),
            high_debt=sum(1 for item in summaries if self._has_risk(item, "HIGH_DEBT")),
            overdue_receivables=sum(1 for item in summaries if item.overdue_receivable > ZERO),
            open_recommendations=sum(item.open_recommendations for item in summaries),
            health_green=sum(1 for item in summaries if item.health_level == HealthLevel.GREEN),
            health_yellow=sum(1 for item in summaries if item.health_level == HealthLevel.YELLOW),
            health_red=sum(1 for item in summaries if item.health_level == HealthLevel.RED),
            upcoming_sessions=upcoming,
            businesses=sorted(
                summaries,
                key=lambda item: (
                    self._severity(item.health_level),
                    item.business_name.lower(),
                ),
                reverse=True,
            ),
            generated_at=utc_now(),
        )
        await self._record_reads(mentor, rows, "SUMMARY")
        return result

    async def businesses(self, mentor: Mentor) -> list[MentorBusinessSummary]:
        return (await self.dashboard(mentor)).businesses

    async def detail(self, mentor: Mentor, business_id: UUID) -> MentorBusinessDetail:
        access, business, profile = await self._required_visible_business(
            mentor.id,
            business_id,
            {MentorAccessScope.SUMMARY, MentorAccessScope.REPORTS},
        )
        summary = await self._summary(mentor.id, access, business, profile)
        start = self._shift_month(date.today().replace(day=1), -5)
        rows = await self.reports.ledger_rows(
            business_id,
            date_from=start,
            date_to=date.today(),
            category=None,
            payment_method=None,
        )
        result = MentorBusinessDetail(
            summary=summary,
            revenue_trend=self._trends(rows, start, 6),
            notes=[
                MentorNoteResponse.model_validate(note)
                for note in await self.repository.notes(mentor.id, business_id)
            ],
            recommendations=[
                RecommendationResponse.model_validate(item)
                for item in await self.repository.recommendations(mentor.id, business_id)
            ],
            sessions=[
                MentoringSessionResponse.model_validate(item)
                for item in await self.repository.sessions(mentor.id, business_id)
            ],
            explanation=self._detail_explanation(summary),
        )
        await self._record_reads(mentor, [(access, business, profile)], "DETAIL")
        return result

    async def aggregate_report(
        self, mentor: Mentor, *, require_export_scope: bool = False
    ) -> MentorAggregateReport:
        required_scopes = {MentorAccessScope.SUMMARY, MentorAccessScope.REPORTS}
        if require_export_scope:
            required_scopes.add(MentorAccessScope.EXPORT_REPORTS)
        dashboard = await self.dashboard(mentor, required_scopes)
        revenue = self._money(sum((item.month_revenue for item in dashboard.businesses), ZERO))
        expense = self._money(sum((item.month_expense for item in dashboard.businesses), ZERO))
        payables = self._money(sum((item.payable_balance for item in dashboard.businesses), ZERO))
        receivables = self._money(
            sum((item.receivable_balance for item in dashboard.businesses), ZERO)
        )
        return MentorAggregateReport(
            dashboard=dashboard,
            total_revenue=revenue,
            total_expense=expense,
            total_profit=self._money(revenue - expense),
            total_payables=payables,
            total_receivables=receivables,
            explanation=(
                f"Dari {dashboard.total_businesses} UMKM binaan, {dashboard.health_red} perlu "
                f"pendampingan dan {dashboard.health_yellow} perlu perhatian. Omzet gabungan "
                f"bulan ini {self._rupiah(revenue)} dengan perkiraan laba "
                f"{self._rupiah(revenue - expense)}."
            ),
        )

    async def create_note(
        self,
        mentor: Mentor,
        business_id: UUID,
        payload: MentorNoteCreate,
        *,
        request_id: str | None,
    ) -> MentorNoteResponse:
        await self._required_access(mentor.id, business_id, {MentorAccessScope.SUMMARY})
        note = MentorNote(
            id=uuid4(),
            business_id=business_id,
            mentor_id=mentor.id,
            content=payload.content,
            visibility=payload.visibility,
        )
        records: list[object] = [
            note,
            self._audit(
                mentor,
                business_id,
                "MENTOR_NOTE_CREATED",
                note.id,
                request_id=request_id,
                after={"visibility": note.visibility, "content": note.content},
            ),
        ]
        if payload.visibility == "SHARED":
            records.append(
                await self._notification(
                    business_id,
                    "MENTOR_NOTE",
                    note.id,
                    "Catatan baru dari pembina",
                    "Pembina menambahkan catatan baru untuk usaha Anda.",
                    date.today(),
                )
            )
        await self._save(note, records)
        return MentorNoteResponse.model_validate(note)

    async def create_recommendation(
        self,
        mentor: Mentor,
        business_id: UUID,
        payload: RecommendationCreate,
        *,
        request_id: str | None,
    ) -> RecommendationResponse:
        await self._required_access(mentor.id, business_id, {MentorAccessScope.SUMMARY})
        item = Recommendation(
            id=uuid4(),
            business_id=business_id,
            mentor_id=mentor.id,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            status=RecommendationStatus.OPEN.value,
            due_date=payload.due_date,
        )
        records: list[object] = [
            item,
            self._audit(
                mentor,
                business_id,
                "MENTOR_RECOMMENDATION_CREATED",
                item.id,
                request_id=request_id,
                after=self._recommendation_snapshot(item),
            ),
            await self._notification(
                business_id,
                "RECOMMENDATION",
                item.id,
                "Rekomendasi baru dari pembina",
                item.title,
                date.today(),
            ),
        ]
        await self._save(item, records)
        return RecommendationResponse.model_validate(item)

    async def update_recommendation(
        self,
        mentor: Mentor,
        business_id: UUID,
        recommendation_id: UUID,
        payload: RecommendationUpdate,
        *,
        request_id: str | None,
    ) -> RecommendationResponse:
        await self._required_access(mentor.id, business_id, {MentorAccessScope.SUMMARY})
        item = await self.repository.recommendation(mentor.id, business_id, recommendation_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Rekomendasi tidak ditemukan.")
        before = self._recommendation_snapshot(item)
        item.status = payload.status.value
        item.follow_up_note = payload.follow_up_note
        item.completed_at = utc_now() if payload.status == RecommendationStatus.DONE else None
        audit = self._audit(
            mentor,
            business_id,
            "MENTOR_RECOMMENDATION_UPDATED",
            item.id,
            request_id=request_id,
            before=before,
            after=self._recommendation_snapshot(item),
            reason=payload.follow_up_note,
        )
        await self._save(
            item,
            [
                audit,
                await self._notification(
                    business_id,
                    f"REC_STATUS_{item.status}",
                    item.id,
                    "Tindak lanjut rekomendasi diperbarui",
                    f"Rekomendasi '{item.title}' kini berstatus {item.status}.",
                    date.today(),
                ),
            ],
        )
        return RecommendationResponse.model_validate(item)

    async def create_session(
        self,
        mentor: Mentor,
        business_id: UUID,
        payload: MentoringSessionCreate,
        *,
        request_id: str | None,
    ) -> MentoringSessionResponse:
        await self._required_access(mentor.id, business_id, {MentorAccessScope.SUMMARY})
        scheduled_at = payload.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=UTC)
        item = MentoringSession(
            id=uuid4(),
            business_id=business_id,
            mentor_id=mentor.id,
            scheduled_at=scheduled_at,
            duration_minutes=payload.duration_minutes,
            mode=payload.mode,
            status=SessionStatus.SCHEDULED.value,
            topic=payload.topic,
            location=payload.location,
        )
        records: list[object] = [
            item,
            self._audit(
                mentor,
                business_id,
                "MENTOR_SESSION_SCHEDULED",
                item.id,
                request_id=request_id,
                after=self._session_snapshot(item),
            ),
            await self._notification(
                business_id,
                "MENTOR_SESSION",
                item.id,
                "Jadwal pendampingan baru",
                f"Pertemuan '{item.topic}' dijadwalkan pada {item.scheduled_at.isoformat()}.",
                item.scheduled_at.date(),
            ),
        ]
        await self._save(item, records)
        return MentoringSessionResponse.model_validate(item)

    async def update_session(
        self,
        mentor: Mentor,
        business_id: UUID,
        session_id: UUID,
        payload: MentoringSessionUpdate,
        *,
        request_id: str | None,
    ) -> MentoringSessionResponse:
        await self._required_access(mentor.id, business_id, {MentorAccessScope.SUMMARY})
        item = await self.repository.mentoring_session(mentor.id, business_id, session_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Kegiatan pendampingan tidak ditemukan.")
        before = self._session_snapshot(item)
        item.status = payload.status.value
        item.outcome = payload.outcome
        item.follow_up_date = payload.follow_up_date
        item.completed_at = utc_now() if payload.status == SessionStatus.COMPLETED else None
        audit = self._audit(
            mentor,
            business_id,
            "MENTOR_SESSION_UPDATED",
            item.id,
            request_id=request_id,
            before=before,
            after=self._session_snapshot(item),
            reason=payload.outcome,
        )
        await self._save(
            item,
            [
                audit,
                await self._notification(
                    business_id,
                    f"SESSION_STATUS_{item.status}",
                    item.id,
                    "Kegiatan pendampingan diperbarui",
                    f"Kegiatan '{item.topic}' kini berstatus {item.status}.",
                    date.today(),
                ),
            ],
        )
        return MentoringSessionResponse.model_validate(item)

    async def audits(self, mentor: Mentor) -> list[MentorAuditResponse]:
        business_ids = [
            business.id
            for _, business, _ in await self._visible_businesses(
                mentor.id, {MentorAccessScope.SUMMARY}
            )
        ]
        return [
            MentorAuditResponse(
                id=audit.id,
                business_id=audit.business_id,
                business_name=business_name,
                action=audit.action,
                entity_type=audit.entity_type,
                entity_id=audit.entity_id,
                reason=audit.reason,
                created_at=audit.created_at,
            )
            for audit, business_name in await self.repository.audits(mentor.user_id, business_ids)
        ]

    async def _summary(
        self,
        mentor_id: UUID,
        access: MentorBusinessAccess,
        business: Business,
        profile: BusinessProfile | None,
    ) -> MentorBusinessSummary:
        today = date.today()
        month_start = today.replace(day=1)
        period_rows = await self.reports.ledger_rows(
            business.id,
            date_from=month_start,
            date_to=today,
            category=None,
            payment_method=None,
        )
        cumulative_rows = await self.reports.ledger_rows(
            business.id,
            date_from=None,
            date_to=today,
            category=None,
            payment_method=None,
        )
        revenue = self._sum_type(period_rows, "REVENUE")
        expense = self._sum_type(period_rows, "EXPENSE")
        payable = self._account_balance(cumulative_rows, {"PAYABLE", "OTHER_PAYABLE"})
        receivable = self._account_balance(cumulative_rows, {"RECEIVABLE"})
        receivables = await self.reports.receivables(business.id)
        overdue_receivable = self._money(
            sum(
                (
                    item.remaining_amount
                    for item in receivables
                    if item.status != "CANCELLED"
                    and item.remaining_amount > ZERO
                    and item.due_date < today
                ),
                ZERO,
            )
        )
        latest = await self.repository.latest_recorded_date(business.id)
        days_since = (today - latest).days if latest is not None else None
        consistency = await self._consistency(business.id, today)
        recommendations = await self.repository.recommendations(mentor_id, business.id)
        open_count = sum(1 for item in recommendations if item.status in OPEN_RECOMMENDATIONS)
        indicators = self._risks(
            days_since=days_since,
            revenue=revenue,
            expense=expense,
            payable=payable,
            overdue_receivable=overdue_receivable,
            consistency=consistency,
        )
        health = max((item.level for item in indicators), key=self._severity)
        health_label, health_icon = HEALTH_PRESENTATION[health]
        return MentorBusinessSummary(
            business_id=business.id,
            business_name=business.name,
            city=profile.city if profile is not None else None,
            province=profile.province if profile is not None else None,
            health_level=health,
            health_label=health_label,
            health_icon=health_icon,
            last_recorded_date=latest,
            days_since_recording=days_since,
            recording_consistency=consistency,
            month_revenue=revenue,
            month_expense=expense,
            month_profit=self._money(revenue - expense),
            payable_balance=payable,
            receivable_balance=receivable,
            overdue_receivable=overdue_receivable,
            open_recommendations=open_count,
            risk_indicators=indicators,
        )

    async def _consistency(self, business_id: UUID, today: date) -> Decimal:
        start = today - timedelta(days=55)
        dates = await self.repository.recording_dates(business_id, start)
        active_weeks = {value - timedelta(days=value.weekday()) for value in dates}
        return self._money(Decimal(len(active_weeks)) / Decimal("8") * Decimal("100"))

    def _risks(
        self,
        *,
        days_since: int | None,
        revenue: Decimal,
        expense: Decimal,
        payable: Decimal,
        overdue_receivable: Decimal,
        consistency: Decimal,
    ) -> list[RiskIndicator]:
        risks: list[RiskIndicator] = []
        if days_since is None or days_since > 7:
            message = (
                "Belum ada pencatatan keuangan."
                if days_since is None
                else f"Tidak mencatat selama {days_since} hari."
            )
            risks.append(
                self._risk("STALE_RECORDING", HealthLevel.RED, "Pencatatan terhenti", message)
            )
        if expense > revenue and expense > ZERO:
            risks.append(
                self._risk(
                    "EXPENSE_OVER_INCOME",
                    HealthLevel.RED,
                    "Pengeluaran melebihi pemasukan",
                    f"Pengeluaran bulan ini lebih besar {self._rupiah(expense - revenue)}.",
                )
            )
        debt_ratio = (
            payable / revenue if revenue > ZERO else (Decimal("99") if payable > ZERO else ZERO)
        )
        if debt_ratio >= Decimal("1"):
            risks.append(
                self._risk(
                    "HIGH_DEBT",
                    HealthLevel.RED,
                    "Utang tinggi",
                    "Saldo utang setara atau melebihi omzet bulan ini.",
                )
            )
        elif debt_ratio >= Decimal("0.5"):
            risks.append(
                self._risk(
                    "HIGH_DEBT",
                    HealthLevel.YELLOW,
                    "Utang perlu diperhatikan",
                    "Saldo utang mencapai sedikitnya separuh omzet bulan ini.",
                )
            )
        if overdue_receivable > ZERO:
            risks.append(
                self._risk(
                    "OVERDUE_RECEIVABLE",
                    HealthLevel.RED,
                    "Piutang terlambat",
                    f"Piutang terlambat berjumlah {self._rupiah(overdue_receivable)}.",
                )
            )
        if consistency < Decimal("50") and not any(
            item.code == "STALE_RECORDING" for item in risks
        ):
            risks.append(
                self._risk(
                    "LOW_CONSISTENCY",
                    HealthLevel.YELLOW,
                    "Pencatatan belum konsisten",
                    "Pencatatan dilakukan pada kurang dari separuh delapan minggu terakhir.",
                )
            )
        if not risks:
            risks.append(
                self._risk(
                    "RELATIVELY_HEALTHY",
                    HealthLevel.GREEN,
                    "Relatif sehat",
                    "Belum ditemukan indikator yang memerlukan perhatian segera.",
                )
            )
        return risks

    @staticmethod
    def _risk(code: str, level: HealthLevel, label: str, message: str) -> RiskIndicator:
        return RiskIndicator(
            code=code,
            level=level,
            label=label,
            message=message,
            icon=HEALTH_PRESENTATION[level][1],
        )

    async def _visible_businesses(
        self, mentor_id: UUID, required_scopes: set[MentorAccessScope]
    ) -> list[tuple[MentorBusinessAccess, Business, BusinessProfile | None]]:
        return [
            row
            for row in await self.repository.access_businesses(mentor_id, now=utc_now())
            if self._has_scopes(row[0], required_scopes)
        ]

    async def _required_visible_business(
        self,
        mentor_id: UUID,
        business_id: UUID,
        required_scopes: set[MentorAccessScope],
    ) -> tuple[MentorBusinessAccess, Business, BusinessProfile | None]:
        for row in await self._visible_businesses(mentor_id, required_scopes):
            if row[1].id == business_id:
                return row
        raise HTTPException(status_code=404, detail="UMKM binaan tidak ditemukan.")

    async def _required_access(
        self,
        mentor_id: UUID,
        business_id: UUID,
        required_scopes: set[MentorAccessScope],
    ) -> MentorBusinessAccess:
        access = await self.repository.access(mentor_id, business_id, now=utc_now())
        if access is None:
            raise HTTPException(status_code=404, detail="UMKM binaan tidak ditemukan.")
        if not self._has_scopes(access, required_scopes):
            raise HTTPException(status_code=403, detail="Ruang lingkup izin tidak mencukupi.")
        await self.repository.touch_access(access, utc_now())
        return access

    async def _record_reads(
        self,
        mentor: Mentor,
        rows: list[tuple[MentorBusinessAccess, Business, BusinessProfile | None]],
        access_kind: str,
    ) -> None:
        now = utc_now()
        for access, business, _ in rows:
            await self.repository.touch_access(access, now)
            self.repository.add(
                self._audit(
                    mentor,
                    business.id,
                    "MENTOR_DATA_ACCESSED",
                    business.id,
                    request_id=None,
                    after={"access_kind": access_kind, "scope": list(access.scope)},
                )
            )
        if rows:
            await self.repository.commit()

    @staticmethod
    def _has_scopes(access: MentorBusinessAccess, required_scopes: set[MentorAccessScope]) -> bool:
        return {scope.value for scope in required_scopes}.issubset(set(access.scope))

    async def _notification(
        self,
        business_id: UUID,
        entity_type: str,
        entity_id: UUID,
        title: str,
        message: str,
        scheduled_for: date,
    ) -> Notification:
        return Notification(
            id=uuid4(),
            business_id=business_id,
            user_id=await self.repository.owner_user_id(business_id),
            notification_type=(
                "NEW_RECOMMENDATION"
                if entity_type == "RECOMMENDATION"
                else "MENTORING_SCHEDULE"
                if entity_type == "MENTOR_SESSION"
                else "NEW_RECOMMENDATION"
            ),
            title=title,
            message=message[:500],
            entity_type=entity_type,
            entity_id=entity_id,
            scheduled_for=scheduled_for,
            payload={"source": "mentor", "entity_id": str(entity_id)},
            action_path="/pembina",
        )

    async def _save(self, instance: object, records: list[object]) -> None:
        self.repository.add_all(records)
        try:
            await self.repository.commit()
            await self.repository.refresh(instance)
        except Exception:
            await self.repository.rollback()
            raise

    @staticmethod
    def _audit(
        mentor: Mentor,
        business_id: UUID,
        action: str,
        entity_id: UUID,
        *,
        request_id: str | None,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
        reason: str | None = None,
    ) -> AuditLog:
        return AuditLog(
            id=uuid4(),
            business_id=business_id,
            actor_user_id=mentor.user_id,
            action=action,
            entity_type="MENTOR_ACTIVITY",
            entity_id=entity_id,
            before_data=before,
            after_data=after,
            reason=reason,
            request_id=request_id,
            created_at=utc_now(),
        )

    @staticmethod
    def _recommendation_snapshot(item: Recommendation) -> dict[str, object]:
        return {
            "title": item.title,
            "priority": item.priority,
            "status": item.status,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "follow_up_note": item.follow_up_note,
        }

    @staticmethod
    def _session_snapshot(item: MentoringSession) -> dict[str, object]:
        return {
            "scheduled_at": item.scheduled_at.isoformat(),
            "status": item.status,
            "mode": item.mode,
            "topic": item.topic,
            "follow_up_date": item.follow_up_date.isoformat() if item.follow_up_date else None,
        }

    @staticmethod
    def _sum_type(rows: list[LedgerRow], account_type: str) -> Decimal:
        return MentorService._money(
            sum(
                (
                    MentorService._normal_amount(row)
                    for row in rows
                    if row.account_type == account_type
                ),
                ZERO,
            )
        )

    @staticmethod
    def _account_balance(rows: list[LedgerRow], keys: set[str]) -> Decimal:
        return MentorService._money(
            sum(
                (MentorService._normal_amount(row) for row in rows if row.account_key in keys),
                ZERO,
            )
        )

    @staticmethod
    def _normal_amount(row: LedgerRow) -> Decimal:
        return row.debit - row.credit if row.normal_balance == "DEBIT" else row.credit - row.debit

    def _trends(self, rows: list[LedgerRow], start: date, count: int) -> list[MentorTrendPoint]:
        values: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"revenue": ZERO, "expense": ZERO}
        )
        for row in rows:
            month = row.entry_date.strftime("%Y-%m")
            if row.account_type == "REVENUE":
                values[month]["revenue"] += self._normal_amount(row)
            elif row.account_type == "EXPENSE":
                values[month]["expense"] += self._normal_amount(row)
        result: list[MentorTrendPoint] = []
        for offset in range(count):
            month_date = self._shift_month(start, offset)
            key = month_date.strftime("%Y-%m")
            revenue = self._money(values[key]["revenue"])
            expense = self._money(values[key]["expense"])
            result.append(
                MentorTrendPoint(
                    month=key,
                    revenue=revenue,
                    expense=expense,
                    profit=self._money(revenue - expense),
                )
            )
        return result

    @staticmethod
    def _is_active(item: MentorBusinessSummary) -> bool:
        return item.days_since_recording is not None and item.days_since_recording <= 7

    @staticmethod
    def _has_risk(item: MentorBusinessSummary, code: str) -> bool:
        return any(risk.code == code for risk in item.risk_indicators)

    @staticmethod
    def _severity(level: HealthLevel) -> int:
        return {HealthLevel.GREEN: 1, HealthLevel.YELLOW: 2, HealthLevel.RED: 3}[level]

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)

    @classmethod
    def _rupiah(cls, value: Decimal) -> str:
        whole = int(cls._money(value))
        sign = "-" if whole < 0 else ""
        return f"{sign}Rp{abs(whole):,}".replace(",", ".")

    @classmethod
    def _detail_explanation(cls, summary: MentorBusinessSummary) -> str:
        return (
            f"{summary.business_name} memperoleh omzet {cls._rupiah(summary.month_revenue)} "
            f"dan perkiraan laba {cls._rupiah(summary.month_profit)} bulan ini. Status "
            f"pendampingan: {summary.health_label.lower()}."
        )

    @staticmethod
    def _shift_month(value: date, count: int) -> date:
        index = value.year * 12 + value.month - 1 + count
        return value.replace(year=index // 12, month=index % 12 + 1, day=1)

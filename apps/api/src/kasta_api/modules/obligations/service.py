from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException

from kasta_api.modules.accounting.constants import AccountKey, TransactionType
from kasta_api.modules.accounting.engine import TransactionCommand, round_money
from kasta_api.modules.accounting.repository import AccountingRepository
from kasta_api.modules.accounting.service import JournalService
from kasta_api.modules.audit.models import AuditLog
from kasta_api.modules.auth.security import utc_now
from kasta_api.modules.obligations.constants import (
    ACTIVE_STATUSES,
    ObligationKind,
    ObligationStatus,
)
from kasta_api.modules.obligations.models import (
    Customer,
    Notification,
    Payable,
    PayablePayment,
    Receivable,
    ReceivablePayment,
    Supplier,
)
from kasta_api.modules.obligations.repository import ObligationRepository
from kasta_api.modules.obligations.schemas import (
    AgingBucket,
    AgingReportResponse,
    AgingSection,
    CancellationRequest,
    NotificationResponse,
    ObligationCreateRequest,
    ObligationDetailResponse,
    ObligationListResponse,
    ObligationResponse,
    PartyCreateRequest,
    PartyResponse,
    PaymentCreateRequest,
    PaymentResponse,
    ReminderGenerationResponse,
    ReminderItem,
    ReminderListResponse,
)

STATUS_LABELS = {
    ObligationStatus.OPEN: "Belum Dibayar",
    ObligationStatus.PARTIALLY_PAID: "Dibayar Sebagian",
    ObligationStatus.PAID: "Sudah Lunas",
    ObligationStatus.OVERDUE: "Terlambat",
    ObligationStatus.CANCELLED: "Dibatalkan",
}
ZERO = Decimal("0.00")


class ObligationService:
    def __init__(
        self,
        repository: ObligationRepository,
        accounting_repository: AccountingRepository,
    ) -> None:
        self.repository = repository
        self.journal = JournalService(accounting_repository)

    async def create_party(
        self,
        business_id: UUID,
        payload: PartyCreateRequest,
        *,
        kind: ObligationKind,
    ) -> PartyResponse:
        receivable = kind == ObligationKind.RECEIVABLE
        existing = await self.repository.party_by_name(
            business_id, payload.name, receivable=receivable
        )
        if existing is not None:
            return PartyResponse.model_validate(existing)
        party = self._new_party(business_id, payload, receivable=receivable)
        self.repository.add(party)
        try:
            await self.repository.commit()
            await self.repository.refresh(party)
        except Exception:
            await self.repository.rollback()
            raise
        return PartyResponse.model_validate(party)

    async def list_parties(self, business_id: UUID, *, kind: ObligationKind) -> list[PartyResponse]:
        rows = await self.repository.list_parties(
            business_id, receivable=kind == ObligationKind.RECEIVABLE
        )
        return [PartyResponse.model_validate(row) for row in rows]

    async def create(
        self,
        business_id: UUID,
        actor_user_id: UUID,
        payload: ObligationCreateRequest,
        *,
        kind: ObligationKind,
        request_id: str | None,
    ) -> ObligationResponse:
        receivable = kind == ObligationKind.RECEIVABLE
        party = await self._resolve_party(business_id, payload, receivable=receivable)
        obligation_id = uuid4()
        amount = round_money(payload.initial_amount)
        description = f"Piutang kepada {party.name}" if receivable else f"Utang kepada {party.name}"
        command = TransactionCommand(
            transaction_type=(
                TransactionType.CREDIT_SALE if receivable else TransactionType.CREDIT_PURCHASE
            ),
            amount=amount,
            transaction_date=payload.transaction_date,
            description=description,
            category_account=(None if receivable else AccountKey.PURCHASES),
            idempotency_key=f"{kind.value.lower()}:{obligation_id}:initial",
            entry_kind="INCOME" if receivable else "EXPENSE",
            counterparty_name=party.name,
        )
        try:
            transaction = await self.journal.post_transaction(
                business_id,
                actor_user_id,
                command,
                request_id=request_id,
                auto_commit=False,
            )
            common = {
                "id": obligation_id,
                "business_id": business_id,
                "initial_transaction_id": transaction.id,
                "initial_amount": amount,
                "paid_amount": ZERO,
                "remaining_amount": amount,
                "transaction_date": payload.transaction_date,
                "due_date": payload.due_date,
                "status": self._status(ZERO, amount, payload.due_date).value,
                "note": payload.note or None,
                "reminder_enabled": payload.reminder_enabled,
                "reminder_days_before": payload.reminder_days_before,
            }
            obligation: Receivable | Payable
            if receivable:
                obligation = Receivable(customer_id=party.id, **common)
            else:
                obligation = Payable(supplier_id=party.id, **common)
            self.repository.add_all(
                [
                    obligation,
                    self._audit(
                        business_id,
                        actor_user_id,
                        f"{kind.value}_CREATED",
                        obligation_id,
                        after={
                            "party_id": str(party.id),
                            "initial_amount": str(amount),
                            "due_date": payload.due_date.isoformat(),
                        },
                        request_id=request_id,
                    ),
                ]
            )
            await self.repository.commit()
            await self.repository.refresh(obligation)
        except Exception:
            await self.repository.rollback()
            raise
        return self._response(obligation, party, kind)

    async def list_obligations(
        self,
        business_id: UUID,
        *,
        kind: ObligationKind,
        query: str | None,
        status: ObligationStatus | None,
        due_from: date | None,
        due_to: date | None,
        overdue_only: bool,
        limit: int,
        offset: int,
    ) -> ObligationListResponse:
        rows = (
            await self.repository.receivables(business_id)
            if kind == ObligationKind.RECEIVABLE
            else await self.repository.payables(business_id)
        )
        items: list[ObligationResponse] = []
        for row in rows:
            party = await self._party_for(row, kind)
            response = self._response(row, party, kind)
            normalized_query = query.strip().lower() if query else None
            if (
                normalized_query
                and normalized_query not in party.name.lower()
                and normalized_query not in (row.note or "").lower()
            ):
                continue
            if status is not None and response.status != status:
                continue
            if due_from is not None and row.due_date < due_from:
                continue
            if due_to is not None and row.due_date > due_to:
                continue
            if overdue_only and response.status != ObligationStatus.OVERDUE:
                continue
            items.append(response)
        total = len(items)
        return ObligationListResponse(
            items=items[offset : offset + limit], total=total, limit=limit, offset=offset
        )

    async def detail(
        self, business_id: UUID, obligation_id: UUID, *, kind: ObligationKind
    ) -> ObligationDetailResponse:
        obligation = await self._required(business_id, obligation_id, kind=kind)
        party = await self._party_for(obligation, kind)
        payments = await self._payments(business_id, obligation_id, kind)
        return ObligationDetailResponse(
            **self._response(obligation, party, kind).model_dump(),
            payments=[PaymentResponse.model_validate(payment) for payment in payments],
        )

    async def pay(
        self,
        business_id: UUID,
        obligation_id: UUID,
        actor_user_id: UUID,
        payload: PaymentCreateRequest,
        *,
        kind: ObligationKind,
        request_id: str | None,
    ) -> ObligationDetailResponse:
        obligation = await self._required(business_id, obligation_id, kind=kind, for_update=True)
        current_status = self._effective_status(obligation)
        if current_status in {ObligationStatus.PAID, ObligationStatus.CANCELLED}:
            raise HTTPException(status_code=409, detail="Tagihan ini tidak dapat dibayar lagi.")
        amount = round_money(payload.amount)
        if amount > obligation.remaining_amount:
            raise HTTPException(
                status_code=409,
                detail=f"Pembayaran melebihi sisa tagihan {obligation.remaining_amount}.",
            )
        receivable = kind == ObligationKind.RECEIVABLE
        party = await self._party_for(obligation, kind)
        payment_id = uuid4()
        transaction_type = (
            TransactionType.RECEIVABLE_RECEIPT if receivable else TransactionType.PAYABLE_PAYMENT
        )
        try:
            transaction = await self.journal.post_transaction(
                business_id,
                actor_user_id,
                TransactionCommand(
                    transaction_type=transaction_type,
                    amount=amount,
                    transaction_date=payload.payment_date,
                    description=(
                        f"Penerimaan piutang dari {party.name}"
                        if receivable
                        else f"Pembayaran utang kepada {party.name}"
                    ),
                    payment_account=AccountKey(payload.payment_account),
                    idempotency_key=f"{kind.value.lower()}:{obligation.id}:payment:{payment_id}",
                    entry_kind="INCOME" if receivable else "EXPENSE",
                    counterparty_name=party.name,
                ),
                request_id=request_id,
                auto_commit=False,
            )
            now = utc_now()
            payment: ReceivablePayment | PayablePayment
            common = {
                "id": payment_id,
                "business_id": business_id,
                "transaction_id": transaction.id,
                "amount": amount,
                "payment_date": payload.payment_date,
                "payment_account_key": payload.payment_account,
                "note": payload.note or None,
                "created_by_user_id": actor_user_id,
                "created_at": now,
            }
            if receivable:
                payment = ReceivablePayment(receivable_id=obligation.id, **common)
            else:
                payment = PayablePayment(payable_id=obligation.id, **common)
            before = obligation.remaining_amount
            obligation.paid_amount += amount
            obligation.remaining_amount -= amount
            obligation.status = self._status(
                obligation.paid_amount, obligation.remaining_amount, obligation.due_date
            ).value
            self.repository.add_all(
                [
                    payment,
                    self._audit(
                        business_id,
                        actor_user_id,
                        f"{kind.value}_PAYMENT_CREATED",
                        obligation.id,
                        before={"remaining_amount": str(before)},
                        after={
                            "payment_id": str(payment.id),
                            "paid_amount": str(obligation.paid_amount),
                            "remaining_amount": str(obligation.remaining_amount),
                            "status": obligation.status,
                        },
                        request_id=request_id,
                    ),
                ]
            )
            await self.repository.commit()
            await self.repository.refresh(obligation)
        except Exception:
            await self.repository.rollback()
            raise
        return await self.detail(business_id, obligation.id, kind=kind)

    async def cancel(
        self,
        business_id: UUID,
        obligation_id: UUID,
        actor_user_id: UUID,
        payload: CancellationRequest,
        *,
        kind: ObligationKind,
        request_id: str | None,
    ) -> ObligationResponse:
        obligation = await self._required(business_id, obligation_id, kind=kind, for_update=True)
        if obligation.status == ObligationStatus.CANCELLED.value:
            raise HTTPException(status_code=409, detail="Tagihan ini sudah dibatalkan.")
        if obligation.paid_amount > ZERO:
            raise HTTPException(
                status_code=409,
                detail="Tagihan yang sudah memiliki pembayaran tidak dapat langsung dibatalkan.",
            )
        party = await self._party_for(obligation, kind)
        try:
            reversal = await self.journal.reverse_transaction(
                business_id,
                obligation.initial_transaction_id,
                actor_user_id,
                reason=payload.reason,
                transaction_date=payload.cancellation_date,
                request_id=request_id,
                auto_commit=False,
            )
            obligation.status = ObligationStatus.CANCELLED.value
            obligation.cancellation_transaction_id = reversal.id
            obligation.cancelled_at = utc_now()
            obligation.cancelled_by_user_id = actor_user_id
            obligation.cancellation_reason = payload.reason
            self.repository.add(
                self._audit(
                    business_id,
                    actor_user_id,
                    f"{kind.value}_CANCELLED",
                    obligation.id,
                    after={
                        "status": obligation.status,
                        "cancellation_transaction_id": str(reversal.id),
                    },
                    reason=payload.reason,
                    request_id=request_id,
                )
            )
            await self.repository.commit()
            await self.repository.refresh(obligation)
        except Exception:
            await self.repository.rollback()
            raise
        return self._response(obligation, party, kind)

    async def aging(self, business_id: UUID, as_of: date) -> AgingReportResponse:
        receivables = await self.repository.receivables(business_id)
        payables = await self.repository.payables(business_id)
        return AgingReportResponse(
            as_of=as_of,
            receivables=self._aging_section(receivables, as_of),
            payables=self._aging_section(payables, as_of),
        )

    async def reminders(self, business_id: UUID, as_of: date) -> ReminderListResponse:
        items: list[ReminderItem] = []
        for kind, rows in (
            (ObligationKind.RECEIVABLE, await self.repository.receivables(business_id)),
            (ObligationKind.PAYABLE, await self.repository.payables(business_id)),
        ):
            for row in rows:
                if not row.reminder_enabled or self._effective_status(row, as_of) not in {
                    ObligationStatus.OPEN,
                    ObligationStatus.PARTIALLY_PAID,
                    ObligationStatus.OVERDUE,
                }:
                    continue
                days = (row.due_date - as_of).days
                if days > row.reminder_days_before:
                    continue
                party = await self._party_for(row, kind)
                items.append(
                    ReminderItem(
                        kind=kind,
                        obligation_id=row.id,
                        party_name=party.name,
                        due_date=row.due_date,
                        remaining_amount=row.remaining_amount,
                        days_until_due=days,
                        message=self._reminder_message(kind, party.name, days),
                    )
                )
        items.sort(key=lambda item: (item.due_date, item.party_name))
        return ReminderListResponse(as_of=as_of, items=items)

    async def generate_reminders(
        self, business_id: UUID, as_of: date
    ) -> ReminderGenerationResponse:
        candidates = await self.reminders(business_id, as_of)
        owner_user_id = await self.repository.owner_user_id(business_id)
        notifications: list[Notification] = []
        for item in candidates.items:
            if await self.repository.notification_exists(
                business_id, item.kind.value, item.obligation_id, as_of
            ):
                continue
            notification = Notification(
                id=uuid4(),
                business_id=business_id,
                user_id=owner_user_id,
                notification_type=(
                    "RECEIVABLE_DUE_SOON"
                    if item.kind == ObligationKind.RECEIVABLE
                    else "PAYABLE_DUE_SOON"
                ),
                title=(
                    "Pengingat Piutang"
                    if item.kind == ObligationKind.RECEIVABLE
                    else "Pengingat Utang"
                ),
                message=item.message,
                entity_type=item.kind.value,
                entity_id=item.obligation_id,
                scheduled_for=as_of,
                payload={
                    "party_name": item.party_name,
                    "due_date": item.due_date.isoformat(),
                    "remaining_amount": str(item.remaining_amount),
                    "days_until_due": item.days_until_due,
                },
                action_path=("/piutang" if item.kind == ObligationKind.RECEIVABLE else "/utang"),
            )
            notifications.append(notification)
        self.repository.add_all(list(notifications))
        try:
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise
        return ReminderGenerationResponse(
            generated_count=len(notifications),
            notification_ids=[notification.id for notification in notifications],
        )

    async def notifications(
        self, business_id: UUID, unread_only: bool
    ) -> list[NotificationResponse]:
        return [
            NotificationResponse.model_validate(row)
            for row in await self.repository.notifications(business_id, unread_only)
        ]

    async def _resolve_party(
        self, business_id: UUID, payload: ObligationCreateRequest, *, receivable: bool
    ) -> Customer | Supplier:
        if payload.party_id is not None:
            party = (
                await self.repository.customer(business_id, payload.party_id)
                if receivable
                else await self.repository.supplier(business_id, payload.party_id)
            )
            if party is None:
                raise HTTPException(
                    status_code=404, detail="Pelanggan atau pemasok tidak ditemukan."
                )
            return party
        name = payload.party_name or ""
        existing = await self.repository.party_by_name(business_id, name, receivable=receivable)
        if existing is not None:
            return existing
        party = self._new_party(
            business_id,
            PartyCreateRequest(name=name, phone=payload.party_phone, email=payload.party_email),
            receivable=receivable,
        )
        self.repository.add(party)
        await self.repository.flush()
        return party

    @staticmethod
    def _new_party(
        business_id: UUID, payload: PartyCreateRequest, *, receivable: bool
    ) -> Customer | Supplier:
        values = {
            "id": uuid4(),
            "business_id": business_id,
            "name": payload.name,
            "phone": payload.phone or None,
            "email": payload.email or None,
            "is_active": True,
        }
        return Customer(**values) if receivable else Supplier(**values)

    async def _required(
        self,
        business_id: UUID,
        obligation_id: UUID,
        *,
        kind: ObligationKind,
        for_update: bool = False,
    ) -> Receivable | Payable:
        obligation = (
            await self.repository.receivable(business_id, obligation_id, for_update=for_update)
            if kind == ObligationKind.RECEIVABLE
            else await self.repository.payable(business_id, obligation_id, for_update=for_update)
        )
        if obligation is None:
            raise HTTPException(status_code=404, detail="Tagihan tidak ditemukan.")
        return obligation

    async def _party_for(
        self, obligation: Receivable | Payable, kind: ObligationKind
    ) -> Customer | Supplier:
        party = (
            await self.repository.customer(obligation.business_id, obligation.customer_id)
            if isinstance(obligation, Receivable)
            else await self.repository.supplier(obligation.business_id, obligation.supplier_id)
        )
        if party is None:
            raise HTTPException(
                status_code=409, detail="Data pelanggan atau pemasok tidak tersedia."
            )
        return party

    async def _payments(
        self, business_id: UUID, obligation_id: UUID, kind: ObligationKind
    ) -> list[ReceivablePayment] | list[PayablePayment]:
        if kind == ObligationKind.RECEIVABLE:
            return await self.repository.receivable_payments(business_id, obligation_id)
        return await self.repository.payable_payments(business_id, obligation_id)

    def _response(
        self,
        obligation: Receivable | Payable,
        party: Customer | Supplier,
        kind: ObligationKind,
        as_of: date | None = None,
    ) -> ObligationResponse:
        effective = self._effective_status(obligation, as_of)
        return ObligationResponse(
            id=obligation.id,
            business_id=obligation.business_id,
            kind=kind,
            party=PartyResponse.model_validate(party),
            initial_transaction_id=obligation.initial_transaction_id,
            cancellation_transaction_id=obligation.cancellation_transaction_id,
            initial_amount=obligation.initial_amount,
            paid_amount=obligation.paid_amount,
            remaining_amount=obligation.remaining_amount,
            transaction_date=obligation.transaction_date,
            due_date=obligation.due_date,
            status=effective,
            status_label=STATUS_LABELS[effective],
            note=obligation.note,
            reminder_enabled=obligation.reminder_enabled,
            reminder_days_before=obligation.reminder_days_before,
            days_until_due=(obligation.due_date - (as_of or date.today())).days,
            created_at=obligation.created_at,
            updated_at=obligation.updated_at,
        )

    @staticmethod
    def _status(
        paid: Decimal,
        remaining: Decimal,
        due_date: date,
        as_of: date | None = None,
    ) -> ObligationStatus:
        today = as_of or date.today()
        if remaining == ZERO:
            return ObligationStatus.PAID
        if due_date < today:
            return ObligationStatus.OVERDUE
        if paid > ZERO:
            return ObligationStatus.PARTIALLY_PAID
        return ObligationStatus.OPEN

    def _effective_status(
        self, obligation: Receivable | Payable, as_of: date | None = None
    ) -> ObligationStatus:
        if obligation.status == ObligationStatus.CANCELLED.value:
            return ObligationStatus.CANCELLED
        return self._status(
            obligation.paid_amount, obligation.remaining_amount, obligation.due_date, as_of
        )

    def _aging_section(self, rows: list[Receivable] | list[Payable], as_of: date) -> AgingSection:
        definitions = (
            ("NOT_DUE", "Belum jatuh tempo"),
            ("DUE_1_30", "Terlambat 1-30 hari"),
            ("DUE_31_60", "Terlambat 31-60 hari"),
            ("DUE_61_90", "Terlambat 61-90 hari"),
            ("DUE_OVER_90", "Terlambat lebih dari 90 hari"),
        )
        values: dict[str, tuple[int, Decimal]] = {code: (0, ZERO) for code, _ in definitions}
        for row in rows:
            if self._effective_status(row, as_of).value not in ACTIVE_STATUSES:
                continue
            days = (as_of - row.due_date).days
            code = (
                "NOT_DUE"
                if days <= 0
                else "DUE_1_30"
                if days <= 30
                else "DUE_31_60"
                if days <= 60
                else "DUE_61_90"
                if days <= 90
                else "DUE_OVER_90"
            )
            count, amount = values[code]
            values[code] = (count + 1, amount + row.remaining_amount)
        buckets = [
            AgingBucket(code=code, label=label, count=values[code][0], amount=values[code][1])
            for code, label in definitions
        ]
        return AgingSection(
            total_open=sum((bucket.amount for bucket in buckets), ZERO), buckets=buckets
        )

    @staticmethod
    def _reminder_message(kind: ObligationKind, party_name: str, days: int) -> str:
        subject = "Piutang" if kind == ObligationKind.RECEIVABLE else "Utang"
        if days < 0:
            return f"{subject} {party_name} terlambat {abs(days)} hari."
        if days == 0:
            return f"{subject} {party_name} jatuh tempo hari ini."
        return f"{subject} {party_name} jatuh tempo dalam {days} hari."

    @staticmethod
    def _audit(
        business_id: UUID,
        actor_user_id: UUID,
        action: str,
        entity_id: UUID,
        *,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
        reason: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        return AuditLog(
            id=uuid4(),
            business_id=business_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type="OBLIGATION",
            entity_id=entity_id,
            before_data=before,
            after_data=after,
            reason=reason,
            request_id=request_id,
            created_at=utc_now(),
        )

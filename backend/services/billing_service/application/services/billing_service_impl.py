import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from services.billing_service.application.domain.transaction import (
    Transaction,
    TransactionType,
)
from services.billing_service.application.exceptions import UserNotFoundError
from services.billing_service.application.ports.input.billing_service import (
    BillingService,
)
from services.billing_service.application.ports.output.billing_repository import (
    BillingRepository,
)
from services.document_service.application.ports.output.document_job_repository import (
    DocumentJobRepository,
)
from shared.models.base_models import (
    TokenUsageRecord,
    UserBalance as UserBalanceResponse,
    TokenUsageSummary as TokenUsageSummaryResponse,
)

_DOCUMENT_TYPE_LABELS = {
    "NOTA_FISCAL_EMITIDA": "Notas fiscais emitidas",
    "NOTA_FISCAL_RECEBIDA": "Notas fiscais recebidas",
    "INFORME_BANCARIO": "Informes bancários",
    "INFORME_RENDIMENTOS": "Informes de rendimentos",
    "DESPESA_DEDUTIVEL": "Despesas dedutíveis",
    "DASN_SIMEI": "Declarações DASN-SIMEI",
    "RECIBO_IR_ANTERIOR": "Recibos de IR",
    "DOC_IDENTIFICACAO": "Documentos de identificação",
    "COMPROVANTE_ENDERECO": "Comprovantes de endereço",
}

_DEFAULT_DOCUMENT_CONTEXT = "Conhecimento geral do agente"

_TRANSACTION_TYPE_LABELS = {
    TransactionType.CHARGE: "consulta",
    TransactionType.REFUND: "estorno",
    TransactionType.INITIAL: "crédito inicial",
}


class BillingServiceImpl(BillingService):
    """
    Concrete implementation of the BillingService input port.
    """

    def __init__(
        self,
        billing_repository: BillingRepository,
        document_job_repository: Optional[DocumentJobRepository] = None,
    ):
        self.billing_repository = billing_repository
        self.document_job_repository = document_job_repository

    def charge_user(self, user_id: uuid.UUID, amount: int, description: str) -> bool:
        current_balance = self.billing_repository.get_user_balance(user_id)

        if not current_balance or current_balance.balance < amount:
            return False

        transaction = Transaction(
            id=uuid.uuid4(),
            user_id=user_id,
            amount=-amount,  # Charging deducts from the balance
            type=TransactionType.CHARGE,
            description=description,
            created_at=datetime.utcnow(),
        )

        try:
            self.billing_repository.create_transaction_and_update_balance(transaction)
            return True
        except Exception:
            return False

    def get_user_balance(self, user_id: uuid.UUID) -> UserBalanceResponse:
        balance = self.billing_repository.get_user_balance(user_id)
        if not balance:
            raise UserNotFoundError(f"Balance for user ID {user_id} not found.")

        return UserBalanceResponse.model_validate(balance, from_attributes=True)

    def get_user_transactions(self, user_id: uuid.UUID) -> List[TokenUsageRecord]:
        transactions = self.billing_repository.get_user_transactions(user_id)
        return [self._map_transaction_to_usage_record(tx) for tx in transactions]

    def get_user_monthly_usage(
        self, user_id: uuid.UUID
    ) -> TokenUsageSummaryResponse:
        start_date, end_date = self._get_current_month_range()
        usage = self.billing_repository.get_user_usage_in_period(
            user_id=user_id, start_date=start_date, end_date=end_date
        )
        return TokenUsageSummaryResponse.model_validate(
            usage, from_attributes=True
        )

    def _get_current_month_range(self) -> Tuple[datetime, datetime]:
        """Returns the datetime range covering the current month."""
        now = datetime.utcnow()
        start_of_month = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        if start_of_month.month == 12:
            start_next_month = start_of_month.replace(
                year=start_of_month.year + 1, month=1
            )
        else:
            start_next_month = start_of_month.replace(
                month=start_of_month.month + 1
            )

        return start_of_month, start_next_month

    def _map_transaction_to_usage_record(
        self, transaction: Transaction
    ) -> TokenUsageRecord:
        consultation_type = self._infer_consultation_type(transaction)
        document_label = self._resolve_document_label(transaction)
        description = self._build_friendly_description(transaction, document_label)

        return TokenUsageRecord(
            id=transaction.id,
            date=transaction.created_at,
            tokens=abs(transaction.amount),
            consultation_type=consultation_type,
            description=description,
            document_type=document_label,
        )

    def _infer_consultation_type(self, transaction: Transaction) -> str:
        base_label = _TRANSACTION_TYPE_LABELS.get(transaction.type, "consulta")

        if transaction.type == TransactionType.CHARGE and transaction.description:
            lowered = transaction.description.lower()
            if "chat" in lowered:
                return "chat"
            if "análise" in lowered or "analise" in lowered:
                return "análise"
        return base_label

    def _resolve_document_label(self, transaction: Transaction) -> str:
        if transaction.type != TransactionType.CHARGE:
            return "Operação financeira"

        if (
            self.document_job_repository is None
            or transaction.related_job_id is None
        ):
            return _DEFAULT_DOCUMENT_CONTEXT

        job = self.document_job_repository.get_by_id(transaction.related_job_id)
        if not job or getattr(job, "document_type", None) is None:
            return _DEFAULT_DOCUMENT_CONTEXT

        document_type_value = getattr(job.document_type, "value", job.document_type)
        if isinstance(document_type_value, str):
            document_type_key = document_type_value
        else:
            document_type_key = str(document_type_value)

        return _DOCUMENT_TYPE_LABELS.get(
            document_type_key,
            document_type_key.replace("_", " ").title(),
        )

    def _build_friendly_description(
        self, transaction: Transaction, document_label: str
    ) -> str:
        localized_description = self._localize_description(transaction.description)

        if not localized_description:
            localized_description = self._default_description_for_type(transaction.type)

        if document_label:
            return f"{localized_description} (Documentos: {document_label})"
        return localized_description

    def _localize_description(self, description: Optional[str]) -> Optional[str]:
        if not description:
            return None

        normalized = description.strip()
        lowered = normalized.lower()

        if lowered.startswith("chat with agent"):
            agent_name = normalized[len("chat with agent") :].strip()
            return (
                f"Conversa com o agente {agent_name}"
                if agent_name
                else "Conversa com o agente"
            )

        return normalized

    def _default_description_for_type(self, transaction_type: TransactionType) -> str:
        if transaction_type == TransactionType.CHARGE:
            return "Uso de tokens"
        if transaction_type == TransactionType.REFUND:
            return "Estorno de tokens"
        if transaction_type == TransactionType.INITIAL:
            return "Crédito inicial de tokens"
        return "Operação de tokens"

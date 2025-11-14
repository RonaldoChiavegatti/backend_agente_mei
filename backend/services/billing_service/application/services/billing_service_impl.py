import uuid
from datetime import datetime
from typing import List, Tuple

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
from shared.models.base_models import (
    Transaction as TransactionResponse,
    UserBalance as UserBalanceResponse,
    TokenUsageSummary as TokenUsageSummaryResponse,
)


class BillingServiceImpl(BillingService):
    """
    Concrete implementation of the BillingService input port.
    """

    def __init__(self, billing_repository: BillingRepository):
        self.billing_repository = billing_repository

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

    def get_user_transactions(self, user_id: uuid.UUID) -> List[TransactionResponse]:
        transactions = self.billing_repository.get_user_transactions(user_id)
        return [
            TransactionResponse.model_validate(tx, from_attributes=True)
            for tx in transactions
        ]

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

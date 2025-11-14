from abc import ABC, abstractmethod
from typing import List
import uuid

from shared.models.base_models import (
    UserBalance as UserBalanceResponse,
    TokenUsageRecord,
    TokenUsageSummary as TokenUsageSummaryResponse,
)


class BillingService(ABC):
    """Input port defining the billing service use cases."""

    @abstractmethod
    def charge_user(self, user_id: uuid.UUID, amount: int, description: str) -> bool:
        """
        Charges a user a specific amount of tokens.
        Returns True on success, False on failure (e.g., insufficient funds).
        """
        pass

    @abstractmethod
    def get_user_balance(self, user_id: uuid.UUID) -> UserBalanceResponse:
        """Retrieves the current balance for a user."""
        pass

    @abstractmethod
    def get_user_transactions(self, user_id: uuid.UUID) -> List[TokenUsageRecord]:
        """Retrieves the transaction history for a user."""
        pass

    @abstractmethod
    def get_user_monthly_usage(
        self, user_id: uuid.UUID
    ) -> TokenUsageSummaryResponse:
        """Retrieves aggregated usage information for the current month."""
        pass

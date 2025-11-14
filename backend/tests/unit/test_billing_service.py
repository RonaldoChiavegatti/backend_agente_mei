import unittest
from unittest.mock import MagicMock
import uuid
from datetime import datetime

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.billing_service.application.services.billing_service_impl import (
    BillingServiceImpl,
)
from services.billing_service.application.domain.balance import UserBalance
from services.billing_service.application.domain.usage_summary import UserMonthlyUsage
from services.billing_service.application.exceptions import UserNotFoundError
from services.billing_service.application.ports.output.billing_repository import (
    BillingRepository,
)


class TestBillingService(unittest.TestCase):
    def setUp(self):
        self.mock_billing_repo = MagicMock(spec=BillingRepository)
        self.service = BillingServiceImpl(billing_repository=self.mock_billing_repo)

        self.user_id = uuid.uuid4()
        self.test_balance = UserBalance(
            user_id=self.user_id, balance=100, last_updated_at=datetime.utcnow()
        )

    def test_charge_user_success(self):
        # Arrange
        self.mock_billing_repo.get_user_balance.return_value = self.test_balance
        self.mock_billing_repo.create_transaction_and_update_balance.return_value = (
            None,
            None,
        )

        # Act
        success = self.service.charge_user(
            user_id=self.user_id, amount=50, description="Test charge"
        )

        # Assert
        self.assertTrue(success)
        self.mock_billing_repo.get_user_balance.assert_called_once_with(self.user_id)
        self.mock_billing_repo.create_transaction_and_update_balance.assert_called_once()

    def test_charge_user_insufficient_funds(self):
        # Arrange
        self.mock_billing_repo.get_user_balance.return_value = self.test_balance

        # Act
        success = self.service.charge_user(
            user_id=self.user_id, amount=200, description="Test charge"
        )

        # Assert
        self.assertFalse(success)
        self.mock_billing_repo.get_user_balance.assert_called_once_with(self.user_id)
        self.mock_billing_repo.create_transaction_and_update_balance.assert_not_called()

    def test_charge_user_no_balance_record(self):
        # Arrange
        self.mock_billing_repo.get_user_balance.return_value = None

        # Act
        success = self.service.charge_user(
            user_id=self.user_id, amount=50, description="Test charge"
        )

        # Assert
        self.assertFalse(success)
        self.mock_billing_repo.create_transaction_and_update_balance.assert_not_called()

    def test_get_user_balance_success(self):
        # Arrange
        self.mock_billing_repo.get_user_balance.return_value = self.test_balance

        # Act
        result = self.service.get_user_balance(user_id=self.user_id)

        # Assert
        self.assertEqual(result.balance, 100)
        self.assertEqual(result.user_id, self.user_id)

    def test_get_user_balance_not_found(self):
        # Arrange
        self.mock_billing_repo.get_user_balance.return_value = None

        # Act & Assert
        with self.assertRaises(UserNotFoundError):
            self.service.get_user_balance(user_id=self.user_id)

    def test_get_user_monthly_usage(self):
        # Arrange
        start_date = datetime(2024, 5, 1)
        end_date = datetime(2024, 6, 1)
        usage_summary = UserMonthlyUsage(
            user_id=self.user_id,
            tokens_consumed=30,
            consultations_count=3,
            start_date=start_date,
            end_date=end_date,
        )

        self.service._get_current_month_range = MagicMock(
            return_value=(start_date, end_date)
        )
        self.mock_billing_repo.get_user_usage_in_period.return_value = (
            usage_summary
        )

        # Act
        result = self.service.get_user_monthly_usage(user_id=self.user_id)

        # Assert
        self.assertEqual(result.tokens_consumed, 30)
        self.assertEqual(result.consultations_count, 3)
        self.mock_billing_repo.get_user_usage_in_period.assert_called_once_with(
            user_id=self.user_id, start_date=start_date, end_date=end_date
        )


if __name__ == "__main__":
    unittest.main()

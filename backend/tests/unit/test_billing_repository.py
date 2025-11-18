import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services.billing_service.application.domain.transaction import (
    Transaction,
    TransactionType,
)
from services.billing_service.infrastructure.adapters.persistence.postgres_billing_repository import (
    PostgresBillingRepository,
)
from services.billing_service.infrastructure.database import (
    Base,
    TransactionModel,
    UserBalanceModel,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _seed_balance(session, user_id: uuid.UUID, balance: int = 0):
    session.add(UserBalanceModel(user_id=user_id, balance=balance))
    session.commit()


def test_create_transaction_and_update_balance_is_atomic():
    session = _session()
    user_id = uuid.uuid4()
    _seed_balance(session, user_id=user_id, balance=100)

    repo = PostgresBillingRepository(session)
    transaction = Transaction(
        id=uuid.uuid4(),
        user_id=user_id,
        amount=-30,
        type=TransactionType.CHARGE,
        description="token charge",
        related_job_id=None,
        created_at=datetime.utcnow(),
    )

    updated_balance, created_transaction = repo.create_transaction_and_update_balance(
        transaction
    )

    persisted_balance = (
        session.query(UserBalanceModel)
        .filter(UserBalanceModel.user_id == user_id)
        .one()
    )
    persisted_transaction = session.query(TransactionModel).one()

    assert updated_balance.balance == 70
    assert persisted_balance.balance == 70
    assert created_transaction.amount == -30
    assert persisted_transaction.amount == -30
    assert created_transaction.id == persisted_transaction.id
    assert persisted_transaction.type == TransactionType.CHARGE


def test_get_user_usage_in_period_sums_charges_only():
    session = _session()
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    _seed_balance(session, user_id=user_id)

    now = datetime(2024, 3, 15)
    start = datetime(2024, 3, 1)
    end = datetime(2024, 4, 1)

    charges = [
        TransactionModel(
            id=uuid.uuid4(),
            user_id=user_id,
            amount=-10,
            type=TransactionType.CHARGE,
            description="consulta",
            related_job_id=None,
            created_at=now,
        ),
        TransactionModel(
            id=uuid.uuid4(),
            user_id=user_id,
            amount=-25,
            type=TransactionType.CHARGE,
            description="consulta 2",
            related_job_id=None,
            created_at=now + timedelta(days=1),
        ),
        TransactionModel(
            id=uuid.uuid4(),
            user_id=other_user_id,
            amount=-50,
            type=TransactionType.CHARGE,
            description="outro usuario",
            related_job_id=None,
            created_at=now,
        ),
        TransactionModel(
            id=uuid.uuid4(),
            user_id=user_id,
            amount=15,
            type=TransactionType.REFUND,
            description="reembolso",
            related_job_id=None,
            created_at=now,
        ),
    ]

    session.add_all(charges)
    session.commit()

    repo = PostgresBillingRepository(session)
    usage = repo.get_user_usage_in_period(user_id=user_id, start_date=start, end_date=end)

    assert usage.tokens_consumed == 35
    assert usage.consultations_count == 2
    assert usage.start_date == start
    assert usage.end_date == end

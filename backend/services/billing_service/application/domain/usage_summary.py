import uuid
from datetime import datetime

from pydantic import BaseModel


class UserMonthlyUsage(BaseModel):
    """Aggregated usage information for a user within a month."""

    user_id: uuid.UUID
    tokens_consumed: int
    consultations_count: int
    start_date: datetime
    end_date: datetime

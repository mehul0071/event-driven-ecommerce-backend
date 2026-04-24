from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass
class OrderCreatedEvent:
    order_id: UUID
    occurred_at: datetime

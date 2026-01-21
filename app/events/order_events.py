from dataclasses import dataclass
from datetime import datetime

@dataclass
class OrderCreatedEvent:
    order_id: int
    occurred_at: datetime

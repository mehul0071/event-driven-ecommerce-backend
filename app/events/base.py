from dataclasses import dataclass
from datetime import datetime

@dataclass
class Event:
    occurred_at: datetime

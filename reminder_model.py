import datetime
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import List


class TriggerType(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class ReminderTask:
    id: str
    content: str
    trigger_type: TriggerType
    trigger_time: datetime.time
    weekdays: List[int]
    next_trigger: datetime.datetime
    created_at: datetime.datetime
    updated_at: datetime.datetime = field(default_factory=datetime.datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "trigger_type": self.trigger_type.value,
            "trigger_time": self.trigger_time.strftime("%H:%M"),
            "weekdays": self.weekdays,
            "next_trigger": self.next_trigger.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data["id"],
            content=data["content"],
            trigger_type=TriggerType(data["trigger_type"]),
            trigger_time=datetime.datetime.strptime(data["trigger_time"], "%H:%M").time(),
            weekdays=data["weekdays"],
            next_trigger=datetime.datetime.fromisoformat(data["next_trigger"]),
            created_at=datetime.datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.datetime.fromisoformat(data["updated_at"])
        )

    @classmethod
    def create(cls, content: str, trigger_type: TriggerType, trigger_time: datetime.time, weekdays: List[int] = None):
        now = datetime.datetime.now()
        next_trigger = cls._calculate_next_trigger(trigger_type, trigger_time, now, weekdays or [])

        return cls(
            id=str(uuid.uuid4()),
            content=content,
            trigger_type=trigger_type,
            trigger_time=trigger_time,
            weekdays=weekdays or [],
            next_trigger=next_trigger,
            created_at=now,
            updated_at=now
        )

    @staticmethod
    def _calculate_next_trigger(trigger_type: TriggerType, trigger_time: datetime.time, now: datetime.datetime, weekdays: List[int]) -> datetime.datetime:
        today = now.date()
        trigger_datetime = datetime.datetime.combine(today, trigger_time)

        if trigger_type == TriggerType.ONCE:
            return trigger_datetime
        elif trigger_type == TriggerType.DAILY:
            if trigger_datetime > now:
                return trigger_datetime
            else:
                return trigger_datetime + datetime.timedelta(days=1)
        elif trigger_type == TriggerType.WEEKLY:
            for offset in range(7):
                test_date = today + datetime.timedelta(days=offset)
                if test_date.weekday() in weekdays:
                    test_datetime = datetime.datetime.combine(test_date, trigger_time)
                    if test_datetime > now:
                        return test_datetime
            return trigger_datetime + datetime.timedelta(days=7)

        return trigger_datetime

    def calculate_next_trigger(self):
        self.next_trigger = self._calculate_next_trigger(
            self.trigger_type,
            self.trigger_time,
            datetime.datetime.now(),
            self.weekdays
        )
        self.updated_at = datetime.datetime.now()

    def is_due(self) -> bool:
        return datetime.datetime.now() >= self.next_trigger

    def is_soon(self, hours: int = 24) -> bool:
        time_diff = self.next_trigger - datetime.datetime.now()
        return 0 < time_diff.total_seconds() <= hours * 3600
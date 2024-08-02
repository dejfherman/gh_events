from typing import Sequence
from sqlalchemy import String, Integer, DateTime, ForeignKey, select, func, and_
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session
from database import Base
from datetime import datetime, timedelta


# EventWindow.key declares an event type, value then holds relevant events of that type
type EventWindow = dict[str, list[Event]]


class Repository(Base):
    __tablename__ = 'repository'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(39))
    owner: Mapped[str] = mapped_column(String(50))
    remote_id: Mapped[int] = mapped_column(Integer, unique=True)
    events: Mapped[list["Event"]] = relationship("Event", back_populates="repository")

    def get_last_event(self, db: Session) -> "Event":
        """Returns the latest Event instance associated with this repository. None if there are no events.
        """
        last_datetime_subquery = (
            select(func.max(Event.created_at))
            .filter(Event.repository_id == self.remote_id)
            .scalar_subquery()
        )
        statement = (
            select(Event)
            .where(Event.repository_id == self.remote_id)
            .where(Event.created_at == last_datetime_subquery)
        )
        return db.execute(statement).scalar_one_or_none()

    def get_recent_events(self, db: Session, max_events: int = 500) -> Sequence["Event"]:
        """Returns a sequence of Events associated with this Repository ordered by date. Returned sequence contains
        up to max_events amount of events or up to week old events, whichever is more limiting.
        """
        week_ago = datetime.now() - timedelta(days=7)

        statement = (
            select(Event)
            .where(Event.created_at >= week_ago, Event.repository_id == self.remote_id)
            .order_by(Event.created_at.desc())
            .limit(max_events)
        )

        return db.execute(statement).scalars().all()

    def get_recent_events_by_type(self, db: Session) -> EventWindow:
        """Returns recent events sorted into a dictionary by their types.
        """
        all_events = self.get_recent_events(db)
        sorted_events = {}

        for event in all_events:
            if event.type not in sorted_events:
                sorted_events[event.type] = []
            sorted_events[event.type].append(event)

        return sorted_events


class Event(Base):
    __tablename__ = 'event'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    remote_id: Mapped[int] = mapped_column(Integer, unique=True, sqlite_on_conflict_unique='IGNORE')
    type: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    repository_id: Mapped[int] = mapped_column(Integer, ForeignKey('repository.remote_id'))
    repository: Mapped["Repository"] = relationship("Repository", back_populates="events")

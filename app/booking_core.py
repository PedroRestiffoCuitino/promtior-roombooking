"""Room-booking domain logic (business rules).

Pure-Python + sqlite3 implementation of the booking system described in the
Promtior technical challenge. The same rules are exposed later as REST
endpoints (FastAPI) and as tools for the LLM agent.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from .config import ROOM_CAPACITIES, OFFICE_OPEN, OFFICE_CLOSE, SLOT_MINUTES, MAX_BOOKING_MINUTES


class BookingError(Exception):
    """Raised when a booking violates any business rule."""


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _validate_slot_alignment(dt: datetime) -> None:
    if dt.minute not in (0, 30) or dt.second != 0 or dt.microsecond != 0:
        raise BookingError(
            f"Times must be aligned to 30-minute slots (got {dt:%H:%M})."
        )


@dataclass
class Booking:
    id: int
    room: str
    date: str          # YYYY-MM-DD
    start: str         # HH:MM
    end: str           # HH:MM
    title: str
    attendees: int
    user: str

    def to_dict(self) -> dict:
        return asdict(self)


class BookingSystem:
    """Booking engine: enforces capacity, slot, contiguity, duration and
    no-overlap rules. Storage is a local SQLite file."""

    def __init__(self, db_path: str = "bookings.db"):
        self._lock = threading.Lock()
        self._db = sqlite3.connect(db_path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.execute(
                """CREATE TABLE IF NOT EXISTS bookings (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       room TEXT NOT NULL,
                       date TEXT NOT NULL,
                       start TEXT NOT NULL,
                       end TEXT NOT NULL,
                       title TEXT NOT NULL,
                       attendees INTEGER NOT NULL,
                       user TEXT NOT NULL
                   )"""
            )
            self._db.commit()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _overlaps(self, room: str, date: str, start: str, end: str,
                  exclude_id: int | None = None) -> list[Booking]:
        """Return existing bookings for that room/day that overlap [start, end).

        Overlap rule: an appointment starting exactly when another ends does
        NOT conflict (e.g. 10:00–11:30 blocks until 11:30, so 11:30–12:00 is fine).
        """
        rows = self._db.execute(
            "SELECT * FROM bookings WHERE room = ? AND date = ?"
            + (" AND id != ?" if exclude_id else "")
            + " ORDER BY start",
            (room, date, exclude_id) if exclude_id else (room, date),
        ).fetchall()
        s, e = _minutes(start), _minutes(end)
        conflicts = []
        for r in rows:
            os_, oe = _minutes(r["start"]), _minutes(r["end"])
            if s < oe and e > os_:
                conflicts.append(self._row_to_booking(r))
        return conflicts

    @staticmethod
    def _row_to_booking(row: sqlite3.Row) -> Booking:
        return Booking(id=row["id"], room=row["room"], date=row["date"],
                       start=row["start"], end=row["end"], title=row["title"],
                       attendees=row["attendees"], user=row["user"])

    # ------------------------------------------------------------------ #
    # Public API (this surface becomes the agent tools + REST endpoints)
    # ------------------------------------------------------------------ #
    def create_booking(self, room: str, date: str, start: str, end: str,
                       title: str, attendees: int, user: str,
                       allow_past: bool = False) -> Booking:
        # --- basic validation ---
        if room not in ROOM_CAPACITIES:
            raise BookingError(
                f"Unknown room '{room}'. Available: {', '.join(ROOM_CAPACITIES)}."
            )
        if not title or not title.strip():
            raise BookingError("A non-empty title is required (e.g. 'Interview with John Doe').")
        if not isinstance(attendees, int) or isinstance(attendees, bool) or attendees < 1:
            raise BookingError("Attendees must be an integer >= 1.")
        if attendees > ROOM_CAPACITIES[room]:
            raise BookingError(
                f"Room {room} holds up to {ROOM_CAPACITIES[room]} people; "
                f"{attendees} attendees exceed its capacity."
            )

        # --- time validation ---
        try:
            start_dt = datetime.strptime(f"{date} {start}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date} {end}", "%Y-%m-%d %H:%M")
        except ValueError:
            raise BookingError("Invalid date/time format. Expected date=YYYY-MM-DD, time=HH:MM.")
        if end_dt <= start_dt:
            raise BookingError("End time must be after start time.")
        _validate_slot_alignment(start_dt)
        _validate_slot_alignment(end_dt)
        duration = (end_dt - start_dt).total_seconds() / 60
        if duration % SLOT_MINUTES != 0:
            raise BookingError("Duration must be a multiple of 30 minutes.")
        if duration < SLOT_MINUTES:
            raise BookingError("Minimum booking is one 30-minute slot.")
        if duration > MAX_BOOKING_MINUTES:
            raise BookingError(
                f"Max duration is {MAX_BOOKING_MINUTES // 60} hours; requested {duration / 60:.1f}."
            )
        if _minutes(start) < _minutes(OFFICE_OPEN) or _minutes(end) > _minutes(OFFICE_CLOSE):
            raise BookingError(
                f"Booking must be within office hours ({OFFICE_OPEN}–{OFFICE_CLOSE})."
            )
        if not allow_past and start_dt < datetime.now().replace(second=0, microsecond=0):
            raise BookingError("Cannot book a slot in the past.")

        # --- overlap validation ---
        conflicts = self._overlaps(room, date, start, end)
        if conflicts:
            c = conflicts[0]
            raise BookingError(
                f"Room {room} is already booked {c.start}–{c.end} "
                f"('{c.title}' by {c.user}). No double bookings allowed."
            )

        with self._lock:
            cur = self._db.execute(
                "INSERT INTO bookings (room, date, start, end, title, attendees, user)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (room, date, start, end, title.strip(), attendees, user),
            )
            self._db.commit()
            new_id = cur.lastrowid
        return self.get_booking(new_id)

    def get_booking(self, booking_id: int) -> Booking:
        row = self._db.execute("SELECT * FROM bookings WHERE id = ?",
                               (booking_id,)).fetchone()
        if row is None:
            raise BookingError(f"Booking #{booking_id} not found.")
        return self._row_to_booking(row)

    def cancel_booking(self, booking_id: int, user: str) -> Booking:
        """Only the user who created the booking may cancel it."""
        booking = self.get_booking(booking_id)
        if booking.user != user:
            raise BookingError(
                f"Booking #{booking_id} belongs to {booking.user}; "
                f"the logged-in user ({user}) cannot cancel it."
            )
        with self._lock:
            self._db.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
            self._db.commit()
        return booking

    def list_available_rooms(self, date: str, start: str, end: str,
                             attendees: int = 1) -> list[dict]:
        """Rooms free for the ENTIRE requested range with enough capacity."""
        if not isinstance(attendees, int) or isinstance(attendees, bool) or attendees < 1:
            raise BookingError("Attendees must be an integer >= 1.")
        available = []
        for room, capacity in ROOM_CAPACITIES.items():
            if capacity < attendees:
                continue
            if not self._overlaps(room, date, start, end):
                available.append({"room": room, "capacity": capacity})
        return available

    def get_room_schedule(self, room: str, date: str,
                          start: str, end: str) -> dict:
        """Slot-by-slot availability for one room within a date/time range."""
        if room not in ROOM_CAPACITIES:
            raise BookingError(f"Unknown room '{room}'.")
        bookings = self._overlaps(room, date, start, end)
        slots = []
        cursor = datetime.strptime(f"{date} {start}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{date} {end}", "%Y-%m-%d %H:%M")
        while cursor < end_dt:
            slot_end = cursor + timedelta(minutes=SLOT_MINUTES)
            occupied = next(
                (b for b in bookings
                 if cursor < datetime.strptime(f"{date} {b.end}", "%Y-%m-%d %H:%M")
                 and slot_end > datetime.strptime(f"{date} {b.start}", "%Y-%m-%d %H:%M")),
                None,
            )
            slots.append({
                "start": f"{cursor:%H:%M}",
                "end": f"{slot_end:%H:%M}",
                "status": "occupied" if occupied else "available",
                "booking": occupied.to_dict() if occupied else None,
            })
            cursor = slot_end
        return {"room": room, "date": date, "capacity": ROOM_CAPACITIES[room], "slots": slots}

    def list_bookings(self, user: str | None = None) -> list[Booking]:
        rows = (self._db.execute("SELECT * FROM bookings WHERE user = ? ORDER BY date, start", (user,))
                if user else
                self._db.execute("SELECT * FROM bookings ORDER BY date, start")).fetchall()
        return [self._row_to_booking(r) for r in rows]

"""LangChain tools that expose the booking system to the LLM agent.

These are the ONLY way the LLM interacts with the booking engine: the model
decides *which* tool to call and *with which arguments*; all business rules
stay in BookingSystem.
"""

from __future__ import annotations

from langchain_core.tools import tool

from .booking_core import BookingError, BookingSystem


def build_tools(system: BookingSystem, user: str) -> list:
    """Create the agent tool set, bound to the authenticated user."""

    @tool
    def create_booking(room: str, date: str, start: str, end: str,
                       title: str, attendees: int) -> str:
        """Book a meeting room for the logged-in user.

        Args:
            room: One of the rooms A, B, C, D, E.
            date: Booking date, YYYY-MM-DD.
            start: Start time HH:MM, aligned to 30 minutes (e.g. 10:00).
            end: End time HH:MM. Duration must be a multiple of 30 minutes, max 3 hours.
            title: Short meeting title, e.g. "Interview with John Doe".
            attendees: Number of people (must not exceed the room capacity).
        """
        try:
            b = system.create_booking(room, date, start, end, title, attendees, user)
        except BookingError as e:
            return f"Booking failed: {e}"
        return (f"Booking #{b.id} confirmed: room {b.room}, {b.date} "
                f"{b.start}-{b.end}, '{b.title}', {b.attendees} attendee(s), "
                f"booked by {b.user}.")

    @tool
    def list_available_rooms(date: str, start: str, end: str,
                             attendees: int = 1) -> str:
        """List rooms free for the WHOLE requested range that fit the attendees."""
        try:
            rooms = system.list_available_rooms(date, start, end, attendees)
        except BookingError as e:
            return f"Error: {e}"
        if not rooms:
            return "No room is available for that range with the requested capacity."
        caps = ", ".join(f"{r['room']} (capacity {r['capacity']})" for r in rooms)
        return f"Available rooms for {date} {start}-{end} ({attendees} attendee(s)): {caps}."

    @tool
    def get_room_schedule(room: str, date: str, start: str, end: str) -> str:
        """Show the 30-minute slot grid (available/occupied) for one room."""
        try:
            sched = system.get_room_schedule(room, date, start, end)
        except BookingError as e:
            return f"Error: {e}"
        lines = [f"Schedule for room {room} on {date} (capacity {sched['capacity']}):"]
        for s in sched["slots"]:
            line = f"- {s['start']}-{s['end']}: {s['status']}"
            if s["booking"]:
                line += f" -> '{s['booking']['title']}' by {s['booking']['user']}"
            lines.append(line)
        return "\n".join(lines)

    @tool
    def cancel_booking(booking_id: int) -> str:
        """Cancel one of YOUR bookings by its id (use list_my_bookings to find ids)."""
        try:
            b = system.cancel_booking(booking_id, user)
        except BookingError as e:
            return f"Cancellation failed: {e}"
        return (f"Booking #{b.id} cancelled: room {b.room}, {b.date} "
                f"{b.start}-{b.end}, '{b.title}'.")

    @tool
    def list_my_bookings() -> str:
        """List all bookings made by you (shows the ids needed to cancel)."""
        bookings = system.list_bookings(user=user)
        if not bookings:
            return "You have no bookings."
        lines = [
            f"#{b.id}: room {b.room}, {b.date} {b.start}-{b.end}, "
            f"'{b.title}', {b.attendees} attendee(s)"
            for b in bookings
        ]
        return "Your bookings:\n" + "\n".join(lines)

    return [create_booking, list_available_rooms, get_room_schedule,
            cancel_booking, list_my_bookings]

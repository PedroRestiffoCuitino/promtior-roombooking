"""LangChain tools that expose the booking system to the LLM agent."""

from langchain_core.tools import tool
from app.booking_core import BookingSystem


def build_tools(system: BookingSystem, user: str):
    """Create the agent tool set, bound to the authenticated user."""

    @tool
    def create_booking(room: str, start_time: str, end_time: str,
                       title: str, attendees: int) -> str:
        """Book a meeting room for the logged-in user.

        Args:
            room: One of the rooms A, B, C, D, E.
            start_time: Start datetime ISO 8601 (e.g. 2026-09-21T10:00).
            end_time: End datetime ISO 8601. Duration must be multiple of 30 min, max 3 hours.
            title: Short meeting title, e.g. "Interview with John Doe".
            attendees: Number of people (must not exceed the room capacity).
        """
        result = system.create_booking(
            room=room, user_id=user, title=title,
            start_time=start_time, end_time=end_time, attendees=attendees
        )
        if not result["success"]:
            return f"Booking failed: {result['error']}"
        return (f"Booking #{result['booking_id']} confirmed: room {result['room']}, "
                f"{result['start_time']} to {result['end_time']}, "
                f"'{result['title']}', {result['attendees']} attendee(s).")

    @tool
    def list_available_rooms(start_time: str, end_time: str,
                             attendees: int = 1) -> str:
        """List rooms free for the WHOLE requested range that fit the attendees."""
        rooms = system.list_available_rooms(start_time, end_time, attendees)
        if not rooms:
            return "No room is available for that range with the requested capacity."
        caps = ", ".join(f"{r['name']} (capacity {r['capacity']})" for r in rooms)
        return f"Available rooms for {start_time} to {end_time} ({attendees} attendee(s)): {caps}."

    @tool
    def get_room_schedule(room: str, start_time: str, end_time: str) -> str:
        """Show bookings (available vs occupied) for one room in a time range."""
        sched = system.get_room_schedule(room, start_time, end_time)
        if "error" in sched:
            return f"Error: {sched['error']}"
        bookings = sched["bookings"]
        if not bookings:
            return f"Room {room} has no bookings between {start_time} and {end_time}."
        lines = [f"Schedule for room {room}:"]
        for b in bookings:
            lines.append(f"- {b['start_time']} to {b['end_time']}: '{b['title']}' by {b['user_id']} ({b['attendees']} people)")
        return "\n".join(lines)

    @tool
    def cancel_booking(booking_id: int) -> str:
        """Cancel one of YOUR bookings by its id."""
        result = system.cancel_booking(booking_id, user)
        if not result["success"]:
            return f"Cancellation failed: {result['error']}"
        return result["message"]

    @tool
    def list_my_bookings() -> str:
        """List all bookings made by you (shows the ids needed to cancel)."""
        bookings = system.list_bookings(user_id=user)
        if not bookings:
            return "You have no bookings."
        lines = [
            f"#{b['booking_id']}: room {b['room']}, {b['start_time']} to {b['end_time']}, "
            f"'{b['title']}', {b['attendees']} attendee(s)"
            for b in bookings
        ]
        return "Your bookings:\n" + "\n".join(lines)

    return [create_booking, list_available_rooms, get_room_schedule,
            cancel_booking, list_my_bookings]
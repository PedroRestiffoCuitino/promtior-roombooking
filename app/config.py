"""Central configuration: rooms, capacities and office hours."""

# The office "Cubo Itaú" has five rooms (A–E).
# NOTE: the challenge PDF requires "room-specific capacities" but does not
# provide the numbers, so they are defined here (documented in /doc).
ROOM_CAPACITIES = {
    "A": 4,
    "B": 6,
    "C": 8,
    "D": 12,
    "E": 20,
}

# Office operating hours (bookings must fit entirely inside this window).
OFFICE_OPEN = "08:00"
OFFICE_CLOSE = "20:00"

SLOT_MINUTES = 30          # bookings are made in 30-minute slots
MAX_BOOKING_MINUTES = 180  # max 3 hours per appointment (contiguous slots)

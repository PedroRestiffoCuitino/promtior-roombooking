"""Test suite for the booking business rules (edge cases from the challenge)."""

import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.booking_core import BookingSystem, BookingError

# Always use a far-future date so "no past bookings" never interferes.
TOMORROW = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
NEXT_WEEK = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")

PASS, FAIL = 0, 0


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  PASS  {name}")
    except AssertionError as e:
        FAIL += 1
        print(f"  FAIL  {name} -> {e}")
    except BookingError as e:
        FAIL += 1
        print(f"  FAIL  {name} -> unexpected BookingError: {e}")


def expect_error(msg_part):
    def decorator(fn):
        def wrapper():
            try:
                fn()
            except BookingError as e:
                assert msg_part.lower() in str(e).lower(), f"error '{e}' missing '{msg_part}'"
                return
            raise AssertionError(f"expected BookingError containing '{msg_part}'")
        return wrapper
    return decorator


def make_system():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return BookingSystem(db_path=path)


# ---------------------------------------------------------------- setup
bs = make_system()

# 1. Happy path: contiguous multi-slot booking (90 min = 3 slots, 1 appointment)
def t_create():
    b = bs.create_booking("C", TOMORROW, "10:00", "11:30", "Sprint planning", 8, "User1")
    assert b.id and b.user == "User1" and b.attendees == 8
check("create booking 10:00-11:30 (3 contiguous slots, one appointment)", t_create)

# 2. Example from the PDF: booking 10:00–11:30 blocks any start before 11:30
@expect_error("already booked")
def t_overlap_1():
    bs.create_booking("C", TOMORROW, "10:30", "11:00", "Overlap mid", 2, "User2")
check("no overlap: 10:30-11:00 inside 10:00-11:30 rejected", t_overlap_1)

@expect_error("already booked")
def t_overlap_2():
    bs.create_booking("C", TOMORROW, "09:00", "10:30", "Overlap start", 2, "User2")
check("no overlap: 09:00-10:30 crossing start rejected", t_overlap_2)

# 3. But a booking starting exactly at 11:30 IS allowed
def t_back_to_back():
    b = bs.create_booking("C", TOMORROW, "11:30", "12:00", "Back-to-back", 3, "User2")
    assert b.start == "11:30"
check("booking starting exactly at 11:30 allowed (end-exclusive rule)", t_back_to_back)

# 4. Other rooms unaffected by room C bookings
def t_other_room():
    b = bs.create_booking("A", TOMORROW, "10:00", "10:30", "1:1", 2, "User1")
    assert b.room == "A"
check("same time in another room is fine", t_other_room)

# 5. Capacity enforcement per room
@expect_error("capacity")
def t_capacity():
    bs.create_booking("A", NEXT_WEEK, "09:00", "09:30", "Too many", 5, "User1")  # A holds 4
check("capacity: 5 attendees in room A (max 4) rejected", t_capacity)

def t_capacity_edge():
    b = bs.create_booking("A", NEXT_WEEK, "09:00", "09:30", "Exactly full", 4, "User2")
    assert b.attendees == 4
check("capacity: exactly 4 in room A accepted", t_capacity_edge)

# 6. Slot alignment and duration rules
@expect_error("30-minute")
def t_alignment():
    bs.create_booking("B", NEXT_WEEK, "09:15", "10:00", "Bad alignment", 2, "User1")
check("slot alignment: 09:15 start rejected", t_alignment)

@expect_error("30-minute")
def t_duration():
    bs.create_booking("B", NEXT_WEEK, "09:00", "10:15", "Bad duration", 2, "User1")
check("duration must be multiple of 30 min", t_duration)

@expect_error("3 hours")
def t_max_3h():
    bs.create_booking("B", NEXT_WEEK, "09:00", "12:30", "Too long", 2, "User1")
check("max duration: 3.5h rejected", t_max_3h)

def t_exactly_3h():
    b = bs.create_booking("B", NEXT_WEEK, "14:00", "17:00", "3h workshop", 2, "User1")
    assert b.end == "17:00"
check("exactly 3h accepted (6 contiguous slots, one appointment)", t_exactly_3h)

@expect_error("end time")
def t_end_before_start():
    bs.create_booking("B", NEXT_WEEK, "11:00", "10:00", "Inverted", 2, "User1")
check("end before start rejected", t_end_before_start)

# 7. Office hours
@expect_error("office hours")
def t_office_hours():
    bs.create_booking("B", NEXT_WEEK, "19:30", "20:30", "Late", 2, "User1")
check("outside office hours (08:00-20:00) rejected", t_office_hours)

# 8. Title required
@expect_error("title")
def t_title():
    bs.create_booking("B", NEXT_WEEK, "10:00", "10:30", "   ", 2, "User1")
check("empty title rejected", t_title)

# 9. Unknown room
@expect_error("unknown room")
def t_room():
    bs.create_booking("F", NEXT_WEEK, "10:00", "10:30", "Ghost room", 2, "User1")
check("unknown room F rejected", t_room)

# 10. Past booking
@expect_error("past")
def t_past():
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    bs.create_booking("B", yesterday, "10:00", "10:30", "Yesterday", 2, "User1")
check("past slot rejected", t_past)

# 11. list_available_rooms: C is busy 10:00-11:30 tomorrow, attendees 8
def t_available():
    rooms = bs.list_available_rooms(TOMORROW, "10:00", "11:30", attendees=8)
    names = [r["room"] for r in rooms]
    # A(4) and B(6) excluded by capacity; C booked 10:00-11:30; D and E free
    assert sorted(names) == ["D", "E"]
check("list_available excludes occupied/too-small rooms", t_available)

def t_available_capacity_filter():
    rooms = bs.list_available_rooms(TOMORROW, "18:00", "19:00", attendees=15)
    assert [r["room"] for r in rooms] == ["E"]
check("capacity filter: only room E fits 15 people", t_available_capacity_filter)

# 12. get_room_schedule
def t_schedule():
    sched = bs.get_room_schedule("C", TOMORROW, "09:30", "12:30")
    status = {s["start"]: s["status"] for s in sched["slots"]}
    assert status["10:00"] == "occupied" and status["11:00"] == "occupied"
    assert status["11:30"] == "occupied"  # back-to-back booking
    assert status["09:30"] == "available" and status["12:00"] == "available"
    occ = [s for s in sched["slots"] if s["status"] == "occupied"]
    assert occ[0]["booking"]["title"] == "Sprint planning"
check("room schedule shows occupied vs available slots", t_schedule)

# 13. Cancel: own booking ok, other user's rejected
def t_cancel_ok():
    b = bs.create_booking("D", NEXT_WEEK, "09:00", "09:30", "To cancel", 5, "User1")
    cancelled = bs.cancel_booking(b.id, "User1")
    assert cancelled.title == "To cancel"
    try:
        bs.get_booking(b.id)
        raise AssertionError("booking should be gone")
    except BookingError:
        pass
check("cancel own booking works and frees the slot", t_cancel_ok)

@expect_error("cannot cancel")
def t_cancel_other():
    b = bs.create_booking("D", NEXT_WEEK, "10:00", "10:30", "User2 meeting", 5, "User2")
    bs.cancel_booking(b.id, "User1")
check("User1 cannot cancel User2's booking", t_cancel_other)

# 14. After cancel, slot is free again
def t_slot_freed():
    rooms = bs.list_available_rooms(NEXT_WEEK, "09:00", "09:30", attendees=5)
    assert "D" in [r["room"] for r in rooms]
check("cancelled slot becomes available again", t_slot_freed)

# 15. list_bookings per user
def t_list_user():
    mine = bs.list_bookings(user="User1")
    assert all(b.user == "User1" for b in mine) and len(mine) >= 3
check("list_bookings filters by user", t_list_user)

print(f"\n=== {PASS} passed, {FAIL} failed ===")
sys.exit(1 if FAIL else 0)

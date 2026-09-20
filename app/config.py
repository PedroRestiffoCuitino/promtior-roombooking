from datetime import time

ROOMS = [
    {"name": "A", "capacity": 4},
    {"name": "B", "capacity": 6},
    {"name": "C", "capacity": 8},
    {"name": "D", "capacity": 12},
    {"name": "E", "capacity": 20},
]

ROOMS_BY_NAME = {r["name"]: r for r in ROOMS}

OFFICE_OPEN = time(8, 0)
OFFICE_CLOSE = time(20, 0)

SLOT_MINUTES = 30
MAX_DURATION_MINUTES = 180
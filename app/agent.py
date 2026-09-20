import os
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from app.config import ROOM_CAPACITIES

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

SYSTEM_PROMPT = f"""You are a helpful room-booking assistant for an office called Cubo Itaú.

Your job is to help users book meeting rooms through natural conversation.
You have access to tools that interact with the booking system.

Available rooms and capacities:
{chr(10).join(f"- Room {room}: max {capacity} people" for room, capacity in ROOM_CAPACITIES.items())}

Booking rules:
- Slots are 30 minutes, aligned to the hour or half-hour (e.g. 09:00, 09:30).
- Maximum booking duration is 3 hours (6 contiguous slots).
- A room can only have one booking per slot (no overlaps).
- The user must provide: room, date, start time, end time, title, and number of attendees.
- If any information is missing, ask the user conversationally before calling the tool.
- When listing rooms, mention capacity so the user can choose appropriately.
- Office hours: 08:00 to 20:00.
- Today is {__import__('datetime').date.today().isoformat()}.

Always respond in the same language the user is using.
"""


def build_agent(system, user):
    """Build a ReAct agent bound to a specific user and booking system."""
    from app.tools import build_tools

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")

    tools = build_tools(system, user)

    llm = ChatGroq(
        api_key=api_key,
        model=DEFAULT_MODEL,
        temperature=0.2,
    )
    return create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)
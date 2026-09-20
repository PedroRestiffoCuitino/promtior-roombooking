"""LLM agent (tool-calling chatbot) built with LangGraph + Groq (free API)."""

from __future__ import annotations

import os
from datetime import date

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from .booking_core import BookingSystem
from .tools import build_tools

SYSTEM_PROMPT = """You are a helpful assistant for the meeting-room booking system of the office "Cubo Itaú". You help employees book, inspect and cancel meeting rooms through the tools available to you.

Rooms and capacities: A=4, B=6, C=8, D=12, E=20 people.
Rules: 30-minute slots (times aligned to :00 or :30), max 3 hours per booking, no overlapping bookings in the same room, bookings only within office hours 08:00-20:00.
Today's date: {today}.

Guidelines:
- If the user is missing information (room, date, time range, title or number of attendees), ask for it conversationally, one thing at a time.
- Use list_available_rooms when the user has no specific room in mind or when the requested room is busy, to propose alternatives.
- Use get_room_schedule to show a room's agenda.
- Confirm the details with the user BEFORE calling create_booking.
- Use list_my_bookings and cancel_booking for cancellations; never try to cancel another user's booking.
- Keep answers short, clear and friendly. Format times as HH:MM and dates as YYYY-MM-DD."""


def build_agent(system: BookingSystem, user: str):
    """Build a fresh agent bound to a specific authenticated user."""
    llm = ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    )
    tools = build_tools(system, user)
    return create_react_agent(llm, tools,
                              prompt=SYSTEM_PROMPT.format(today=date.today()))

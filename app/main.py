"""FastAPI service exposing the booking system and the chatbot agent.

Run with:  uvicorn app.main:app --reload
Docs at:   http://localhost:8000/docs
"""

from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .agent import build_agent
from .auth import create_token, decode_token, verify_user
from .booking_core import BookingError, BookingSystem
from .schemas import BookingCreateRequest, ChatRequest, LoginRequest, TokenResponse

DB_PATH = os.getenv("BOOKING_DB", "bookings.db")
system = BookingSystem(db_path=DB_PATH)

app = FastAPI(title="Promtior Room Booking API", version="1.0.0")
bearer = HTTPBearer()


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    user = decode_token(creds.credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    if not verify_user(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_token(body.username))


@app.post("/bookings", status_code=201)
def create_booking(body: BookingCreateRequest, user: str = Depends(get_current_user)):
    try:
        b = system.create_booking(**body.model_dump(), user=user)
    except BookingError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return b.to_dict()


@app.get("/bookings")
def my_bookings(user: str = Depends(get_current_user)):
    return [b.to_dict() for b in system.list_bookings(user=user)]


@app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: int, user: str = Depends(get_current_user)):
    try:
        return system.cancel_booking(booking_id, user).to_dict()
    except BookingError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/rooms/available")
def available_rooms(date: str, start: str, end: str, attendees: int = 1):
    try:
        return system.list_available_rooms(date, start, end, attendees)
    except BookingError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/rooms/{room}/schedule")
def room_schedule(room: str, date: str, start: str, end: str):
    try:
        return system.get_room_schedule(room, date, start, end)
    except BookingError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/chat")
def chat(body: ChatRequest, user: str = Depends(get_current_user)):
    """Conversational endpoint: the LLM agent answers using its tools."""
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured")
    agent = build_agent(system, user)
    result = agent.invoke({"messages": [("user", body.message)]})
    return {"reply": result["messages"][-1].content}

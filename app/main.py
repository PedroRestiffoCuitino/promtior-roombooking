"""FastAPI service exposing the booking system and the chatbot agent.

Run with:  uvicorn app.main:app --reload
Docs at:   http://localhost:8000/docs
"""

import os
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.agent import build_agent
from app.auth import create_token, decode_token, verify_user
from app.booking_core import BookingSystem
from app.schemas import BookingCreateRequest, ChatRequest, LoginRequest, TokenResponse

system = BookingSystem()

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
    result = system.create_booking(
        room=body.room, user_id=user, title=body.title,
        start_time=body.start_time, end_time=body.end_time, attendees=body.attendees
    )
    if not result["success"]:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@app.get("/bookings")
def my_bookings(user: str = Depends(get_current_user)):
    return system.list_bookings(user_id=user)


@app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: int, user: str = Depends(get_current_user)):
    result = system.cancel_booking(booking_id, user)
    if not result["success"]:
        raise HTTPException(status_code=403, detail=result["error"])
    return result


@app.get("/rooms/available")
def available_rooms(start_time: str, end_time: str, attendees: int = 1):
    return system.list_available_rooms(start_time, end_time, attendees)


@app.get("/rooms/{room}/schedule")
def room_schedule(room: str, start_time: str, end_time: str):
    return system.get_room_schedule(room, start_time, end_time)


@app.post("/chat")
def chat(body: ChatRequest, user: str = Depends(get_current_user)):
    """Conversational endpoint: the LLM agent answers using its tools."""
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured")
    agent = build_agent(system, user)
    result = agent.invoke({"messages": [("user", body.message)]})
    return {"reply": result["messages"][-1].content}
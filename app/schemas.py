"""Pydantic schemas for the REST API."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BookingCreateRequest(BaseModel):
    room: str = Field(..., examples=["C"])
    date: str = Field(..., examples=["2026-09-25"])
    start: str = Field(..., examples=["10:00"])
    end: str = Field(..., examples=["11:30"])
    title: str = Field(..., examples=["Interview with John Doe"])
    attendees: int = Field(..., examples=[6])


class ChatRequest(BaseModel):
    message: str

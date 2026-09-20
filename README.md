# Promtior Technical Challenge — Room Booking Chatbot

Chatbot with **tool-calling capabilities** that lets employees of the Cubo Itaú office
book meeting rooms through a conversational interface.

## Stack

| Layer | Technology |
|---|---|
| LLM (free API, no credit card) | **Groq** — Llama 3.3 70B via `langchain-groq` |
| Agent framework | **LangGraph** `create_react_agent` (tool-calling) |
| Booking system | Pure Python domain core + SQLite |
| REST API | **FastAPI** (JWT auth) |
| UI | **Streamlit** chat |
| Deploy | Docker → Hugging Face Spaces / Railway |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export GROQ_API_KEY="gsk_..."        # free key: https://console.groq.com
export JWT_SECRET="some-random-secret"   # optional, dev default exists

# Option A: conversational UI
streamlit run ui/streamlit_app.py

# Option B: REST API (+ interactive docs at http://localhost:8000/docs)
uvicorn app.main:app --reload

# Tests (business rules, no external services needed)
python tests/run_tests.py
```

## Credentials (defined by the challenge)

- Users: `User1`, `User2` — password: `TechnicalChallengePromtior`

## Business rules

- Rooms A–E with capacities A=4, B=6, C=8, D=12, E=20 *(capacities are not given in
  the challenge PDF; this assignment is a documented decision, see `/doc`)*
- 30-minute slots, bookings may combine **contiguous** slots up to **3 hours max**
- One booking per slot — **no overlaps** within the same room (end-exclusive:
  a room booked 10:00–11:30 is free again from 11:30, as in the challenge example)
- Attendees must fit the room capacity; every booking requires a title
- A user can only cancel **their own** bookings
- Office hours 08:00–20:00; past slots cannot be booked

## Repository layout

```
app/
  config.py         # rooms, capacities, office hours
  booking_core.py   # domain logic + SQLite persistence
  auth.py           # User1/User2 login, JWT tokens
  tools.py          # LangChain tools (the agent's only door to the system)
  agent.py          # Groq LLM + ReAct agent with system prompt
  main.py           # FastAPI REST API (also exposes POST /chat)
  schemas.py        # Pydantic request/response models
ui/streamlit_app.py # conversational interface with login
tests/run_tests.py  # 23 business-rule tests
notebook/           # Jupyter notebook explaining the technologies
doc/                # architecture overview + component diagram
```

## Documentation & notebook

See [`doc/architecture.md`](doc/architecture.md) for the approach, key decisions and
the component diagram, and [`notebook/challenge_notebook.ipynb`](notebook/challenge_notebook.ipynb)
for a guided explanation of the technologies with runnable code.

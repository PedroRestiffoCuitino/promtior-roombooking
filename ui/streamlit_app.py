"""Conversational UI (Streamlit) for the room-booking chatbot.

Run with:  streamlit run ui/streamlit_app.py
Requires the GROQ_API_KEY environment variable.
"""

import os

import streamlit as st

from app.agent import build_agent
from app.auth import verify_user
from app.booking_core import BookingSystem

st.set_page_config(page_title="Cubo Itaú Room Booking", page_icon="🏢")

if "system" not in st.session_state:
    st.session_state.system = BookingSystem(os.getenv("BOOKING_DB", "bookings.db"))
if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ------------------------------------------------------------------ login
if st.session_state.user is None:
    st.title("🏢 Cubo Itaú — Room Booking Assistant")
    st.caption("Sign in to book and manage meeting rooms (A–E).")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Sign in"):
            if verify_user(username.strip(), password):
                st.session_state.user = username.strip()
                st.rerun()
            else:
                st.error("Invalid credentials.")
    st.stop()

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.write(f"Signed in as **{st.session_state.user}**")
    if st.button("Sign out"):
        st.session_state.user = None
        st.session_state.messages = []
        st.rerun()
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.subheader("My bookings")
    mine = st.session_state.system.list_bookings(user=st.session_state.user)
    if mine:
        for b in mine:
            st.write(f"#{b.id} · Room {b.room} · {b.date} {b.start}-{b.end} · {b.title}")
    else:
        st.write("No bookings yet.")

# ------------------------------------------------------------------ chat
st.title("💬 Room Booking Chat")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if not os.getenv("GROQ_API_KEY"):
    st.warning("GROQ_API_KEY is not set - chat is disabled until you configure it.")

prompt = st.chat_input("e.g. Book room C tomorrow from 10:00 to 11:30 for 6 people...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        agent = build_agent(st.session_state.system, st.session_state.user)
        result = agent.invoke({"messages": st.session_state.messages})
        reply = result["messages"][-1].content
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})

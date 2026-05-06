import streamlit as st
from streamlit_gsheets import GSheetsConnection
import holidays
import pandas as pd
from datetime import date, datetime, timedelta
import calendar

# --- KONFIGURATION ---
st.set_page_config(page_title="Team Kalender", layout="wide")

# HIER DEINE URL EINTRAGEN
URL = "https://docs.google.com/spreadsheets/d/1pk6k10OKOEeR7JPfOm6AjRiccLTx6Fnh01MitDGEXsE/edit?gid=0#gid=0"

# Verbindung aufbauen
conn = st.connection("gsheets", type=GSheetsConnection)

# --- DATEN LADEN ---
def load_data():
    u = conn.read(spreadsheet=URL, worksheet="users")
    e = conn.read(spreadsheet=URL, worksheet="events")
    return u, e

try:
    df_users, df_events = load_data()
except:
    df_users = pd.DataFrame(columns=["name", "color"])
    df_events = pd.DataFrame(columns=["title", "date", "user"])

# --- SIDEBAR (User & Ansicht) ---
st.sidebar.title("⚙️ Steuerung")
view_mode = st.sidebar.radio("Ansicht:", ["Monat", "Woche", "Liste"])

with st.sidebar.expander("👤 User anlegen"):
    new_name = st.text_input("Name")
    new_color = st.color_picker("Farbe", "#3498db")
    if st.button("User speichern"):
        new_row = pd.DataFrame([{"name": new_name, "color": new_color}])
        updated = pd.concat([df_users, new_row], ignore_index=True)
        conn.update(spreadsheet=URL, worksheet="users", data=updated)
        st.rerun()

# --- TERMIN EINTRAGEN ---
st.title("📅 Team-Kalender 2026")
with st.expander("➕ Neuen Termin eintragen"):
    with st.form("event_form"):
        col1, col2, col3 = st.columns(3)
        t_title = col1.text_input("Was?")
        t_date = col2.date_input("Wann?", date.today())
        t_user = col3.selectbox("Wer?", df_users["name"].tolist() if not df_users.empty else ["-"])
        if st.form_submit_button("Speichern"):
            new_ev = pd.DataFrame([{"title": t_title, "date": str(t_date), "user": t_user}])
            updated_ev = pd.concat([df_events, new_ev], ignore_index=True)
            conn.update(spreadsheet=URL, worksheet="events", data=updated_ev)
            st.rerun()

# --- KALENDER LOGIK (MONAT) ---
if view_mode == "Monat":
    curr = date.today()
    month_days = calendar.monthcalendar(2026, curr.month)
    de_hols = holidays.Germany(subdiv='SH', years=2026)
    
    cols = st.columns(7)
    for i, d in enumerate(["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]):
        cols[i].write(f"**{d}**")

    for week in month_days:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                d_obj = date(2026, curr.month, day)
                # Check Feiertag
                h_name = de_hols.get(d_obj)
                # Check User-Termine
                u_events = df_events[df_events["date"] == str(d_obj)]
                
                with cols[i]:
                    box_html = f"<div style='border:1px solid #555; padding:5px; height:80px; font-size:12px;'>"
                    box_html += f"<b>{day}</b>"
                    if h_name:
                        box_html += f"<div style='background:#7f8c8d; color:white; padding:2px; border-radius:3px;'>{h_name}</div>"
                    for _, row in u_events.iterrows():
                        u_color = df_users[df_users["name"] == row["user"]]["color"].values[0] if row["user"] in df_users["name"].values else "#333"
                        box_html += f"<div style='background:{u_color}; color:white; padding:2px; margin-top:2px; border-radius:3px;'>{row['title']}</div>"
                    box_html += "</div>"
                    st.markdown(box_html, unsafe_allow_html=True)

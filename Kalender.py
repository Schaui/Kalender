import streamlit as st
from streamlit_gsheets import GSheetsConnection
import holidays
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import requests

# --- KONFIGURATION ---
st.set_page_config(page_title="Team Kalender", layout="wide")

# HIER DEINE URL EINTRAGEN
URL = "https://docs.google.com/spreadsheets/d/1pk6k10OKOEeR7JPfOm6AjRiccLTx6Fnh01MitDGEXsE/edit#gid=0"

# Verbindung aufbauen
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FERIEN DATEN LADEN ---
@st.cache_data(ttl=3600)
def get_ferien(land, jahr):
    try:
        url = f"https://ferien-api.de/api/v1/holidays/{land}/{jahr}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except:
        return []
    return []

# --- DATEN LADEN (USERS & EVENTS) ---
def load_data():
    u = conn.read(spreadsheet=URL, worksheet="users", ttl=5)
    e = conn.read(spreadsheet=URL, worksheet="events", ttl=5)
    
    if "name" not in u.columns:
        u = pd.DataFrame(columns=["name", "color"])
    if "date" not in e.columns:
        e = pd.DataFrame(columns=["title", "date", "user"])
    return u, e

try:
    df_users, df_events = load_data()
except:
    df_users = pd.DataFrame(columns=["name", "color"])
    df_events = pd.DataFrame(columns=["title", "date", "user"])

# --- SIDEBAR ---
st.sidebar.title("⚙️ Steuerung")
view_mode = st.sidebar.radio("Ansicht:", ["Monat", "Woche", "Jahr", "Liste"])

land = st.sidebar.selectbox("Bundesland für Feiertage & Ferien:", 
                            ["BW", "BY", "BE", "BB", "HB", "HH", "HE", "MV", 
                             "NI", "NW", "RP", "SL", "SN", "ST", "SH", "TH"], index=14)

only_national = st.sidebar.checkbox("Nur bundeseinheitliche Feiertage")
show_ferien = st.sidebar.checkbox("Ferien anzeigen", value=True)

# Navigation für Monat (falls Modus "Monat")
selected_month = date.today().month
if view_mode == "Monat":
    selected_month = st.sidebar.slider("Monat wählen:", 1, 12, date.today().month)

# --- USER MANAGEMENT IN SIDEBAR ---
with st.sidebar.expander("👤 User anlegen"):
    new_name = st.text_input("Name")
    new_color = st.color_picker("Farbe", "#3498db")
    if st.button("User speichern"):
        new_row = pd.DataFrame([{"name": new_name, "color": new_color}])
        updated = pd.concat([df_users, new_row], ignore_index=True)
        conn.update(spreadsheet=URL, worksheet="users", data=updated)
        st.success("User angelegt!")
        st.rerun()

with st.sidebar.expander("📝 User bearbeiten"):
    if not df_users.empty:
        user_to_edit = st.selectbox("Welchen User bearbeiten?", df_users["name"].tolist(), key="edit_user_sel")
        current_row = df_users[df_users["name"] == user_to_edit].iloc[0]
        new_name_edit = st.text_input("Neuer Name", value=current_row["name"])
        new_color_edit = st.color_picker("Neue Farbe", value=current_row["color"])
        if st.button("Änderungen speichern"):
            df_users = df_users[df_users["name"] != user_to_edit]
            edit_row = pd.DataFrame([{"name": new_name_edit, "color": new_color_edit}])
            updated_users = pd.concat([df_users, edit_row], ignore_index=True)
            conn.update(spreadsheet=URL, worksheet="users", data=updated_users)
            if new_name_edit != user_to_edit:
                df_events.loc[df_events["user"] == user_to_edit, "user"] = new_name_edit
                conn.update(spreadsheet=URL, worksheet="events", data=df_events)
            st.success("User aktualisiert!")
            st.rerun()

with st.sidebar.expander("❌ User löschen"):
    if not df_users.empty:
        user_to_del = st.selectbox("Welchen User löschen?", df_users["name"].tolist(), key="del_user_sel")
        delete_events = st.checkbox("Auch alle Termine dieses Users löschen?")
        if st.button("User endgültig entfernen"):
            updated_users = df_users[df_users["name"] != user_to_del]
            conn.update(spreadsheet=URL, worksheet="users", data=updated_users)
            if delete_events:
                updated_events = df_events[df_events["user"] != user_to_del]
                conn.update(spreadsheet=URL, worksheet="events", data=updated_events)
            st.success(f"User {user_to_del} wurde gelöscht!")
            st.rerun()

# --- TERMIN FORMULARE ---
st.title(f"📅 Team-Kalender {date.today().year}")
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
            st.success("Termin gespeichert!")
            st.rerun()

with st.expander("🗑️ Termin löschen"):
    if not df_events.empty:
        event_options = df_events.apply(lambda x: f"{x['title']} ({x['date']})", axis=1).tolist()
        event_to_delete_str = st.selectbox("Welchen Termin entfernen?", event_options)
        if st.button("Termin endgültig löschen"):
            idx = event_options.index(event_to_delete_str)
            updated_ev = df_events.drop(df_events.index[idx])
            conn.update(spreadsheet=URL, worksheet="events", data=updated_ev)
            st.success("Gelöscht!")
            st.rerun()
    else:
        st.info("Keine Termine vorhanden.")

# --- KALENDER LOGIK ---
year = date.today().year
de_hols = holidays.Germany(subdiv=land, years=year)
national_hols = holidays.Germany(years=year)
ferien_daten = get_ferien(land, year)

def render_day_content(d_obj, compact=False):
    h_name = de_hols.get(d_obj)
    if only_national and d_obj not in national_hols:
        h_name = None
        
    is_ferien = False
    f_name = ""
    if show_ferien:
        for f in ferien_daten:
            f_start = datetime.strptime(f["start"].split("T")[0], "%Y-%m-%d").date()
            f_end = datetime.strptime(f["end"].split("T")[0], "%Y-%m-%d").date()
            if f_start <= d_obj <= f_end:
                is_ferien = True
                f_name = f["name"]
                break

    u_events = df_events[df_events["date"] == str(d_obj)]
    is_today = (d_obj == date.today())
    
    # Styling
    bg = "#3d3d3d" if is_today else "transparent"
    f_bg = "rgba(241, 196, 15, 0.1)" if is_ferien else "transparent"
    border = "1px solid #555"
    if compact:
        # Mini-Logik für Jahresansicht
        dot_color = "transparent"
        if h_name: dot_color = "#e74c3c"
        elif not u_events.empty:
            dot_color = df_users[df_users["name"] == u_events.iloc[0]["user"]]["color"].values[0] if not df_users.empty else "#3498db"
        
        dot_html = f"<div style='height:4px; width:4px; background:{dot_color}; border-radius:50%; margin: 0 auto;'></div>" if dot_color != "transparent" else ""
        return f"<div style='text-align:center; background:{f_bg}; font-size:10px; border-radius:2px;'>{d_obj.day}{dot_html}</div>"

    # Standard Box
    html = f"<div style='border:{border}; background-color:{bg}; background-image: linear-gradient({f_bg}, {f_bg}); padding:5px; min-height:90px; border-radius:5px;'>"
    html += f"<b style='font-size:14px;'>{d_obj.day}</b>"
    if h_name:
        html += f"<div style='background:#e74c3c; color:white; padding:2px; font-size:9px; border-radius:3px; margin-bottom:2px;'>{h_name}</div>"
    if is_ferien and not h_name:
        html += f"<div style='color:#f1c40f; font-size:8px; font-style:italic;'>{f_name}</div>"
    for _, row in u_events.iterrows():
        u_color = df_users[df_users["name"] == row["user"]]["color"].values[0] if row["user"] in df_users["name"].values else "#333"
        html += f"<div style='background:{u_color}; color:white; padding:2px; margin-top:2px; font-size:10px; border-radius:3px;'>{row['title']}</div>"
    html += "</div>"
    return html

# --- ANSICHTEN RENDERN ---
if view_mode == "Monat":
    st.subheader(f"{calendar.month_name[selected_month]} {year}")
    month_days = calendar.monthcalendar(year, selected_month)
    cols = st.columns(7)
    for i, d in enumerate(["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]):
        cols[i].write(f"**{d}**")
    for week in month_days:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                with cols[i]:
                    st.markdown(render_day_content(date(year, selected_month, day)), unsafe_allow_html=True)

elif view_mode == "Woche":
    start_of_week = date.today() - timedelta(days=date.today().weekday())
    cols = st.columns(7)
    for i in range(7):
        d_obj = start_of_week + timedelta(days=i)
        with cols[i]:
            st.write(f"**{calendar.day_name[i][:2]}** ({d_obj.day}.{d_obj.month}.)")
            st.markdown(render_day_content(d_obj), unsafe_allow_html=True)

elif view_mode == "Jahr":
    st.subheader(f"Jahresübersicht {year}")
    for r in range(4): # 4 Zeilen
        cols = st.columns(3) # 3 Monate pro Zeile
        for c in range(3):
            m_idx = r * 3 + c + 1
            with cols[c]:
                st.markdown(f"<p style='text-align:center; margin-bottom:0;'><b>{calendar.month_name[m_idx]}</b></p>", unsafe_allow_html=True)
                m_days = calendar.monthcalendar(year, m_idx)
                for week in m_days:
                    d_cols = st.columns(7)
                    for i, day in enumerate(week):
                        if day != 0:
                            d_cols[i].markdown(render_day_content(date(year, m_idx, day), compact=True), unsafe_allow_html=True)
                st.write("---")

elif view_mode == "Liste":
    st.subheader("Anstehende Ereignisse")
    st.dataframe(df_events, use_container_width=True)

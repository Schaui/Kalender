import streamlit as st
from streamlit_gsheets import GSheetsConnection
import holidays
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import requests

# --- KONFIGURATION ---
st.set_page_config(page_title="Team Kalender Pro", layout="wide")

st.markdown("""
    <style>
    [data-testid="column"] {
        min-width: 150px;
    }
    .stMarkdown p {
        margin-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# HIER DEINE URL EINTRAGEN
URL = "https://docs.google.com/spreadsheets/d/1pk6k10OKOEeR7JPfOm6AjRiccLTx6Fnh01MitDGEXsE/edit#gid=0"

# Verbindung aufbauen
conn = st.connection("gsheets", type=GSheetsConnection)

# Konstanten für deutsche Anzeige
MONATS_NAMEN = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

# Mapping Bundesländer Namen zu Kürzeln
BUNDESLAENDER_MAP = {
    "Baden-Württemberg": "BW",
    "Bayern": "BY",
    "Berlin": "BE",
    "Brandenburg": "BB",
    "Bremen": "HB",
    "Hamburg": "HH",
    "Hessen": "HE",
    "Mecklenburg-Vorpommern": "MV",
    "Niedersachsen": "NI",
    "Nordrhein-Westfalen": "NW",
    "Rheinland-Pfalz": "RP",
    "Saarland": "SL",
    "Sachsen": "SN",
    "Sachsen-Anhalt": "ST",
    "Schleswig-Holstein": "SH",
    "Thüringen": "TH"
}

# --- FUNKTIONEN: DATEN LADEN ---
@st.cache_data(ttl=3600)
def get_ferien(land_code, jahr):
    try:
        url = f"https://ferien-api.de/api/v1/holidays/{land_code}/{jahr}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except:
        return []
    return []

def load_data():
    u = conn.read(spreadsheet=URL, worksheet="users", ttl=5)
    e = conn.read(spreadsheet=URL, worksheet="events", ttl=5)
    if "name" not in u.columns: u = pd.DataFrame(columns=["name", "color"])
    if "date" not in e.columns: e = pd.DataFrame(columns=["title", "date", "user"])
    return u, e

try:
    df_users, df_events = load_data()
except:
    df_users = pd.DataFrame(columns=["name", "color"])
    df_events = pd.DataFrame(columns=["title", "date", "user"])

# --- SIDEBAR: STEUERUNG ---
st.sidebar.title("⚙️ Einstellungen")
view_mode = st.sidebar.radio("Ansicht:", ["Monat", "Woche", "Jahr", "Liste"])

# Dynamische Jahr- und Monatswahl
selected_year = st.sidebar.number_input("Jahr wählen:", min_value=2024, max_value=2030, value=date.today().year)

if view_mode == "Monat":
    selected_month_name = st.sidebar.select_slider(
        "Monat wählen:", 
        options=MONATS_NAMEN,
        value=MONATS_NAMEN[date.today().month - 1]
    )
    selected_month = MONATS_NAMEN.index(selected_month_name) + 1
else:
    selected_month = date.today().month

# Bundesland Auswahl voll ausgeschrieben
land_voller_name = st.sidebar.selectbox(
    "Bundesland (Ferien & Feiertage):", 
    options=list(BUNDESLAENDER_MAP.keys()), 
    index=14 # Schleswig-Holstein
)
land = BUNDESLAENDER_MAP[land_voller_name]

only_national = st.sidebar.checkbox("Nur bundeseinheitliche Feiertage")
show_ferien = st.sidebar.checkbox("Ferien anzeigen", value=True)

# --- SIDEBAR: USER MANAGEMENT ---
with st.sidebar.expander("👤 Nutzer-Verwaltung"):
    tab1, tab2, tab3 = st.tabs(["Neu", "Bearbeiten", "Löschen"])
    with tab1:
        new_name = st.text_input("Name", key="new_u")
        new_color = st.color_picker("Farbe", "#3498db", key="new_c")
        if st.button("Benutzer erstellen"):
            new_row = pd.DataFrame([{"name": new_name, "color": new_color}])
            updated = pd.concat([df_users, new_row], ignore_index=True)
            conn.update(spreadsheet=URL, worksheet="users", data=updated)
            st.rerun()
    with tab2:
        if not df_users.empty:
            u_edit = st.selectbox("Wählen:", df_users["name"].tolist(), key="edit_u")
            curr_c = df_users[df_users["name"] == u_edit]["color"].values[0]
            new_n_edit = st.text_input("Neuer Name", value=u_edit)
            new_c_edit = st.color_picker("Neue Farbe", value=curr_c)
            if st.button("Aktualisieren"):
                df_users.loc[df_users["name"] == u_edit, ["name", "color"]] = [new_n_edit, new_c_edit]
                conn.update(spreadsheet=URL, worksheet="users", data=df_users)
                if new_n_edit != u_edit:
                    df_events.loc[df_events["user"] == u_edit, "user"] = new_n_edit
                    conn.update(spreadsheet=URL, worksheet="events", data=df_events)
                st.rerun()
    with tab3:
        if not df_users.empty:
            u_del = st.selectbox("Löschen:", df_users["name"].tolist(), key="del_u")
            del_ev = st.checkbox("Auch Termine löschen?")
            if st.button("Benutzer entfernen"):
                df_users = df_users[df_users["name"] != u_del]
                conn.update(spreadsheet=URL, worksheet="users", data=df_users)
                if del_ev:
                    df_events = df_events[df_events["user"] != u_del]
                    conn.update(spreadsheet=URL, worksheet="events", data=df_events)
                st.rerun()

# --- HAUPTBEREICH: TERMINE ---
st.title(f"📅 Team-Kalender {selected_year}")

col_ev1, col_ev2 = st.columns(2)
with col_ev1.expander("➕ Neuen Termin eintragen"):
    with st.form("add_event"):
        t_title = st.text_input("Was?")
        t_date = st.date_input("Wann?", date.today())
        t_user = st.selectbox("Wer?", df_users["name"].tolist() if not df_users.empty else ["-"])
        if st.form_submit_button("Speichern"):
            new_ev = pd.DataFrame([{"title": t_title, "date": str(t_date), "user": t_user}])
            updated_ev = pd.concat([df_events, new_ev], ignore_index=True)
            conn.update(spreadsheet=URL, worksheet="events", data=updated_ev)
            st.rerun()

with col_ev2.expander("🗑️ Termin löschen"):
    if not df_events.empty:
        ev_list = df_events.apply(lambda x: f"{x['title']} ({x['date']})", axis=1).tolist()
        ev_to_del = st.selectbox("Termin wählen:", ev_list)
        if st.button("Löschen"):
            idx = ev_list.index(ev_to_del)
            df_events = df_events.drop(df_events.index[idx])
            conn.update(spreadsheet=URL, worksheet="events", data=df_events)
            st.rerun()

# --- KALENDER LOGIK ---
de_hols = holidays.Germany(subdiv=land, years=selected_year)
national_hols = holidays.Germany(years=selected_year)
ferien_daten = get_ferien(land, selected_year)

def render_day_content(d_obj, compact=False):
    h_name = de_hols.get(d_obj)
    if only_national and d_obj not in national_hols: h_name = None
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
    bg = "#3d3d3d" if is_today else "transparent"
    f_bg = "rgba(241, 196, 15, 0.1)" if is_ferien else "transparent"
    if compact:
        dot_color = "transparent"
        if h_name: dot_color = "#e74c3c"
        elif not u_events.empty:
            dot_color = df_users[df_users["name"] == u_events.iloc[0]["user"]]["color"].values[0] if not df_users.empty else "#3498db"
        dot_html = f"<div style='height:4px; width:4px; background:{dot_color}; border-radius:50%; margin: 0 auto;'></div>" if dot_color != "transparent" else ""
        return f"<div style='text-align:center; background:{f_bg}; font-size:10px; border-radius:2px;'>{d_obj.day}{dot_html}</div>"
    html = f"<div style='border:1px solid #555; background-color:{bg}; background-image: linear-gradient({f_bg}, {f_bg}); padding:5px; min-height:90px; border-radius:5px;'>"
    html += f"<b style='font-size:14px;'>{d_obj.day}</b>"
    if h_name:
        html += f"<div style='background:#e74c3c; color:white; padding:2px; font-size:9px; border-radius:3px; margin-bottom:2px;'>{h_name}</div>"
    if is_ferien and not h_name:
        html += f"<div style='color:#f1c40f; font-size:8px; font-style:italic;'>{f_name}</div>"
    for _, row in u_events.iterrows():
        u_color = df_users[df_users["name"] == row["user"]]["color"].values[0] if row["user"] in df_users["name"].values else "#333"
        html += f"<div style='background:{u_color}; color:white; padding:2px; margin-top:2px; font-size:10px; border-radius:3px;'>{row['title']}</div>"
    return html + "</div>"

# --- ANSICHTEN ---
if view_mode == "Monat":
    st.subheader(f"{MONATS_NAMEN[selected_month-1]} {selected_year}")
    month_days = calendar.monthcalendar(selected_year, selected_month)
    cols = st.columns(7)
    for i, d in enumerate(WOCHENTAGE): cols[i].write(f"**{d}**")
    for week in month_days:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                with cols[i]: st.markdown(render_day_content(date(selected_year, selected_month, day)), unsafe_allow_html=True)

elif view_mode == "Woche":
    start_of_week = date.today() - timedelta(days=date.today().weekday())
    cols = st.columns(7)
    for i in range(7):
        d_obj = start_of_week + timedelta(days=i)
        with cols[i]:
            st.write(f"**{WOCHENTAGE[i]}** ({d_obj.day}.{d_obj.month}.)")
            st.markdown(render_day_content(d_obj), unsafe_allow_html=True)

elif view_mode == "Jahr":
    for r in range(4):
        cols = st.columns(3)
        for c in range(3):
            m_idx = r * 3 + c + 1
            with cols[c]:
                st.markdown(f"<p style='text-align:center; margin-bottom:0;'><b>{MONATS_NAMEN[m_idx-1]}</b></p>", unsafe_allow_html=True)
                for week in calendar.monthcalendar(selected_year, m_idx):
                    d_cols = st.columns(7)
                    for i, day in enumerate(week):
                        if day != 0: d_cols[i].markdown(render_day_content(date(selected_year, m_idx, day), compact=True), unsafe_allow_html=True)
                st.write("---")

elif view_mode == "Liste":
    st.subheader("Alle gespeicherten Termine")
    if not df_events.empty:
        st.dataframe(df_events.sort_values("date"), use_container_width=True)
    else:
        st.info("Keine Termine vorhanden.")

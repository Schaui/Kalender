import streamlit as st
from streamlit_gsheets import GSheetsConnection
import holidays
import pandas as pd
from datetime import date, datetime
import calendar
import requests

# --- KONFIGURATION ---
st.set_page_config(page_title="Team Kalender", layout="wide")

st.markdown("""
    <style>
    .dot-container { display: flex; justify-content: center; gap: 1px; margin-top: 1px; flex-wrap: wrap; }
    .dot { height: 4px; width: 4px; border-radius: 50%; }
    .event-card {
        border-radius: 8px; margin-bottom: 10px; display: flex;
        justify-content: space-between; align-items: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# Google Sheets URL
URL = "https://docs.google.com/spreadsheets/d/1pk6k10OKOEeR7JPfOm6AjRiccLTx6Fnh01MitDGEXsE/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# Konstanten
MONATS_NAMEN = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
LAND_CODE = "SH" 

# --- DATEN LADEN ---
@st.cache_data(ttl=3600)
def get_ferien(land_code, jahr):
    try:
        # Wir versuchen die Daten von ferien-api.de zu laden
        url = f"https://ferien-api.de/api/v1/holidays/{land_code}/{jahr}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if not data:
                return []
            return data
    except Exception as e:
        return []
    return []

def load_data():
    u = conn.read(spreadsheet=URL, worksheet="users", ttl=5)
    e = conn.read(spreadsheet=URL, worksheet="events", ttl=5)
    return u, e

df_users, df_events = load_data()

# --- SIDEBAR ---
st.sidebar.title("⚙️ Einstellungen")
view_mode = st.sidebar.radio("Ansicht:", ["Monat", "Jahr", "Liste"])
selected_year = st.sidebar.number_input("Jahr:", min_value=2024, max_value=2030, value=date.today().year)

if view_mode == "Monat":
    selected_month_name = st.sidebar.select_slider("Monat:", options=MONATS_NAMEN, 
                                                   value=MONATS_NAMEN[date.today().month - 1] if date.today().year == selected_year else "Januar")
    selected_month = MONATS_NAMEN.index(selected_month_name) + 1
else:
    selected_month = date.today().month

# Toggles
st.sidebar.subheader("Anzeige Kalender")
show_hols_cal = st.sidebar.checkbox("Feiertage anzeigen", value=True)
show_ferien_cal = st.sidebar.checkbox("Ferien anzeigen", value=True)

# Benutzer-Filter
st.sidebar.markdown("---")
visible_users = []
if not df_users.empty:
    for _, user_row in df_users.iterrows():
        if st.sidebar.checkbox(f"{user_row['name']}", value=True, key=f"f_{user_row['name']}"):
            visible_users.append(user_row['name'])

df_events_filtered = df_events[df_events["user"].isin(visible_users)] if not df_events.empty else df_events

# --- FERIEN & FEIERTAGE LADEN ---
de_hols = holidays.Germany(subdiv=LAND_CODE, years=selected_year)
ferien_daten = get_ferien(LAND_CODE, selected_year)

# Falls keine Ferien gefunden wurden, kleinen Hinweis in Sidebar
if show_ferien_cal and not ferien_daten:
    st.sidebar.warning(f"Keine Feriendaten für {selected_year} verfügbar.")

def is_date_in_ferien(d_obj):
    if not show_ferien_cal or not ferien_daten:
        return False, ""
    for f in ferien_daten:
        try:
            start = datetime.strptime(f["start"][:10], "%Y-%m-%d").date()
            end = datetime.strptime(f["end"][:10], "%Y-%m-%d").date()
            if start <= d_obj <= end:
                return True, f["name"].split(" ")[0]
        except: continue
    return False, ""

# --- RENDER FUNKTION ---
def render_day(d_obj, compact=False):
    h_name = de_hols.get(d_obj) if show_hols_cal else None
    in_f, f_name = is_date_in_ferien(d_obj)
    
    u_evs = df_events_filtered[df_events_filtered["date"] == str(d_obj)] if not df_events_filtered.empty else pd.DataFrame()
    
    bg_color = "#3d3d3d" if d_obj == date.today() else "transparent"
    f_overlay = "rgba(241, 196, 15, 0.25)" if in_f else "transparent"
    
    if compact:
        dots = ("<div class='dot' style='background:#e74c3c;'></div>" if h_name else "") + \
               "".join([f"<div class='dot' style='background:{df_users[df_users['name']==u]['color'].values[0] if u in df_users['name'].values else '#3498db'};'></div>" for u in u_evs["user"].unique()])
        return f"<div style='text-align:center; background:{f_overlay}; border-radius:2px;'>{d_obj.day}<div class='dot-container'>{dots}</div></div>"
    
    html = f"<div style='border:1px solid #555; background-color:{bg_color}; background-image: linear-gradient({f_overlay}, {f_overlay}); padding:5px; min-height:85px; border-radius:5px;'>"
    html += f"<div style='display:flex; justify-content:space-between;'><b>{d_obj.day}</b>"
    if in_f: html += f"<span style='color:#f1c40f; font-size:9px;'>{f_name}</span>"
    html += "</div>"
    if h_name: html += f"<div style='background:#e74c3c; color:white; padding:2px; font-size:8px; border-radius:3px; margin-top:2px;'>{h_name}</div>"
    for _, row in u_evs.iterrows():
        c = df_users[df_users["name"] == row["user"]]["color"].values[0] if row["user"] in df_users["name"].values else "#555"
        html += f"<div style='background:{c}; color:white; padding:2px; margin-top:2px; font-size:9px; border-radius:3px;'>{row['title']}</div>"
    return html + "</div>"

# --- HAUPTANSICHT ---
st.title(f"📅 Team-Kalender {selected_year}")

if view_mode == "Monat":
    cols = st.columns(7)
    for i, d in enumerate(WOCHENTAGE): cols[i].write(f"**{d}**")
    for week in calendar.monthcalendar(selected_year, selected_month):
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                with cols[i]: st.markdown(render_day(date(selected_year, selected_month, day)), unsafe_allow_html=True)

elif view_mode == "Jahr":
    for r in range(4):
        cols = st.columns(3)
        for c in range(3):
            m = r * 3 + c + 1
            with cols[c]:
                st.write(f"**{MONATS_NAMEN[m-1]}**")
                for week in calendar.monthcalendar(selected_year, m):
                    d_cols = st.columns(7)
                    for i, day in enumerate(week):
                        if day != 0: d_cols[i].markdown(render_day(date(selected_year, m, day), True), unsafe_allow_html=True)

else:
    st.subheader("📋 Liste")
    c1, c2 = st.columns(2)
    show_h_l = c1.toggle("Feiertage", value=True)
    show_f_l = c2.toggle("Ferien", value=True)
    
    items = []
    # Termine
    if not df_events_filtered.empty:
        for _, r in df_events_filtered.iterrows():
            items.append({"d": datetime.strptime(r["date"], "%Y-%m-%d").date(), "t": r["title"], "u": r["user"], "type": "ev"})
    # Feiertage
    if show_h_l:
        for d, n in de_hols.items():
            if d.year == selected_year: items.append({"d": d, "t": n, "u": "Feiertag", "type": "hol"})
    # Ferien
    if show_f_l and ferien_daten:
        for f in ferien_daten:
            s = datetime.strptime(f["start"][:10], "%Y-%m-%d").date()
            items.append({"d": s, "t": f"{f['name']} (Beginn)", "u": "Ferien", "type": "fer"})
            
    if not items:
        st.info("Keine Einträge.")
    else:
        for item in sorted(items, key=lambda x: x["d"]):
            if item["type"] == "ev":
                bc, bg, lc = (df_users[df_users["name"]==item["u"]]["color"].values[0] if item["u"] in df_users["name"].values else "#3498db"), "#262730", (df_users[df_users["name"]==item["u"]]["color"].values[0] if item["u"] in df_users["name"].values else "#3498db")
            elif item["type"] == "hol": bc, bg, lc = "#e74c3c", "#4d1a1a", "#e74c3c"
            else: bc, bg, lc = "#f1c40f", "#3d3516", "#f1c40f"
            
            st.markdown(f"""
                <div class="event-card" style="border-left: 5px solid {bc}; background-color: {bg}; padding: 10px 15px;">
                    <div><small style="color: #aaa;">{item['d'].strftime('%d.%m.%Y')}</small><br><b>{item['t']}</b></div>
                    <div style="background:{lc}; color:white; padding:2px 10px; border-radius:15px; font-size:11px;">{item['u']}</div>
                </div>
            """, unsafe_allow_html=True)

# Expander für Verwaltung am Ende
with st.sidebar.expander("🛠️ Verwaltung"):
    st.write("Hier Nutzer/Events pflegen (siehe vorherige Versionen)")

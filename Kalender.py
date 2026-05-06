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
    [data-testid="column"] { min-width: 150px; }
    .stMarkdown p { margin-bottom: 5px; }
    .dot-container { display: flex; justify-content: center; gap: 1px; margin-top: 1px; flex-wrap: wrap; }
    .dot { height: 4px; width: 4px; border-radius: 50%; }
    .event-card {
        border-radius: 8px; 
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
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
        url = f"https://ferien-api.de/api/v1/holidays/{land_code}/{jahr}"
        response = requests.get(url)
        return response.json() if response.status_code == 200 else []
    except: return []

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

show_ferien = st.sidebar.checkbox("Ferien im Kalender anzeigen", value=True)

# --- BENUTZER-FILTER ---
st.sidebar.markdown("---")
st.sidebar.subheader("👥 Filter (Anzeige)")
visible_users = []
if not df_users.empty:
    for _, user_row in df_users.iterrows():
        is_visible = st.sidebar.checkbox(f"{user_row['name']}", value=True, key=f"filter_{user_row['name']}")
        if is_visible:
            visible_users.append(user_row['name'])

df_events_filtered = df_events[df_events["user"].isin(visible_users)] if not df_events.empty else df_events

# --- NUTZER VERWALTUNG ---
with st.sidebar.expander("👤 Nutzer-Verwaltung"):
    t1, t2, t3 = st.tabs(["Neu", "Edit", "Del"])
    with t1:
        n_n = st.text_input("Name")
        n_c = st.color_picker("Farbe", "#3498db")
        if st.button("Hinzufügen"):
            df_users = pd.concat([df_users, pd.DataFrame([{"name": n_n, "color": n_c}])], ignore_index=True)
            conn.update(spreadsheet=URL, worksheet="users", data=df_users); st.rerun()
    with t2:
        if not df_users.empty:
            u_sel = st.selectbox("Wähle Nutzer", df_users["name"])
            u_idx = df_users[df_users["name"] == u_sel].index[0]
            u_new_c = st.color_picker("Neue Farbe", df_users.at[u_idx, "color"])
            if st.button("Farbe speichern"):
                df_users.at[u_idx, "color"] = u_new_c
                conn.update(spreadsheet=URL, worksheet="users", data=df_users); st.rerun()
    with t3:
        if not df_users.empty:
            u_del = st.selectbox("Lösche Nutzer", df_users["name"])
            if st.button("Entfernen"):
                df_users = df_users[df_users["name"] != u_del]
                conn.update(spreadsheet=URL, worksheet="users", data=df_users); st.rerun()

# --- HAUPTBEREICH: EVENT MANAGEMENT ---
st.title(f"📅 Team-Kalender {selected_year}")

c1, c2, c3 = st.columns(3)
with c1.expander("➕ Neuer Termin"):
    with st.form("add_e"):
        t = st.text_input("Was?")
        d = st.date_input("Wann?", date.today())
        u = st.selectbox("Wer?", df_users["name"].tolist() if not df_users.empty else ["-"])
        if st.form_submit_button("Speichern"):
            new_ev = pd.DataFrame([{"title": t, "date": str(d), "user": u}])
            df_events = pd.concat([df_events, new_ev], ignore_index=True)
            conn.update(spreadsheet=URL, worksheet="events", data=df_events); st.rerun()

with c2.expander("✏️ Termin bearbeiten"):
    if not df_events.empty:
        ev_list = df_events.apply(lambda x: f"{x['title']} ({x['date']}) - {x['user']}", axis=1).tolist()
        sel_ev_text = st.selectbox("Termin wählen", ev_list, key="edit_sel")
        idx_to_edit = ev_list.index(sel_ev_text)
        with st.form("edit_e"):
            et = st.text_input("Titel", value=df_events.at[idx_to_edit, "title"])
            ed = st.date_input("Datum", value=datetime.strptime(df_events.at[idx_to_edit, "date"], "%Y-%m-%d").date())
            eu = st.selectbox("Nutzer", df_users["name"].tolist(), 
                              index=df_users["name"].tolist().index(df_events.at[idx_to_edit, "user"]) if df_events.at[idx_to_edit, "user"] in df_users["name"].values else 0)
            if st.form_submit_button("Änderungen speichern"):
                df_events.at[idx_to_edit, "title"] = et
                df_events.at[idx_to_edit, "date"] = str(ed)
                df_events.at[idx_to_edit, "user"] = eu
                conn.update(spreadsheet=URL, worksheet="events", data=df_events); st.rerun()

with c3.expander("🗑️ Termin löschen"):
    if not df_events.empty:
        ev_del_list = df_events.apply(lambda x: f"{x['title']} ({x['date']}) - {x['user']}", axis=1).tolist()
        ev_to_del = st.selectbox("Wählen:", ev_del_list, key="del_sel")
        if st.button("Endgültig löschen"):
            df_events = df_events.drop(ev_del_list.index(ev_to_del))
            conn.update(spreadsheet=URL, worksheet="events", data=df_events); st.rerun()

# --- KALENDER LOGIK ---
de_hols = holidays.Germany(subdiv=LAND_CODE, years=selected_year)
ferien_daten = get_ferien(LAND_CODE, selected_year)

def render_day_content(d_obj, compact=False):
    h_name = de_hols.get(d_obj)
    is_ferien = False
    f_display_name = ""
    if show_ferien:
        for f in ferien_daten:
            f_s = datetime.strptime(f["start"].split("T")[0], "%Y-%m-%d").date()
            f_e = datetime.strptime(f["end"].split("T")[0], "%Y-%m-%d").date()
            if f_s <= d_obj <= f_e:
                is_ferien = True
                f_display_name = f["name"].split(f" {selected_year}")[0].capitalize()
                break
    
    u_evs = df_events_filtered[df_events_filtered["date"] == str(d_obj)]
    bg = "#3d3d3d" if d_obj == date.today() else "transparent"
    f_ov = "rgba(241, 196, 15, 0.25)" if is_ferien else "transparent"
    
    if compact:
        dots = ("<div class='dot' style='background:#e74c3c;'></div>" if h_name else "") + \
               "".join([f"<div class='dot' style='background:{df_users[df_users['name']==u]['color'].values[0] if u in df_users['name'].values else '#3498db'};'></div>" for u in u_evs["user"].unique()])
        return f"<div style='text-align:center; background:{f_ov}; font-size:10px; border-radius:2px; min-height:20px;'>{d_obj.day}<div class='dot-container'>{dots}</div></div>"
    
    html = f"<div style='border:1px solid #555; background-color:{bg}; background-image: linear-gradient({f_ov}, {f_ov}); padding:5px; min-height:90px; border-radius:5px;'>"
    html += f"<div style='display:flex; justify-content:flex-start; align-items:baseline; gap:8px;'><b style='font-size:14px;'>{d_obj.day}</b><span style='color:black; font-size:10px; font-weight:bold;'>{f_display_name}</span></div>"
    if h_name: html += f"<div style='background:#e74c3c; color:white; padding:2px; font-size:9px; border-radius:3px; margin-top:2px;'>{h_name}</div>"
    for _, row in u_evs.iterrows():
        c = df_users[df_users["name"] == row["user"]]["color"].values[0] if row["user"] in df_users["name"].values else "#333"
        html += f"<div style='background:{c}; color:white; padding:2px; margin-top:2px; font-size:10px; border-radius:3px;'>{row['title']}</div>"
    return html + "</div>"

# --- RENDER ANSICHTEN ---
if view_mode == "Monat":
    st.subheader(f"{MONATS_NAMEN[selected_month-1]} {selected_year}")
    cols = st.columns(7)
    for i, d in enumerate(WOCHENTAGE): cols[i].write(f"**{d}**")
    for week in calendar.monthcalendar(selected_year, selected_month):
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                with cols[i]: st.markdown(render_day_content(date(selected_year, selected_month, day)), unsafe_allow_html=True)

elif view_mode == "Jahr":
    for r in range(4):
        cols = st.columns(3)
        for c in range(3):
            m = r * 3 + c + 1
            with cols[c]:
                st.markdown(f"<p style='text-align:center; margin-bottom:0;'><b>{MONATS_NAMEN[m-1]}</b></p>", unsafe_allow_html=True)
                for week in calendar.monthcalendar(selected_year, m):
                    d_cols = st.columns(7)
                    for i, day in enumerate(week):
                        if day != 0: d_cols[i].markdown(render_day_content(date(selected_year, m, day), True), unsafe_allow_html=True)
                st.write("---")

else:
    st.subheader("📋 Geplante Termine")
    show_extra_list = st.toggle("Feiertage & Ferien in Liste anzeigen", value=True)
    
    df_list = df_events_filtered.copy()
    if not df_list.empty:
        df_list['date_obj'] = pd.to_datetime(df_list['date']).dt.date
    else:
        df_list = pd.DataFrame(columns=['title', 'date_obj', 'user', 'type'])
    df_list['type'] = 'event'

    if show_extra_list:
        # Feiertage
        for d_obj, name in de_hols.items():
            if d_obj.year == selected_year:
                new_row = pd.DataFrame([{"title": name, "date_obj": d_obj, "user": "Feiertag", "type": "holiday"}])
                df_list = pd.concat([df_list, new_row], ignore_index=True)
        # Ferien
        for f in ferien_daten:
            f_s = datetime.strptime(f["start"].split("T")[0], "%Y-%m-%d").date()
            f_e = datetime.strptime(f["end"].split("T")[0], "%Y-%m-%d").date()
            f_name = f["name"].split(f" {selected_year}")[0].capitalize()
            new_row = pd.DataFrame([{"title": f"{f_name} (Beginn)", "date_obj": f_s, "user": "Ferien", "type": "ferien"}])
            df_list = pd.concat([df_list, new_row], ignore_index=True)

    if df_list.empty:
        st.info("Keine Einträge gefunden.")
    else:
        df_list = df_list.sort_values('date_obj')
        for _, row in df_list.iterrows():
            d_fmt = row['date_obj'].strftime('%d. %b %Y')
            if row['type'] == 'holiday':
                bg_color, border_color, label_color = "#4d1a1a", "#e74c3c", "#e74c3c"
            elif row['type'] == 'ferien':
                bg_color, border_color, label_color = "#3d3516", "#f1c40f", "#f1c40f"
            else:
                u_color = df_users[df_users["name"] == row["user"]]["color"].values[0] if row["user"] in df_users["name"].values else "#3498db"
                bg_color, border_color, label_color = "#262730", u_color, u_color

            st.markdown(f"""
                <div class="event-card" style="border-left: 5px solid {border_color}; background-color: {bg_color}; padding: 15px;">
                    <div style="flex-grow: 1;">
                        <span style="color: #aaa; font-size: 0.85rem;">{d_fmt}</span>
                        <h4 style="margin: 0; color: white;">{row['title']}</h4>
                    </div>
                    <div style="background-color: {label_color}; color: white; padding: 4px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: bold;">
                        {row['user']}
                    </div>
                </div>
            """, unsafe_allow_html=True)

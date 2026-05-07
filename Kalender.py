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
    .dot-container { display: flex; justify-content: center; gap: 1px; margin-top: 1px; flex-wrap: wrap; }
    .dot { height: 4px; width: 4px; border-radius: 50%; }
    .event-card {
        border-radius: 8px; margin-bottom: 10px; display: flex;
        justify-content: space-between; align-items: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# Google Sheets Verbindung
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
        response = requests.get(url, timeout=5)
        return response.json() if response.status_code == 200 else []
    except: return []

def load_data():
    try:
        u = conn.read(spreadsheet=URL, worksheet="users", ttl=5)
    except:
        u = pd.DataFrame(columns=["name", "color"])
    try:
        e = conn.read(spreadsheet=URL, worksheet="events", ttl=5)
    except:
        e = pd.DataFrame(columns=["title", "date", "user"])
    
    if u.empty: u = pd.DataFrame(columns=["name", "color"])
    if e.empty: e = pd.DataFrame(columns=["title", "date", "user"])
    return u, e

df_users, df_events = load_data()

# --- SIDEBAR EINSTELLUNGEN ---
st.sidebar.title("⚙️ Einstellungen")
view_mode = st.sidebar.radio("Ansicht:", ["Monat", "Jahr", "Liste"])
selected_year = st.sidebar.number_input("Jahr:", min_value=2024, max_value=2030, value=date.today().year)

if view_mode == "Monat":
    default_m = MONATS_NAMEN[date.today().month - 1] if date.today().year == selected_year else "Januar"
    selected_month_name = st.sidebar.select_slider("Monat:", options=MONATS_NAMEN, value=default_m)
    selected_month = MONATS_NAMEN.index(selected_month_name) + 1
else:
    selected_month = date.today().month

st.sidebar.subheader("Anzeige Kalender")
show_hols_cal = st.sidebar.checkbox("Feiertage anzeigen", value=True)
show_ferien_cal = st.sidebar.checkbox("Ferien anzeigen", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("👥 Personen Filter")
visible_users = []

if "name" in df_users.columns and not df_users.empty:
    for _, user_row in df_users.iterrows():
        if st.sidebar.checkbox(f"{user_row['name']}", value=True, key=f"filter_{user_row['name']}"):
            visible_users.append(user_row['name'])

if not df_events.empty and "user" in df_events.columns:
    df_events_filtered = df_events[df_events["user"].isin(visible_users)]
else:
    df_events_filtered = df_events

# --- LOGIK: FEIERTAGS & FERIEN DATEN ---
de_hols = holidays.Germany(subdiv=LAND_CODE, years=selected_year)
ferien_daten = get_ferien(LAND_CODE, selected_year)

def is_date_in_ferien(d_obj):
    if not show_ferien_cal or not ferien_daten:
        return False, ""
    for f in ferien_daten:
        try:
            start = datetime.strptime(f["start"][:10], "%Y-%m-%d").date()
            end = datetime.strptime(f["end"][:10], "%Y-%m-%d").date()
            if start <= d_obj <= end:
                return True, f["name"].split(" ")[0].capitalize()
        except: continue
    return False, ""

# --- RENDER FUNKTION KALENDER ---
def render_day(d_obj, compact=False):
    h_name = de_hols.get(d_obj) if show_hols_cal else None
    in_f, f_name = is_date_in_ferien(d_obj)
    
    u_evs = pd.DataFrame()
    if not df_events_filtered.empty and "date" in df_events_filtered.columns:
        u_evs = df_events_filtered[df_events_filtered["date"] == str(d_obj)]
    
    bg_today = "#3d3d3d" if d_obj == date.today() else "transparent"
    f_ov = "rgba(241, 196, 15, 0.2)" if in_f else "transparent"
    
    if compact:
        dots = ("<div class='dot' style='background:#e74c3c;'></div>" if h_name else "")
        if not u_evs.empty and "user" in u_evs.columns:
             dots += "".join([f"<div class='dot' style='background:{df_users[df_users['name']==u]['color'].values[0] if u in df_users['name'].values else '#3498db'};'></div>" for u in u_evs["user"].unique()])
        return f"<div style='text-align:center; background:{f_ov}; border-radius:2px;'>{d_obj.day}<div class='dot-container'>{dots}</div></div>"
    
    html = f"<div style='border:1px solid #555; background-color:{bg_today}; background-image: linear-gradient({f_ov}, {f_ov}); padding:5px; min-height:85px; border-radius:5px;'>"
    html += f"<div style='display:flex; justify-content:space-between;'><b>{d_obj.day}</b>"
    if in_f: html += f"<span style='color:#f1c40f; font-size:9px; font-weight:bold;'>{f_name}</span>"
    html += "</div>"
    if h_name: html += f"<div style='background:#e74c3c; color:white; padding:2px; font-size:8px; border-radius:3px; margin-top:2px;'>{h_name}</div>"
    
    if not u_evs.empty:
        for _, row in u_evs.iterrows():
            user_name = row.get("user", "Unbekannt")
            title = row.get("title", "Termin")
            c = df_users[df_users["name"] == user_name]["color"].values[0] if user_name in df_users["name"].values else "#555"
            html += f"<div style='background:{c}; color:white; padding:2px; margin-top:2px; font-size:9px; border-radius:3px;'>{title}</div>"
    return html + "</div>"

# --- HAUPTBEREICH: TERMIN-MANAGEMENT ---
st.title(f"📅 Team-Kalender {selected_year}")

c1, c2, c3 = st.columns(3)
with c1.expander("➕ Neuer Termin"):
    with st.form("add_event"):
        t = st.text_input("Titel")
        d = st.date_input("Datum", date.today())
        user_options = df_users["name"].tolist() if "name" in df_users.columns else []
        u = st.selectbox("Nutzer", user_options)
        if st.form_submit_button("Speichern"):
            new_ev = pd.DataFrame([{"title": t, "date": str(d), "user": u}])
            df_events = pd.concat([df_events, new_ev], ignore_index=True)
            conn.update(spreadsheet=URL, worksheet="events", data=df_events)
            st.rerun()

with c2.expander("✏️ Bearbeiten"):
    if not df_events.empty and "title" in df_events.columns:
        ev_list = df_events.apply(lambda x: f"{x.get('title','')} ({x.get('date','')})", axis=1).tolist()
        sel_ev = st.selectbox("Termin wählen", ev_list)
        idx = ev_list.index(sel_ev)
        with st.form("edit_event"):
            et = st.text_input("Titel", value=df_events.at[idx, "title"])
            ed = st.date_input("Datum", value=datetime.strptime(df_events.at[idx, "date"], "%Y-%m-%d").date())
            u_list = df_users["name"].tolist()
            curr_u = df_events.at[idx, "user"]
            u_idx = u_list.index(curr_u) if curr_u in u_list else 0
            eu = st.selectbox("Nutzer", u_list, index=u_idx)
            if st.form_submit_button("Update"):
                df_events.at[idx, "title"], df_events.at[idx, "date"], df_events.at[idx, "user"] = et, str(ed), eu
                conn.update(spreadsheet=URL, worksheet="events", data=df_events)
                st.rerun()

with c3.expander("🗑️ Löschen"):
    if not df_events.empty:
        ev_del_list = df_events.apply(lambda x: f"{x.get('title','')} ({x.get('date','')})", axis=1).tolist()
        to_del = st.selectbox("Termin wählen", ev_del_list, key="del_ev")
        if st.button("Endgültig löschen"):
            df_events = df_events.drop(ev_del_list.index(to_del))
            conn.update(spreadsheet=URL, worksheet="events", data=df_events)
            st.rerun()

# --- ANSICHTEN RENDER ---
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

else: # Liste
    st.subheader("📋 Liste")
    lt1, lt2 = st.columns(2)
    show_h_l = lt1.toggle("Feiertage einblenden", value=True)
    show_f_l = lt2.toggle("Ferien einblenden", value=True)
    
    items = []
    if not df_events_filtered.empty and "date" in df_events_filtered.columns:
        for _, r in df_events_filtered.iterrows():
            items.append({"d": datetime.strptime(r["date"], "%Y-%m-%d").date(), "t": r["title"], "u": r["user"], "type": "ev", "info": ""})
    
    if show_h_l:
        for d, n in de_hols.items():
            if d.year == selected_year: items.append({"d": d, "t": n, "u": "Feiertag", "type": "hol", "info": ""})
    
    if show_f_l and ferien_daten:
        for f in ferien_daten:
            try:
                s = datetime.strptime(f["start"][:10], "%Y-%m-%d").date()
                e = datetime.strptime(f["end"][:10], "%Y-%m-%d").date()
                items.append({"d": s, "t": f["name"].split(" ")[0].capitalize(), "u": "Ferien", "type": "fer", "info": f"{s.strftime('%d.%m.')} – {e.strftime('%d.%m.')}"})
            except: continue
            
    if not items: st.info("Keine Einträge.")
    else:
        for item in sorted(items, key=lambda x: x["d"]):
            if item["type"] == "ev":
                u_c = df_users[df_users["name"]==item["u"]]["color"].values[0] if ("name" in df_users.columns and item["u"] in df_users["name"].values) else "#3498db"
                bc, bg, lc = u_c, "#262730", u_c
            elif item["type"] == "hol": bc, bg, lc = "#e74c3c", "#4d1a1a", "#e74c3c"
            else: bc, bg, lc = "#f1c40f", "#3d3516", "#f1c40f"
            
            info_text = f"<div style='color:#f1c40f; font-size:0.85rem;'>{item['info']}</div>" if item['info'] else ""
            st.markdown(f"""
                <div class="event-card" style="border-left: 5px solid {bc}; background-color: {bg}; padding: 10px 15px;">
                    <div><small style="color: #aaa;">{item['d'].strftime('%d.%m.%Y')}</small><br><b>{item['t']}</b>{info_text}</div>
                    <div style="background:{lc}; color:white; padding:4px 12px; border-radius:15px; font-size:11px; font-weight:bold;">{item['u']}</div>
                </div>
            """, unsafe_allow_html=True)

# --- BENUTZER VERWALTUNG ---
st.sidebar.markdown("---")
with st.sidebar.expander("👤 Benutzer-Verwaltung"):
    tab1, tab2, tab3 = st.tabs(["Neu", "Farbe", "Löschen"])
    with tab1:
        new_name = st.text_input("Name", key="new_u")
        new_color = st.color_picker("Farbe", "#3498db", key="new_c")
        if st.button("Nutzer anlegen"):
            if new_name:
                df_users = pd.concat([df_users, pd.DataFrame([{"name": new_name, "color": new_color}])], ignore_index=True)
                conn.update(spreadsheet=URL, worksheet="users", data=df_users)
                st.rerun()
    with tab2:
        if not df_users.empty and "name" in df_users.columns:
            edit_u = st.selectbox("Nutzer wählen", df_users["name"], key="edit_u_sel")
            u_idx = df_users[df_users["name"] == edit_u].index[0]
            new_c_val = st.color_picker("Neue Farbe", df_users.at[u_idx, "color"], key="edit_c_val")
            if st.button("Speichern"):
                df_users.at[u_idx, "color"] = new_c_val
                conn.update(spreadsheet=URL, worksheet="users", data=df_users)
                st.rerun()
    with tab3:
        if not df_users.empty and "name" in df_users.columns:
            del_u = st.selectbox("Löschen", df_users["name"], key="del_u_sel")
            if st.button("Nutzer entfernen"):
                df_users = df_users[df_users["name"] != del_u]
                conn.update(spreadsheet=URL, worksheet="users", data=df_users)
                st.rerun()

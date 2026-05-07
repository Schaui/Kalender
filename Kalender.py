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
    except: u = pd.DataFrame(columns=["name", "color"])
    try:
        e = conn.read(spreadsheet=URL, worksheet="events", ttl=5)
    except: e = pd.DataFrame(columns=["title", "date", "user"])
    
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

df_events_filtered = df_events[df_events["user"].isin(visible_users)] if not df_events.empty and "user" in df_events.columns else df_events

# --- LOGIK: FEIERTAGS & FERIEN ---
de_hols = holidays.Germany(subdiv=LAND_CODE, years=selected_year)
ferien_daten = get_ferien(LAND_CODE, selected_year)

def is_date_in_ferien(d_obj):
    if not show_ferien_cal or not ferien_daten: return False, ""
    for f in ferien_daten:
        try:
            start = datetime.strptime(f["start"][:10], "%Y-%m-%d").date()
            end = datetime.strptime(f["end"][:10], "%Y-%m-%d").date()
            if start <= d_obj <= end: return True, f["name"].split(" ")[0].capitalize()
        except: continue
    return False, ""

# --- RENDER FUNKTION ---
def render_day(d_obj, compact=False):
    h_name = de_hols.get(d_obj) if show_hols_cal else None
    in_f, f_name = is_date_in_ferien(d_obj)
    u_evs = df_events_filtered[df_events_filtered["date"] == str(d_obj)] if not df_events_filtered.empty else pd.DataFrame()
    
    bg_today = "#3d3d3d" if d_obj == date.today() else "transparent"
    f_ov = "rgba(241, 196, 15, 0.15)" if in_f else "transparent"
    
    if compact:
        dots = ("<div class='dot' style='background:#e74c3c;'></div>" if h_name else "")
        if not u_evs.empty:
            dots += "".join([f"<div class='dot' style='background:{df_users[df_users['name']==u]['color'].values[0] if u in df_users['name'].values else '#3498db'};'></div>" for u in u_evs["user"].unique()])
        return f"<div style='text-align:center; background:{f_ov}; border-radius:2px;'>{d_obj.day}<div class='dot-container'>{dots}</div></div>"
    
    html = f"<div style='border:1px solid #555; background-color:{bg_today}; background-image: linear-gradient({f_ov}, {f_ov}); padding:5px; min-height:85px; border-radius:5px;'>"
    html += f"<div style='display:flex; justify-content:space-between;'><b>{d_obj.day}</b>"
    if in_f: html += f"<span style='color:#f1c40f; font-size:9px;'>{f_name}</span>"
    html += "</div>"
    if h_name: html += f"<div style='background:#e74c3c; color:white; padding:2px; font-size:8px; border-radius:3px; margin-top:2px;'>{h_name}</div>"
    if not u_evs.empty:
        for _, row in u_evs.iterrows():
            c = df_users[df_users["name"] == row['user']]["color"].values[0] if row['user'] in df_users["name"].values else "#555"
            html += f"<div style='background:{c}; color:white; padding:2px; margin-top:2px; font-size:9px; border-radius:3px;'>{row['title']}</div>"
    return html + "</div>"

# --- TERMIN MANAGEMENT ---
st.title(f"📅 Team-Kalender {selected_year}")
c1, c2, c3 = st.columns(3)

with c1.expander("➕ Neuer Termin / Zeitraum"):
    with st.form("add_event"):
        t = st.text_input("Titel")
        is_range = st.checkbox("Zeitraum (von-bis)")
        if is_range: d_input = st.date_input("Zeitraum wählen", [date.today(), date.today()])
        else: d_input = st.date_input("Datum", date.today())
        u = st.selectbox("Nutzer", df_users["name"].tolist() if not df_users.empty else [])
        if st.form_submit_button("Speichern"):
            if t and u:
                new_data = []
                if is_range and len(d_input) == 2:
                    curr, end = d_input
                    while curr <= end:
                        new_data.append({"title": t, "date": str(curr), "user": u})
                        curr += timedelta(days=1)
                else:
                    new_data.append({"title": t, "date": str(d_input if not is_range else d_input[0]), "user": u})
                df_events = pd.concat([df_events, pd.DataFrame(new_data)], ignore_index=True)
                conn.update(spreadsheet=URL, worksheet="events", data=df_events)
                st.rerun()

with c2.expander("✏️ Bearbeiten"):
    if not df_events.empty:
        ev_list = df_events.apply(lambda x: f"{x['title']} ({x['date']}) - {x['user']}", axis=1).tolist()
        sel_ev = st.selectbox("Wählen", ev_list, key="edit_sel")
        idx = ev_list.index(sel_ev)
        with st.form("edit_form"):
            et, eu = st.text_input("Titel", df_events.at[idx, "title"]), st.selectbox("Nutzer", df_users["name"].tolist(), index=df_users["name"].tolist().index(df_events.at[idx, "user"]) if df_events.at[idx, "user"] in df_users["name"].values else 0)
            ed = st.date_input("Datum (nur für diesen Tag)", datetime.strptime(df_events.at[idx, "date"], "%Y-%m-%d").date())
            mode = st.radio("Anwenden auf:", ["Nur diesen Tag", "Ganzen Zeitraum (gleicher Name & Nutzer)"])
            if st.form_submit_button("Update"):
                if mode == "Nur diesen Tag":
                    df_events.at[idx, "title"], df_events.at[idx, "user"], df_events.at[idx, "date"] = et, eu, str(ed)
                else:
                    mask = (df_events["title"] == df_events.at[idx, "title"]) & (df_events["user"] == df_events.at[idx, "user"])
                    df_events.loc[mask, "title"], df_events.loc[mask, "user"] = et, eu
                conn.update(spreadsheet=URL, worksheet="events", data=df_events)
                st.rerun()

with c3.expander("🗑️ Löschen"):
    if not df_events.empty:
        ev_del_list = df_events.apply(lambda x: f"{x['title']} ({x['date']}) - {x['user']}", axis=1).tolist()
        to_del = st.selectbox("Wählen", ev_del_list, key="del_sel")
        idx_del = ev_del_list.index(to_del)
        mode_del = st.radio("Lösch-Modus:", ["Nur diesen Tag", "Ganzen Zeitraum"], key="del_mode")
        if st.button("Löschen bestätigen", type="primary"):
            if mode_del == "Nur diesen Tag": df_events = df_events.drop(idx_del)
            else: df_events = df_events[~((df_events["title"] == df_events.at[idx_del, "title"]) & (df_events["user"] == df_events.at[idx_del, "user"]))]
            conn.update(spreadsheet=URL, worksheet="events", data=df_events)
            st.rerun()

# --- ANSICHTEN ---
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

else: # Liste (Komprimiert)
    st.subheader("📋 Komprimierte Übersicht")
    items = []
    
    # 1. Termine verarbeiten
    if not df_events_filtered.empty:
        df_sorted = df_events_filtered.copy()
        df_sorted["date"] = pd.to_datetime(df_sorted["date"]).dt.date
        df_sorted = df_sorted.sort_values(["user", "title", "date"])
        for (user, title), group in df_sorted.groupby(["user", "title"]):
            dates = sorted(group["date"].tolist())
            start = dates[0]
            for i in range(1, len(dates) + 1):
                if i == len(dates) or (dates[i] - dates[i-1]).days > 1:
                    end = dates[i-1]
                    info = f"{start.strftime('%d.%m.')} – {end.strftime('%d.%m.')}" if start != end else ""
                    items.append({"d": start, "t": title, "u": user, "type": "ev", "info": info})
                    if i < len(dates): start = dates[i]
    
    # 2. Feiertage hinzufügen
    if st.sidebar.checkbox("Feiertage in Liste", True):
        for d, n in de_hols.items():
            if d.year == selected_year:
                items.append({"d": d, "t": n, "u": "Feiertag", "type": "hol", "info": ""})
                
    # 3. Ferien hinzufügen
    if st.sidebar.checkbox("Ferien in Liste", True) and ferien_daten:
        for f in ferien_daten:
            try:
                s = datetime.strptime(f["start"][:10], "%Y-%m-%d").date()
                e = datetime.strptime(f["end"][:10], "%Y-%m-%d").date()
                if s.year == selected_year:
                    items.append({"d": s, "t": f["name"].split(" ")[0].capitalize() + "ferien", "u": "Ferien", "type": "fer", "info": f"{s.strftime('%d.%m.')} – {e.strftime('%d.%m.')}"})
            except: continue

    if not items:
        st.info("Keine Einträge.")
    else:
        for item in sorted(items, key=lambda x: x["d"]):
            if item["type"] == "ev":
                u_c = df_users[df_users["name"]==item["u"]]["color"].values[0] if item["u"] in df_users["name"].values else "#3498db"
                bg = "#262730"
            elif item["type"] == "hol": u_c, bg = "#e74c3c", "#4d1a1a"
            else: u_c, bg = "#f1c40f", "#3d3516"
            
            st.markdown(f'''<div class="event-card" style="border-left:5px solid {u_c}; background:{bg}; padding:10px;"><div><small>{item["d"].strftime("%d.%m.%Y")}</small><br><b>{item["t"]}</b><br><small style="color:#f1c40f">{item["info"]}</small></div><div style="background:{u_c}; color:white; padding:3px 10px; border-radius:12px; font-size:10px; font-weight:bold;">{item["u"]}</div></div>''', unsafe_allow_html=True)

# --- BENUTZER VERWALTUNG (SIDEBAR) ---
st.sidebar.markdown("---")
with st.sidebar.expander("👤 Benutzer-Verwaltung"):
    tab1, tab2, tab3 = st.tabs(["Neu", "Bearbeiten", "Löschen"])
    with tab1:
        nu = st.text_input("Name", key="new_u_name")
        nc = st.color_picker("Farbe", "#3498db", key="new_u_color")
        if st.button("Hinzufügen"):
            if nu:
                df_users = pd.concat([df_users, pd.DataFrame([{"name": nu, "color": nc}])], ignore_index=True)
                conn.update(spreadsheet=URL, worksheet="users", data=df_users)
                st.rerun()
    with tab2:
        if not df_users.empty:
            edit_u = st.selectbox("Nutzer wählen", df_users["name"].tolist(), key="edit_u_sel")
            u_idx = df_users[df_users["name"] == edit_u].index[0]
            new_c_val = st.color_picker("Neue Farbe", df_users.at[u_idx, "color"], key="edit_u_color")
            if st.button("Änderung speichern"):
                df_users.at[u_idx, "color"] = new_c_val
                conn.update(spreadsheet=URL, worksheet="users", data=df_users)
                st.rerun()
    with tab3:
        if not df_users.empty:
            del_u = st.selectbox("Nutzer entfernen", df_users["name"].tolist(), key="del_u_sel")
            if st.button("Endgültig entfernen"):
                df_users = df_users[df_users["name"] != del_u]
                conn.update(spreadsheet=URL, worksheet="users", data=df_users)
                st.rerun()

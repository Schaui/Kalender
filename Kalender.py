import streamlit as st
from streamlit_gsheets import GSheetsConnection
import holidays
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import requests

# --- 1. KONFIGURATION & STYLING ---
st.set_page_config(page_title="Team Kalender Pro", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    [data-testid="column"] { min-width: 150px; }
    .dot-container { display: flex; justify-content: center; gap: 1px; margin-top: 1px; flex-wrap: wrap; }
    .dot { height: 4px; width: 4px; border-radius: 50%; }
    .event-card { border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    .sidebar-color-dot { height: 12px; width: 12px; border-radius: 50%; border: 1px solid #555; display: inline-block; margin-top: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGO ---
col_l1, col_l2, col_l3 = st.columns([1, 1, 1])
with col_l2:
    st.image("https://github.com/Schaui/Kalender/blob/main/Gemini_Generated_Image_cn6fltcn6fltcn6f.png?raw=true", use_container_width=True)

# --- 3. DATEN & VERBINDUNG ---
URL = "https://docs.google.com/spreadsheets/d/1pk6k10OKOEeR7JPfOm6AjRiccLTx6Fnh01MitDGEXsE/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)
MONATS_NAMEN = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
LAND_CODE = "SH" 

calendar.setfirstweekday(calendar.MONDAY)

def load_data():
    try:
        u = conn.read(spreadsheet=URL, worksheet="users", ttl=0)
        e = conn.read(spreadsheet=URL, worksheet="events", ttl=0)
    except:
        u, e = pd.DataFrame(columns=["name", "color"]), pd.DataFrame(columns=["title", "date", "user"])
    return u, e

@st.cache_data(ttl=3600)
def get_ferien(land_code, jahr):
    try:
        r = requests.get(f"https://ferien-api.de/api/v1/holidays/{land_code}/{jahr}", timeout=5)
        return r.json() if r.status_code == 200 else []
    except: return []

df_users, df_events = load_data()

# --- 4. SIDEBAR ---
st.sidebar.title("⚙️ Einstellungen")
view_mode = st.sidebar.radio("Ansicht:", ["Monat", "Jahr", "Liste"])
selected_year = st.sidebar.number_input("Jahr:", min_value=2024, max_value=2030, value=date.today().year)
selected_month = (MONATS_NAMEN.index(st.sidebar.select_slider("Monat:", options=MONATS_NAMEN, value=MONATS_NAMEN[date.today().month-1])) + 1) if view_mode == "Monat" else date.today().month

st.sidebar.subheader("Anzeige")
show_hols = st.sidebar.checkbox("Feiertage 🔴", value=True)
show_ferien = st.sidebar.checkbox("Ferien 🟡", value=True)

st.sidebar.markdown("---")
visible_users = []
if not df_users.empty:
    for _, row in df_users.iterrows():
        c_left, c_right = st.sidebar.columns([0.85, 0.15])
        if c_left.checkbox(row['name'], value=True, key=f"f_{row['name']}"):
            visible_users.append(row['name'])
        c_right.markdown(f'<div class="sidebar-color-dot" style="background-color:{row["color"]};"></div>', unsafe_allow_html=True)

df_ev_filt = df_events[df_events["user"].isin(visible_users)] if not df_events.empty else df_events

# --- 5. LOGIK (FEIERTAGS- & FERIEN-MARKIERUNG) ---
de_hols = holidays.Germany(subdiv=LAND_CODE, years=selected_year)
ferien_daten = get_ferien(LAND_CODE, selected_year)

def is_ferien(d):
    for f in ferien_daten:
        try:
            s_f = datetime.strptime(f["start"][:10], "%Y-%m-%d").date()
            e_f = datetime.strptime(f["end"][:10], "%Y-%m-%d").date()
            if s_f <= d <= e_f: 
                return True, f["name"].split(" ")[0].capitalize()
        except: continue
    return False, ""

def render_day(d_obj, compact=False):
    h_name = de_hols.get(d_obj) if show_hols else None
    in_f, f_n = is_ferien(d_obj)
    display_f = in_f if show_ferien else False
    
    u_evs = df_ev_filt[df_ev_filt["date"] == str(d_obj)] if not df_ev_filt.empty else pd.DataFrame()
    
    # Farben definieren
    is_today = d_obj == date.today()
    today_color = "rgba(255, 255, 255, 0.15)" # Dezentes Weiß/Grau für heute
    ferien_color = "rgba(241, 196, 15, 0.25)" # Gelb für Ferien
    
    # Hintergrund-Logik: Priorität auf Ferien, dann heute
    bg_style = "transparent"
    if display_f:
        bg_style = ferien_color
    elif is_today:
        bg_style = today_color

    if compact:
        dots = ("<div class='dot' style='background:#e74c3c;'></div>" if h_name else "")
        dots += "".join([f"<div class='dot' style='background:{df_users[df_users['name']==u]['color'].values[0] if u in df_users['name'].values else '#3498db'};'></div>" for u in u_evs["user"].unique()])
        return f"<div style='text-align:center; background:{bg_style}; border-radius:3px; padding:2px;'>{d_obj.day}<div class='dot-container'>{dots}</div></div>"
    
    # Große Ansicht (Monat)
    border = "2px solid #f1c40f" if display_f else "1px solid #555"
    html = f"<div style='border:{border}; background:{bg_style}; padding:5px; min-height:85px; border-radius:5px; position:relative;'>"
    html += f"<div style='display:flex; justify-content:space-between; align-items:center;'><b style='font-size:14px;'>{d_obj.day}</b>"
    
    if display_f: 
        html += f"<span style='background:#f1c40f; color:black; font-size:9px; font-weight:bold; padding:1px 4px; border-radius:3px;'>{f_n}</span>"
    html += "</div>"
    
    if h_name: 
        html += f"<div style='background:#e74c3c; color:white; padding:2px; font-size:10px; border-radius:3px; margin-top:2px; line-height:1.1;'>{h_name}</div>"
    
    for _, r in u_evs.iterrows():
        c = df_users[df_users["name"]==r['user']]["color"].values[0] if r['user'] in df_users["name"].values else "#555"
        html += f"<div style='background:{c}; color:white; padding:3px; margin-top:3px; font-size:11px; font-weight:bold; border-radius:3px; line-height:1.1; text-align:center; box-shadow: 1px 1px 2px rgba(0,0,0,0.2);'>{r['title']}</div>"
    
    return html + "</div>"

# --- 6. CRUD & LISTEN-LOGIK ---
def get_grouped_event_list(df):
    if df.empty: return [], []
    df_g = df.copy()
    df_g["date"] = pd.to_datetime(df_g["date"]).dt.date
    df_g = df_g.sort_values(["user", "title", "date"])
    display_list, data_refs = [], []
    for (user, title), group in df_g.groupby(["user", "title"]):
        dates = sorted(group["date"].tolist())
        start = dates[0]
        for i in range(1, len(dates) + 1):
            if i == len(dates) or (dates[i] - dates[i-1]).days > 1:
                end = dates[i-1]
                period = f"{start.strftime('%d.%m.')}-{end.strftime('%d.%m.')}" if start != end else f"{start.strftime('%d.%m.')}"
                display_list.append(f"{title} ({period}) - {user}")
                data_refs.append({"start": start, "end": end, "title": title, "user": user})
                if i < len(dates): start = dates[i]
    return display_list, data_refs

st.title(f"📅 Team-Kalender {selected_year}")
c1, c2, c3 = st.columns(3)
display_options, ref_data = get_grouped_event_list(df_events)

with c1.expander("➕ Neuer Eintrag"):
    with st.form("add_form", clear_on_submit=True):
        t = st.text_input("Titel")
        ca, cb = st.columns(2)
        ds, de = ca.date_input("Von", date.today()), cb.date_input("Bis", date.today())
        u = st.selectbox("Wer?", df_users["name"].tolist() if not df_users.empty else [])
        if st.form_submit_button("Eintragen"):
            if t and u:
                f_e = de if de >= ds else ds
                new = [{"title": t, "date": str(ds + timedelta(days=i)), "user": u} for i in range((f_e - ds).days + 1)]
                df_events = pd.concat([df_events, pd.DataFrame(new)], ignore_index=True)
                conn.update(spreadsheet=URL, worksheet="events", data=df_events)
                st.cache_data.clear(); st.rerun()

with c2.expander("✏️ Bearbeiten"):
    if display_options:
        sel = st.selectbox("Block wählen", range(len(display_options)), format_func=lambda x: display_options[x])
        ref = ref_data[sel]
        with st.form("edit_form"):
            nt, nu = st.text_input("Titel", ref["title"]), st.selectbox("Nutzer", df_users["name"].tolist(), index=df_users["name"].tolist().index(ref["user"]) if ref["user"] in df_users["name"].values else 0)
            if st.form_submit_button("Speichern"):
                mask = (df_events["title"] == ref["title"]) & (df_events["user"] == ref["user"]) & (pd.to_datetime(df_events["date"]).dt.date >= ref["start"]) & (pd.to_datetime(df_events["date"]).dt.date <= ref["end"])
                df_events.loc[mask, "title"], df_events.loc[mask, "user"] = nt, nu
                conn.update(spreadsheet=URL, worksheet="events", data=df_events); st.cache_data.clear(); st.rerun()

with c3.expander("🗑️ Löschen"):
    if display_options:
        idx_d = st.selectbox("Block wählen", range(len(display_options)), format_func=lambda x: display_options[x], key="d_sel")
        if st.button("Löschen", type="primary"):
            rd = ref_data[idx_d]
            mask = (df_events["title"] == rd["title"]) & (df_events["user"] == rd["user"]) & (pd.to_datetime(df_events["date"]).dt.date >= rd["start"]) & (pd.to_datetime(df_events["date"]).dt.date <= rd["end"])
            df_events = df_events[~mask]
            conn.update(spreadsheet=URL, worksheet="events", data=df_events); st.cache_data.clear(); st.rerun()

# --- 7. RENDERING ---
if view_mode == "Monat":
    cols = st.columns(7)
    for i, d in enumerate(WOCHENTAGE): cols[i].write(f"**{d}**")
    for week in calendar.monthcalendar(selected_year, selected_month):
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0: cols[i].markdown(render_day(date(selected_year, selected_month, day)), unsafe_allow_html=True)

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

else: # LISTE
    st.subheader("📋 Übersicht")
    l_items = []
    _, refs = get_grouped_event_list(df_ev_filt)
    for r in refs: l_items.append({"d": r["start"], "t": r["title"], "u": r["user"], "type": "ev", "info": f"{r['start'].strftime('%d.%m.')}-{r['end'].strftime('%d.%m.')}" if r['start']!=r['end'] else ""})
    if show_hols:
        for d, n in de_hols.items():
            if d.year == selected_year: l_items.append({"d": d, "t": n, "u": "Feiertag", "type": "hol", "info": ""})
    if show_ferien:
        for f in ferien_daten:
            try:
                s_f, e_f = datetime.strptime(f["start"][:10], "%Y-%m-%d").date(), datetime.strptime(f["end"][:10], "%Y-%m-%d").date()
                l_items.append({"d": s_f, "t": f["name"].split(" ")[0].capitalize(), "u": "Ferien", "type": "fer", "info": f"{s_f.strftime('%d.%m.')}-{e_f.strftime('%d.%m.')}"})
            except: continue
    for item in sorted(l_items, key=lambda x: x["d"]):
        if item["type"] == "ev": c = df_users[df_users["name"]==item["u"]]["color"].values[0] if item["u"] in df_users["name"].values else "#3498db"
        elif item["type"] == "hol": c = "#e74c3c"
        else: c = "#f1c40f"
        st.markdown(f'<div class="event-card" style="border-left:5px solid {c}; background:#262730; padding:10px;"><div><small>{item["d"].strftime("%d.%m.%Y")}</small><br><b>{item["t"]}</b><br><small style="color:#aaa">{item["info"]}</small></div><div style="background:{c}; color:white; padding:3px 10px; border-radius:12px; font-size:10px; font-weight:bold;">{item["u"]}</div></div>', unsafe_allow_html=True)

# --- 8. NUTZER VERWALTUNG ---
st.sidebar.markdown("---")
with st.sidebar.expander("👤 Nutzer verwalten"):
    t1, t2, t3 = st.tabs(["Neu", "Bearbeiten", "Löschen"])
    with t1:
        nu, nc = st.text_input("Name"), st.color_picker("Farbe", "#3498db")
        if st.button("Hinzufügen"):
            if nu:
                df_users = pd.concat([df_users, pd.DataFrame([{"name": nu, "color": nc}])], ignore_index=True)
                conn.update(spreadsheet=URL, worksheet="users", data=df_users); st.cache_data.clear(); st.rerun()
    with t2:
        if not df_users.empty:
            u_e = st.selectbox("Nutzer", df_users["name"].tolist())
            idx = df_users[df_users["name"] == u_e].index[0]
            new_c = st.color_picker("Farbe", df_users.at[idx, "color"])
            if st.button("Aktualisieren"):
                df_users.at[idx, "color"] = new_c
                conn.update(spreadsheet=URL, worksheet="users", data=df_users); st.cache_data.clear(); st.rerun()
    with t3:
        if not df_users.empty:
            u_d = st.selectbox("Löschen", df_users["name"].tolist(), key="du")
            if st.button("Entfernen"):
                df_users = df_users[df_users["name"] != u_d]
                conn.update(spreadsheet=URL, worksheet="users", data=df_users); st.cache_data.clear(); st.rerun()

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import holidays
import pandas as pd
from datetime import date, datetime, timedelta
import calendar

# --- KONFIGURATION ---
st.set_page_config(page_title="Team Kalender", layout="wide")

# HIER DEINE URL EINTRAGEN
URL = "https://docs.google.com/spreadsheets/d/1pk6k10OKOEeR7JPfOm6AjRiccLTx6Fnh01MitDGEXsE/edit#gid=0"

# Verbindung aufbauen
conn = st.connection("gsheets", type=GSheetsConnection)

# --- DATEN LADEN ---
def load_data():
    u = conn.read(spreadsheet=URL, worksheet="users", ttl=5) # ttl=5 für schnelles Refreshing
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
view_mode = st.sidebar.radio("Ansicht:", ["Monat", "Woche", "Liste"])

# Bundesland Auswahl
land = st.sidebar.selectbox("Bundesland für Feiertage:", 
                            ["BW", "BY", "BE", "BB", "HB", "HH", "HE", "MV", 
                             "NI", "NW", "RP", "SL", "SN", "ST", "SH", "TH"], index=14) # Default SH

# Nur bundeseinheitliche Feiertage?
only_national = st.sidebar.checkbox("Nur bundeseinheitliche Feiertage")

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
        
        # Aktuelle Daten holen
        current_row = df_users[df_users["name"] == user_to_edit].iloc[0]
        
        new_name_edit = st.text_input("Neuer Name", value=current_row["name"])
        new_color_edit = st.color_picker("Neue Farbe", value=current_row["color"])
        
        if st.button("Änderungen speichern"):
            # Den alten Eintrag entfernen und den neuen hinzufügen
            df_users = df_users[df_users["name"] != user_to_edit]
            edit_row = pd.DataFrame([{"name": new_name_edit, "color": new_color_edit}])
            updated_users = pd.concat([df_users, edit_row], ignore_index=True)
            
            # In Cloud speichern
            conn.update(spreadsheet=URL, worksheet="users", data=updated_users)
            
            # WICHTIG: Wenn der Name geändert wurde, müssen auch die Termine aktualisiert werden!
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
            # User entfernen
            updated_users = df_users[df_users["name"] != user_to_del]
            conn.update(spreadsheet=URL, worksheet="users", data=updated_users)
            
            # Termine entfernen (falls gewünscht)
            if delete_events:
                updated_events = df_events[df_events["user"] != user_to_del]
                conn.update(spreadsheet=URL, worksheet="events", data=updated_events)
            
            st.success(f"User {user_to_del} wurde gelöscht!")
            st.rerun()

# --- TERMIN EINTRAGEN ---
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

# --- TERMIN LÖSCHEN ---
with st.expander("🗑️ Termin löschen"):
    if not df_events.empty:
        # Wir erstellen eine Liste mit Anzeigenamen (Titel + Datum), 
        # damit man bei gleichen Namen weiß, welchen man löscht.
        event_options = df_events.apply(lambda x: f"{x['title']} ({x['date']})", axis=1).tolist()
        
        event_to_delete_str = st.selectbox("Welchen Termin möchtest du entfernen?", event_options)
        
        if st.button("Termin endgültig löschen"):
            # Den Index des gewählten Termins finden
            idx = event_options.index(event_to_delete_str)
            
            # Das DataFrame ohne diese Zeile neu erstellen
            updated_ev = df_events.drop(df_events.index[idx])
            
            # Die komplette Tabelle in Google Sheets überschreiben
            conn.update(spreadsheet=URL, worksheet="events", data=updated_ev)
            
            st.success("Der Termin wurde aus der Cloud gelöscht!")
            st.rerun()
    else:
        st.info("Keine Termine zum Löschen vorhanden.")

# --- FEIERTAGS-LOGIK ---
year = date.today().year
de_hols = holidays.Germany(subdiv=land, years=year)
national_hols = holidays.Germany(years=year)

# --- HELFER-FUNKTION: BOX RENDERN ---
def render_day_content(d_obj):
    h_name = de_hols.get(d_obj)
    # Filter: Falls "Nur National", dann h_name ignorieren wenn nicht in national_hols
    if only_national and d_obj not in national_hols:
        h_name = None
        
    u_events = df_events[df_events["date"] == str(d_obj)]
    
    # Heute markieren
    is_today = (d_obj == date.today())
    bg = "#3d3d3d" if is_today else "transparent"
    
    html = f"<div style='border:1px solid #555; padding:5px; min-height:80px; background-color:{bg}; border-radius:5px;'>"
    html += f"<b>{d_obj.day}</b>"
    if h_name:
        html += f"<div style='background:#7f8c8d; color:white; padding:2px; font-size:10px; border-radius:3px;'>{h_name}</div>"
    for _, row in u_events.iterrows():
        u_color = df_users[df_users["name"] == row["user"]]["color"].values[0] if row["user"] in df_users["name"].values else "#333"
        html += f"<div style='background:{u_color}; color:white; padding:2px; margin-top:2px; font-size:10px; border-radius:3px;'>{row['title']}</div>"
    html += "</div>"
    return html

# --- ANSICHTEN ---
if view_mode == "Monat":
    curr = date.today()
    month_days = calendar.monthcalendar(year, curr.month)
    cols = st.columns(7)
    for i, d in enumerate(["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]):
        cols[i].write(f"**{d}**")
    for week in month_days:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                with cols[i]:
                    st.markdown(render_day_content(date(year, curr.month, day)), unsafe_allow_html=True)

elif view_mode == "Woche":
    start_of_week = date.today() - timedelta(days=date.today().weekday())
    cols = st.columns(7)
    days_labels = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    for i in range(7):
        d_obj = start_of_week + timedelta(days=i)
        with cols[i]:
            st.write(f"**{days_labels[i]}** ({d_obj.day}.{d_obj.month}.)")
            st.markdown(render_day_content(d_obj), unsafe_allow_html=True)

elif view_mode == "Liste":
    st.subheader("Alle anstehenden Termine & Feiertage")
    combined = []
    # Feiertage sammeln
    for d, n in sorted(de_hols.items()):
        if not only_national or d in national_hols:
            combined.append({"Datum": d, "Ereignis": n, "User": "Gesetzlich", "Color": "#7f8c8d"})
    # User Events sammeln
    for _, row in df_events.iterrows():
        c = df_users[df_users["name"] == row["user"]]["color"].values[0] if row["user"] in df_users["name"].values else "#333"
        combined.append({"Datum": datetime.strptime(row["date"], "%Y-%m-%d").date(), "Ereignis": row["title"], "User": row["user"], "Color": c})
    
    combined.sort(key=lambda x: x["Datum"])
    for item in combined:
        if item["Datum"] >= date.today():
            st.markdown(f"<div style='border-left: 5px solid {item['Color']}; padding-left: 10px; margin-bottom: 5px;'><b>{item['Datum']}</b>: {item['Ereignis']} ({item['User']})</div>", unsafe_allow_html=True)

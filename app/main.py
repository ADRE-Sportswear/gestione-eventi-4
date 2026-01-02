# app/main.py
import streamlit as st
from datetime import date, timedelta, datetime
from db import init_db, list_artists, list_formats, list_events, get_event, upsert_event, delete_event
from seed_data import seed
from auth import ensure_default_users, hash_password, verify_password
from ui_components import month_grid
import db as DB
import json

st.set_page_config(page_title="Event Manager", layout="wide", initial_sidebar_state="expanded")

# Init DB and seed
init_db()
seed()
ensure_default_users()

# --- Authentication (basic) ---
if "user" not in st.session_state:
    st.session_state.user = None

def login_form():
    st.sidebar.header("Login")
    email = st.sidebar.text_input("Email")
    pwd = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        user = DB.get_user_by_email(email)
        if user and verify_password(pwd, user["password_hash"]):
            st.session_state.user = {"email": email, "name": user.get("name")}
            st.experimental_rerun()
        else:
            st.sidebar.error("Credenziali non valide")

def logout():
    st.session_state.user = None
    st.experimental_rerun()

if not st.session_state.user:
    login_form()
    st.sidebar.markdown("---")
    st.sidebar.markdown("Account di prova: admin@example.com / admin123")
    st.stop()
else:
    st.sidebar.write(f"Connesso come **{st.session_state.user['email']}**")
    if st.sidebar.button("Logout"):
        logout()

# --- Sidebar filters ---
st.sidebar.header("Filtri")
artists = list_artists()
formats = list_formats()
artist_options = {a["name"]: a["id"] for a in artists}
format_options = {f["name"]: f["id"] for f in formats}

selected_artists = st.sidebar.multiselect("Artisti", options=list(artist_options.keys()))
selected_formats = st.sidebar.multiselect("Format", options=list(format_options.keys()))

# date range quick
today = date.today()
month_picker = st.sidebar.date_input("Mese (scegli il primo giorno del mese)", value=today.replace(day=1))
if isinstance(month_picker, list):
    month_picker = month_picker[0]

# main layout: tabs
tab = st.tabs(["Calendario generale","Calendari per artista/format","Lista eventi","Crea evento"])
# prepare filters
artist_ids = [artist_options[n] for n in selected_artists] if selected_artists else None
format_ids = [format_options[n] for n in selected_formats] if selected_formats else None

# --- Calendario generale ---
with tab[0]:
    st.header("Calendario generale")
    weeks = month_grid(month_picker)
    # load events for month
    start = weeks[0][0].isoformat()
    end = weeks[-1][-1].isoformat()
    events = list_events(date_from=start, date_to=end, artist_ids=artist_ids, format_ids=format_ids)
    # group by date
    events_by_date = {}
    for e in events:
        events_by_date.setdefault(e["date"], []).append(e)

    cols = st.columns(7)
    # header weekdays
    weekdays = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    for i, c in enumerate(cols):
        c.markdown(f"**{weekdays[i]}**")
    for week in weeks:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                key = day.isoformat()
                evs = events_by_date.get(key, [])
                # highlight current month
                if day.month == month_picker.month:
                    st.markdown(f"**{day.day}**")
                else:
                    st.markdown(f"<span style='color:#999'>{day.day}</span>", unsafe_allow_html=True)
                for e in evs:
                    st.button(e["title"], key=f"btn_{e['id']}", on_click=lambda eid=e["id"]: st.session_state.update({"open_event": eid}))
    # open event modal if requested
    if "open_event" in st.session_state and st.session_state.get("open_event"):
        eid = st.session_state.pop("open_event")
        ev = get_event(eid)
        if ev:
            st.experimental_set_query_params(event=eid)
            st.write("### Scheda evento")
            with st.form("edit_event"):
                title = st.text_input("Titolo", value=ev["title"])
                date_val = st.date_input("Data", value=datetime.fromisoformat(ev["date"]).date())
                # artists multi
                artist_map = {a["id"]:a["name"] for a in artists}
                selected = ev.get("artist_ids") or []
                selected_names = [artist_map.get(int(i)) for i in selected if int(i) in artist_map]
                chosen = st.multiselect("Artisti", options=list(artist_options.keys()), default=selected_names)
                chosen_ids = [artist_options[n] for n in chosen]
                fmt = None
                if ev.get("format_id"):
                    fmt = next((f["name"] for f in formats if f["id"]==ev["format_id"]), None)
                fmt_choice = st.selectbox("Format", options=[""]+list(format_options.keys()), index=(list(format_options.keys()).index(fmt) + 1) if fmt else 0)
                notes = st.text_area("Note", value=ev.get("notes") or "")
                status = st.selectbox("Status", options=["planned","confirmed","cancelled"], index=["planned","confirmed","cancelled"].index(ev.get("status","planned")))
                submitted = st.form_submit_button("Salva")
                if submitted:
                    upsert_event({
                        "id": ev["id"],
                        "title": title,
                        "date": date_val.isoformat(),
                        "format_id": format_options.get(fmt_choice) if fmt_choice else None,
                        "artist_ids": chosen_ids,
                        "notes": notes,
                        "status": status,
                        "services_json": ev.get("services_json") or []
                    })
                    st.success("Evento aggiornato")
                    st.experimental_rerun()

# --- Calendari per artista/format ---
with tab[1]:
    st.header("Calendari per artista / format")
    sel_type = st.radio("Visualizza per", ["Artista","Format"])
    if sel_type == "Artista":
        sel = st.selectbox("Scegli artista", options=list(artist_options.keys()))
        if sel:
            aid = artist_options[sel]
            # show next 60 days for artista
            start = date.today().isoformat()
            end = (date.today() + timedelta(days=60)).isoformat()
            evs = list_events(date_from=start, date_to=end, artist_ids=[aid])
            st.subheader(f"Eventi per {sel}")
            for e in evs:
                st.card = st.expander(f"{e['date']} — {e['title']}")
                with st.expander(f"{e['date']} — {e['title']}"):
                    st.write(e.get("notes") or "")
                    if st.button("Modifica", key=f"mod_{e['id']}"):
                        st.session_state.update({"open_event": e["id"]})
                        st.experimental_rerun()
    else:
        sel = st.selectbox("Scegli format", options=list(format_options.keys()))
        if sel:
            fid = format_options[sel]
            start = date.today().isoformat()
            end = (date.today() + timedelta(days=365)).isoformat()
            evs = list_events(date_from=start, date_to=end, format_ids=[fid])
            st.subheader(f"Eventi per format {sel}")
            for e in evs:
                with st.expander(f"{e['date']} — {e['title']}"):
                    st.write(e.get("notes") or "")
                    if st.button("Modifica", key=f"modf_{e['id']}"):
                        st.session_state.update({"open_event": e["id"]})
                        st.experimental_rerun()

# --- Lista eventi ---
with tab[2]:
    st.header("Lista eventi")
    start = st.date_input("Da", value=date.today() - timedelta(days=30))
    end = st.date_input("A", value=date.today() + timedelta(days=90))
    evs = list_events(date_from=start.isoformat(), date_to=end.isoformat(), artist_ids=artist_ids, format_ids=format_ids)
    st.write(f"Trovati {len(evs)} eventi")
    for e in sorted(evs, key=lambda x: x["date"]):
        cols = st.columns([3,1,1,1])
        cols[0].markdown(f"**{e['date']}** — {e['title']}")
        cols[1].write(", ".join([a for a in e.get("artist_ids") or []]) )
        if cols[2].button("Apri", key=f"open_{e['id']}"):
            st.session_state.update({"open_event": e["id"]})
            st.experimental_rerun()
        if cols[3].button("Elimina", key=f"del_{e['id']}"):
            delete_event(e["id"])
            st.experimental_rerun()

# --- Crea evento ---
with tab[3]:
    st.header("Crea nuovo evento")
    with st.form("create_event"):
        title = st.text_input("Titolo")
        date_val = st.date_input("Data", value=date.today())
        chosen = st.multiselect("Artisti", options=list(artist_options.keys()))
        chosen_ids = [artist_options[n] for n in chosen]
        fmt_choice = st.selectbox("Format", options=[""]+list(format_options.keys()))
        notes = st.text_area("Note")
        submitted = st.form_submit_button("Crea")
        if submitted:
            upsert_event({
                "title": title,
                "date": date_val.isoformat(),
                "format_id": format_options.get(fmt_choice) if fmt_choice else None,
                "artist_ids": chosen_ids,
                "notes": notes,
                "services_json": []
            })
            st.success("Evento creato")
            st.experimental_rerun()

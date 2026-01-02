# app/ui_components.py
import streamlit as st
from datetime import date, timedelta
import pandas as pd

def month_grid(selected_month: date):
    # ritorna lista di settimane con giorni (per visualizzazione calendario semplice)
    first = selected_month.replace(day=1)
    start = first - timedelta(days=first.weekday())  # lunedì come primo giorno
    weeks = []
    cur = start
    for w in range(6):
        week = []
        for d in range(7):
            week.append(cur)
            cur = cur + timedelta(days=1)
        weeks.append(week)
    return weeks

def day_card(day, events_for_day, highlight=False):
    # semplice card per giorno
    st.markdown(f"**{day.day}** {'— ' + day.strftime('%a')}")
    if events_for_day:
        for e in events_for_day:
            st.markdown(f"- {e['title']}  ")
    else:
        st.write("")

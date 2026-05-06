import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date, timedelta
import calendar

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sala Riunioni",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300..700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background-color: #f7f6f2; }

/* Header custom */
.sala-header {
    background: #f9f8f5;
    border-bottom: 1px solid #d4d1ca;
    padding: 12px 24px;
    display: flex; align-items: center; gap: 12px;
    margin: -1rem -1rem 1.5rem -1rem;
}
.sala-header-logo { font-size: 1.5rem; }
.sala-header-title { font-size: 1.1rem; font-weight: 700; color: #28251d; }

/* Stat cards */
.stat-row { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 1.5rem; }
.stat-card {
    background: #f9f8f5; border: 1px solid #d4d1ca;
    border-radius: 10px; padding: 16px 20px;
    flex: 1; min-width: 150px;
}
.stat-label { font-size: 0.7rem; color: #7a7974; text-transform: uppercase;
    letter-spacing: .05em; margin-bottom: 4px; }
.stat-value { font-size: 1.8rem; font-weight: 700; color: #28251d;
    font-variant-numeric: tabular-nums; line-height: 1; }
.stat-sub { font-size: 0.75rem; color: #01696f; margin-top: 4px; }

/* Booking card */
.bk-card {
    background: #f9f8f5; border: 1px solid #d4d1ca;
    border-radius: 10px; padding: 16px; margin-bottom: 10px;
    display: grid; grid-template-columns: 64px 1fr auto;
    gap: 16px; align-items: start;
}
.bk-date { background: #f3f0ec; border-radius: 8px;
    padding: 10px 8px; text-align: center; }
.bk-day { font-size: 1.6rem; font-weight: 700; color: #01696f; line-height: 1; }
.bk-month { font-size: 0.65rem; color: #7a7974; text-transform: uppercase;
    letter-spacing: .05em; }
.bk-title { font-size: 0.95rem; font-weight: 600; color: #28251d; }
.bk-meta { font-size: 0.8rem; color: #7a7974; margin-top: 6px; }

/* Badges */
.badge {
    display: inline-block; padding: 2px 10px;
    border-radius: 999px; font-size: 0.7rem; font-weight: 500;
}
.badge-confirmed { background: #d4dfcc; color: #437a22; }
.badge-pending   { background: #ddcfc6; color: #964219; }
.badge-cancelled { background: #e6e4df; color: #7a7974; }

/* Calendar */
.cal-grid {
    display: grid; grid-template-columns: repeat(7, 1fr);
    gap: 4px; margin-top: 8px;
}
.cal-header-cell {
    text-align: center; font-size: 0.7rem; font-weight: 600;
    color: #7a7974; text-transform: uppercase; letter-spacing: .05em;
    padding: 8px 0;
}
.cal-cell {
    background: #f9f8f5; border: 1px solid #d4d1ca;
    border-radius: 8px; padding: 6px; min-height: 90px;
    font-size: 0.8rem;
}
.cal-cell.other { opacity: .4; }
.cal-cell.today { border-color: #01696f; }
.cal-num { font-weight: 600; margin-bottom: 4px; font-size: 0.85rem; }
.cal-num-today {
    background: #01696f; color: white; border-radius: 50%;
    width: 22px; height: 22px; display: flex; align-items: center;
    justify-content: center; font-size: 0.8rem; font-weight: 600;
}
.cal-ev {
    font-size: 0.65rem; padding: 1px 5px;
    border-radius: 4px; margin-bottom: 2px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.cal-ev-confirmed { background: #cedcd8; color: #01696f; }
.cal-ev-pending   { background: #ddcfc6; color: #964219; }

.conflict-warning {
    background: #ddcfc6; border: 1px solid #964219;
    border-radius: 8px; padding: 10px 14px;
    font-size: 0.85rem; color: #964219; margin: 8px 0;
}
</style>
""", unsafe_allow_html=True)

# ─── Google Sheets connection ──────────────────────────────────────────────────
SHEET_NAME = "SalaRiunioni"  # Nome del foglio Google Sheets da creare
WORKSHEET_NAME = "prenotazioni"

@st.cache_resource(ttl=30)
def get_sheet():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets",
                  "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(dict(creds_dict), scopes=scopes)
        gc = gspread.authorize(creds)
        # Prova ad aprire, altrimenti crea
        try:
            sh = gc.open(SHEET_NAME)
        except gspread.SpreadsheetNotFound:
            sh = gc.create(SHEET_NAME)
            sh.share(None, perm_type='anyone', role='reader')
        try:
            ws = sh.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(WORKSHEET_NAME, rows=1000, cols=10)
            ws.append_row(["id","titolo","organizzatore","data","inizio","fine",
                           "partecipanti","note","stato"])
        return ws
    except Exception as e:
        st.error(f"❌ Errore connessione Google Sheets: {e}")
        return None

@st.cache_data(ttl=15)
def load_bookings():
    ws = get_sheet()
    if ws is None:
        return pd.DataFrame()
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["id","titolo","organizzatore","data",
                                     "inizio","fine","partecipanti","note","stato"])
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
    return df

def save_booking(row: dict):
    ws = get_sheet()
    if ws is None:
        return False
    ws.append_row([
        row["id"], row["titolo"], row["organizzatore"], str(row["data"]),
        row["inizio"], row["fine"], row["partecipanti"], row["note"], row["stato"]
    ])
    load_bookings.clear()
    return True

def update_booking(row_id, updates: dict):
    ws = get_sheet()
    if ws is None:
        return False
    records = ws.get_all_records()
    for i, r in enumerate(records, start=2):
        if str(r.get("id")) == str(row_id):
            col_map = {"id":1,"titolo":2,"organizzatore":3,"data":4,"inizio":5,
                       "fine":6,"partecipanti":7,"note":8,"stato":9}
            for k, v in updates.items():
                if k in col_map:
                    ws.update_cell(i, col_map[k], str(v))
            break
    load_bookings.clear()
    return True

def delete_booking(row_id):
    ws = get_sheet()
    if ws is None:
        return False
    records = ws.get_all_records()
    for i, r in enumerate(records, start=2):
        if str(r.get("id")) == str(row_id):
            ws.delete_rows(i)
            break
    load_bookings.clear()
    return True

def get_next_id(df):
    if df.empty or "id" not in df.columns:
        return 1
    try:
        return int(df["id"].max()) + 1
    except:
        return 1

def check_conflict(df, data, inizio, fine, exclude_id=None):
    sub = df[(df["data"] == data) & (df["stato"] != "cancellata")]
    if exclude_id is not None:
        sub = sub[sub["id"] != exclude_id]
    conflicts = sub[(sub["inizio"] < fine) & (sub["fine"] > inizio)]
    return conflicts

# ─── HEADER ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="sala-header">
  <div class="sala-header-logo">🏢</div>
  <div class="sala-header-title">Sala Riunioni</div>
</div>
""", unsafe_allow_html=True)

# ─── TABS ────────────────────────────────────────────────────────────────────
tab_cal, tab_list, tab_new = st.tabs(["📅 Calendario", "📋 Prenotazioni", "➕ Nuova prenotazione"])

df = load_bookings()
MONTHS_IT = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno",
             "Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
DAY_IT = ["Lun","Mar","Mer","Gio","Ven","Sab","Dom"]
today = date.today()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 – CALENDARIO
# ═══════════════════════════════════════════════════════════════════════════════
with tab_cal:
    col_nav1, col_nav2, col_nav3 = st.columns([1, 3, 1])
    if "cal_year" not in st.session_state:
        st.session_state.cal_year = today.year
        st.session_state.cal_month = today.month

    with col_nav1:
        if st.button("◀ Prec.", key="prev_month"):
            if st.session_state.cal_month == 1:
                st.session_state.cal_month = 12
                st.session_state.cal_year -= 1
            else:
                st.session_state.cal_month -= 1
    with col_nav2:
        st.markdown(f"<h3 style='text-align:center;margin:0;'>{MONTHS_IT[st.session_state.cal_month-1]} {st.session_state.cal_year}</h3>", unsafe_allow_html=True)
    with col_nav3:
        if st.button("Succ. ▶", key="next_month"):
            if st.session_state.cal_month == 12:
                st.session_state.cal_month = 1
                st.session_state.cal_year += 1
            else:
                st.session_state.cal_month += 1

    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("Oggi", key="go_today"):
            st.session_state.cal_year = today.year
            st.session_state.cal_month = today.month

    yr, mo = st.session_state.cal_year, st.session_state.cal_month
    cal = calendar.monthcalendar(yr, mo)

    # Build HTML calendar
    header_html = "".join(f'<div class="cal-header-cell">{d}</div>' for d in DAY_IT)
    cells_html = ""
    for week in cal:
        for day in week:
            if day == 0:
                cells_html += '<div class="cal-cell other"><div class="cal-num"></div></div>'
            else:
                this_date = date(yr, mo, day)
                is_today = this_date == today
                day_bk = df[df["data"] == this_date] if not df.empty else pd.DataFrame()
                num_html = f'<div class="cal-num-today">{day}</div>' if is_today else f'<div class="cal-num">{day}</div>'
                events_html = ""
                for _, bk in day_bk.iterrows():
                    if bk.get("stato") == "cancellata":
                        continue
                    cls = "cal-ev-confirmed" if bk.get("stato") == "confermata" else "cal-ev-pending"
                    ev_text = f"{bk.get('inizio','')} {bk.get('titolo','')}"
                    events_html += f'<div class="cal-ev {cls}" title="{ev_text}">{ev_text}</div>'
                cell_cls = "cal-cell today" if is_today else "cal-cell"
                cells_html += f'<div class="{cell_cls}">{num_html}{events_html}</div>'

    st.markdown(f'<div class="cal-grid">{header_html}{cells_html}</div>', unsafe_allow_html=True)

    # Legenda
    st.markdown("""
    <div style="display:flex;gap:16px;margin-top:12px;font-size:0.75rem;color:#7a7974;">
      <span><span class="cal-ev cal-ev-confirmed" style="padding:2px 8px;border-radius:4px;">■</span> Confermata</span>
      <span><span class="cal-ev cal-ev-pending" style="padding:2px 8px;border-radius:4px;">■</span> In attesa</span>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 – LISTA PRENOTAZIONI
# ═══════════════════════════════════════════════════════════════════════════════
with tab_list:
    # Stats
    if not df.empty:
        upcoming = df[(df["data"] >= today) & (df["stato"] != "cancellata")].shape[0]
        this_mo = df[(df["data"].apply(lambda x: x.month if pd.notnull(x) else 0) == today.month) &
                     (df["data"].apply(lambda x: x.year if pd.notnull(x) else 0) == today.year) &
                     (df["stato"] != "cancellata")].shape[0]
        confirmed = df[df["stato"] == "confermata"].shape[0]
        pending = df[df["stato"] == "in attesa"].shape[0]
    else:
        upcoming = this_mo = confirmed = pending = 0

    st.markdown(f"""
    <div class="stat-row">
      <div class="stat-card">
        <div class="stat-label">Prossime</div>
        <div class="stat-value">{upcoming}</div>
        <div class="stat-sub">da oggi in poi</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Questo mese</div>
        <div class="stat-value">{this_mo}</div>
        <div class="stat-sub">{MONTHS_IT[today.month-1]}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Confermate</div>
        <div class="stat-value">{confirmed}</div>
        <div class="stat-sub">totale</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">In attesa</div>
        <div class="stat-value">{pending}</div>
        <div class="stat-sub">da confermare</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Filtri
    fc1, fc2, fc3 = st.columns([1, 1, 2])
    with fc1:
        f_stato = st.selectbox("Stato", ["Tutti", "confermata", "in attesa", "cancellata"], key="f_stato")
    with fc2:
        f_mese = st.selectbox("Mese", ["Tutti"] + MONTHS_IT, key="f_mese")
    with fc3:
        f_cerca = st.text_input("Cerca titolo / organizzatore", key="f_cerca")

    filtered = df.copy() if not df.empty else pd.DataFrame()
    if not filtered.empty:
        if f_stato != "Tutti":
            filtered = filtered[filtered["stato"] == f_stato]
        if f_mese != "Tutti":
            mo_idx = MONTHS_IT.index(f_mese) + 1
            filtered = filtered[filtered["data"].apply(lambda x: x.month if pd.notnull(x) else 0) == mo_idx]
        if f_cerca:
            mask = (filtered["titolo"].str.contains(f_cerca, case=False, na=False) |
                    filtered["organizzatore"].str.contains(f_cerca, case=False, na=False))
            filtered = filtered[mask]
        filtered = filtered.sort_values(["data","inizio"])

    if filtered.empty:
        st.info("Nessuna prenotazione trovata. Usa il tab ➕ per aggiungerne una.")
    else:
        for _, bk in filtered.iterrows():
            d_obj = bk["data"]
            day_num = d_obj.day if pd.notnull(d_obj) else "?"
            month_str = MONTHS_IT[d_obj.month-1][:3].upper() if pd.notnull(d_obj) else "---"
            stato = bk.get("stato", "in attesa")
            badge_cls = "badge-confirmed" if stato == "confermata" else "badge-pending" if stato == "in attesa" else "badge-cancelled"
            badge_lbl = "✓ Confermata" if stato == "confermata" else "⏳ In attesa" if stato == "in attesa" else "✕ Cancellata"

            parts_html = f"👥 {bk['partecipanti']}" if bk.get("partecipanti") else ""
            notes_html = f"📝 {bk['note']}" if bk.get("note") else ""

            st.markdown(f"""
            <div class="bk-card">
              <div class="bk-date"><div class="bk-day">{day_num}</div><div class="bk-month">{month_str}</div></div>
              <div>
                <div class="bk-title">{bk['titolo']}</div>
                <span class="badge {badge_cls}">{badge_lbl}</span>
                <div class="bk-meta">🕐 {bk['inizio']}–{bk['fine']} &nbsp; 👤 {bk['organizzatore']} &nbsp; {parts_html} &nbsp; {notes_html}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            ca, cb, cc, cd = st.columns([1, 1, 1, 4])
            with ca:
                if stato == "in attesa":
                    if st.button("✓ Conferma", key=f"conf_{bk['id']}"):
                        update_booking(bk["id"], {"stato": "confermata"})
                        st.rerun()
            with cb:
                if st.button("✏️ Modifica", key=f"edit_{bk['id']}"):
                    st.session_state["edit_id"] = bk["id"]
                    st.session_state["edit_data"] = dict(bk)
            with cc:
                if st.button("🗑 Elimina", key=f"del_{bk['id']}"):
                    delete_booking(bk["id"])
                    st.success("Prenotazione eliminata.")
                    st.rerun()

    # Modifica inline
    if "edit_id" in st.session_state:
        bd = st.session_state["edit_data"]
        st.divider()
        st.subheader("✏️ Modifica prenotazione")
        with st.form("edit_form"):
            ec1, ec2 = st.columns(2)
            with ec1:
                e_titolo = st.text_input("Oggetto", value=bd.get("titolo",""))
                e_org = st.text_input("Organizzatore", value=bd.get("organizzatore",""))
                e_data = st.date_input("Data", value=bd.get("data", today))
            with ec2:
                e_start = st.text_input("Ora inizio (HH:MM)", value=bd.get("inizio","09:00"))
                e_end = st.text_input("Ora fine (HH:MM)", value=bd.get("fine","10:00"))
                e_stato = st.selectbox("Stato", ["confermata","in attesa","cancellata"],
                                       index=["confermata","in attesa","cancellata"].index(bd.get("stato","confermata")))
            e_att = st.text_input("Partecipanti", value=bd.get("partecipanti",""))
            e_notes = st.text_area("Note", value=bd.get("note",""), height=80)
            sub_e, canc_e = st.columns(2)
            with sub_e:
                submitted_e = st.form_submit_button("💾 Salva modifiche", use_container_width=True)
            with canc_e:
                cancel_e = st.form_submit_button("Annulla", use_container_width=True)

        if submitted_e:
            if e_start >= e_end:
                st.error("L'ora di fine deve essere successiva all'ora di inizio.")
            else:
                conflicts = check_conflict(df, e_data, e_start, e_end, exclude_id=bd["id"])
                if not conflicts.empty:
                    names = ", ".join(conflicts["titolo"].tolist())
                    st.markdown(f'<div class="conflict-warning">⚠️ Conflitto con: {names}</div>', unsafe_allow_html=True)
                else:
                    update_booking(bd["id"], {"titolo":e_titolo,"organizzatore":e_org,
                                              "data":str(e_data),"inizio":e_start,"fine":e_end,
                                              "partecipanti":e_att,"note":e_notes,"stato":e_stato})
                    del st.session_state["edit_id"]
                    del st.session_state["edit_data"]
                    st.success("✅ Prenotazione aggiornata!")
                    st.rerun()
        if cancel_e:
            del st.session_state["edit_id"]
            del st.session_state["edit_data"]
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 – NUOVA PRENOTAZIONE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_new:
    st.subheader("Nuova prenotazione")
    with st.form("new_booking", clear_on_submit=True):
        n1, n2 = st.columns(2)
        with n1:
            n_titolo = st.text_input("Oggetto riunione *")
            n_org = st.text_input("Organizzatore *")
            n_data = st.date_input("Data *", value=today, min_value=today)
        with n2:
            n_start = st.text_input("Ora inizio (HH:MM) *", value="09:00")
            n_end = st.text_input("Ora fine (HH:MM) *", value="10:00")
            n_stato = st.selectbox("Stato", ["confermata","in attesa"])
        n_att = st.text_input("Partecipanti (separati da virgola)")
        n_notes = st.text_area("Note / Agenda", height=80)

        submitted = st.form_submit_button("🏢 Prenota sala", use_container_width=True, type="primary")

    if submitted:
        if not n_titolo or not n_org:
            st.error("Compila i campi obbligatori: Oggetto e Organizzatore.")
        elif n_start >= n_end:
            st.error("L'ora di fine deve essere successiva all'ora di inizio.")
        else:
            df_fresh = load_bookings()
            conflicts = check_conflict(df_fresh, n_data, n_start, n_end)
            if not conflicts.empty:
                names = ", ".join(conflicts["titolo"].tolist())
                st.markdown(f'<div class="conflict-warning">⚠️ Conflitto di orario con: <strong>{names}</strong> ({conflicts.iloc[0]["inizio"]}–{conflicts.iloc[0]["fine"]})</div>', unsafe_allow_html=True)
            else:
                new_id = get_next_id(df_fresh)
                ok = save_booking({
                    "id": new_id, "titolo": n_titolo, "organizzatore": n_org,
                    "data": n_data, "inizio": n_start, "fine": n_end,
                    "partecipanti": n_att, "note": n_notes, "stato": n_stato
                })
                if ok:
                    st.success(f"✅ Sala prenotata! [{n_data} dalle {n_start} alle {n_end}]")
                    st.balloons()

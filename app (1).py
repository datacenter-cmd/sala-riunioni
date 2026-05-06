import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import locale

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
.sala-header {
    background: #f9f8f5; border-bottom: 1px solid #d4d1ca;
    padding: 12px 24px; display: flex; align-items: center; gap: 12px;
    margin: -1rem -1rem 1.5rem -1rem;
}
.sala-header-logo { font-size: 1.5rem; }
.sala-header-title { font-size: 1.1rem; font-weight: 700; color: #28251d; }
.stat-row { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 1.5rem; }
.stat-card { background: #f9f8f5; border: 1px solid #d4d1ca; border-radius: 10px; padding: 16px 20px; flex: 1; min-width: 150px; }
.stat-label { font-size: 0.7rem; color: #7a7974; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px; }
.stat-value { font-size: 1.8rem; font-weight: 700; color: #28251d; font-variant-numeric: tabular-nums; line-height: 1; }
.stat-sub { font-size: 0.75rem; color: #01696f; margin-top: 4px; }
.bk-card { background: #f9f8f5; border: 1px solid #d4d1ca; border-radius: 10px; padding: 16px; margin-bottom: 10px; display: grid; grid-template-columns: 64px 1fr auto; gap: 16px; align-items: start; }
.bk-date { background: #f3f0ec; border-radius: 8px; padding: 10px 8px; text-align: center; }
.bk-day { font-size: 1.6rem; font-weight: 700; color: #01696f; line-height: 1; }
.bk-month { font-size: 0.65rem; color: #7a7974; text-transform: uppercase; letter-spacing: .05em; }
.bk-title { font-size: 0.95rem; font-weight: 600; color: #28251d; }
.bk-meta { font-size: 0.8rem; color: #7a7974; margin-top: 6px; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.7rem; font-weight: 500; }
.badge-confirmed { background: #d4dfcc; color: #437a22; }
.badge-pending { background: #ddcfc6; color: #964219; }
.badge-cancelled { background: #e6e4df; color: #7a7974; }
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-top: 8px; }
.cal-header-cell { text-align: center; font-size: 0.7rem; font-weight: 600; color: #7a7974; text-transform: uppercase; letter-spacing: .05em; padding: 8px 0; }
.cal-cell { background: #f9f8f5; border: 1px solid #d4d1ca; border-radius: 8px; padding: 6px; min-height: 90px; font-size: 0.8rem; }
.cal-cell.other { opacity: .4; }
.cal-cell.today { border-color: #01696f; }
.cal-num { font-weight: 600; margin-bottom: 4px; font-size: 0.85rem; }
.cal-num-today { background: #01696f; color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; font-weight: 600; }
.cal-ev { font-size: 0.65rem; padding: 1px 5px; border-radius: 4px; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cal-ev-confirmed { background: #cedcd8; color: #01696f; }
.cal-ev-pending { background: #ddcfc6; color: #964219; }
.conflict-warning { background: #ddcfc6; border: 1px solid #964219; border-radius: 8px; padding: 10px 14px; font-size: 0.85rem; color: #964219; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

# ─── Colleghi ─────────────────────────────────────────────────────────────────
COLLEGHI = [
    "Carlotta Aquilini",
    "Sara Bandini",
    "Valeria Bracciali",
    "Domenico D'Andrea",
    "Ilaria Di Sciullo",
    "Eduart Dyla",
    "Oriljana Dyla",
    "Abduljcerim Ese",
    "Marco Filippelli",
    "Ignazio Gatta",
    "Simone Marra",
    "Daniele Notaro",
    "Leonardo Nuti",
    "Flavio Piraino",
    "Tiziana Prestigiacomo",
    "Andrea Rindinella",
    "Lorenzo Russo",
    "Veronica Serratore",
    "Andrea Torricelli",
    "Alessia Valle",
]

# ─── Date helpers ─────────────────────────────────────────────────────────────
MONTHS_IT = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno",
             "Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
DAY_IT = ["Lun","Mar","Mer","Gio","Ven","Sab","Dom"]
MONTHS_IT_SHORT = ["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"]

def format_date_it(d):
    """Restituisce data in formato italiano: es. 6 maggio 2026"""
    if pd.isnull(d):
        return ""
    if isinstance(d, str):
        try:
            d = datetime.strptime(d, "%Y-%m-%d").date()
        except:
            return d
    return f"{d.day} {MONTHS_IT[d.month-1].lower()} {d.year}"

def format_date_short_it(d):
    """es. 06/05/2026"""
    if pd.isnull(d):
        return ""
    if isinstance(d, str):
        try:
            d = datetime.strptime(d, "%Y-%m-%d").date()
        except:
            return d
    return f"{d.day:02d}/{d.month:02d}/{d.year}"

# ─── Google Sheets connection ──────────────────────────────────────────────────
SHEET_NAME = "SalaRiunioni"
WORKSHEET_NAME = "prenotazioni"

@st.cache_resource(ttl=30)
def get_sheet():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets",
                  "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(dict(creds_dict), scopes=scopes)
        gc = gspread.authorize(creds)
        try:
            sh = gc.open(SHEET_NAME)
        except gspread.SpreadsheetNotFound:
            sh = gc.create(SHEET_NAME)
            sh.share(None, perm_type="anyone", role="reader")
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
    ws.append_row([row["id"], row["titolo"], row["organizzatore"], str(row["data"]),
                   row["inizio"], row["fine"], row["partecipanti"], row["note"], row["stato"]])
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
    return sub[(sub["inizio"] < fine) & (sub["fine"] > inizio)]

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
today = date.today()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 – CALENDARIO
# ═══════════════════════════════════════════════════════════════════════════════
with tab_cal:
    # View selector
    view_col, nav_col1, nav_col2, nav_col3, today_col = st.columns([2, 0.5, 2, 0.5, 1])
    if "cal_year" not in st.session_state:
        st.session_state.cal_year = today.year
        st.session_state.cal_month = today.month
        st.session_state.cal_week = today
        st.session_state.cal_day = today
        st.session_state.cal_view = "month"

    with view_col:
        view_choice = st.radio("Vista", ["📅 Mese", "📆 Settimana", "🗓 Giorno"],
                               horizontal=True, key="cal_view_radio",
                               index=["📅 Mese","📆 Settimana","🗓 Giorno"].index(
                                   {"month":"📅 Mese","week":"📆 Settimana","day":"🗓 Giorno"}.get(st.session_state.cal_view,"📅 Mese")))
        st.session_state.cal_view = {"📅 Mese":"month","📆 Settimana":"week","🗓 Giorno":"day"}[view_choice]

    # Navigation label
    if st.session_state.cal_view == "month":
        nav_label = f"{MONTHS_IT[st.session_state.cal_month-1]} {st.session_state.cal_year}"
    elif st.session_state.cal_view == "week":
        ws = st.session_state.cal_week
        we = ws + timedelta(days=6)
        nav_label = f"{ws.day} {MONTHS_IT_SHORT[ws.month-1]} – {we.day} {MONTHS_IT_SHORT[we.month-1]} {we.year}"
    else:
        d = st.session_state.cal_day
        nav_label = format_date_it(d)

    with nav_col1:
        if st.button("◀", key="nav_prev"):
            if st.session_state.cal_view == "month":
                if st.session_state.cal_month == 1: st.session_state.cal_month = 12; st.session_state.cal_year -= 1
                else: st.session_state.cal_month -= 1
            elif st.session_state.cal_view == "week":
                st.session_state.cal_week -= timedelta(days=7)
            else:
                st.session_state.cal_day -= timedelta(days=1)
    with nav_col2:
        st.markdown(f"<h4 style='text-align:center;margin:6px 0;'>{nav_label}</h4>", unsafe_allow_html=True)
    with nav_col3:
        if st.button("▶", key="nav_next"):
            if st.session_state.cal_view == "month":
                if st.session_state.cal_month == 12: st.session_state.cal_month = 1; st.session_state.cal_year += 1
                else: st.session_state.cal_month += 1
            elif st.session_state.cal_view == "week":
                st.session_state.cal_week += timedelta(days=7)
            else:
                st.session_state.cal_day += timedelta(days=1)
    with today_col:
        if st.button("Oggi", key="go_today"):
            st.session_state.cal_year = today.year
            st.session_state.cal_month = today.month
            st.session_state.cal_week = today - timedelta(days=(today.weekday()))
            st.session_state.cal_day = today

    # ── MONTH VIEW ──────────────────────────────────────────────────────────
    if st.session_state.cal_view == "month":
        yr, mo = st.session_state.cal_year, st.session_state.cal_month
        cal_grid = calendar.monthcalendar(yr, mo)
        header_html = "".join(f'<div class="cal-header-cell">{d}</div>' for d in DAY_IT)
        cells_html = ""
        for week in cal_grid:
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
                        if bk.get("stato") == "cancellata": continue
                        cls = "cal-ev-confirmed" if bk.get("stato") == "confermata" else "cal-ev-pending"
                        ev_text = f"{bk.get('inizio','')} {bk.get('titolo','')}"
                        events_html += f'<div class="cal-ev {cls}">{ev_text}</div>'
                    cell_cls = "cal-cell today" if is_today else "cal-cell"
                    cells_html += f'<div class="{cell_cls}">{num_html}{events_html}</div>'
        st.markdown(f'<div class="cal-grid">{header_html}{cells_html}</div>', unsafe_allow_html=True)

    # ── WEEK VIEW ────────────────────────────────────────────────────────────
    elif st.session_state.cal_view == "week":
        week_start = st.session_state.cal_week
        # Make sure it starts on Monday
        week_start = week_start - timedelta(days=week_start.weekday())
        week_days = [week_start + timedelta(days=i) for i in range(7)]
        HOURS = list(range(8, 20))
        SLOT_H = 60  # px per hour

        # Build week grid HTML
        grid_html = '''
        <style>
        .wk-grid { display: grid; grid-template-columns: 52px repeat(7, 1fr); border: 1px solid #d4d1ca; border-radius: 10px; overflow: hidden; font-family: Inter, sans-serif; }
        .wk-hdr { background: #f3f0ec; padding: 6px 4px; text-align: center; font-size: 0.7rem; font-weight: 600; color: #7a7974; border-bottom: 1px solid #d4d1ca; border-right: 1px solid #e6e4df; }
        .wk-hdr.today-col { color: #01696f; background: #e8f0ef; }
        .wk-hdr-day { font-size: 1.1rem; font-weight: 700; color: #28251d; }
        .wk-hdr-day.today-day { color: #01696f; }
        .wk-time-col { background: #f9f8f5; border-right: 1px solid #d4d1ca; }
        .wk-time-label { height: 60px; display: flex; align-items: flex-start; justify-content: flex-end; padding: 4px 6px 0 0; font-size: 0.65rem; color: #7a7974; border-bottom: 1px solid #f0ede8; }
        .wk-day-col { position: relative; border-right: 1px solid #e6e4df; background: #f9f8f5; }
        .wk-day-col.today-col { background: #f4faf9; }
        .wk-slot { height: 60px; border-bottom: 1px solid #f0ede8; }
        .wk-event {
            position: absolute; left: 2px; right: 2px;
            border-radius: 5px; padding: 3px 6px;
            font-size: 0.68rem; font-weight: 500; overflow: hidden;
            cursor: pointer; z-index: 2; box-shadow: 0 1px 3px rgba(0,0,0,.1);
        }
        .wk-event.confirmed { background: #01696f; color: white; }
        .wk-event.pending   { background: #964219; color: white; }
        .wk-event-title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .wk-event-time  { font-size: 0.6rem; opacity: .85; }
        </style>
        <div class="wk-grid">
        '''

        # Corner cell
        grid_html += '<div class="wk-hdr"></div>'
        # Day headers
        for d in week_days:
            is_t = d == today
            grid_html += f'''<div class="wk-hdr {"today-col" if is_t else ""}">
                {DAY_IT[d.weekday()]}<br>
                <span class="wk-hdr-day {"today-day" if is_t else ""}">{d.day}</span>
            </div>'''

        # Time rows + events
        # Pre-compute events per day
        day_events = {}
        for d in week_days:
            evs = df[df["data"] == d] if not df.empty else pd.DataFrame()
            evs = evs[evs["stato"] != "cancellata"] if not evs.empty else evs
            day_events[d] = evs

        # Time column + slots
        grid_html += '<div class="wk-time-col">'
        for h in HOURS:
            grid_html += f'<div class="wk-time-label">{h:02d}:00</div>'
        grid_html += '</div>'

        for d in week_days:
            is_t = d == today
            grid_html += f'<div class="wk-day-col {"today-col" if is_t else ""}" style="height:{SLOT_H*len(HOURS)}px;">'
            # Slots (visual grid lines)
            for h in HOURS:
                grid_html += f'<div class="wk-slot"></div>'
            # Events overlay
            evs = day_events[d]
            if not evs.empty:
                for _, ev in evs.iterrows():
                    try:
                        sh_parts = ev["inizio"].split(":")
                        eh_parts = ev["fine"].split(":")
                        start_h = int(sh_parts[0]) + int(sh_parts[1])/60
                        end_h = int(eh_parts[0]) + int(eh_parts[1])/60
                        top = (start_h - HOURS[0]) * SLOT_H
                        height = max((end_h - start_h) * SLOT_H, 20)
                        cls = "confirmed" if ev["stato"] == "confermata" else "pending"
                        grid_html += f'''<div class="wk-event {cls}" style="top:{top}px;height:{height}px;">
                            <div class="wk-event-time">{ev["inizio"]}–{ev["fine"]}</div>
                            <div class="wk-event-title">{ev["titolo"]}</div>
                        </div>'''
                    except:
                        pass
            grid_html += '</div>'

        grid_html += '</div>'
        st.markdown(grid_html, unsafe_allow_html=True)

    # ── DAY VIEW ─────────────────────────────────────────────────────────────
    else:
        d = st.session_state.cal_day
        HOURS = list(range(8, 20))
        SLOT_H = 64
        day_bk = df[(df["data"] == d) & (df["stato"] != "cancellata")] if not df.empty else pd.DataFrame()

        day_html = '''
        <style>
        .day-grid { display: grid; grid-template-columns: 56px 1fr; border: 1px solid #d4d1ca; border-radius: 10px; overflow: hidden; font-family: Inter, sans-serif; }
        .day-time-label { height: 64px; background: #f9f8f5; border-right: 1px solid #d4d1ca; border-bottom: 1px solid #f0ede8; display: flex; align-items: flex-start; justify-content: flex-end; padding: 6px 8px 0 0; font-size: 0.68rem; color: #7a7974; }
        .day-col { position: relative; background: #f9f8f5; }
        .day-slot { height: 64px; border-bottom: 1px solid #f0ede8; }
        .day-event { position: absolute; left: 8px; right: 8px; border-radius: 7px; padding: 6px 10px; font-size: 0.8rem; font-weight: 500; box-shadow: 0 2px 6px rgba(0,0,0,.1); z-index: 2; }
        .day-event.confirmed { background: #01696f; color: white; }
        .day-event.pending   { background: #964219; color: white; }
        .day-event-title { font-weight: 600; margin-bottom: 2px; }
        .day-event-meta  { font-size: 0.7rem; opacity: .85; }
        </style>
        '''

        day_html += f'<div style="background:#f3f0ec;padding:10px 16px;border-radius:10px 10px 0 0;font-weight:600;color:#28251d;border:1px solid #d4d1ca;border-bottom:none;">'
        day_html += f'{DAY_IT[d.weekday()]} {format_date_it(d)} — {len(day_bk)} riunion{"e" if len(day_bk)==1 else "i"}</div>'
        day_html += '<div class="day-grid">'

        for h in HOURS:
            day_html += f'<div class="day-time-label">{h:02d}:00</div>'
            day_html += '<div class="day-slot"></div>'

        # Events overlay (positioned over the day column using a wrapper)
        if not day_bk.empty:
            day_html = day_html.replace('<div class="day-grid">',
                '<div style="position:relative"><div class="day-grid">'
            )
            overlay = f'<div style="position:absolute;top:0;left:56px;right:0;pointer-events:none;">'
            for _, ev in day_bk.iterrows():
                try:
                    sh_p = ev["inizio"].split(":"); eh_p = ev["fine"].split(":")
                    start_h = int(sh_p[0]) + int(sh_p[1])/60
                    end_h   = int(eh_p[0]) + int(eh_p[1])/60
                    top = (start_h - HOURS[0]) * SLOT_H
                    height = max((end_h - start_h) * SLOT_H - 4, 24)
                    cls = "confirmed" if ev["stato"] == "confermata" else "pending"
                    overlay += f'''<div class="day-event {cls}" style="top:{top}px;height:{height}px;pointer-events:auto;">
                        <div class="day-event-title">{ev["titolo"]}</div>
                        <div class="day-event-meta">🕐 {ev["inizio"]}–{ev["fine"]} &nbsp; 👤 {ev["organizzatore"]}</div>
                        {"<div class=\'day-event-meta\'>👥 " + ev["partecipanti"] + "</div>" if ev.get("partecipanti") else ""}
                    </div>'''
                except:
                    pass
            overlay += '</div></div>'
            day_html += '</div>' + overlay
        else:
            day_html += '</div>'
            day_html += '<div style="text-align:center;padding:40px;color:#7a7974;font-size:0.9rem;border:1px solid #d4d1ca;border-top:none;border-radius:0 0 10px 10px;">Nessuna riunione programmata per questo giorno.</div>'

        st.markdown(day_html, unsafe_allow_html=True)

    # Legenda
    st.markdown("""
    <div style="display:flex;gap:16px;margin-top:12px;font-size:0.75rem;color:#7a7974;">
      <span><span style="background:#cedcd8;color:#01696f;padding:2px 8px;border-radius:4px;">■</span> Confermata</span>
      <span><span style="background:#ddcfc6;color:#964219;padding:2px 8px;border-radius:4px;">■</span> In attesa</span>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 – LISTA PRENOTAZIONI
# ═══════════════════════════════════════════════════════════════════════════════
with tab_list:
    if not df.empty:
        upcoming = df[(df["data"] >= today) & (df["stato"] != "cancellata")].shape[0]
        this_mo = df[
            (df["data"].apply(lambda x: x.month if pd.notnull(x) else 0) == today.month) &
            (df["data"].apply(lambda x: x.year if pd.notnull(x) else 0) == today.year) &
            (df["stato"] != "cancellata")].shape[0]
        confirmed = df[df["stato"] == "confermata"].shape[0]
        pending = df[df["stato"] == "in attesa"].shape[0]
    else:
        upcoming = this_mo = confirmed = pending = 0

    st.markdown(f"""
    <div class="stat-row">
      <div class="stat-card"><div class="stat-label">Prossime</div><div class="stat-value">{upcoming}</div><div class="stat-sub">da oggi in poi</div></div>
      <div class="stat-card"><div class="stat-label">Questo mese</div><div class="stat-value">{this_mo}</div><div class="stat-sub">{MONTHS_IT[today.month-1]}</div></div>
      <div class="stat-card"><div class="stat-label">Confermate</div><div class="stat-value">{confirmed}</div><div class="stat-sub">totale</div></div>
      <div class="stat-card"><div class="stat-label">In attesa</div><div class="stat-value">{pending}</div><div class="stat-sub">da confermare</div></div>
    </div>
    """, unsafe_allow_html=True)

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
            month_str = MONTHS_IT_SHORT[d_obj.month-1] if pd.notnull(d_obj) else "---"
            date_full = format_date_it(d_obj)
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
                <div class="bk-meta">📅 {date_full} &nbsp; 🕐 {bk['inizio']}–{bk['fine']} &nbsp; 👤 {bk['organizzatore']} &nbsp; {parts_html} &nbsp; {notes_html}</div>
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
                org_val = bd.get("organizzatore","")
                org_idx = COLLEGHI.index(org_val) if org_val in COLLEGHI else 0
                e_org = st.selectbox("Organizzatore", COLLEGHI, index=org_idx)
                e_data = st.date_input("Data", value=bd.get("data", today),
                                       format="DD/MM/YYYY")
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
            n_org = st.selectbox("Organizzatore *", COLLEGHI)
            n_data = st.date_input("Data *", value=today, min_value=today,
                                   format="DD/MM/YYYY")
        with n2:
            n_start = st.text_input("Ora inizio (HH:MM) *", value="09:00")
            n_end = st.text_input("Ora fine (HH:MM) *", value="10:00")
            n_stato = st.selectbox("Stato", ["confermata","in attesa"])
        n_att = st.text_input("Partecipanti (separati da virgola)")
        n_notes = st.text_area("Note / Agenda", height=80)
        submitted = st.form_submit_button("🏢 Prenota sala", use_container_width=True, type="primary")

    if submitted:
        if not n_titolo:
            st.error("Inserisci l'oggetto della riunione.")
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
                ok = save_booking({"id": new_id, "titolo": n_titolo, "organizzatore": n_org,
                                   "data": n_data, "inizio": n_start, "fine": n_end,
                                   "partecipanti": n_att, "note": n_notes, "stato": n_stato})
                if ok:
                    data_it = format_date_it(n_data)
                    st.success(f"✅ Sala prenotata! {data_it} dalle {n_start} alle {n_end}")
                    st.balloons()

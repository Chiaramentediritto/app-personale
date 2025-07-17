import streamlit as st

# 🔐 PASSWORD
def check_password():
    def password_entered():
        if st.session_state["password"] == "8888":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # nasconde dopo login
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔐 Inserisci la password per accedere:", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["password_correct"]:
        st.text_input("🔐 Password errata, riprova:", type="password", on_change=password_entered, key="password")
        st.warning("❌ Password errata.")
        st.stop()

check_password()

import streamlit as st
import pandas as pd
import uuid
from datetime import date
from pathlib import Path
from fpdf import FPDF
import base64

def draw_home_background(img_path: str, width_px: int = 700, opacity: float = 0.05):
    """
    Mostra l’immagine in basso a destra con opacità ridotta (watermark).
    """
    with open(img_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""
        <style>
          .bg-home {{
            position: fixed;
            bottom: 10px;
            right: 10px;
            width: {width_px}px;
            opacity: {opacity};
            pointer-events: none;
            z-index: 0;
          }}
          /* Assicuriamoci che il resto del contenuto stia sopra */
          .main > div:nth-child(1) {{
            position: relative;
            z-index: 1;
          }}
        </style>
        <img src="data:image/jpeg;base64,{data}" class="bg-home" />
        """,
        unsafe_allow_html=True,
    )






# ───────────────────────── CONFIGURAZIONE FATTURA ────────────────────────────
# Url base che usi per il link "Fattura"
INVOICE_BASE_URL = (
    "https://asit.studiodigitale.cloud/wt00014499/login.sto"
    "?Login_Service=https%3A%2F%2Fasit.studiodigitale.cloud%2Fwt00014499%2Findex.sto"
    "&StwTokenSel=1123321717211031&utentebak=|wt00014499"
)

# ───────────────────────── CONFIG ────────────────────────────
st.set_page_config(page_title="Tutor Manager", layout="centered")
APP_DIR = Path(__file__).parent

FILES = {
    "students":  APP_DIR / "students.csv",
    "lessons":   APP_DIR / "lessons.csv",
    "summaries": APP_DIR / "summaries.csv",
    "payments":  APP_DIR / "payments.csv",
     "day_checks": APP_DIR / "day_checks.csv",
}

COLUMNS = {
    "students":  ["id", "name", "hourly_rate", "note"],
    "lessons":   ["id", "student_id", "date", "duration_min", "amount"],
    "summaries": ["id", "student_id", "date", "title", "price", "author", "paid"],
    "payments":  ["student_id", "year", "month"],
     "day_checks": ["date", "checked"],
}


# ────────────────────────── UTILS ─────────────────────────────
def load_csv(path: Path, cols: list):
    if path.exists():
        df = pd.read_csv(path)
        df = df[[c for c in df.columns if c in cols]]
        for col in cols:
            if col not in df.columns:
                df[col] = pd.NA
        return df[cols]
    return pd.DataFrame(columns=cols)


def save_csv(df: pd.DataFrame, path: Path):
    df.to_csv(path, index=False)


def new_id():
    return uuid.uuid4().hex[:8]


def student_label(sid):
    row = students[students["id"] == sid]
    if row.empty:
        return sid
    r = row.iloc[0]
    return f"{r['name']} — {r['hourly_rate']:.2f} EUR/h"


def rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()


# ───────────────────────── ADVANCED ────────────────────────────
def toggle_paid(sid, year, month):
    mask = (payments.student_id == sid) & (payments.year == year) & (payments.month == month)
    if payments.loc[mask].empty:
        payments.loc[len(payments)] = {"student_id": sid, "year": year, "month": month}
    else:
        payments.drop(index=payments.loc[mask].index, inplace=True)
    save_csv(payments, FILES["payments"])
    rerun()


def generate_invoice_pdf(name, lessons_rows, year, month, total):
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"Report lezioni - {name}", ln=1, align="C")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"Mese: {month:02d}/{year}", ln=1)
    pdf.ln(4)
    for r in lessons_rows:
        pdf.cell(
            0,
            7,
            f"{r['date']}  |  {int(r['duration_min'])} min  |  {r['amount']:.2f} EUR",
            ln=1,
        )
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Totale lezioni: {total:.2f} EUR", ln=1)
    out = pdf.output(dest="S")
    if isinstance(out, bytearray):
        out = bytes(out)
    return out


def toggle_summary_author(sid):
    idx = summaries[summaries.id == sid].index
    if not idx.empty:
        i = idx[0]
        curr = summaries.at[i, "author"]
        summaries.at[i, "author"] = "P" if curr == "C" else "C"
        save_csv(summaries, FILES["summaries"])
        rerun()


def toggle_summary_paid(rid: str):
    """
    Al click sul badge Pagato/Non pagato, inverte il valore nel CSV.
    """
    # trova l’indice del riassunto con quell’id
    idx = summaries[summaries.id == rid].index
    if not idx.empty:
        i = idx[0]
        # inverte il valore True<->False
        summaries.at[i, "paid"] = not summaries.at[i, "paid"]
        save_csv(summaries, FILES["summaries"])
        rerun()



# ──────────────────────── LOAD DATA ───────────────────────────
students  = load_csv(FILES["students"],  COLUMNS["students"])
if "note" not in students.columns:
    students["note"] = ""
lessons   = load_csv(FILES["lessons"],   COLUMNS["lessons"])
summaries = load_csv(FILES["summaries"], COLUMNS["summaries"])
payments  = load_csv(FILES["payments"],  COLUMNS["payments"])
# ── Carica e inizializza lo stato dei giorni checkati ──
day_checks = load_csv(FILES["day_checks"], COLUMNS["day_checks"])
# Assicuriamoci che la colonna checked sia di tipo booleano
day_checks["checked"] = day_checks["checked"].fillna(False).astype(bool)


# default author = 'C'
summaries["author"] = summaries["author"].fillna("C")

# assegna False a tutti i paid vuoti in summaries
summaries["paid"] = summaries["paid"].fillna(False)


# ────────────────────────── SIDEBAR ────────────────────────────
page = st.sidebar.radio(
    "Menu",
    ("Home", "Studenti", "Lezioni", "Riassunti", "Report Mensile")
)


# ─────────────────────────── HOME ──────────────────────────────
if page == "Home":
    st.title("Tutor Manager")
    st.write("Benvenuta Chiara")
    draw_home_background("foto.jpeg", width_px=580, opacity=0.30)



# ───────────────────────── STUDENTI ─────────────────────────────
elif page == "Studenti":
    st.header("Studenti")

    # ── Form per aggiungere un nuovo studente con nota
    with st.form("add_student"):
        name = st.text_input("Nome completo", key="student_name")
        rate = st.number_input(
            "Tariffa oraria (€)",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            key="student_rate"
        )
        note = st.text_area("Note", key="student_note")
        if st.form_submit_button("Aggiungi"):
            students.loc[len(students)] = {
                "id":       new_id(),
                "name":     name,
                "hourly_rate": rate,
                "note":     note
            }
            save_csv(students, FILES["students"])
            st.success("Studente aggiunto!")
            rerun()

    st.subheader("Elenco studenti")
    # ── Stampa in ordine alfabetico per nome
    for _, row in students.sort_values("name").iterrows():
        sid       = row["id"]
        note_text = row.get("note", "")

        # gestisco NA o stringa vuota
        if pd.isna(note_text) or note_text == "":
            display_note = "*Nessuna nota*"
        else:
            display_note = note_text

        c1, c2, c3, c4 = st.columns([4, 4, 1, 1])
        # nome + tariffa
        c1.write(f"**{row['name']}** — {row['hourly_rate']:.2f} EUR/h")
        # nota
        c2.write(display_note)
        # bottone modifica nota
        if c3.button("✏️", key=f"edit_note_btn_{sid}"):
            st.session_state[f"edit_note_{sid}"] = True
        # bottone elimina studente
        if c4.button("🗑", key=f"delstud_{sid}"):
            lessons.drop(
                index=lessons[lessons.student_id == sid].index, inplace=True
            )
            summaries.drop(
                index=summaries[summaries.student_id == sid].index, inplace=True
            )
            students.drop(
                index=students[students.id == sid].index, inplace=True
            )
            save_csv(lessons, FILES["lessons"])
            save_csv(summaries, FILES["summaries"])
            save_csv(students, FILES["students"])
            rerun()

        # ── Form di modifica nota, mostrato solo se edit_note_[sid] == True
        if st.session_state.get(f"edit_note_{sid}", False):
            # default_note non può essere NA
            default_note = "" if pd.isna(note_text) else note_text
            new_note = st.text_area(
                f"Modifica nota per {row['name']}",
                value=default_note,
                key=f"note_input_{sid}"
            )
            if st.button("Salva nota", key=f"save_note_{sid}"):
                idx = students[students.id == sid].index[0]
                students.at[idx, "note"] = new_note
                save_csv(students, FILES["students"])
                st.session_state[f"edit_note_{sid}"] = False
                st.success("Nota aggiornata!")
                rerun()







# ───────────────────────── LEZIONI ──────────────────────────────
elif page == "Lezioni":
    st.header("Lezioni")

    # ── FORM AGGIUNGI LEZIONE (4 spazi)
    with st.form(key="add_lesson"):
        # Creiamo la lista di ID ordinati per nome
        sorted_ids = students.sort_values("name")["id"].tolist()
        sid = st.selectbox(
            "Studente",
            sorted_ids,
            format_func=student_label,
            key="lesson_student"  # chiave unica
        )
        d   = st.date_input("Data", date.today(), key="lesson_date")
        dur = st.number_input(
            "Durata (min)",
            min_value=1,
            step=5,
            value=60,
            key="lesson_duration"
        )
        
        if st.form_submit_button("Aggiungi lezione"):
            rate   = students.loc[students.id == sid, "hourly_rate"].iloc[0]
            amount = dur / 60 * rate
            lessons.loc[len(lessons)] = {
                "id": new_id(),
                "student_id": sid,
                "date": d.isoformat(),
                "duration_min": dur,
                "amount": amount,
            }
            save_csv(lessons, FILES["lessons"])
            st.success("Lezione salvata!")
            for key in ("lesson_date", "lesson_duration"):
                if key in st.session_state:
                    del st.session_state[key]
            rerun()

    # ── FILTRO MESE/ANNO ─────────────────────────────────────────────────────
    st.markdown("**Filtra per mese e anno**")
    today     = date.today()
    cy, cm    = st.columns(2)
    year_sel  = cy.selectbox("Anno", list(range(today.year, 2019, -1)), index=0)
    month_sel = cm.selectbox("Mese", list(range(1, 13)), index=today.month - 1)

    # ── COSTRUISCO IL DATAFRAME df DOPO IL FILTRO ──────────────────────────
    df = lessons.copy()
    df["dt"] = pd.to_datetime(df["date"])
    df = df[
        (df["dt"].dt.year  == year_sel) &
        (df["dt"].dt.month == month_sel)
    ]

    # ── DAY_CHECKS: carico lo stato salvato prima di usarlo ────────────────
    day_checks = load_csv(FILES["day_checks"], COLUMNS["day_checks"])
    day_checks["checked"] = day_checks["checked"].fillna(False).astype(bool)

    # ── ORA POSSO USARE df ──────────────────────────────────────────────────
    if df.empty:
        st.info("Nessuna lezione per il mese scelto.")
    else:
        st.subheader("Vista giornaliera")
        for day in sorted(df["date"].unique(), reverse=True):
            # recupero lo stato del cerchio
            row     = day_checks[day_checks["date"] == day]
            checked = bool(row["checked"].iloc[0]) if not row.empty else False

            # expander (chiuso di default)
            with st.expander(f"📅  {pd.to_datetime(day).strftime('%d/%m/%Y')}", expanded=False):
                # titolo + toggle
                c0, c1 = st.columns([9, 1])
                c0.markdown(f"**📅 {pd.to_datetime(day).strftime('%d/%m/%Y')}**")
                circle = "🟢" if checked else "🔴"
                if c1.button(circle, key=f"check_{day}"):
                    if row.empty:
                        day_checks.loc[len(day_checks)] = {"date": day, "checked": not checked}
                    else:
                        idx = row.index[0]
                        day_checks.at[idx, "checked"] = not checked
                    save_csv(day_checks, FILES["day_checks"])
                    rerun()

                # elenco lezioni di quel giorno
                sub = df[df["date"] == day].sort_index()
                for _, r2 in sub.iterrows():
                    cA, cB = st.columns([9, 1])
                    name   = student_label(r2["student_id"]).split(" — ")[0]
                    cA.write(name)
                    if cB.button("🗑", key=f"delless_{r2['id']}"):
                        idx2 = lessons[lessons.id == r2["id"]].index
                        lessons.drop(index=idx2, inplace=True)
                        save_csv(lessons, FILES["lessons"])
                        rerun()















elif page == "Riassunti":
    st.header("Riassunti")

    # ── Barra di ricerca per studente o titolo
    search_s = st.text_input(
        "🔍 Cerca riassunti per studente o titolo",
        value="",
        help="Digita parte del nome dello studente o del titolo"
    )

    # ── Totali per autore
    chiara_total = summaries[summaries["author"] == "C"]["price"].sum()
    pier_total   = summaries[summaries["author"] == "P"]["price"].sum()
    st.markdown(
        f"<div style='margin-bottom:12px;font-size:1rem;'>"
        f"<b>Chiara:</b> {chiara_total:.2f} EUR&nbsp;&nbsp;"
        f"<b>Pierangelo:</b> {pier_total:.2f} EUR"
        f"</div>",
        unsafe_allow_html=True
    )

    # ── Form per aggiungere riassunto
    with st.form(key="add_summary"):
        sid_exist = st.selectbox(
            "Studente esistente",
            students.id,
            format_func=student_label
        )
        new_name = st.text_input("Oppure nuovo studente")
        d        = st.date_input("Data", date.today(), key="sum_date")
        title    = st.text_input("Titolo del riassunto", key="sum_title")
        price    = st.number_input(
            "Prezzo (€)",
            min_value=0.0,
            step=0.5,
            format="%.2f",
            key="sum_price"
        )
        if st.form_submit_button("Aggiungi riassunto"):
            # crea nuovo studente se richiesto
            if new_name:
                new_sid = new_id()
                students.loc[len(students)] = {
                    "id": new_sid,
                    "name": new_name,
                    "hourly_rate": 0.0
                }
                save_csv(students, FILES["students"])
                sid = new_sid
            else:
                sid = sid_exist

            summaries.loc[len(summaries)] = {
                "id": new_id(),
                "student_id": sid,
                "date": d.isoformat(),
                "title": title,
                "price": price,
                "author": "C",
                "paid": False
            }
            save_csv(summaries, FILES["summaries"])
            st.success("Riassunto salvato!")
            rerun()

    # ── Elenco riassunti filtrato, con data formattata, toggle e delete
    st.subheader("Elenco riassunti")
    df = summaries.copy()

    # Applica ricerca su titolo o studente
    if search_s:
        mask_name  = df["student_id"].map(student_label).str.lower().str.contains(search_s.lower())
        mask_title = df["title"].str.lower().str.contains(search_s.lower())
        df = df[mask_name | mask_title]

    if df.empty:
        st.info("Nessun riassunto corrisponde alla ricerca.")
    else:
        # ordina per data discendente
        df["dt"] = pd.to_datetime(df["date"])
        df = df.sort_values("dt", ascending=False)

        for _, r in df.iterrows():
            c1, c2, c3, c4, c5, c6 = st.columns([3, 2, 2, 1, 1, 1])
            # Titolo e studente
            c1.write(f"{r['title']} ({student_label(r['student_id']).split(' — ')[0]})")
            # Data formattata in gg/mm/aaaa
            dt_obj = pd.to_datetime(r["date"])
            c2.write(dt_obj.strftime("%d/%m/%Y"))
            # Prezzo
            c3.write(f"{r['price']:.2f} EUR")
            # Toggle Author (C/P)
            if c4.button(r["author"], key=f"auth_{r['id']}", help="C = Chiara, P = Pierangelo"):
                toggle_summary_author(r["id"])
            # Toggle Pagato/Non pagato
            paid_label = "🟢" if r["paid"] else "🔴"
            if c5.button(paid_label, key=f"paid_sum_{r['id']}"):
                toggle_summary_paid(r["id"])
            # Delete
            if c6.button("🗑", key=f"delsum_{r['id']}"):
                idx = summaries[summaries.id == r["id"]].index
                summaries.drop(index=idx, inplace=True)
                save_csv(summaries, FILES["summaries"])
                rerun()








# ──────────────────────────── REPORT MENSILE ─────────────────────────────────
elif page == "Report Mensile":
    st.header("Report Mensile")
    today = date.today()
    cy, cm = st.columns(2)
    year  = cy.selectbox("Anno", list(range(today.year, 2019, -1)), index=0)
    month = cm.selectbox("Mese", list(range(1, 13)), index=today.month - 1)

    # Filtra dati per mese/anno
    les_m = lessons[
        (pd.to_datetime(lessons["date"]).dt.year == year) &
        (pd.to_datetime(lessons["date"]).dt.month == month)
    ]
    sum_m = summaries[
        (pd.to_datetime(summaries["date"]).dt.year == year) &
        (pd.to_datetime(summaries["date"]).dt.month == month)
    ]

    if les_m.empty and sum_m.empty:
        st.info("Nessun dato per il mese selezionato.")
        st.stop()

    # Totali globali del mese
    tot_less_glob = les_m.groupby("student_id")["amount"].sum().sum()
    tot_sum_glob  = sum_m.groupby("student_id")["price"].sum().sum()
    tot_month_glob = tot_less_glob + tot_sum_glob
    st.markdown(
        f"<div style='border:1px solid #ddd; border-radius:6px; "
        f"padding:6px 12px; background:#f8f8f8; margin-bottom:14px; "
        f"font-size:0.9rem;'>"
        f"<b>Totale lezioni:</b> {tot_less_glob:.2f} EUR &nbsp;|&nbsp;"
        f"<b>Totale riassunti:</b> {tot_sum_glob:.2f} EUR &nbsp;|&nbsp;"
        f"<b>Totale mensile:</b> {tot_month_glob:.2f} EUR"
        f"</div>",
        unsafe_allow_html=True
    )

    # Link fattura unico
    st.markdown(f"[📄 Vai alla Fattura]({INVOICE_BASE_URL})", unsafe_allow_html=True)
    st.write("")

    # Dettaglio per studente
    st.subheader(f"Dettaglio {month:02d}/{year}")
    # calcola totali per studente
    tot_less = les_m.groupby("student_id")["amount"].sum()
    tot_sum  = sum_m.groupby("student_id")["price"].sum()
    student_ids = sorted(
    set(tot_less.index).union(tot_sum.index),
    key=lambda sid: student_label(sid).split(" — ")[0].lower()
)
     # ── BARRA DI RICERCA STUDENTE
    search_rep = st.text_input(
        "🔍 Cerca studente",
        value="",
        help="Digita parte del nome per filtrare il report"
    )
    if search_rep:
        student_ids = [
            sid for sid in student_ids
            if search_rep.lower() in student_label(sid).lower()
        ]


    for sid in student_ids:
        name  = student_label(sid).split(" — ")[0]
        l_tot = tot_less.get(sid, 0.0)
        s_tot = tot_sum.get(sid, 0.0)
        grand = l_tot + s_tot

        # sei colonne: c1–c4 testo, c5 toggle, c6 PDF
        c1, c2, c3, c4, c5, c6 = st.columns([3, 2, 2, 2, 1, 1])
        c1.write(f"**{name}**")
        c2.write(f"Lezioni: {l_tot:.2f} EUR")
        c3.write(f"Riassunti: {s_tot:.2f} EUR")
        c4.write(f"**Totale: {grand:.2f} EUR**")

        # Toggle Pagato
        paid = not payments[
            (payments.student_id == sid)
            & (payments.year == year)
            & (payments.month == month)
        ].empty
        label = "🟢" if paid else "🔴"
        if c5.button(label, key=f"pay_{sid}_{year}_{month}"):
            toggle_paid(sid, year, month)

        # Scarica PDF
        rows = les_m[les_m.student_id == sid].to_dict("records")
        if rows and c6.download_button(
                "📄",
                data=generate_invoice_pdf(name, rows, year, month, l_tot),
                file_name=f"{name}_{year}_{month:02d}.pdf",
                mime="application/pdf",
                key=f"pdf_{sid}_{year}_{month}"
            ):
            pass

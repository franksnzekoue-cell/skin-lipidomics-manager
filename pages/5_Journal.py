import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import df_query, execute, init_db

init_db()
st.set_page_config(page_title="Journal de bord — Lipidomique Peau", page_icon="📝", layout="wide")

st.title("📝 Journal de bord")
st.caption("Consignez vos notes, résultats, décisions et comptes-rendus de réunion au fil du temps.")

ENTRY_TYPES = ["Note", "Résultat", "Réunion", "Décision"]

tab1, tab2 = st.tabs(["🗓️ Chronologie", "➕ Nouvelle entrée"])

# ===========================================================================
# TAB 1 — CHRONOLOGIE
# ===========================================================================
with tab1:
    journal_df = df_query("""
        SELECT j.*, p.name as project_name
        FROM journal j
        LEFT JOIN projects p ON j.project_id = p.id
        ORDER BY j.entry_date DESC, j.created_at DESC
    """)

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        f_type = st.multiselect("Filtrer par type", ENTRY_TYPES)
    with col_f2:
        f_proj = st.multiselect("Filtrer par projet", journal_df["project_name"].dropna().unique().tolist() if not journal_df.empty else [])

    filtered = journal_df.copy()
    if f_type:
        filtered = filtered[filtered["entry_type"].isin(f_type)]
    if f_proj:
        filtered = filtered[filtered["project_name"].isin(f_proj)]

    if filtered.empty:
        st.info("Aucune entrée de journal pour le moment.")
    else:
        type_icons = {"Note": "🗒️", "Résultat": "📊", "Réunion": "🤝", "Décision": "⚖️"}
        for _, row in filtered.iterrows():
            icon = type_icons.get(row["entry_type"], "🗒️")
            st.markdown(f"##### {icon} {row['entry_date']} — {row['entry_type']}"
                        + (f" · _{row['project_name']}_" if row['project_name'] else ""))
            st.write(row["entry_text"])
            if st.button("🗑️ Supprimer", key=f"deljournal_{row['id']}"):
                execute("DELETE FROM journal WHERE id = ?", [row["id"]])
                st.rerun()
            st.markdown("---")

# ===========================================================================
# TAB 2 — NOUVELLE ENTREE
# ===========================================================================
with tab2:
    st.subheader("Ajouter une entrée au journal")
    projects_list = df_query("SELECT id, name FROM projects ORDER BY name")

    with st.form("new_journal_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            entry_date = st.date_input("Date", value=date.today())
        with c2:
            entry_type = st.selectbox("Type d'entrée", ENTRY_TYPES)
        with c3:
            project_choice = st.selectbox(
                "Projet associé",
                options=[None] + list(projects_list["id"]),
                format_func=lambda x: "—" if x is None else projects_list.loc[projects_list["id"] == x, "name"].values[0]
            )
        entry_text = st.text_area("Contenu de l'entrée *", height=150)

        submitted = st.form_submit_button("✅ Ajouter au journal", use_container_width=True)
        if submitted:
            if not entry_text:
                st.error("Le contenu de l'entrée est obligatoire.")
            else:
                now = datetime.now().isoformat()
                execute(
                    """INSERT INTO journal (project_id, entry_date, entry_text, entry_type, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    [project_choice, entry_date.isoformat(), entry_text, entry_type, now]
                )
                st.success("Entrée ajoutée au journal.")
                st.rerun()

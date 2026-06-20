import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import df_query, execute, init_db

init_db()
st.set_page_config(page_title="Échantillons — Lipidomique Peau", page_icon="🧪", layout="wide")

st.title("🧪 Base de données d'échantillons")

SAMPLE_TYPES = ["Tape strip", "Biopsie", "Sébum", "Cellules", "Plasma", "Autre"]
STATUTS_SAMPLE = ["Disponible", "Réservé", "En analyse", "Épuisé"]

tab1, tab2 = st.tabs(["📋 Inventaire", "➕ Nouvel échantillon"])

# ===========================================================================
# TAB 1 — INVENTAIRE
# ===========================================================================
with tab1:
    samples_df = df_query("""
        SELECT s.*, p.name as project_name
        FROM samples s
        LEFT JOIN projects p ON s.project_id = p.id
        ORDER BY s.collection_date DESC
    """)

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        f_type = st.multiselect("Type d'échantillon", SAMPLE_TYPES)
    with col_f2:
        f_status = st.multiselect("Statut", STATUTS_SAMPLE)
    with col_f3:
        f_site = st.text_input("Recherche site anatomique")
    with col_f4:
        f_subject = st.text_input("Recherche sujet (ID)")

    filtered = samples_df.copy()
    if f_type:
        filtered = filtered[filtered["sample_type"].isin(f_type)]
    if f_status:
        filtered = filtered[filtered["status"].isin(f_status)]
    if f_site:
        filtered = filtered[filtered["body_site"].str.contains(f_site, case=False, na=False)]
    if f_subject:
        filtered = filtered[filtered["subject_id"].str.contains(f_subject, case=False, na=False)]

    st.markdown(f"**{len(filtered)} échantillon(s) trouvé(s)** sur {len(samples_df)} au total")

    if not filtered.empty:
        display_cols = {
            "sample_code": "Code échantillon", "sample_type": "Type", "subject_id": "Sujet",
            "body_site": "Site anatomique", "collection_date": "Date de prélèvement",
            "storage_location": "Stockage", "status": "Statut", "project_name": "Projet"
        }
        st.dataframe(
            filtered[list(display_cols.keys())].rename(columns=display_cols),
            use_container_width=True, hide_index=True
        )

        # Export CSV
        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exporter en CSV", csv, "echantillons.csv", "text/csv")
    else:
        st.info("Aucun échantillon ne correspond aux filtres.")

    st.markdown("---")
    st.subheader("Détail et mise à jour d'un échantillon")
    if not samples_df.empty:
        selected_code = st.selectbox("Sélectionner un échantillon", samples_df["sample_code"])
        sample_row = samples_df[samples_df["sample_code"] == selected_code].iloc[0]

        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Type :** {sample_row['sample_type']}")
            st.write(f"**Sujet :** {sample_row['subject_id']}")
            st.write(f"**Site anatomique :** {sample_row['body_site']}")
            st.write(f"**Méthode de prélèvement :** {sample_row['collection_method']}")
            st.write(f"**Quantité :** {sample_row['quantity']}")
        with c2:
            st.write(f"**Date de prélèvement :** {sample_row['collection_date']}")
            st.write(f"**Stockage :** {sample_row['storage_location']} ({sample_row['storage_temp']})")
            st.write(f"**Projet associé :** {sample_row['project_name']}")
            st.write(f"**Notes :** {sample_row['notes'] or '—'}")

        new_status = st.selectbox(
            "Mettre à jour le statut", STATUTS_SAMPLE,
            index=STATUTS_SAMPLE.index(sample_row["status"]) if sample_row["status"] in STATUTS_SAMPLE else 0
        )
        if st.button("Mettre à jour"):
            execute("UPDATE samples SET status = ? WHERE id = ?", [new_status, int(sample_row["id"])])
            st.success("Statut mis à jour.")
            st.rerun()

# ===========================================================================
# TAB 2 — NOUVEL ECHANTILLON
# ===========================================================================
with tab2:
    st.subheader("Enregistrer un nouvel échantillon")
    projects_list = df_query("SELECT id, name FROM projects ORDER BY name")

    with st.form("new_sample_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            sample_code = st.text_input("Code échantillon (unique) *", placeholder="ex: DA-003-LES")
            sample_type = st.selectbox("Type d'échantillon *", SAMPLE_TYPES)
            subject_id = st.text_input("ID sujet", placeholder="ex: SUBJ-003")
            body_site = st.text_input("Site anatomique", placeholder="ex: Avant-bras")
            collection_method = st.text_input("Méthode de prélèvement", placeholder="ex: D-Squame D100")
        with c2:
            collection_date = st.date_input("Date de prélèvement", value=date.today())
            storage_location = st.text_input("Lieu de stockage", placeholder="ex: -80°C Congel.A étagère 2")
            storage_temp = st.selectbox("Température de stockage", ["-80°C", "-20°C", "4°C", "Température ambiante"])
            quantity = st.text_input("Quantité disponible", placeholder="ex: 5 tapes / 1 biopsie")
            project_choice = st.selectbox(
                "Projet associé",
                options=[None] + list(projects_list["id"]),
                format_func=lambda x: "—" if x is None else projects_list.loc[projects_list["id"] == x, "name"].values[0]
            )
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("✅ Enregistrer l'échantillon", use_container_width=True)
        if submitted:
            if not sample_code:
                st.error("Le code échantillon est obligatoire.")
            else:
                try:
                    now = datetime.now().isoformat()
                    execute(
                        """INSERT INTO samples (sample_code, project_id, sample_type, subject_id, body_site,
                           collection_method, collection_date, storage_location, storage_temp, quantity,
                           status, notes, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        [sample_code, project_choice, sample_type, subject_id, body_site,
                         collection_method, collection_date.isoformat(), storage_location, storage_temp,
                         quantity, "Disponible", notes, now]
                    )
                    st.success(f"Échantillon « {sample_code} » enregistré.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : ce code échantillon existe peut-être déjà. ({e})")

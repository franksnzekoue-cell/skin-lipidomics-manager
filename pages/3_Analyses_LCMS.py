import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import df_query, execute, init_db

init_db()
st.set_page_config(page_title="Analyses LC-MS — Lipidomique Peau", page_icon="⚗️", layout="wide")

st.title("⚗️ Suivi des analyses LC-MS")

ACQUISITION_MODES = ["DDA", "DIA", "PRM", "Full MS", "Full MS + ddMS2"]
ION_MODES = ["Positif", "Négatif", "Polarity switching"]
QC_STATUSES = ["En attente", "Conforme", "Non conforme", "À revoir"]

tab1, tab2, tab3 = st.tabs(["📋 Liste des batchs", "➕ Nouveau batch", "🔗 Associer échantillons"])

# ===========================================================================
# TAB 1 — LISTE DES BATCHS
# ===========================================================================
with tab1:
    batches_df = df_query("""
        SELECT b.*, p.name as project_name
        FROM lcms_batches b
        LEFT JOIN projects p ON b.project_id = p.id
        ORDER BY b.run_date DESC
    """)

    if batches_df.empty:
        st.info("Aucun batch LC-MS enregistré.")
    else:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            f_qc = st.multiselect("Filtrer par statut QC", QC_STATUSES)
        with col_f2:
            f_proj = st.multiselect("Filtrer par projet", batches_df["project_name"].dropna().unique().tolist())

        filtered = batches_df.copy()
        if f_qc:
            filtered = filtered[filtered["qc_status"].isin(f_qc)]
        if f_proj:
            filtered = filtered[filtered["project_name"].isin(f_proj)]

        for _, row in filtered.iterrows():
            qc_icon = {"Conforme": "✅", "En attente": "⏳", "Non conforme": "❌", "À revoir": "⚠️"}.get(row["qc_status"], "⏳")
            with st.expander(f"{qc_icon} **{row['batch_code']}** — {row['method_name']} ({row['run_date']})"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Instrument :** {row['instrument']}")
                    st.write(f"**Mode d'acquisition :** {row['acquisition_mode']}")
                    st.write(f"**Mode d'ionisation :** {row['ion_mode']}")
                    st.write(f"**Opérateur :** {row['operator']}")
                with c2:
                    st.write(f"**Projet associé :** {row['project_name']}")
                    st.write(f"**Nombre d'échantillons :** {row['n_samples']}")
                    st.write(f"**Statut QC :** {row['qc_status']}")
                    st.write(f"**Notes QC :** {row['qc_notes'] or '—'}")

                # Echantillons liés
                linked = df_query("""
                    SELECT s.sample_code, s.sample_type, s.body_site, bs.injection_order
                    FROM batch_samples bs
                    JOIN samples s ON bs.sample_id = s.id
                    WHERE bs.batch_id = ?
                    ORDER BY bs.injection_order
                """, [row["id"]])
                if not linked.empty:
                    st.write("**Échantillons inclus dans ce batch :**")
                    st.dataframe(
                        linked.rename(columns={
                            "sample_code": "Code", "sample_type": "Type",
                            "body_site": "Site", "injection_order": "Ordre d'injection"
                        }),
                        use_container_width=True, hide_index=True
                    )

                st.markdown("---")
                new_qc = st.selectbox(
                    "Mettre à jour le statut QC", QC_STATUSES,
                    index=QC_STATUSES.index(row["qc_status"]) if row["qc_status"] in QC_STATUSES else 0,
                    key=f"qc_{row['id']}"
                )
                qc_notes_update = st.text_area("Notes QC", value=row["qc_notes"] or "", key=f"qcnotes_{row['id']}")
                if st.button("Mettre à jour le QC", key=f"updqc_{row['id']}"):
                    execute(
                        "UPDATE lcms_batches SET qc_status = ?, qc_notes = ? WHERE id = ?",
                        [new_qc, qc_notes_update, row["id"]]
                    )
                    st.success("Statut QC mis à jour.")
                    st.rerun()

# ===========================================================================
# TAB 2 — NOUVEAU BATCH
# ===========================================================================
with tab2:
    st.subheader("Enregistrer un nouveau batch LC-MS")
    projects_list = df_query("SELECT id, name FROM projects ORDER BY name")

    with st.form("new_batch_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            batch_code = st.text_input("Code batch (unique) *", placeholder="ex: BATCH-2026-003")
            method_name = st.text_input("Méthode analytique *", placeholder="ex: RPLC CSH-C18 untargeted lipidomique")
            instrument = st.text_input("Instrument", value="Orbitrap Exploris 480")
            acquisition_mode = st.selectbox("Mode d'acquisition", ACQUISITION_MODES)
            ion_mode = st.selectbox("Mode d'ionisation", ION_MODES)
        with c2:
            run_date = st.date_input("Date d'acquisition", value=date.today())
            n_samples = st.number_input("Nombre d'échantillons", min_value=0, step=1)
            operator = st.text_input("Opérateur", value="Franks")
            project_choice = st.selectbox(
                "Projet associé",
                options=[None] + list(projects_list["id"]),
                format_func=lambda x: "—" if x is None else projects_list.loc[projects_list["id"] == x, "name"].values[0]
            )
            qc_status = st.selectbox("Statut QC initial", QC_STATUSES, index=0)
        notes = st.text_area("Notes générales sur le batch")

        submitted = st.form_submit_button("✅ Enregistrer le batch", use_container_width=True)
        if submitted:
            if not batch_code or not method_name:
                st.error("Le code batch et la méthode sont obligatoires.")
            else:
                try:
                    now = datetime.now().isoformat()
                    execute(
                        """INSERT INTO lcms_batches (batch_code, project_id, method_name, instrument,
                           acquisition_mode, ion_mode, run_date, n_samples, qc_status, operator, notes, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        [batch_code, project_choice, method_name, instrument, acquisition_mode,
                         ion_mode, run_date.isoformat(), n_samples, qc_status, operator, notes, now]
                    )
                    st.success(f"Batch « {batch_code} » enregistré.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : ce code batch existe peut-être déjà. ({e})")

# ===========================================================================
# TAB 3 — ASSOCIER ECHANTILLONS A UN BATCH
# ===========================================================================
with tab3:
    st.subheader("Associer des échantillons à un batch")
    batches_list = df_query("SELECT id, batch_code FROM lcms_batches ORDER BY batch_code")
    samples_list = df_query("SELECT id, sample_code, sample_type, status FROM samples WHERE status != 'Épuisé' ORDER BY sample_code")

    if batches_list.empty:
        st.warning("Créez d'abord un batch avant d'associer des échantillons.")
    elif samples_list.empty:
        st.warning("Aucun échantillon disponible à associer.")
    else:
        batch_choice = st.selectbox(
            "Sélectionner le batch",
            options=batches_list["id"],
            format_func=lambda x: batches_list.loc[batches_list["id"] == x, "batch_code"].values[0]
        )

        already_linked = df_query("SELECT sample_id FROM batch_samples WHERE batch_id = ?", [batch_choice])
        already_ids = already_linked["sample_id"].tolist() if not already_linked.empty else []

        available_samples = samples_list[~samples_list["id"].isin(already_ids)]

        selected_samples = st.multiselect(
            "Échantillons à ajouter à ce batch",
            options=available_samples["id"],
            format_func=lambda x: f"{available_samples.loc[available_samples['id']==x,'sample_code'].values[0]} "
                                   f"({available_samples.loc[available_samples['id']==x,'sample_type'].values[0]})"
        )

        if st.button("➕ Ajouter les échantillons sélectionnés au batch", use_container_width=True):
            if selected_samples:
                current_max = df_query(
                    "SELECT MAX(injection_order) as m FROM batch_samples WHERE batch_id = ?", [batch_choice]
                )
                start_order = (current_max["m"].iloc[0] or 0) + 1 if not current_max.empty else 1
                for i, sid in enumerate(selected_samples):
                    execute(
                        "INSERT INTO batch_samples (batch_id, sample_id, injection_order) VALUES (?, ?, ?)",
                        [batch_choice, sid, start_order + i]
                    )
                    execute("UPDATE samples SET status = 'En analyse' WHERE id = ?", [sid])
                st.success(f"{len(selected_samples)} échantillon(s) ajouté(s) au batch.")
                st.rerun()
            else:
                st.warning("Sélectionnez au moins un échantillon.")

        st.markdown("---")
        st.write("**Échantillons déjà associés à ce batch :**")
        current_linked = df_query("""
            SELECT s.sample_code, s.sample_type, bs.injection_order
            FROM batch_samples bs JOIN samples s ON bs.sample_id = s.id
            WHERE bs.batch_id = ? ORDER BY bs.injection_order
        """, [batch_choice])
        if not current_linked.empty:
            st.dataframe(
                current_linked.rename(columns={
                    "sample_code": "Code", "sample_type": "Type", "injection_order": "Ordre d'injection"
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.caption("Aucun échantillon associé pour le moment.")

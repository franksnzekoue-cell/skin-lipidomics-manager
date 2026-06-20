import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import df_query, execute, init_db

init_db()
st.set_page_config(page_title="Projets — Lipidomique Peau", page_icon="📁", layout="wide")

st.title("📁 Projets & Expériences")

CATEGORIES = ["Céramides", "Resolvins", "Lipides pro-inflammatoires", "Lipides anti-inflammatoires", "Autre"]
STATUTS = ["Planifié", "En cours", "En pause", "Terminé", "Abandonné"]
PRIORITES = ["Haute", "Moyenne", "Basse"]

tab1, tab2, tab3 = st.tabs(["📋 Vue d'ensemble", "➕ Nouveau projet", "🔬 Expériences"])

# ===========================================================================
# TAB 1 — VUE D'ENSEMBLE
# ===========================================================================
with tab1:
    projects_df = df_query("SELECT * FROM projects ORDER BY updated_at DESC")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_cat = st.multiselect("Filtrer par catégorie", CATEGORIES, default=[])
    with col_f2:
        filter_status = st.multiselect("Filtrer par statut", STATUTS, default=[])
    with col_f3:
        filter_priority = st.multiselect("Filtrer par priorité", PRIORITES, default=[])

    filtered = projects_df.copy()
    if filter_cat:
        filtered = filtered[filtered["category"].isin(filter_cat)]
    if filter_status:
        filtered = filtered[filtered["status"].isin(filter_status)]
    if filter_priority:
        filtered = filtered[filtered["priority"].isin(filter_priority)]

    st.markdown(f"**{len(filtered)} projet(s) trouvé(s)**")

    if filtered.empty:
        st.info("Aucun projet ne correspond aux filtres sélectionnés.")
    else:
        for _, row in filtered.iterrows():
            status_color = {
                "Planifié": "🔵", "En cours": "🟢", "En pause": "🟠",
                "Terminé": "✅", "Abandonné": "⚫"
            }.get(row["status"], "⚪")
            priority_badge = {"Haute": "🔴 Haute", "Moyenne": "🟡 Moyenne", "Basse": "🟢 Basse"}.get(row["priority"], row["priority"])

            with st.expander(f"{status_color} **{row['name']}** — {row['category']} · {priority_badge}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**Description :** {row['description']}")
                    st.write(f"**Responsable :** {row['owner']}")
                with c2:
                    st.write(f"**Statut actuel :** {row['status']}")
                    st.write(f"**Début :** {row['start_date']}  ·  **Échéance :** {row['due_date']}")

                # Expériences liées
                exps = df_query("SELECT * FROM experiments WHERE project_id = ?", [row["id"]])
                if not exps.empty:
                    st.write("**Expériences associées :**")
                    st.dataframe(
                        exps[["name", "status", "start_date", "due_date"]].rename(
                            columns={"name": "Expérience", "status": "Statut", "start_date": "Début", "due_date": "Échéance"}
                        ),
                        use_container_width=True, hide_index=True
                    )

                st.markdown("---")
                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    new_status = st.selectbox(
                        "Modifier le statut", STATUTS,
                        index=STATUTS.index(row["status"]) if row["status"] in STATUTS else 0,
                        key=f"status_{row['id']}"
                    )
                    if new_status != row["status"]:
                        if st.button("Mettre à jour le statut", key=f"upd_{row['id']}"):
                            execute(
                                "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
                                [new_status, datetime.now().isoformat(), row["id"]]
                            )
                            st.success("Statut mis à jour.")
                            st.rerun()
                with edit_col2:
                    if st.button("🗑️ Supprimer ce projet", key=f"del_{row['id']}"):
                        execute("DELETE FROM projects WHERE id = ?", [row["id"]])
                        st.success("Projet supprimé.")
                        st.rerun()

# ===========================================================================
# TAB 2 — NOUVEAU PROJET
# ===========================================================================
with tab2:
    st.subheader("Créer un nouveau projet")
    with st.form("new_project_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Nom du projet *")
            category = st.selectbox("Catégorie *", CATEGORIES)
            owner = st.text_input("Responsable", value="Franks")
            priority = st.selectbox("Priorité", PRIORITES, index=1)
        with c2:
            status = st.selectbox("Statut initial", STATUTS, index=0)
            start_date = st.date_input("Date de début", value=date.today())
            due_date = st.date_input("Échéance prévue")
        description = st.text_area("Description / objectifs du projet")

        submitted = st.form_submit_button("✅ Créer le projet", use_container_width=True)
        if submitted:
            if not name:
                st.error("Le nom du projet est obligatoire.")
            else:
                now = datetime.now().isoformat()
                execute(
                    """INSERT INTO projects (name, category, description, status, priority, owner,
                       start_date, due_date, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [name, category, description, status, priority, owner,
                     start_date.isoformat(), due_date.isoformat(), now, now]
                )
                st.success(f"Projet « {name} » créé avec succès !")
                st.rerun()

# ===========================================================================
# TAB 3 — EXPERIENCES
# ===========================================================================
with tab3:
    st.subheader("Ajouter une expérience à un projet")
    projects_list = df_query("SELECT id, name FROM projects ORDER BY name")

    if projects_list.empty:
        st.warning("Créez d'abord un projet avant d'ajouter des expériences.")
    else:
        with st.form("new_exp_form", clear_on_submit=True):
            project_choice = st.selectbox(
                "Projet associé *",
                options=projects_list["id"],
                format_func=lambda x: projects_list.loc[projects_list["id"] == x, "name"].values[0]
            )
            exp_name = st.text_input("Nom de l'expérience *")
            objective = st.text_area("Objectif")
            c1, c2, c3 = st.columns(3)
            with c1:
                exp_status = st.selectbox("Statut", STATUTS, index=0, key="exp_status")
            with c2:
                exp_start = st.date_input("Début", value=date.today(), key="exp_start")
            with c3:
                exp_due = st.date_input("Échéance", key="exp_due")
            notes = st.text_area("Notes complémentaires")

            submitted_exp = st.form_submit_button("✅ Ajouter l'expérience", use_container_width=True)
            if submitted_exp:
                if not exp_name:
                    st.error("Le nom de l'expérience est obligatoire.")
                else:
                    now = datetime.now().isoformat()
                    execute(
                        """INSERT INTO experiments (project_id, name, objective, status, start_date, due_date, notes, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        [project_choice, exp_name, objective, exp_status,
                         exp_start.isoformat(), exp_due.isoformat(), notes, now]
                    )
                    st.success(f"Expérience « {exp_name} » ajoutée.")
                    st.rerun()

    st.markdown("---")
    st.subheader("Toutes les expériences")
    all_exps = df_query("""
        SELECT e.id, p.name as projet, e.name as experience, e.status, e.start_date, e.due_date
        FROM experiments e
        LEFT JOIN projects p ON e.project_id = p.id
        ORDER BY e.due_date
    """)
    if not all_exps.empty:
        st.dataframe(
            all_exps.rename(columns={
                "projet": "Projet", "experience": "Expérience", "status": "Statut",
                "start_date": "Début", "due_date": "Échéance"
            }).drop(columns=["id"]),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Aucune expérience enregistrée.")

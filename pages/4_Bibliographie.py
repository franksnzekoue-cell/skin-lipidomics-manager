import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import df_query, execute, init_db

init_db()
st.set_page_config(page_title="Bibliographie — Lipidomique Peau", page_icon="📚", layout="wide")

st.title("📚 Bibliographie & Références")

RELEVANCE_LEVELS = ["Haute", "Moyenne", "Basse"]

tab1, tab2 = st.tabs(["📋 Liste des références", "➕ Ajouter une référence"])

# ===========================================================================
# TAB 1 — LISTE
# ===========================================================================
with tab1:
    refs_df = df_query("""
        SELECT r.*, p.name as project_name
        FROM references_lib r
        LEFT JOIN projects p ON r.project_id = p.id
        ORDER BY r.year DESC, r.created_at DESC
    """)

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        search_term = st.text_input("🔍 Recherche (titre, auteurs, tags)")
    with col_f2:
        f_relevance = st.multiselect("Pertinence", RELEVANCE_LEVELS)
    with col_f3:
        f_project = st.multiselect("Projet", refs_df["project_name"].dropna().unique().tolist() if not refs_df.empty else [])

    filtered = refs_df.copy()
    if search_term:
        mask = (
            filtered["title"].str.contains(search_term, case=False, na=False) |
            filtered["authors"].str.contains(search_term, case=False, na=False) |
            filtered["topic_tags"].str.contains(search_term, case=False, na=False)
        )
        filtered = filtered[mask]
    if f_relevance:
        filtered = filtered[filtered["relevance"].isin(f_relevance)]
    if f_project:
        filtered = filtered[filtered["project_name"].isin(f_project)]

    st.markdown(f"**{len(filtered)} référence(s) trouvée(s)**")

    if filtered.empty:
        st.info("Aucune référence ne correspond à la recherche.")
    else:
        for _, row in filtered.iterrows():
            relevance_icon = {"Haute": "🔴", "Moyenne": "🟡", "Basse": "🟢"}.get(row["relevance"], "⚪")
            with st.expander(f"{relevance_icon} **{row['title']}** ({row['year']})"):
                st.write(f"**Auteurs :** {row['authors']}")
                st.write(f"**Journal :** {row['journal']} ({row['year']})")
                if row["doi_url"]:
                    st.write(f"**DOI/URL :** {row['doi_url']}")
                st.write(f"**Tags :** {row['topic_tags']}")
                st.write(f"**Résumé :** {row['summary']}")
                st.write(f"**Projet associé :** {row['project_name'] or '—'}")
                st.write(f"**Pertinence :** {row['relevance']}")

                if st.button("🗑️ Supprimer", key=f"delref_{row['id']}"):
                    execute("DELETE FROM references_lib WHERE id = ?", [row["id"]])
                    st.success("Référence supprimée.")
                    st.rerun()

        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exporter en CSV", csv, "bibliographie.csv", "text/csv")

# ===========================================================================
# TAB 2 — AJOUTER
# ===========================================================================
with tab2:
    st.subheader("Ajouter une référence bibliographique")
    projects_list = df_query("SELECT id, name FROM projects ORDER BY name")

    with st.form("new_ref_form", clear_on_submit=True):
        title = st.text_input("Titre de l'article *")
        c1, c2 = st.columns(2)
        with c1:
            authors = st.text_input("Auteurs", placeholder="ex: Castro J.P. et al.")
            journal = st.text_input("Journal", placeholder="ex: Free Radic. Biol. Med.")
            year = st.number_input("Année", min_value=1950, max_value=2030, value=2025, step=1)
        with c2:
            doi_url = st.text_input("DOI ou URL")
            topic_tags = st.text_input("Tags (séparés par des virgules)", placeholder="céramides, barrière, biomarqueur")
            relevance = st.selectbox("Pertinence pour vos projets", RELEVANCE_LEVELS, index=1)
        project_choice = st.selectbox(
            "Projet associé",
            options=[None] + list(projects_list["id"]),
            format_func=lambda x: "—" if x is None else projects_list.loc[projects_list["id"] == x, "name"].values[0]
        )
        summary = st.text_area("Résumé / points clés", height=120)

        submitted = st.form_submit_button("✅ Ajouter la référence", use_container_width=True)
        if submitted:
            if not title:
                st.error("Le titre est obligatoire.")
            else:
                now = datetime.now().isoformat()
                execute(
                    """INSERT INTO references_lib (project_id, title, authors, journal, year, doi_url,
                       topic_tags, summary, relevance, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [project_choice, title, authors, journal, year, doi_url,
                     topic_tags, summary, relevance, now]
                )
                st.success(f"Référence « {title} » ajoutée.")
                st.rerun()

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
import requests

sys.path.append(str(Path(__file__).parent.parent))
from utils.database import df_query, execute, init_db

init_db()
st.set_page_config(page_title="Bibliographie — Lipidomique Peau", page_icon="📚", layout="wide")

st.title("📚 Bibliographie & Références")

RELEVANCE_LEVELS = ["Haute", "Moyenne", "Basse"]

tab1, tab2 = st.tabs(["📋 Liste des références", "➕ Ajouter une référence"])

# ===========================================================================
# TAB 1 — LISTE DES RÉFÉRENCES
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
                
                # Le nom du journal est cliquable si un lien ou un DOI est enregistré
                if row["doi_url"]:
                    st.markdown(f"**Journal :** [{row['journal']}]({row['doi_url']}) ({row['year']}) 🔗 *(Cliquer pour ouvrir l'article)*")
                else:
                    st.write(f"**Journal :** {row['journal']} ({row['year']})")
                
                if row["doi_url"]:
                    st.caption(f"**Lien direct :** {row['doi_url']}")
                st.write(f"**Tags :** {row['topic_tags']}")
                st.write(f"**Résumé / Abstract :** {row['summary']}")
                st.write(f"**Projet associé :** {row['project_name'] or '—'}")
                st.write(f"**Pertinence :** {row['relevance']}")

                if st.button("🗑️ Supprimer", key=f"delref_{row['id']}"):
                    execute("DELETE FROM references_lib WHERE id = ?", [row["id"]])
                    st.success("Référence supprimée.")
                    st.rerun()

        csv = filtered.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exporter en CSV", csv, "bibliographie.csv", "text/csv")


# ===========================================================================
# TAB 2 — AJOUTER UNE RÉFÉRENCE (VERSION AUTOMATIQUE VIA DOI)
# ===========================================================================
with tab2:
    st.subheader("Ajouter une référence bibliographique")
    projects_list = df_query("SELECT id, name FROM projects ORDER BY name")

    # Initialisation des variables dans le State de Streamlit pour l'auto-remplissage
    if "api_title" not in st.session_state: st.session_state.api_title = ""
    if "api_authors" not in st.session_state: st.session_state.api_authors = ""
    if "api_journal" not in st.session_state: st.session_state.api_journal = ""
    if "api_year" not in st.session_state: st.session_state.api_year = 2025
    if "api_abstract" not in st.session_state: st.session_state.api_abstract = ""
    if "api_url" not in st.session_state: st.session_state.api_url = ""

    # Zone de recherche rapide par DOI (hors du formulaire pour pouvoir faire un "submit" intermédiaire)
    st.markdown("#### ⚡ Remplissage automatique via DOI")
    col_doi1, col_doi2 = st.columns([3, 1])
    with col_doi1:
        doi_input = st.text_input("Saisir le DOI de l'article", placeholder="ex: 10.1016/j.freeradbiomed.2023.10.001")
    with col_doi2:
        st.write("##") # Alignement vertical
        if st.button("🔍 Récupérer les métadonnées", use_container_width=True):
            if doi_input:
                clean_doi = doi_input.strip().replace("https://doi.org/", "")
                url_api = f"https://api.crossref.org/works/{clean_doi}"
                
                try:
                    with st.spinner("Recherche de l'article sur CrossRef..."):
                        response = requests.get(url_api, headers={"User-Agent": "SkinLipidomicsApp/1.0 (mailto:votre_email@labo.com)"}, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()["message"]
                        
                        # 1. Extraction du Titre
                        st.session_state.api_title = data.get("title", [""])[0] if data.get("title") else ""
                        
                        # 2. Extraction des Auteurs
                        author_list = data.get("author", [])
                        formatted_authors = []
                        for a in author_list:
                            formatted_authors.append(f"{a.get('family', '')} {a.get('given', '')[:1]}.")
                        st.session_state.api_authors = ", ".join(formatted_authors) if formatted_authors else ""
                        
                        # 3. Journal & Année
                        st.session_state.api_journal = data.get("container-title", [""])[0] if data.get("container-title") else ""
                        if "published-print" in data:
                            st.session_state.api_year = data["published-print"]["date-parts"][0][0]
                        elif "published-online" in data:
                            st.session_state.api_year = data["published-online"]["date-parts"][0][0]
                        
                        # 4. URL de l'article
                        st.session_state.api_url = data.get("URL", f"https://doi.org/{clean_doi}")
                        
                        # 5. Extraction de l'Abstract (CrossRef renvoie souvent du JATS XML, on nettoie les balises basiques)
                        raw_abstract = data.get("abstract", "")
                        if raw_abstract:
                            clean_abstract = raw_abstract.replace("<jats:title>Abstract</jats:title>", "")
                            clean_abstract = clean_abstract.replace("<jats:p>", "").replace("</jats:p>", " ")
                            clean_abstract = clean_abstract.replace("<jats:sub>", "").replace("</jats:sub>", "")
                            clean_abstract = clean_abstract.replace("<jats:sec>", "").replace("</jats:sec>", "")
                            st.session_state.api_abstract = clean_abstract.strip()
                        else:
                            st.session_state.api_abstract = "Abstract non disponible automatiquement sur CrossRef. À compléter manuellement."
                        
                        st.success("✅ Métadonnées récupérées avec succès ! Vérifiez et ajustez le formulaire ci-dessous.")
                    else:
                        st.error("DOI introuvable ou API injoignable. Remplissez manuellement.")
                except Exception as e:
                    st.error(f"Erreur lors de la connexion à l'API : {e}")
            else:
                st.warning("Veuillez entrer un DOI valide.")

    st.markdown("---")
    st.markdown("#### 📝 Formulaire de validation")

    # Formulaire final connecté aux variables du Session State
    with st.form("new_ref_form", clear_on_submit=False):
        title = st.text_input("Titre de l'article *", value=st.session_state.api_title)
        
        c1, c2 = st.columns(2)
        with c1:
            authors = st.text_input("Auteurs", value=st.session_state.api_authors, placeholder="ex: Castro J.P. et al.")
            journal = st.text_input("Journal", value=st.session_state.api_journal, placeholder="ex: Free Radic. Biol. Med.")
            year = st.number_input("Année", min_value=1950, max_value=2035, value=int(st.session_state.api_year), step=1)
        with c2:
            doi_url = st.text_input("Lien internet de l'article (URL ou DOI)", value=st.session_state.api_url)
            topic_tags = st.text_input("Tags (séparés par des virgules)", placeholder="céramides, barrière, biomarqueur")
            relevance = st.selectbox("Pertinence pour vos projets", RELEVANCE_LEVELS, index=1)
        
        project_choice = st.selectbox(
            "Projet associé",
            options=[None] + list(projects_list["id"]),
            format_func=lambda x: "—" if x is None else projects_list.loc[projects_list["id"] == x, "name"].values[0]
        )
        summary = st.text_area("Résumé / Abstract / Points clés", value=st.session_state.api_abstract, height=200)

        submitted = st.form_submit_button("✅ Valider et Enregistrer la référence", use_container_width=True)
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
                
                # Réinitialisation du state après envoi réussi
                st.session_state.api_title = ""
                st.session_state.api_authors = ""
                st.session_state.api_journal = ""
                st.session_state.api_abstract = ""
                st.session_state.api_url = ""
                st.rerun()

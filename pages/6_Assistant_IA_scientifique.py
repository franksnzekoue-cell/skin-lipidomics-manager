import streamlit as st
import pandas as pd
from pathlib import Path

from utils.ai_assistant import (
    answer_project_questions,
    interpret_data_frame,
    provider_message,
    summarize_text,
)
from utils.database import df_query

st.set_page_config(
    page_title="IA Assistant Scientifique Local",
    page_icon="🧠",
    layout="wide"
)

DATA_DIR = Path("data")
LIPIDS_FILE = DATA_DIR / "lipids.csv"

def load_csv(path):
    if path.exists():
        try:
            return pd.read_csv(path)
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier CSV : {e}")
            return pd.DataFrame()
    return pd.DataFrame()

lipids = load_csv(LIPIDS_FILE)
projects_df = df_query("SELECT * FROM projects")
samples_df = df_query("SELECT * FROM samples")
batches_df = df_query("SELECT * FROM lcms_batches")
experiments_df = df_query("SELECT * FROM experiments")
references_df = df_query("SELECT * FROM references_lib")
journal_df = df_query("SELECT * FROM journal")

st.title("🧠 Assistant IA Scientifique")
st.caption("Cette page peut utiliser Ollama, OpenAI ou un mode de secours local selon la configuration disponible.")
st.info(provider_message("auto"))

st.subheader("💬 Questions sur vos projets et données")
st.write("Posez une question naturelle sur un projet, un échantillon, un batch LC-MS, une référence ou votre journal de bord.")
question = st.text_area(
    "Votre question",
    placeholder="Exemple : Quel est le statut du projet Profil céramides peau saine vs DA ?",
    height=120,
)

if st.button("❓ Demander à l'IA", use_container_width=True):
    if question.strip():
        with st.spinner("Recherche dans vos données en cours..."):
            answer = answer_project_questions(
                question,
                projects_df=projects_df,
                samples_df=samples_df,
                batches_df=batches_df,
                experiments_df=experiments_df,
                references_df=references_df,
                journal_df=journal_df,
            )
        st.markdown("### 🧠 Réponse")
        st.write(answer)
    else:
        st.warning("⚠️ Veuillez écrire une question avant de lancer la recherche.")

st.markdown("---")

tab1, tab2 = st.tabs(["📚 Résumer un article ou des notes", "⚗️ Interpréter des données locales"])

# ===========================================================================
# 1. RÉSUMÉ DE TEXTE / NOTES DE LABORATOIRE
# ===========================================================================
with tab1:
    st.subheader("📚 Résumé d'un texte ou de vos notes d'expériences")
    st.write("Collez vos comptes-rendus de manipulations ou vos abstracts pour obtenir une synthèse structurée.")

    article_text = st.text_area(
        "Collez vos notes ou textes scientifiques ici...",
        height=250,
        placeholder="Décrivez vos résultats bruts ou collez un texte..."
    )

    if st.button("✨ Générer le résumé", use_container_width=True):
        if article_text.strip():
            with st.spinner("Analyse du texte en cours..."):
                summary, provider = summarize_text(article_text)
            st.markdown("---")
            st.markdown("### 📋 Synthèse de l'IA")
            st.write(summary)
            st.caption(provider_message(provider))
        else:
            st.warning("⚠️ Veuillez ajouter du texte avant de lancer l'analyse.")

# ===========================================================================
# 2. INTERPRÉTATION DES DONNÉES LOCALES (Lipides ou Expériences)
# ===========================================================================
with tab2:
    st.subheader("⚗️ Analyse de vos tableaux de données")
    
    if lipids.empty:
        st.info("📊 Le fichier `data/lipids.csv` est vide ou introuvable.")
        st.write("Vous pouvez également copier-coller des tableaux directement dans l'onglet de gauche pour les faire analyser par l'IA.")
    else:
        st.dataframe(lipids, use_container_width=True)
        
        if "Sample_ID" in lipids.columns:
            sample_filter = st.selectbox("Choisir un échantillon à analyser", lipids["Sample_ID"].unique())
            sample_data = lipids[lipids["Sample_ID"] == sample_filter]
            
            if st.button("🚀 Analyser l'échantillon", use_container_width=True):
                with st.spinner("Analyse bioinformatique en cours..."):
                    report, provider = interpret_data_frame(sample_data, sample_name=str(sample_filter))
                st.markdown("---")
                st.subheader(f"📋 Rapport — {sample_filter}")
                st.write(report)
                st.caption(provider_message(provider))
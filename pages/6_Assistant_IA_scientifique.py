import streamlit as st
import pandas as pd
from openai import OpenAI
from pathlib import Path

st.set_page_config(
    page_title="IA Assistant Scientifique",
    page_icon="🧠",
    layout="wide"
)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

DATA_DIR = Path("data")
LIPIDS_FILE = DATA_DIR / "lipids.csv"

def load_csv(path):
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()

lipids = load_csv(LIPIDS_FILE)

st.title("🧠 Assistant IA scientifique lipidomique")

tab1, tab2 = st.tabs(["📚 Résumer article", "⚗️ Interpréter résultats"])

# -----------------------------
# 1. RESUME ARTICLE
# -----------------------------

with tab1:

    st.subheader("📚 Résumé d’article scientifique")

    article_text = st.text_area(
        "Colle ici un abstract ou un article",
        height=250
    )

    if st.button("Résumer l’article"):

        if article_text:

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """
Tu es un expert en lipidomique cutanée, céramides, inflammation et biologie de la peau.

Tu dois :
- Résumer clairement le texte scientifique
- Extraire les points clés
- Expliquer les implications pour la peau et les lipides
- Rester précis et scientifique
"""
                    },
                    {
                        "role": "user",
                        "content": article_text
                    }
                ]
            )

            st.write(response.choices[0].message.content)

        else:
            st.warning("Ajoute un texte scientifique")

# -----------------------------
# 2. INTERPRETATION RESULTATS
# -----------------------------

with tab2:

    st.subheader("⚗️ Analyse des résultats LC-MS")

    if lipids.empty:
        st.warning("Aucune donnée lipidomique disponible")
        st.stop()

    st.dataframe(lipids)

    sample_filter = st.selectbox(
        "Choisir un échantillon",
        lipids["Sample_ID"].unique()
    )

    sample_data = lipids[
        lipids["Sample_ID"] == sample_filter
    ]

    if st.button("Analyser les résultats"):

        prompt = f"""
Voici des résultats lipidomiques LC-MS d’un échantillon cutané :

{sample_data.to_string(index=False)}

Analyse :
- Résume les profils lipidiques
- Identifie tendances (augmentation/diminution)
- Interprète en termes de barrière cutanée
- Indique si profil inflammatoire probable
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """
Tu es un bioinformaticien expert en lipidomique cutanée et LC-MS.
Tu analyses des données scientifiques, pas du texte général.
"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        st.subheader("🧠 Interprétation IA")
        st.write(response.choices[0].message.content)
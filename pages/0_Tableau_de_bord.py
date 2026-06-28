import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Raccordement au dossier parent pour la base de données
sys.path.append(str(Path(__file__).parent.parent))
from utils.database import df_query, init_db

init_db()
st.set_page_config(page_title="Tableau de bord — Lipidomique Peau", page_icon="📊", layout="wide")

st.title("📊 Synthèse & Tableau de bord")
st.caption("Aperçu en temps réel de l'avancement des projets, des stocks d'échantillons et des analyses de l'Orbitrap Exploris 480.")

# ===========================================================================
# REQUÊTES DE DONNÉES (KPIs)
# ===========================================================================
kpi_projects = df_query("SELECT COUNT(*) as total FROM projects WHERE status = 'En cours'")
kpi_samples = df_query("SELECT COUNT(*) as total FROM samples WHERE status = 'Disponible'")
kpi_batches = df_query("SELECT COUNT(*) as total FROM lcms_batches WHERE qc_status = 'En attente'")

proj_count = kpi_projects["total"].iloc[0] if not kpi_projects.empty else 0
samp_count = kpi_samples["total"].iloc[0] if not kpi_samples.empty else 0
batch_count = kpi_batches["total"].iloc[0] if not kpi_batches.empty else 0

# 1. AFFICHAGE DES METRICS METIERS
c1, c2, c3 = st.columns(3)
with c1:
    st.metric(label="📁 Projets actifs en cours", value=proj_count)
with c2:
    st.metric(label="🧪 Échantillons disponibles (-80°C)", value=samp_count)
with c3:
    st.metric(label="⚗️ Batchs LC-MS en attente de QC", value=batch_count, delta=batch_count if batch_count > 0 else None, delta_color="inverse")

st.markdown("---")

# ===========================================================================
# SECTION : ALERTES & ECHEANCES PROCHES
# ===========================================================================
st.subheader("⚠️ Échéances et jalons à venir")

upcoming_deadlines = df_query("""
    SELECT 'Projet' as type, name, due_date, status 
    FROM projects 
    WHERE status NOT IN ('Terminé', 'Abandonné')
    UNION ALL
    SELECT 'Expérience' as type, name, due_date, status 
    FROM experiments 
    WHERE status NOT IN ('Terminé', 'Abandonné')
    ORDER BY due_date ASC
    LIMIT 3
""")

if upcoming_deadlines.empty:
    st.success("🎉 Aucune échéance urgente planifiée. Tous les projets sont à jour !")
else:
    cols = st.columns(len(upcoming_deadlines))
    today = datetime.today().date()
    
    for idx, row in upcoming_deadlines.iterrows():
        with cols[idx]:
            try:
                due_dt = datetime.strptime(row["due_date"], "%Y-%m-%d").date()
                days_left = (due_dt - today).days
                if days_left < 0:
                    time_status = f"🔴 En retard de {abs(days_left)} jours"
                elif days_left <= 7:
                    time_status = f"⚠️ J-{days_left} (Cette semaine)"
                else:
                    time_status = f"⏳ J-{days_left}"
            except:
                time_status = f"📅 Échéance : {row['due_date']}"

            with st.container(border=True):
                st.markdown(f"**{row['type']}:** {row['name']}")
                st.caption(f"Statut : {row['status']}")
                st.subheader(time_status)

st.markdown("---")

# ===========================================================================
# GRAPHIQUES & REPARTITIONS ANALYTIQUES
# ===========================================================================
col_graph1, col_graph2 = st.columns(2)

with col_graph1:
    st.subheader("💡 Projets par catégories de Lipides")
    cat_df = df_query("SELECT category, COUNT(*) as nombre FROM projects GROUP BY category")
    if not cat_df.empty:
        st.bar_chart(data=cat_df, x="category", y="nombre", color="#4285F4")
    else:
        st.caption("Aucune donnée de projet disponible.")

with col_graph2:
    st.subheader("📦 État du stock d'échantillons")
    stock_df = df_query("SELECT sample_type, COUNT(*) as nombre FROM samples GROUP BY sample_type")
    if not stock_df.empty:
        st.bar_chart(data=stock_df, x="sample_type", y="nombre", color="#34A853")
    else:
        st.caption("Aucun échantillon en stock.")

st.markdown("---")

# ===========================================================================
# ACTIVITÉ RÉCENTE (FIL DU JOURNAL DE BORD)
# ===========================================================================
st.subheader("📝 Dernières entrées du journal de bord")

recent_journal = df_query("""
    SELECT j.*, p.name as project_name
    FROM journal j
    LEFT JOIN projects p ON j.project_id = p.id
    ORDER BY j.entry_date DESC, j.created_at DESC
    LIMIT 4
""")

if recent_journal.empty:
    st.info("Aucun événement consigné récemment dans le journal.")
else:
    type_icons = {"Note": "🗒️", "Résultat": "📊", "Réunion": "🤝", "Décision": "⚖️"}
    col_j1, col_j2 = st.columns(2)
    
    for idx, row in recent_journal.iterrows():
        icon = type_icons.get(row["entry_type"], "🗒️")
        target_col = col_j1 if idx % 2 == 0 else col_j2
        
        with target_col:
            with st.container(border=True):
                st.markdown(f"**{icon} {row['entry_type']}** — *{row['entry_date']}*")
                if row['project_name']:
                    st.caption(f"📁 Projet : {row['project_name']}")
                st.write(row["entry_text"][:200] + ("..." if len(row["entry_text"]) > 200 else ""))
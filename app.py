"""
Application de gestion de projet — Lipidomique cutanée
Page d'accueil : Tableau de bord
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from utils.database import init_db, seed_demo_data, df_query

st.set_page_config(
    page_title="Lipidomique Peau — Gestion de Projet",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
seed_demo_data()

# ---------------------------------------------------------------------------
# STYLE
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fb;
        border: 1px solid #e3e6ec;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
    }
    .stat-num { font-size: 32px; font-weight: 700; color: #2d3142; }
    .stat-label { font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: .04em;}
    h1, h2, h3 { font-family: 'Source Sans Pro', sans-serif; }
    .priority-haute { color: #c0392b; font-weight: 600; }
    .priority-moyenne { color: #d68910; font-weight: 600; }
    .priority-basse { color: #2980b9; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
st.sidebar.title("🧬 Lipidomique Peau")
st.sidebar.caption("Gestion de projet — Céramides · Resolvins · Lipides inflammatoires")
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="📊 Tableau de bord", icon=None)
st.sidebar.page_link("pages/1_Projets.py", label="📁 Projets & Expériences")
st.sidebar.page_link("pages/2_Echantillons.py", label="🧪 Échantillons")
st.sidebar.page_link("pages/3_Analyses_LCMS.py", label="⚗️ Analyses LC-MS")
st.sidebar.page_link("pages/4_Bibliographie.py", label="📚 Bibliographie")
st.sidebar.page_link("pages/5_Journal.py", label="📝 Journal de bord")
st.sidebar.markdown("---")
st.sidebar.caption("Instrument : Orbitrap Exploris 480")

# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
st.title("Tableau de bord — Lipidomique cutanée")
st.caption(f"Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")

# ---------------------------------------------------------------------------
# KPIs PRINCIPAUX
# ---------------------------------------------------------------------------
projects_df = df_query("SELECT * FROM projects")
samples_df = df_query("SELECT * FROM samples")
batches_df = df_query("SELECT * FROM lcms_batches")
experiments_df = df_query("SELECT * FROM experiments")
refs_df = df_query("SELECT * FROM references_lib")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    n_active = len(projects_df[projects_df["status"] == "En cours"]) if not projects_df.empty else 0
    st.markdown(f"""<div class="metric-card"><div class="stat-num">{n_active}</div>
                <div class="stat-label">Projets en cours</div></div>""", unsafe_allow_html=True)

with col2:
    n_samples = len(samples_df) if not samples_df.empty else 0
    st.markdown(f"""<div class="metric-card"><div class="stat-num">{n_samples}</div>
                <div class="stat-label">Échantillons</div></div>""", unsafe_allow_html=True)

with col3:
    n_batches = len(batches_df) if not batches_df.empty else 0
    st.markdown(f"""<div class="metric-card"><div class="stat-num">{n_batches}</div>
                <div class="stat-label">Batchs LC-MS</div></div>""", unsafe_allow_html=True)

with col4:
    n_pending_qc = len(batches_df[batches_df["qc_status"] == "En attente"]) if not batches_df.empty else 0
    st.markdown(f"""<div class="metric-card"><div class="stat-num">{n_pending_qc}</div>
                <div class="stat-label">QC en attente</div></div>""", unsafe_allow_html=True)

with col5:
    n_refs = len(refs_df) if not refs_df.empty else 0
    st.markdown(f"""<div class="metric-card"><div class="stat-num">{n_refs}</div>
                <div class="stat-label">Références</div></div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# GRAPHIQUES
# ---------------------------------------------------------------------------
g1, g2 = st.columns([1, 1])

with g1:
    st.subheader("Répartition des projets par catégorie")
    if not projects_df.empty:
        cat_counts = projects_df["category"].value_counts().reset_index()
        cat_counts.columns = ["Catégorie", "Nombre"]
        fig = px.pie(
            cat_counts, names="Catégorie", values="Nombre", hole=0.45,
            color_discrete_sequence=["#5b8def", "#f2994a", "#27ae60", "#9b59b6", "#e74c3c"]
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=True, height=350, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun projet enregistré.")

with g2:
    st.subheader("Statut des projets")
    if not projects_df.empty:
        status_counts = projects_df["status"].value_counts().reset_index()
        status_counts.columns = ["Statut", "Nombre"]
        color_map = {
            "Planifié": "#95a5a6", "En cours": "#5b8def", "En pause": "#f2994a",
            "Terminé": "#27ae60", "Abandonné": "#e74c3c"
        }
        fig = px.bar(
            status_counts, x="Statut", y="Nombre", color="Statut",
            color_discrete_map=color_map, text="Nombre"
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, height=350, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun projet enregistré.")

g3, g4 = st.columns([1, 1])

with g3:
    st.subheader("Échantillons par type")
    if not samples_df.empty:
        type_counts = samples_df["sample_type"].value_counts().reset_index()
        type_counts.columns = ["Type", "Nombre"]
        fig = px.bar(
            type_counts, x="Nombre", y="Type", orientation="h",
            color="Nombre", color_continuous_scale="Blues", text="Nombre"
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, height=320, margin=dict(t=10, b=10, l=10, r=10), coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun échantillon enregistré.")

with g4:
    st.subheader("Statut QC des batchs LC-MS")
    if not batches_df.empty:
        qc_counts = batches_df["qc_status"].value_counts().reset_index()
        qc_counts.columns = ["Statut QC", "Nombre"]
        color_map_qc = {
            "Conforme": "#27ae60", "En attente": "#95a5a6",
            "Non conforme": "#e74c3c", "À revoir": "#f2994a"
        }
        fig = px.pie(
            qc_counts, names="Statut QC", values="Nombre", hole=0.45,
            color="Statut QC", color_discrete_map=color_map_qc
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=320, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun batch enregistré.")

st.markdown("---")

# ---------------------------------------------------------------------------
# ECHEANCES A VENIR
# ---------------------------------------------------------------------------
st.subheader("🗓️ Échéances à venir (projets & expériences)")

today = date.today().isoformat()

upcoming_projects = projects_df[
    (projects_df["due_date"] >= today) & (projects_df["status"].isin(["En cours", "Planifié"]))
].sort_values("due_date") if not projects_df.empty else pd.DataFrame()

upcoming_exp = experiments_df[
    (experiments_df["due_date"] >= today) & (experiments_df["status"].isin(["En cours", "Planifié"]))
].sort_values("due_date") if not experiments_df.empty else pd.DataFrame()

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("**Projets**")
    if not upcoming_projects.empty:
        for _, row in upcoming_projects.iterrows():
            priority_class = f"priority-{row['priority'].lower()}"
            st.markdown(
                f"- **{row['name']}** · <span class='{priority_class}'>{row['priority']}</span> · "
                f"échéance : {row['due_date']}",
                unsafe_allow_html=True
            )
    else:
        st.caption("Aucune échéance de projet à venir.")

with col_b:
    st.markdown("**Expériences**")
    if not upcoming_exp.empty:
        exp_with_proj = upcoming_exp.merge(
            projects_df[["id", "name"]], left_on="project_id", right_on="id", suffixes=("", "_proj")
        )
        for _, row in exp_with_proj.iterrows():
            st.markdown(f"- **{row['name']}** _(projet : {row['name_proj']})_ · échéance : {row['due_date']}")
    else:
        st.caption("Aucune échéance d'expérience à venir.")

st.markdown("---")
st.caption("💡 Utilisez le menu latéral pour naviguer entre les modules : Projets, Échantillons, Analyses LC-MS, Bibliographie et Journal de bord.")

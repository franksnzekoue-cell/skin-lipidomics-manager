import os
import re
from typing import Tuple

import pandas as pd


def _load_project_context(projects_df: pd.DataFrame | None = None, samples_df: pd.DataFrame | None = None,
                          batches_df: pd.DataFrame | None = None, experiments_df: pd.DataFrame | None = None,
                          references_df: pd.DataFrame | None = None, journal_df: pd.DataFrame | None = None) -> dict:
    try:
        from utils.database import df_query
    except Exception:
        return {
            "projects": projects_df if projects_df is not None else pd.DataFrame(),
            "samples": samples_df if samples_df is not None else pd.DataFrame(),
            "batches": batches_df if batches_df is not None else pd.DataFrame(),
            "experiments": experiments_df if experiments_df is not None else pd.DataFrame(),
            "references": references_df if references_df is not None else pd.DataFrame(),
            "journal": journal_df if journal_df is not None else pd.DataFrame(),
        }

    if projects_df is None:
        projects_df = df_query("SELECT * FROM projects")
    if samples_df is None:
        samples_df = df_query("SELECT * FROM samples")
    if batches_df is None:
        batches_df = df_query("SELECT * FROM lcms_batches")
    if experiments_df is None:
        experiments_df = df_query("SELECT * FROM experiments")
    if references_df is None:
        references_df = df_query("SELECT * FROM references_lib")
    if journal_df is None:
        journal_df = df_query("SELECT * FROM journal")

    return {
        "projects": projects_df if projects_df is not None else pd.DataFrame(),
        "samples": samples_df if samples_df is not None else pd.DataFrame(),
        "batches": batches_df if batches_df is not None else pd.DataFrame(),
        "experiments": experiments_df if experiments_df is not None else pd.DataFrame(),
        "references": references_df if references_df is not None else pd.DataFrame(),
        "journal": journal_df if journal_df is not None else pd.DataFrame(),
    }


def _format_dataframe_for_prompt(df: pd.DataFrame, columns: list[str] | None = None) -> str:
    if df is None or df.empty:
        return "Aucune donnée disponible."
    if columns:
        subset = df.loc[:, [c for c in columns if c in df.columns]]
    else:
        subset = df
    return subset.fillna("").to_string(index=False)


def _get_openai_client():
    try:
        from openai import OpenAI
    except Exception:
        return None

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return OpenAI(api_key=api_key)

    try:
        import streamlit as st
    except Exception:
        return None

    secrets = getattr(st, "secrets", {})
    if isinstance(secrets, dict):
        key = secrets.get("OPENAI_API_KEY")
        if key:
            return OpenAI(api_key=key)
    return None


def _get_provider():
    try:
        import ollama

        return "ollama", ollama
    except Exception:
        pass

    client = _get_openai_client()
    if client is not None:
        return "openai", client

    return "fallback", None


def fallback_summarize_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return "Aucun texte fourni pour l'analyse."

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
    if not sentences:
        sentences = [cleaned]

    bullets = []
    for sentence in sentences[:4]:
        bullets.append(f"- {sentence}")

    return (
        "Résumé local de secours\n\n"
        "Voici une synthèse simple et structurée du contenu fourni :\n"
        + "\n".join(bullets)
        + "\n\n"
        "Points de vigilance : vérifier les valeurs biologiques, le contexte expérimental et les observations associées."
    )


def fallback_interpret_data_frame(df: pd.DataFrame, sample_name: str | None = None) -> str:
    if df is None or df.empty:
        return "Aucune donnée n'a été fournie pour l'analyse."

    numeric_cols = [col for col in df.select_dtypes(include="number").columns if col.lower() != "id"]
    sample_label = sample_name or "l'échantillon"
    lines = [f"Analyse locale de secours pour {sample_label}"]
    lines.append("")

    if not numeric_cols:
        lines.append("Aucune colonne numérique n'a été détectée. Les données doivent être enrichies pour une interprétation quantitative.")
        return "\n".join(lines)

    for col in numeric_cols[:6]:
        values = pd.to_numeric(df[col], errors="coerce").dropna()
        if values.empty:
            continue
        mean_val = values.mean()
        min_val = values.min()
        max_val = values.max()
        lines.append(f"- {col}: moyenne {mean_val:.2f}, minimum {min_val:.2f}, maximum {max_val:.2f}")

    lines.append("")
    lines.append("Interprétation générale : les variations observées suggèrent un effet biologique potentiel à confirmer par comparaison avec les groupes de référence et les contrôles qualité.")
    return "\n".join(lines)


def summarize_text(text: str, model_name: str = "llama3") -> Tuple[str, str]:
    provider, client = _get_provider()

    if provider == "ollama":
        try:
            response = client.chat(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": """
Tu es un chercheur senior expert en lipidomique cutanée et biologie de la peau.
Résume clairement le texte en français, extrais les points clés sous forme de liste à puces et donne les implications majeures.
Structure la réponse proprement.
""",
                    },
                    {"role": "user", "content": text},
                ],
            )
            return response["message"]["content"], provider
        except Exception:
            return fallback_summarize_text(text), "fallback"

    if provider == "openai":
        try:
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "Tu es un expert en lipidomique cutanée. Réponds en français, de façon claire et structurée."},
                    {"role": "user", "content": text},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content, provider
        except Exception:
            return fallback_summarize_text(text), "fallback"

    return fallback_summarize_text(text), provider


def interpret_data_frame(df: pd.DataFrame, sample_name: str | None = None, model_name: str = "llama3") -> Tuple[str, str]:
    provider, client = _get_provider()

    if provider == "ollama":
        try:
            prompt = f"""
Voici les données de l'échantillon {sample_name or 'local'} :
{df.to_string(index=False)}

Analyse ces données chiffrées, identifie les tendances et interprète l'état de la barrière cutanée en français. Réponds de façon claire et concise.
"""
            response = client.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": "Tu es un bioinformaticien expert en lipidomique cutanée. Tu analyses des données chiffrées de manière rigoureuse."},
                    {"role": "user", "content": prompt},
                ],
            )
            return response["message"]["content"], provider
        except Exception:
            return fallback_interpret_data_frame(df, sample_name), "fallback"

    if provider == "openai":
        try:
            prompt = f"""
Voici les données de l'échantillon {sample_name or 'local'} :
{df.to_string(index=False)}

Analyse ces données chiffrées, identifie les tendances et interprète l'état de la barrière cutanée en français. Réponds de façon claire et concise.
"""
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "Tu es un bioinformaticien expert en lipidomique cutanée. Tu analyses des données chiffrées de manière rigoureuse."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content, provider
        except Exception:
            return fallback_interpret_data_frame(df, sample_name), "fallback"

    return fallback_interpret_data_frame(df, sample_name), provider


def answer_project_questions(question: str, projects_df: pd.DataFrame | None = None, samples_df: pd.DataFrame | None = None,
                              batches_df: pd.DataFrame | None = None, experiments_df: pd.DataFrame | None = None,
                              references_df: pd.DataFrame | None = None, journal_df: pd.DataFrame | None = None,
                              model_name: str = "llama3") -> str:
    context = _load_project_context(projects_df, samples_df, batches_df, experiments_df, references_df, journal_df)
    projects_df = context["projects"]
    samples_df = context["samples"]
    batches_df = context["batches"]
    experiments_df = context["experiments"]
    references_df = context["references"]
    journal_df = context["journal"]

    if question is None:
        return "Veuillez poser une question sur vos projets ou vos données."

    normalized = question.lower()
    selected_projects = projects_df.copy()
    if not projects_df.empty and "name" in projects_df.columns:
        names = [name for name in projects_df["name"].dropna().astype(str) if name]
        matched_names = [name for name in names if name.lower() in normalized or normalized in name.lower()]
        if matched_names:
            selected_projects = projects_df[projects_df["name"].astype(str).str.lower().isin([name.lower() for name in matched_names])]

    related_samples = samples_df.copy()
    related_batches = batches_df.copy()
    related_experiments = experiments_df.copy()
    related_references = references_df.copy()
    related_journal = journal_df.copy()

    if not selected_projects.empty and "id" in selected_projects.columns:
        project_ids = selected_projects["id"].astype(int).tolist()
        if not samples_df.empty and "project_id" in samples_df.columns:
            related_samples = samples_df[samples_df["project_id"].astype(str).isin([str(pid) for pid in project_ids])]
        if not batches_df.empty and "project_id" in batches_df.columns:
            related_batches = batches_df[batches_df["project_id"].astype(str).isin([str(pid) for pid in project_ids])]
        if not experiments_df.empty and "project_id" in experiments_df.columns:
            related_experiments = experiments_df[experiments_df["project_id"].astype(str).isin([str(pid) for pid in project_ids])]
        if not references_df.empty and "project_id" in references_df.columns:
            related_references = references_df[references_df["project_id"].astype(str).isin([str(pid) for pid in project_ids])]
        if not journal_df.empty and "project_id" in journal_df.columns:
            related_journal = journal_df[journal_df["project_id"].astype(str).isin([str(pid) for pid in project_ids])]

    if not selected_projects.empty and ("statut" in normalized or "status" in normalized or "projet" in normalized):
        if "statut" in normalized or "status" in normalized:
            rows = []
            for _, row in selected_projects.iterrows():
                rows.append(f"- {row.get('name', '-')} : {row.get('status', 'inconnu')}")
            return "Voici le statut demandé :\n" + "\n".join(rows)

    if not selected_projects.empty and ("échantillon" in normalized or "sample" in normalized or "échantillons" in normalized):
        if related_samples.empty:
            return "Aucun échantillon associé n'a été trouvé pour ce projet."
        summary = []
        for _, row in related_samples.head(5).iterrows():
            summary.append(f"- {row.get('sample_code', '-')} ({row.get('sample_type', '-')}) — statut: {row.get('status', '-')}")
        return "Échantillons associés :\n" + "\n".join(summary)

    if not selected_projects.empty and ("batch" in normalized or "analyse" in normalized or "qc" in normalized):
        if related_batches.empty:
            return "Aucun batch d'analyse associé n'a été trouvé pour ce projet."
        summary = []
        for _, row in related_batches.head(5).iterrows():
            summary.append(f"- {row.get('batch_code', '-')} — QC: {row.get('qc_status', '-')} — {row.get('method_name', '-')}")
        return "Batches associés :\n" + "\n".join(summary)

    if not selected_projects.empty and ("référence" in normalized or "bibliographie" in normalized or "article" in normalized):
        if related_references.empty:
            return "Aucune référence bibliographique associée n'a été trouvée pour ce projet."
        summary = []
        for _, row in related_references.head(5).iterrows():
            summary.append(f"- {row.get('title', '-')} ({row.get('year', '-')}) — {row.get('relevance', '-')}")
        return "Références associées :\n" + "\n".join(summary)

    if not selected_projects.empty and ("journal" in normalized or "note" in normalized or "activité" in normalized):
        if related_journal.empty:
            return "Aucune entrée de journal n'a été trouvée pour ce projet."
        summary = []
        for _, row in related_journal.head(5).iterrows():
            summary.append(f"- {row.get('entry_date', '-')} — {row.get('entry_text', '-')}")
        return "Entrées de journal :\n" + "\n".join(summary)

    provider, client = _get_provider()
    if provider in {"ollama", "openai"}:
        try:
            prompt = f"""
Tu es un assistant scientifique pour une application de lipidomique cutanée.
Utilise uniquement les données fournies ci-dessous pour répondre à la question utilisateur.

Contexte de base de données :
Projets:
{_format_dataframe_for_prompt(projects_df, ['name','category','status','priority','owner'])}

Échantillons:
{_format_dataframe_for_prompt(samples_df, ['sample_code','project_id','sample_type','status'])}

Batches LC-MS:
{_format_dataframe_for_prompt(batches_df, ['batch_code','project_id','qc_status','method_name'])}

Expériences:
{_format_dataframe_for_prompt(experiments_df, ['name','project_id','status'])}

Références:
{_format_dataframe_for_prompt(references_df, ['title','project_id','year','relevance'])}

Journal:
{_format_dataframe_for_prompt(journal_df, ['entry_date','project_id','entry_type','entry_text'])}

Question utilisateur : {question}

Réponds en français, de façon concise, utile et factuelle. Si certaines informations sont absentes, mentionne-le clairement.
"""
            if provider == "ollama":
                response = client.chat(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "Tu es un assistant scientifique fiable et concis."},
                        {"role": "user", "content": prompt},
                    ],
                )
                return response["message"]["content"]
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "Tu es un assistant scientifique fiable et concis."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content
        except Exception:
            pass

    if selected_projects.empty:
        return "Aucune information de projet n'a été trouvée pour répondre à cette question."

    summary = []
    for _, row in selected_projects.head(3).iterrows():
        summary.append(f"- {row.get('name', '-')} — statut: {row.get('status', '-')}, priorité: {row.get('priority', '-')}")
    if related_samples.empty and related_batches.empty and related_experiments.empty and related_references.empty and related_journal.empty:
        return "Voici ce que je peux dire à partir des données disponibles :\n" + "\n".join(summary)

    return "Voici un résumé utile à partir de votre base locale :\n" + "\n".join(summary)


def provider_message(provider: str | None = None) -> str:
    if provider in (None, "auto"):
        detected_provider, _ = _get_provider()
        provider = detected_provider

    if provider == "ollama":
        return "✅ IA locale via Ollama active."
    if provider == "openai":
        return "✅ IA via OpenAI active."
    return "🧠 Mode local de secours actif. L'assistant fonctionne sans dépendance externe."

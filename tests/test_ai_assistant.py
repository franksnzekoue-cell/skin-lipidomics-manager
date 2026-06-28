import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.ai_assistant import answer_project_questions


def test_answer_project_questions_uses_project_context():
    projects_df = pd.DataFrame([
        {"id": 1, "name": "Projet Alpha", "category": "Céramides", "status": "En cours", "priority": "Haute"}
    ])
    samples_df = pd.DataFrame([
        {"id": 1, "sample_code": "S1", "project_id": 1, "sample_type": "Tape strip", "status": "Disponible"}
    ])
    batches_df = pd.DataFrame([
        {"id": 1, "batch_code": "B1", "project_id": 1, "qc_status": "Conforme"}
    ])

    answer = answer_project_questions(
        "Quel est le statut du projet Projet Alpha ?",
        projects_df=projects_df,
        samples_df=samples_df,
        batches_df=batches_df,
    )

    assert "Projet Alpha" in answer
    assert "En cours" in answer

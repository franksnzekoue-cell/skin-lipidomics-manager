"""
Module de gestion de la base de données SQLite pour l'application
de gestion de projet lipidomique cutanée.
"""
import sqlite3
import pandas as pd
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "lipidomics.db"
DB_PATH.parent.mkdir(exist_ok=True)


def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Crée toutes les tables si elles n'existent pas déjà."""
    conn = get_connection()
    c = conn.cursor()

    # ---------- PROJETS ----------
    c.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,                 -- Céramides / Resolvins / Lipides pro-inflammatoires / Autre
        description TEXT,
        status TEXT DEFAULT 'Planifié', -- Planifié / En cours / En pause / Terminé / Abandonné
        priority TEXT DEFAULT 'Moyenne', -- Haute / Moyenne / Basse
        owner TEXT,
        start_date TEXT,
        due_date TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    # ---------- EXPERIENCES (sous-tâches d'un projet) ----------
    c.execute("""
    CREATE TABLE IF NOT EXISTS experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        objective TEXT,
        status TEXT DEFAULT 'Planifié',
        start_date TEXT,
        due_date TEXT,
        notes TEXT,
        created_at TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
    """)

    # ---------- ECHANTILLONS ----------
    c.execute("""
    CREATE TABLE IF NOT EXISTS samples (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sample_code TEXT UNIQUE NOT NULL,
        project_id INTEGER,
        sample_type TEXT,         -- Peau / Sébum / Biopsie / Tape strip / Cellules / Autre
        subject_id TEXT,
        body_site TEXT,
        collection_method TEXT,
        collection_date TEXT,
        storage_location TEXT,    -- ex: -80°C Congel.A, étagère 3
        storage_temp TEXT,
        quantity TEXT,
        status TEXT DEFAULT 'Disponible',  -- Disponible / Épuisé / Réservé / En analyse
        notes TEXT,
        created_at TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
    )
    """)

    # ---------- BATCHS / ANALYSES LC-MS ----------
    c.execute("""
    CREATE TABLE IF NOT EXISTS lcms_batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_code TEXT UNIQUE NOT NULL,
        project_id INTEGER,
        method_name TEXT,         -- ex: CSH-C18 lipidomique untargeted, ZIC-pHILIC...
        instrument TEXT DEFAULT 'Orbitrap Exploris 480',
        acquisition_mode TEXT,    -- DDA / DIA / PRM / Full MS
        ion_mode TEXT,            -- Positif / Négatif / Polarity switching
        run_date TEXT,
        n_samples INTEGER,
        qc_status TEXT DEFAULT 'En attente', -- En attente / Conforme / Non conforme / À revoir
        qc_notes TEXT,
        operator TEXT,
        notes TEXT,
        created_at TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
    )
    """)

    # ---------- LIEN ECHANTILLON <-> BATCH ----------
    c.execute("""
    CREATE TABLE IF NOT EXISTS batch_samples (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER NOT NULL,
        sample_id INTEGER NOT NULL,
        injection_order INTEGER,
        FOREIGN KEY (batch_id) REFERENCES lcms_batches(id) ON DELETE CASCADE,
        FOREIGN KEY (sample_id) REFERENCES samples(id) ON DELETE CASCADE
    )
    """)

    # ---------- REFERENCES BIBLIOGRAPHIQUES ----------
    c.execute("""
    CREATE TABLE IF NOT EXISTS references_lib (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        title TEXT NOT NULL,
        authors TEXT,
        journal TEXT,
        year INTEGER,
        doi_url TEXT,
        topic_tags TEXT,         -- tags séparés par virgules
        summary TEXT,
        relevance TEXT DEFAULT 'Moyenne', -- Haute / Moyenne / Basse
        created_at TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
    )
    """)

    # ---------- JOURNAL / NOTES TIMELINE ----------
    c.execute("""
    CREATE TABLE IF NOT EXISTS journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        entry_date TEXT,
        entry_text TEXT,
        entry_type TEXT DEFAULT 'Note', -- Note / Résultat / Réunion / Décision
        created_at TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
    )
    """)

    conn.commit()
    conn.close()


def seed_demo_data():
    """Insère des données de démonstration si la base est vide."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM projects")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    now = datetime.now().isoformat()

    projects = [
        ("Profil céramides peau saine vs DA", "Céramides",
         "Caractérisation lipidomique comparative des classes de céramides du stratum corneum entre peau saine et dermatite atopique par tape stripping + LC-HRMS.",
         "En cours", "Haute", "Franks", "2026-01-15", "2026-06-30"),
        ("Resolvins et résolution de l'inflammation cutanée", "Resolvins",
         "Quantification des resolvins D et E (RvD1, RvD2, RvE1) dans les biopsies cutanées par SPE + LC-MS/MS ciblée, en lien avec la résolution de l'inflammation.",
         "Planifié", "Haute", "Franks", "2026-03-01", "2026-09-30"),
        ("Lipides pro-inflammatoires sébum acné", "Lipides pro-inflammatoires",
         "Profilage des oxylipines et leucotriènes dans le sébum de patients acnéiques vs témoins.",
         "Planifié", "Moyenne", "Franks", "2026-04-01", "2026-10-31"),
        ("Biosynthèse verte de céramides par fermentation", "Céramides",
         "Exploration de voies de biosynthèse microbienne pour céramides humains-identiques (CER[NS], CER[NP]).",
         "En pause", "Basse", "Franks", "2026-02-01", "2026-12-31"),
    ]
    c.executemany("""
        INSERT INTO projects (name, category, description, status, priority, owner, start_date, due_date, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], now, now) for p in projects])
    conn.commit()

    experiments = [
        (1, "Tape stripping cohorte DA (n=20)", "Collecter 5 tape strips par site lésionnel/non-lésionnel", "Terminé", "2026-01-20", "2026-02-10"),
        (1, "Extraction MTBE + LC-HRMS", "Extraction lipidique et acquisition Orbitrap Exploris 480", "En cours", "2026-02-15", "2026-04-30"),
        (1, "Analyse statistique différentielle", "MOR et comparaison de classes de céramides entre groupes", "Planifié", "2026-05-01", "2026-06-15"),
        (2, "Mise au point SPE resolvins", "Validation du protocole C18 SPE + lavage hexane", "Planifié", "2026-03-01", "2026-04-15"),
    ]
    c.executemany("""
        INSERT INTO experiments (project_id, name, objective, status, start_date, due_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [(e[0], e[1], e[2], e[3], e[4], e[5], now) for e in experiments])
    conn.commit()

    samples = [
        ("DA-001-LES", 1, "Tape strip", "SUBJ-001", "Avant-bras (lésionnel)", "D-Squame D100", "2026-01-22", "-80°C Congel.A étagère 2", "-80°C", "5 tapes", "Disponible"),
        ("DA-001-NL", 1, "Tape strip", "SUBJ-001", "Avant-bras (non-lésionnel)", "D-Squame D100", "2026-01-22", "-80°C Congel.A étagère 2", "-80°C", "5 tapes", "Disponible"),
        ("DA-002-LES", 1, "Tape strip", "SUBJ-002", "Pli du coude (lésionnel)", "D-Squame D100", "2026-01-23", "-80°C Congel.A étagère 2", "-80°C", "5 tapes", "En analyse"),
        ("SEB-AC-014", 3, "Sébum", "SUBJ-014", "Front", "Sebutape", "2026-01-30", "-80°C Congel.B étagère 1", "-80°C", "2 patches", "Disponible"),
        ("BIOP-HC-005", 2, "Biopsie", "SUBJ-005", "Avant-bras", "Punch biopsy 4mm", "2026-02-02", "-80°C Congel.A étagère 4", "-80°C", "1 biopsie", "Réservé"),
    ]
    c.executemany("""
        INSERT INTO samples (sample_code, project_id, sample_type, subject_id, body_site, collection_method,
                              collection_date, storage_location, storage_temp, quantity, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], s[8], s[9], s[10], now) for s in samples])
    conn.commit()

    batches = [
        ("BATCH-2026-001", 1, "RPLC CSH-C18 untargeted lipidomique", "Orbitrap Exploris 480", "DDA", "Polarity switching", "2026-02-20", 12, "Conforme", "Franks"),
        ("BATCH-2026-002", 2, "HILIC ZIC-pHILIC resolvins ciblé", "Orbitrap Exploris 480", "PRM", "Négatif", "2026-03-10", 8, "En attente", "Franks"),
    ]
    c.executemany("""
        INSERT INTO lcms_batches (batch_code, project_id, method_name, instrument, acquisition_mode, ion_mode,
                                   run_date, n_samples, qc_status, operator, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7], b[8], b[9], now) for b in batches])
    conn.commit()

    refs = [
        (1, "Skin barrier ceramide ratio CER[NdS]/CER[NH] as an aging biomarker", "Various authors",
         "J. Lipid Res.", 2024, "", "céramides,vieillissement,biomarqueur", "Le ratio corrèle avec l'âge et la sécheresse cutanée.", "Haute"),
        (2, "Resolvin D2 maintains skin barrier integrity via Alox15", "Hashimoto et al.",
         "PLoS One", 2018, "", "resolvins,barrière,inflammation", "RvD2 nécessaire à l'intégrité de la barrière cutanée.", "Haute"),
        (1, "Combined LC/MS platform for analysis of all major stratum corneum lipids", "Opálka et al.",
         "BBA Mol. Cell Biol. Lipids", 2021, "", "céramides,LC-MS,méthode", "Méthode combinée pour lipides majeurs du SC.", "Haute"),
    ]
    c.executemany("""
        INSERT INTO references_lib (project_id, title, authors, journal, year, doi_url, topic_tags, summary, relevance, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], now) for r in refs])
    conn.commit()

    journal_entries = [
        (1, "2026-02-10", "Tape stripping terminé pour les 20 sujets de la cohorte DA. Bonne qualité visuelle des prélèvements.", "Résultat"),
        (1, "2026-02-21", "Premier batch LC-MS QC conforme. CV inter-échantillons < 15% sur les pools QC.", "Résultat"),
        (2, "2026-01-10", "Réunion de lancement avec Aude — priorité haute sur les resolvins, lien avec le projet céramides à explorer.", "Réunion"),
    ]
    c.executemany("""
        INSERT INTO journal (project_id, entry_date, entry_text, entry_type, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, [(j[0], j[1], j[2], j[3], now) for j in journal_entries])
    conn.commit()
    conn.close()


def df_query(query, params=None):
    """Exécute une requête SELECT et retourne un DataFrame pandas."""
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params or [])
    conn.close()
    return df


def execute(query, params=None):
    """Exécute une requête INSERT/UPDATE/DELETE."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(query, params or [])
    conn.commit()
    last_id = c.lastrowid
    conn.close()
    return last_id


def executemany(query, params_list):
    conn = get_connection()
    c = conn.cursor()
    c.executemany(query, params_list)
    conn.commit()
    conn.close()

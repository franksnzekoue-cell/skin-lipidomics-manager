# 🧬 Application de gestion de projet — Lipidomique cutanée

Application Streamlit pour gérer vos projets de recherche en lipidomique de la peau
(céramides, resolvins, lipides pro/anti-inflammatoires), avec base de données SQLite intégrée.

---

## 🚀 Installation

### 1. Prérequis
- Python 3.9 ou supérieur

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Lancer l'application

```bash
streamlit run app.py
```

L'application s'ouvre automatiquement dans votre navigateur à l'adresse `http://localhost:8501`.

---

## 📁 Structure du projet

```
lipidomics_app/
├── app.py                      # Page d'accueil / tableau de bord
├── requirements.txt
├── data/
│   └── lipidomics.db           # Base SQLite (créée automatiquement au premier lancement)
├── utils/
│   └── database.py             # Couche d'accès aux données (schéma + requêtes)
└── pages/
    ├── 1_Projets.py            # Gestion des projets et expériences
    ├── 2_Echantillons.py       # Base de données d'échantillons
    ├── 3_Analyses_LCMS.py      # Suivi des batchs LC-MS et QC
    ├── 4_Bibliographie.py      # Références bibliographiques
    └── 5_Journal.py            # Journal de bord chronologique
```

---

## 🧩 Modules disponibles

### 📊 Tableau de bord
Vue d'ensemble avec KPIs (projets actifs, échantillons, batchs, QC en attente, références),
graphiques de répartition par catégorie/statut, et échéances à venir.

### 📁 Projets & Expériences
- Création et suivi de projets (catégories : Céramides, Resolvins, Lipides pro/anti-inflammatoires)
- Statuts : Planifié / En cours / En pause / Terminé / Abandonné
- Priorités : Haute / Moyenne / Basse
- Sous-expériences liées à chaque projet avec leurs propres échéances

### 🧪 Échantillons
- Inventaire complet (tape strips, biopsies, sébum, cellules...)
- Traçabilité : sujet, site anatomique, méthode de prélèvement, lieu de stockage
- Statuts de disponibilité (Disponible / Réservé / En analyse / Épuisé)
- Recherche et filtres multicritères, export CSV

### ⚗️ Analyses LC-MS
- Suivi des batchs d'acquisition (méthode, instrument, mode d'ionisation)
- Statut QC par batch (Conforme / Non conforme / À revoir)
- Association d'échantillons à un batch avec ordre d'injection

### 📚 Bibliographie
- Base de références liées à vos projets
- Tags thématiques, niveau de pertinence, résumés
- Recherche par mot-clé, export CSV

### 📝 Journal de bord
- Notes chronologiques (résultats, réunions, décisions)
- Filtrable par projet et par type d'entrée

---

## 💾 Données de démonstration

Au premier lancement, l'application insère automatiquement des données d'exemple
(4 projets, 4 expériences, 5 échantillons, 2 batchs LC-MS, 3 références, 3 entrées de journal)
pour vous permettre d'explorer immédiatement toutes les fonctionnalités.

Pour repartir d'une base vierge, supprimez simplement le fichier `data/lipidomics.db`
puis relancez l'application.

---

## 🛠️ Personnalisation

- **Catégories de projet** : modifiables dans `pages/1_Projets.py` (variable `CATEGORIES`)
- **Types d'échantillons** : modifiables dans `pages/2_Echantillons.py` (variable `SAMPLE_TYPES`)
- **Méthodes/instruments LC-MS** : champs libres, adaptables à votre Orbitrap Exploris 480
  ou tout autre instrument

---

## 📌 Notes techniques

- Base de données : SQLite (fichier local, aucune installation de serveur requise)
- Les clés étrangères assurent la cohérence (suppression en cascade des expériences
  si un projet est supprimé, etc.)
- L'application est multi-pages native Streamlit (dossier `pages/`)

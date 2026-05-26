# 📍 SODIGAZ - Dedicated Locator Backend Microservice

Ce dossier contient un **microservice backend dédié et ultra-léger** développé spécifiquement pour l'application **Sodigaz Locator** (Flutter) et son panel d'administration **Locator Admin Panel** (React).

---

## 🚀 Architecture & Fonctionnalités

*   **FastAPI & Python 3** : Performance maximale, validation automatique des types via Pydantic, et documentation Swagger interactive intégrée.
*   **Base de données SQLite autonome (`locator.db`)** : Totalement découplée de la base de données principale de l'application pour une flexibilité et des performances optimales lors des requêtes géographiques fréquentes.
*   **Sécurité JWT autonome** : Système d'authentification robuste (`OAuth2PasswordBearer` avec jetons signés HS256).
*   **Importateur CSV Intelligent** : Intègre le parseur gérant le format classique de tableur ET le format d'exportation Google Maps basé sur les **Plus Codes** (nécessite `openlocationcode`).
*   **Suivi & Statistiques en temps réel** : Enregistrement des sessions d'utilisation et de l'historique des requêtes de localisation géographiques des utilisateurs mobiles.

---

## 🛠️ Guide d'installation et de démarrage rapide

### 1. Installation des dépendances
Ouvrez votre terminal dans ce dossier et exécutez :
```bash
pip install -r requirements.txt
```

### 2. Initialisation & Chargement des données (Seeding)
Exécutez le script d'initialisation pour créer la base de données SQLite localement, ajouter les identifiants administrateur par défaut et charger automatiquement les **75 dépôts/points de vente réels** à partir du fichier `location.csv` de l'application mobile :
```bash
python seed_locator_data.py
```

### 3. Lancement du serveur local
Démarrez le microservice sur un port dédié (par exemple, le port **`8002`**) :
```bash
uvicorn app.main:app --reload --port 8002
```
*   **Documentation interactive Swagger UI** : Accessible à l'adresse [http://127.0.0.1:8002/docs](http://127.0.0.1:8002/docs)
*   **Documentation alternative Redoc** : Accessible à l'adresse [http://127.0.0.1:8002/redoc](http://127.0.0.1:8002/redoc)

---

## 🔑 Identifiants d'Administration par défaut

Ces identifiants sont automatiquement insérés par le script de seeding et vous permettent de vous connecter immédiatement au panel d'administration :
*   **Email / Identifiant** : `admin@sodigaz.com`
*   **Mot de passe** : `admin123`

---

## 📋 Documentation des API exposées

Tous les endpoints sont préfixés par `/api` :

| Méthode | Chemin | Rôle | Accès |
| :--- | :--- | :--- | :--- |
| **POST** | `/api/auth/login` | Authentification (retourne un Token JWT) | Public |
| **GET** | `/api/auth/me` | Profil de l'utilisateur connecté | Authentifié |
| **POST** | `/api/auth/change-password` | Modification du mot de passe admin | Authentifié |
| **GET** | `/api/user/public/depots/map` | Récupération des dépôts filtrés par ville/quartier/recherche | Public |
| **GET** | `/api/user/public/depots/{id}` | Coordonnées et détails d'un dépôt spécifique | Public |
| **GET** | `/api/admin/depots` | Liste complète de tous les dépôts | Administrateur |
| **POST** | `/api/admin/depots` | Création manuelle d'un nouveau point de vente | Administrateur |
| **PUT** | `/api/admin/depots/{id}` | Mise à jour des informations ou des stocks d'un dépôt | Administrateur |
| **DELETE** | `/api/admin/depots/{id}` | Suppression définitive d'un point de vente | Administrateur |
| **POST** | `/api/admin/depots/import-csv` | Importation en masse (Upload de fichier CSV) | Administrateur |
| **GET** | `/api/locator/stats` | Données statistiques d'usage pour le tableau de bord | Administrateur |
| **POST** | `/api/locator/sessions` | Signalement du début d'une session mobile de recherche | Public |
| **POST** | `/api/locator/sessions/{id}/end` | Signalement de la fin d'une session | Public |
| **POST** | `/api/locator/locations` | Enregistrement d'une requête GPS utilisateur (pour historique) | Public |
| **GET** | `/api/locator/sessions` | Liste des sessions utilisateurs loguées | Administrateur |
| **GET** | `/api/locator/history` | Historique de positionnement géographique enregistré | Administrateur |

---

## 🗂️ Structure du Projet

```text
backend-locator/
│
├── app/
│   ├── __init__.py
│   ├── database.py          # Connexion SQLite locale
│   ├── models.py            # Modèles SQLAlchemy (User, Depot, Session, Location)
│   ├── schemas.py           # Validateurs de données Pydantic
│   ├── auth.py              # Système de sécurité & vérification JWT
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py          # Routes d'authentification
│   │   └── depots.py        # Routes logistiques, géographiques et d'administration
│   │
│   └── main.py              # Point d'entrée de l'application & CORS
│
├── requirements.txt         # Dépendances Python requises
├── seed_locator_data.py     # Script d'initialisation et seeding
├── import_locator_csv.py    # Algorithme d'importation CSV intelligent
└── locator.db               # Base de données SQLite locale (générée après seeding)
```

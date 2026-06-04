# Games Comparator


## Prerequis

- Python 3.10+
- Node.js 18+
- MySQL 8+

---

## Installation

### 1. Cloner le depot

```bash
git clone <url-du-repo>
cd Games-Comparator
```

### 2. Variables d environnement

```bash
cp .env.example .env
```

Edite `.env` avec tes identifiants MySQL :

```env
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/games_comparator

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=user
MYSQL_PASSWORD=password
MYSQL_DATABASE=games_comparator
```

### 3. Creer la base de donnees MySQL

Connecte-toi a MySQL et cree la base :

```sql
CREATE DATABASE games_comparator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. Environnement Python

```bash
python -m venv .venv
```

**Windows**
```bash
.venv\Scripts\activate
```


```bash
pip install -r requirements.txt
```

### 5. Initialiser les tables

```bash
python -c "from database import init_db; init_db()"
```

Cela cree les tables `games` et `prices` dans la base MySQL.

### 6. API Node.js

```bash
cd api
npm install
```


## Structure du projet

```
Games-Comparator/
+-- database/         # Modeles SQLAlchemy + CRUD (ecriture scrapers)
+-- scrapers/         # Un scraper par site
+-- api/              # API Express - lit la DB MySQL
+-- front/            # React - consomme l API
+-- run_scrapers.py   # Lance tous les scrapers
+-- .env              # Variables d environnement (non versionne)
+-- .env.example      # Template a copier
+-- requirements.txt
```

## Endpoints API

| Methode | URL | Description |
|---|---|---|
| GET | `/api/games?q=...&platform=...` | Recherche de jeux avec meilleur prix |
| GET | `/api/games/:id` | Detail d un jeu + prix par source |
| GET | `/api/games/:id/history?source=...` | Historique des prix pour une source |

## Front (interface)

Le dossier `front/` contient l'application React qui consomme l'API Express située dans `api/`.

Installation et lancement (depuis la racine du projet) :

```bash
cd front
npm install
npm run dev
```

Si l'application nécessite des variables d'environnement, créez un fichier `.env` dans `front/` ou adaptez la configuration selon `package.json`.

Pour construire l'application pour la production :

```bash
cd front
npm run build
```
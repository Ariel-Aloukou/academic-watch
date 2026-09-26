# Fonctionnement de Python et GitHub Actions

## 1. Objectif

Ce document explique comment Python et GitHub Actions vont fonctionner ensemble dans Academic Watch.

Le principe est simple :

> Python fait le travail. GitHub Actions lance automatiquement Python.

---

# 2. Rôle de Python

Python constitue le cœur du programme.

Il s'occupe de :

```text
Récupérer
   ↓
Analyser
   ↓
Filtrer
   ↓
Comparer
   ↓
Sauvegarder
   ↓
Notifier
```

Le programme peut être exécuté localement avec :

```bash
python src/main.py
```

---

# 3. Rôle de GitHub

GitHub sert principalement à :

* stocker le code ;
* conserver l'historique du projet ;
* permettre le travail avec Git ;
* exécuter automatiquement le programme avec GitHub Actions.

GitHub n'est donc pas le programme de veille lui-même.

---

# 4. Rôle de GitHub Actions

GitHub Actions est le système d'automatisation.

Il peut exécuter le programme :

* manuellement ;
* à une heure donnée ;
* régulièrement selon un calendrier.

Exemple :

```text
Chaque jour
    ↓
GitHub Actions démarre
    ↓
Python est installé
    ↓
Les dépendances sont installées
    ↓
main.py est exécuté
```

---

# 5. Workflow GitHub Actions

Le fichier sera :

```text
.github/workflows/veille.yml
```

Structure minimale :

```yaml
name: Academic Watch

on:
  workflow_dispatch:

  schedule:
    - cron: "0 7 * * *"

jobs:
  veille:
    runs-on: ubuntu-latest

    steps:

      - name: Télécharger le projet
        uses: actions/checkout@v4

      - name: Installer Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Installer les dépendances
        run: pip install -r requirements.txt

      - name: Exécuter la veille
        run: python src/main.py
```

---

# 6. Exécution manuelle

Le workflow doit contenir :

```yaml
workflow_dispatch:
```

Cela permet de lancer manuellement le programme depuis GitHub.

C'est important pendant le développement.

On peut ainsi tester :

```text
Modifier le code
      ↓
Push GitHub
      ↓
Lancer le workflow
      ↓
Observer le résultat
```

---

# 7. Exécution automatique

La section :

```yaml
schedule:
```

permet d'exécuter automatiquement le programme.

Exemple :

```yaml
schedule:
  - cron: "0 7 * * *"
```

Cela signifie une exécution quotidienne à 07:00 selon le fuseau utilisé par GitHub Actions.

Le système de planification utilise le format **cron** (une notation permettant de définir des horaires automatiquement).

---

# 8. Attention au fuseau horaire

GitHub Actions utilise généralement UTC pour les horaires cron.

La Côte d'Ivoire est également en UTC.

Ainsi :

```text
07:00 UTC
=
07:00 Côte d'Ivoire
```

Si le projet est utilisé depuis un autre pays, il faudra tenir compte de son fuseau horaire.

---

# 9. Installation des dépendances

Les bibliothèques Python utilisées seront indiquées dans :

```text
requirements.txt
```

Exemple :

```text
requests
beautifulsoup4
```

GitHub Actions exécutera :

```bash
pip install -r requirements.txt
```

Le projet doit éviter d'avoir trop de dépendances.

---

# 10. Exécution locale

Avant d'utiliser GitHub Actions, le programme doit fonctionner localement.

Commande :

```bash
python src/main.py
```

Pour installer les dépendances :

```bash
pip install -r requirements.txt
```

Pour vérifier :

```bash
pip list
```

---

# 11. Git

Git permet de suivre les modifications.

Exemple :

```bash
git add .
git commit -m "Ajout de la collecte des opportunités"
git push
```

Après le `push`, GitHub reçoit les modifications.

Si le workflow est configuré pour être déclenché par un `push`, GitHub Actions peut alors lancer automatiquement le programme.

---

# 12. Variables secrètes

Certaines informations ne doivent jamais être placées directement dans le code.

Exemples :

```text
TOKEN_TELEGRAM
EMAIL_PASSWORD
API_KEY
```

Elles doivent être enregistrées dans les **GitHub Secrets**.

Le code pourra ensuite les récupérer depuis les variables d'environnement.

Exemple Python :

```python
import os

token = os.getenv("TELEGRAM_TOKEN")
```

Il ne faut jamais faire :

```python
token = "123456789abcdef"
```

dans le dépôt GitHub.

---

# 13. Flux complet

Le fonctionnement final sera :

```text
                 GITHUB
                    │
                    ▼
          GitHub Actions
                    │
                    ▼
              Environnement
                 Python
                    │
                    ▼
              src/main.py
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
      scraper    filters   storage
          │         │         │
          └─────────┼─────────┘
                    ▼
               notifier
                    │
                    ▼
              Notification
                    │
                    ▼
                 Utilisateur
```

---

# 14. Ce qui doit rester local au début

Pendant le développement, les tests doivent être réalisés localement.

Exemple :

```text
Modifier scraper.py
       ↓
Tester localement
       ↓
Corriger
       ↓
Tester encore
       ↓
git commit
       ↓
git push
       ↓
Tester GitHub Actions
```

Il est inutile de faire tourner GitHub Actions à chaque petite erreur de syntaxe. L'humanité a déjà suffisamment souffert.

---

# 15. Gestion des données

Les données du programme seront initialement conservées dans des fichiers JSON.

Exemple :

```text
data/
├── opportunities.json
└── seen.json
```

`opportunities.json` contient les opportunités collectées.

`seen.json` permet de savoir quelles opportunités ont déjà été rencontrées.

---

# 16. Problème important avec GitHub Actions

GitHub Actions utilise des environnements temporaires.

Cela signifie qu'un fichier créé pendant une exécution n'est pas automatiquement conservé pour la prochaine exécution.

Le projet devra donc prévoir une méthode pour conserver les données importantes.

Pour la première version, une solution simple pourra être utilisée :

```text
Git
 ↓
fichiers JSON
 ↓
commit automatique
 ↓
push
```

Une autre possibilité sera d'utiliser les **GitHub Actions Artifacts** (fichiers conservés par GitHub après une exécution).

La méthode définitive sera choisie lorsque la sauvegarde sera développée.

---

# 17. Principe de sécurité

Le dépôt ne doit jamais contenir :

```text
mot de passe
token
clé API
identifiants
```

Les secrets doivent être stockés dans GitHub.

Le fichier :

```text
.gitignore
```

doit également empêcher l'envoi de fichiers locaux inutiles.

---

# 18. Résultat attendu

Une fois la V1.0 terminée, le fonctionnement sera :

```text
07:00
  ↓
GitHub Actions
  ↓
Python
  ↓
Recherche des sources
  ↓
Extraction
  ↓
Filtrage
  ↓
Comparaison avec l'historique
  ↓
Nouvelles opportunités
  ↓
Sauvegarde
  ↓
Notification
```

Et l'utilisateur n'aura plus besoin de lancer manuellement Python tous les jours.

---

# 19. Règle de développement

Le projet doit toujours pouvoir être lancé localement avec :

```bash
python src/main.py
```

GitHub Actions doit seulement automatiser cette exécution.

Il ne faut donc jamais construire une logique qui fonctionne uniquement dans GitHub Actions.

Le principe est :

```text
LOCAL
Python fonctionne
    ↓
GITHUB
Le code est stocké
    ↓
ACTIONS
Python est exécuté automatiquement
```

C'est cette séparation qui rend le projet simple à comprendre et à maintenir.

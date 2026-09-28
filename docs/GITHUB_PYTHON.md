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

**Cette structure minimale ne suffit plus.** Elle était correcte au moment où
elle a été écrite, et elle est devenue fausse : il lui manque l'étape qui
enregistre les résultats.

Un runner GitHub Actions est une machine jetable, détruite à la fin de
l'exécution. Ce workflow écrit 69 fiches dans `data/`, puis la machine disparaît
avec. La veille fonctionnerait en local et perdrait toute mémoire dès le
premier run automatique. C'est le défaut que le workflow réel corrige, avec
l'étape `Enregistrer les résultats`, la permission `contents: write`,
`fetch-depth: 0` sans lequel le rebase de sécurité échoue, et
`timeout-minutes: 30` sans lequel un run bloqué resterait en cours pendant les
360 minutes du défaut de GitHub.

Le workflow à utiliser est `.github/workflows/veille.yml`, et le détail de chaque
choix est dans `docs/VERSIONS.md` V0.8 pour l'exécution et V0.9 pour la
planification. `tests/test_workflow.py` en vérifie les invariants, parce que ce
fichier est le seul du projet qui ne peut pas être lancé chez soi.

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

## Ce que GitHub décide seul

Deux règles de la plateforme s'appliquent et ne se configurent pas.

**La planification ne s'exécute que sur la branche par défaut.** Le workflow est
écrit dans `main`, donc c'est déjà le bon cas. Le modifier dans une branche ne
change rien tant qu'il n'est pas poussé sur `main`.

**Un dépôt public sans activité pendant soixante jours voit sa planification
désactivée.** GitHub le formule ainsi : *In a public repository, scheduled
workflows are automatically disabled when no repository activity has occurred in
60 days.* La règle ne concerne que les dépôts publics.

Academic Watch ne produit pas d'activité quotidienne : un jour sans nouveauté ne
crée aucun commit, par la décision de la V0.8. Une période de soixante jours sans
changement des données compterait donc comme une période sans activité.

Si la planification s'arrête un jour, elle se réactive dans l'onglet **Actions** :
sélectionner **Academic Watch** dans la barre latérale, puis **Enable workflow**.
La même opération existe en ligne de commande :

```shell
gh workflow enable Academic Watch
```

Le moyen de le savoir reste le même que pour le reste : l'onglet Actions montre
les exécutions, et une journée sans exécution se remarque à l'absence de ligne.

Le détail de la fréquence choisie est dans `docs/VERSIONS.md` V0.9.

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

### Les six secrets de la veille

Voici les six variables que le programme attend, et les valeurs exactes qu'il
faut mettre. Les noms ne sont pas libres : ce sont ceux que `src/notifier.py`
lit, et un test les compare avec le workflow. **Les six ensemble, ou pas du
tout** — il en manque une, le programme reste en console et le dit, ce qui est
le mode par défaut.

| Nom | Ce qu'on y met, pour une adresse Outlook | Exemple |
| --- | --------------------------------------- | ------- |
| `SMTP_HOST` | le serveur d'envoi | `smtp-mail.outlook.com` |
| `SMTP_PORT` | le port de soumission, **en texte** | `587` |
| `SMTP_USER` | l'adresse Outlook, en clair | `etudiant@outlook.com` |
| `SMTP_PASSWORD` | le mot de passe d'application, **pas** celui du compte | 16 caractères |
| `EMAIL_FROM` | l'adresse qui envoie, la même que `SMTP_USER` | `etudiant@outlook.com` |
| `EMAIL_TO` | l'adresse qui reçoit, où la vôtre | `etudiant@outlook.com` |

### Où obtenir un mot de passe d'application

C'est le point qui bloque le plus souvent, parce que le mot de passe du compte
ne fonctionne pas — Microsoft l'a désactivé pour les applications qui ne savent
pas gérer la double authentification.

1. Sur [account.microsoft.com](https://account.microsoft.com), se connecter
   avec l'adresse Outlook et activer la double authentification ;
2. Aller dans **Sécurité > Mot de passe d'application**, en choisir un, le
   nommer, et le valider par code postal ;
3. Copier le mot de passe de 16 caractères. C'est le seul mot de passe qui
   fonctionne, et Microsoft ne l'affiche qu'une seule fois.

Sans double authentification activée, la page des mots de passe d'application
n'existe pas. Ce n'est pas une panne : c'est la conception de Microsoft.

### Où les entrer dans le dépôt

Dans le dépôt : **Settings > Secrets and variables > Actions > New repository
secret**, une fois par variable, avec le nom exact du tableau ci-dessus. Six
secrets, six fois l'opération.

Ces noms de menus sont ceux de l'interface de GitHub, qui est en anglais. Ils
ne se trouvent pas dans une version française, et c'est le premier endroit où
l'on peut bloquer un après-midi.

Ils sont passés au programme par `env`, jamais dans la ligne de commande, et le
workflow fonctionne sans aucun d'eux. Pour vérifier, lancer le workflow
**manuellement** : le résumé d'étape dit `Notification : email envoyé ...` ou
nomme le secret qui manque.

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

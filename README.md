# Academic Watch

Veille académique : recherche de programmes de Master et de financements
correspondant à un profil, sur des sources officielles.

Le projet en est à la **V0.2** : deux sources sont extraites, le filtrage n'existe
pas encore. Tout ce qui n'est pas fait est indiqué comme tel ci-dessous.

## État réel

| Version | Objet | État |
| ------- | ----- | ---- |
| V0.1 | Chargement et affichage du profil | fait |
| V0.2 | Collecte et extraction des sources | fait, 2 sources, 46 opportunités |
| V0.3 | Filtrage selon le profil | à faire |
| V0.4 | Sauvegarde des résultats | à faire |
| V0.5 | Détection des nouveautés | à faire |
| V0.6 | Notification | à faire |
| V0.7 | Passage à l'échelle | à faire |

Le programme fonctionne **en ligne uniquement** : il télécharge les pages au
moment de l'exécution et n'écrit rien. Aucune donnée n'est conservée d'une
exécution à l'autre pour l'instant.

## Architecture

```
academic-watch/
├── .github/
│   └── workflows/
│       └── veille.yml      # Exécution planifiée (07:00 UTC) - non branchée
├── config/
│   ├── profile.json        # Tes critères de recherche
│   ├── sources.json        # Registre des sources à surveiller
│   └── selectors.json      # Règles d'extraction par source
├── data/
│   ├── opportunities.json  # Opportunités détectées (vide pour l'instant)
│   └── seen.json           # IDs déjà traités (vide pour l'instant)
├── docs/
│   ├── README.md           # Cahier des charges
│   ├── VERSIONS.md         # Feuille de route version par version
│   ├── SOURCES.md          # État réel de chaque source, mesuré
│   └── GITHUB_PYTHON.md    # Mise en ligne
├── src/
│   ├── main.py             # Point d'entrée : orchestration
│   ├── models.py           # Format commun Opportunity
│   ├── scraper.py          # Validation des sources + extraction
│   ├── filters.py          # Vide - V0.3
│   ├── storage.py          # Vide - V0.4
│   └── notifier.py         # Vide - V0.6
├── requirements.txt
├── README.md
└── .gitignore
```

Deux fichiers de configuration, deux rôles : `sources.json` dit **quelles**
sources faire partie de la veille, `selectors.json` dit **où** trouver les
informations dans chaque page. C'est ce qui permet d'inscrire une source dans
le cahier des charges avant de savoir la lire, et d'ajouter une source sans
modifier le code.

## Installation

```bash
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Utilisation

Collecter et afficher les opportunités :

```bash
python src/main.py
```

Vérifier que les sources du registre sont réellement lisibles :

```bash
python src/scraper.py
```

La seconde commande teste chaque URL déclarée et indique si elle contient une
vraie liste d'opportunités, un simple formulaire de recherche, ou si elle est
bloquée. Elle n'écrit rien. Le détail des verdicts est dans `docs/SOURCES.md`.

## Sources

18 sources sont déclarées, réparties en trois catégories : sites officiels
d'universités, organismes officiels de bourses, portails spécialisés.

Deux sont aujourd'hui exploitées :

* **TUM** (Allemagne), 10 programmes ;
* **KAIST** (Corée du Sud), 36 programmes.

Les 16 autres sont décidées et documentées, mais pas encore lues. La majorité
sont des portails de recherche dont les résultats ne sont pas dans le HTML :
elles ne peuvent pas être extraites avec une simple requête. `docs/SOURCES.md`
dit lesquelles, et pourquoi.

## Règles de conception

* **Ne rien inventer.** Une information absente d'une page reste absente du
  résultat, elle n'est pas devinée.
* **Une version fonctionne avant la suivante.** Le filtrage n'a pas été écrit
  avant que l'extraction soit fiable, pour ne pas filtrer des données vides.
* **Une source non lisible est signalée, pas contournée.** Voir
  `docs/SOURCES.md` §1.3.

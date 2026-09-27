# Academic Watch

Veille académique : recherche de programmes de Master et de financements
correspondant à un profil, sur des sources officielles.

Le projet en est à la **V0.4** : quatre sources sont extraites, la correspondance
avec le profil classe les opportunités et explique pourquoi, et le résultat est
écrit sur disque. Sur les 69 opportunités collectées, 9 correspondent au profil.
Tout ce qui n'est pas fait est indiqué comme tel ci-dessous.

## État réel

| Version | Objet | État |
| ------- | ----- | ---- |
| V0.1 | Chargement et affichage du profil | fait |
| V0.2 | Collecte et extraction des sources | fait, 4 sources, 69 opportunités |
| V0.3 | Correspondance avec le profil | fait, 9 retenues sur 69 |
| V0.4 | Sauvegarde des résultats | fait, 69 fiches et 9 déjà vues |
| V0.5 | Détection des nouveautés | à faire |
| V0.6 | Notification | à faire |
| V0.7 | Passage à l'échelle | à faire |
| V0.8 | GitHub Actions | écrit et testé, **jamais exécuté sur GitHub** |

Deux critères de la V0.3 ne sont pas implémentés, et ne le sont pas par oubli :
aucune source ne renseigne de langue d'enseignement, et aucune ne publie de
date limite. C'est vérifié page par page, pas supposé ; `docs/SOURCES.md` §6.3
distingue ce qui a été mesuré négatif de ce qui n'a pas pu être lu.

Le programme télécharge les pages au moment de l'exécution et **écrit deux
fichiers** dans `data/` : l'historique complet et la mémoire de ce qui a déjà
été montré. Relancer le programme ne signale plus rien de neuf tant que les
sources n'ont pas changé.

## Exécution automatique

Le workflow `.github/workflows/veille.yml` collecte chaque jour à 07:00 UTC,
puis **committe `data/`**. Ce commit est indispensable : un runner GitHub
Actions est une machine jetable, et sans lui la veille fonctionnerait en local
et perdrait toute mémoire dès le premier run automatique.

Un commit n'est fait que si `data/` a réellement changé, donc une journée sans
nouveauté ne produit rien dans l'historique du dépôt. Le message dit ce qui a
été trouvé, et le résultat est affiché en tête de run.

Le workflow est écrit et testé, mais **il n'a pas encore été exécuté sur
GitHub**. C'est le seul endroit du projet qui ne peut pas être validé en local.
Il reste à l'activer, ou à attendre le prochain 07:00 UTC. Le détail des
choix est dans `docs/VERSIONS.md` V0.8.

## Architecture

```
academic-watch/
├── .github/
│   └── workflows/
│       └── veille.yml      # Exécution planifiée (07:00 UTC) + commit des données
├── config/
│   ├── profile.json        # Tes critères de recherche
│   ├── sources.json        # Registre des sources à surveiller
│   └── selectors.json      # Règles d'extraction par source
├── data/
│   ├── opportunities.json  # Historique complet des opportunités, 69 fiches
│   └── seen.json           # Identités déjà montrées, 9 entrées
├── docs/
│   ├── README.md           # Cahier des charges
│   ├── VERSIONS.md         # Feuille de route version par version
│   ├── SOURCES.md          # État réel de chaque source, mesuré
│   └── GITHUB_PYTHON.md    # Mise en ligne
├── src/
│   ├── main.py             # Point d'entrée : orchestration
│   ├── models.py           # Format commun Opportunity
│   ├── scraper.py          # Validation des sources + extraction
│   ├── parsers/
│   │   └── kaist_scholarship.py  # Parseur dédié, structure non exprimable en CSS
│   ├── matches.py          # Correspondance avec le profil, score, raisons
│   ├── storage.py          # Historique JSON et détection des doublons
│   └── notifier.py         # Vide - V0.6
├── tests/                  # 231 tests, lancés par pytest
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
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

Pour DEVELOPPER, il faut aussi les dépendances de test :

```bash
pip install -r requirements-dev.txt
```

Elles sont à part, et c'est volontaire : le programme n'a pas besoin de pytest
pour fonctionner, et le workflow l'installe donc séparément.

## Tests

```bash
python -m pytest
```

231 tests, environ deux secondes, **sans accès au réseau**. Ils vérifient la
sauvegarde, la correspondance avec le profil, la cohérence des deux fichiers de
`data/`, les choix écrits du workflow, et l'encodage des fichiers du dépôt.

Aucun test ne dépend d'une page vivante. Ce qui dépend d'un site est vérifié à
la main et écrit dans `docs/SOURCES.md` : un test qui dépend d'un site étranger
échoue pour une raison qui n'a rien à voir avec le code.

Ils sont exécutés par GitHub Actions **avant** chaque collecte. Une veille qui
écrit des données fausses ne se voit pas ; une veille arrêtée, si. Le runner
signale l'échec, donc l'arrêt reste visible.

Mettre les tests dans le dépôt a immédiatement produit un défaut que la
relecture n'avait pas vu : une bourse qui écrit « Open to international
students » était comptée comme réservée aux nationaux, parce que « national
student » en est une sous-chaîne. Elle perdait ses 25 points et était écartée.
Les trois bourses de KAIST y échappaient par chance, la page écrivant
« applicants ». Le détail est dans `docs/VERSIONS.md` V0.3 et V0.4.

## Utilisation

Collecter et afficher les opportunités :

```bash
python src/main.py
```

Chaque opportunité est affichée avec son score et la raison de chaque critère,
et `[OUI]` ou `[non]` indique si elle est retenue. Un programme et une bourse
ne sont pas mesurés de la même façon : un programme se juge sur sa matière, une
bourse sur qui peut en bénéficier. Les détails sont dans `docs/VERSIONS.md`
V0.3.

Cette commande **écrit deux fichiers** dans `data/` :

* `opportunities.json`, l'historique complet. Une opportunité déjà vue garde sa
  date de première apparition, et ses données sont rafraîchies ;
* `seen.json`, la mémoire de ce qui a déjà été montré.

Lancer la commande une seconde fois de suite affiche donc `0 nouvelles depuis la
dernière exécution`, et ne réécrit pas les fichiers : rien n'ayant changé, il
n'y a rien à écrire. C'est ce qui permettra plus tard à GitHub Actions de ne
commiter que lorsqu'il y a effectivement quelque chose de nouveau.

Les deux fichiers sont versionnés, parce qu'une veille qui recommence à zéro
chaque jour ne sert à rien. Pour repartir de zéro, les vider ou les supprimer —
en sachant que tout sera alors signalé comme nouveau.

Vérifier que les sources du registre sont réellement lisibles :

```bash
python src/scraper.py
```

La seconde commande teste chaque URL déclarée et indique si elle contient une
vraie liste d'opportunités, un simple formulaire de recherche, ou si elle est
bloquée. Elle n'écrit rien. Le détail des verdicts est dans `docs/SOURCES.md`.

## Sources

19 sources sont déclarées, réparties en trois catégories : sites officiels
d'universités, organismes officiels de bourses, portails spécialisés.

Quatre sont aujourd'hui exploitées :

* **TUM** (Allemagne), 10 programmes ;
* **KAIST – Explore Programs** (Corée du Sud), 36 programmes ;
* **KAIST – Scholarship** (Corée du Sud), 3 bourses ;
* **EACEA – catalogue Erasmus Mundus** (Union européenne), 20 programmes.

Une seule des 20 opportunités EACEA correspond au profil, « Master's Programme
in Cybersecurity and Assurance », en correspondance directe. Ce catalogue est
un annuaire large, pas une source de cybersécurité : le résultat est le bon
résultat, pas une déception.

Les 15 autres sont décidées et documentées, mais pas encore lues. La majorité
sont des portails de recherche dont les résultats ne sont pas dans le HTML :
elles ne peuvent pas être extraites avec une simple requête. `docs/SOURCES.md`
dit lesquelles, et pourquoi.

## Règles de conception

* **Ne rien inventer.** Une information absente d'une page reste absente du
  résultat, elle n'est pas devinée.
* **Une version fonctionne avant la suivante.** La correspondance n'a pas été
  écrite avant que l'extraction soit fiable, pour ne pas filtrer des données
  vides.
* **Le profil ne devient pas un miroir des sites.** Les domaines de
  `config/profile.json` restent la définition de l'objectif. Le vocabulaire que
  les universités utilisent pour le désigner est porté par `related_terms`,
  avec un niveau de proximité explicite. Voir `docs/README.md` §6
  (`src/matches.py`) et `docs/VERSIONS.md` V0.3.
* **Une source non lisible est signalée, pas contournée.** Voir
  `docs/SOURCES.md` §1.3.

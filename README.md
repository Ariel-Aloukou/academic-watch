# Academic Watch

Veille académique : recherche de programmes de Master et de financements
correspondant à un profil, sur des sources officielles.

Le projet en est à la **V0.10** : quatre sources sont extraites, la correspondance
avec le profil classe les opportunités et explique pourquoi, le résultat est
écrit sur disque, le programme **ne signale que ce qui n'a pas encore été
montré**, et cette veille tourne seule chaque jour à 07:00 UTC. Sur les 69
opportunités collectées, 9 correspondent au profil. Le bulletin part par email
et par un salon Discord, selon ce qui est configuré.
Tout ce qui n'est pas fait est indiqué comme tel ci-dessous.

## État réel

| Version | Objet | État |
| ------- | ----- | ---- |
| V0.1 | Chargement et affichage du profil | fait |
| V0.2 | Collecte et extraction des sources | fait, 4 sources, 69 opportunités |
| V0.3 | Correspondance avec le profil | fait, 9 retenues sur 69 |
| V0.4 | Sauvegarde des résultats | fait, 69 fiches et 9 déjà vues |
| V0.5 | Détection des nouveautés | fait, 9 signalées puis 0 au run suivant |
| V0.6 | Notification par email | fait, 6 secrets optionnels |
| V0.7 | Plusieurs sources | fait, 4 sources sans toucher au programme |
| V0.8 | GitHub Actions | fait, **jamais exécuté sur GitHub** |
| V0.9 | Veille automatique | fait, planification et plafond d'exécution |
| V0.10 | Second canal de notification | fait, webhook Discord, **jamais exécuté sur GitHub** |

Deux critères de la V0.3 ne sont pas implémentés, et ne le sont pas par oubli :
aucune source ne renseigne de langue d'enseignement, et aucune ne publie de
date limite. C'est vérifié page par page, pas supposé ; `docs/SOURCES.md` §6.3
distingue ce qui a été mesuré négatif de ce qui n'a pas pu être lu.

Le programme télécharge les pages au moment de l'exécution et **écrit deux
fichiers** dans `data/` : l'historique complet et la mémoire de ce qui a déjà
été montré. Il n'affiche plus que les opportunités retenues qui n'ont pas
encore été montrées, et celles dont la page a changé depuis la dernière
exécution. Relancer le programme ne signale plus rien tant que les sources
n'ont pas changé : le cas courant est un « rien de nouveau » en trois lignes.

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
choix est dans `docs/VERSIONS.md` V0.8 pour l'exécution et V0.9 pour la
planification.

Une règle de GitHub ne se configure pas et vaut mieux être connue : la
planification est désactivée automatiquement sur un dépôt **public** sans
activité pendant soixante jours. Comme un jour sans nouveauté ne crée aucun
commit, une longue période calme compte comme une période sans activité. La
réactivation se fait dans l'onglet Actions, ou par
`gh workflow enable Academic Watch`.

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
│   ├── scraper.py          # Validation, extraction, rapport par source
│   ├── parsers/
│   │   └── kaist_scholarship.py  # Parseur dédié, structure non exprimable en CSS
│   ├── matches.py          # Correspondance avec le profil, score, raisons
│   ├── storage.py          # Historique JSON et détection des doublons
│   └── notifier.py         # Bulletin : rendu une fois, console + email
├── tests/                  # 358 tests, lancés par pytest
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

Ce que la veille lit au 28 septembre 2026 : **4 sources sur 19 inscrites**, dont
4 sur 16 activées. Les 15 autres ont une URL vérifiée et pas de sélecteurs
écrits, et c'est un état normal, pas un oubli — sauf pour celles qui avaient des
sélecteurs et n'en produisent plus, et c'est précisément ce que la veille
signale désormais, source par source, dans son journal et dans le résumé d'étape
du workflow.

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

390 tests, environ cinq secondes, **sans accès au réseau**. Ils vérifient la
sauvegarde, la correspondance avec le profil, ce que la veille affiche, la
cohérence des deux fichiers de `data/`, le découpage du bulletin pour Discord,
les choix écrits du workflow, et l'encodage des fichiers du dépôt.

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

Le programme n'affiche **que ce qu'il faut signaler** : les opportunités
retenues jamais montrées, et celles dont la fiche a changé depuis la dernière
exécution. Chacune est affichée avec son score et la raison de chaque critère,
et `[nouvelle]` ou `[mise à jour]` dit pourquoi elle est là. Un programme et une
bourse ne sont pas mesurés de la même façon : un programme se juge sur sa
matière, une bourse sur qui peut en bénéficier. Les détails sont dans
`docs/VERSIONS.md` V0.3, et le choix de ce qui est signalé dans V0.5.

Le détail des 69 fiches n'est plus imprimé : une veille quotidienne qui réaffiche
69 fiches déjà lues n'est plus lisible. Le compte reste affiché, et les 69 fiches
restent dans `data/opportunities.json`.

Cette commande **écrit deux fichiers** dans `data/` :

* `opportunities.json`, l'historique complet. Une opportunité déjà vue garde sa
  date de première apparition, et ses données sont rafraîchies ;
* `seen.json`, la mémoire de ce qui a déjà été montré.

Lancer la commande une seconde fois de suite affiche donc `Rien de nouveau` et
`0 nouvelles depuis la dernière exécution`, et ne réécrit pas les fichiers :
rien n'ayant changé, il n'y a rien à écrire. C'est ce qui permet à GitHub
Actions de ne commiter que lorsqu'il y a effectivement quelque chose de
nouveau.

Les deux fichiers sont versionnés, parce qu'une veille qui recommence à zéro
chaque jour ne sert à rien. Pour repartir de zéro, les vider ou les supprimer —
en sachant que tout sera alors signalé comme nouveau.

Le bulletin part aussi par Discord, si le secret `DISCORD_WEBHOOK` est posé.
C'est un **webhook**, donc une URL qui donne le droit d'écrire dans un salon :
elle se crée dans Discord, dans les paramètres du salon, et se met dans les
secrets du dépôt comme les six autres. Elle ne doit jamais être écrite dans un
fichier du dépôt. La marche à suivre complète est dans `docs/GITHUB_PYTHON.md`
§12.

Sans aucun secret, ce qui est le mode par défaut, le programme écrit quand même
le bulletin sur la console et le dit :

```text
Notification : console seule, il manque SMTP_HOST, SMTP_PORT, SMTP_USER,
SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO, Discord non configuré
```

Les cinq formes possibles de cette ligne sont dans `docs/VERSIONS.md` V0.10.
C'est elle que le workflow recopie dans le résumé d'étape, et c'est la seule
trace qu'un run automatique a réussi à notifier.

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

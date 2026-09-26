# Versions du projet Academic Watch

Ce document définit les fonctionnalités à développer pour chaque version.

L'objectif est de construire le projet progressivement.

Chaque version doit fonctionner avant de commencer la suivante.

---

# V0.1 - Base du projet

## Objectif

Créer la structure du projet et vérifier que Python fonctionne correctement.

## À développer

Créer :

```text
config/profile.json
src/main.py
src/models.py
requirements.txt
.gitignore
```

Le profil doit contenir :

* niveau d'étude ;
* diplôme recherché ;
* domaines ;
* pays ;
* langues ;
* financement ;
* statut international.

## Résultat attendu

Le programme doit pouvoir être lancé avec :

```bash
python src/main.py
```

et afficher les informations de configuration chargées.

---

# V0.2 - Première collecte

## Objectif

Ajouter la première source de données.

Les sources retenues et leurs URLs sont définies dans `docs/SOURCES.md`.

## À développer

Créer :

```text
src/scraper.py
```

Le programme doit pouvoir :

1. accéder à une source ;
2. récupérer les informations ;
3. transformer les données dans un format commun ;
4. afficher les opportunités trouvées.

Le programme doit aussi pouvoir **vérifier** une source déclarée avant de
l'exploiter : `test_sources()` teste chaque URL de `config/sources.json` et
indique si elle contient réellement une liste d'opportunités. Les cinq verdicts
sont décrits dans `docs/SOURCES.md` §1.3. Cette vérification conditionne la
décision d'écrire des sélecteurs pour une source.

État : **TUM et KAIST – Explore Programs sont implémentées**, 46 opportunités.
KAIST n'a demandé qu'un bloc dans `config/selectors.json`, sans une seule ligne
ajoutée à `src/scraper.py`. C'est la démonstration que le format commun tient
dès la deuxième source.

Une troisième source, KAIST – Scholarship, est venue en V0.3. Elle n'a demandé
ni sélecteur, ni ligne dans `scraper.py`, mais un parseur dédié : voir
`docs/SOURCES.md` §7. Le compte est donc de 49 opportunités.

Une quatrième, EACEA, est venue en dernier et n'a demandé qu'un bloc de
sélecteurs de plus, toujours sans ligne dans `scraper.py`. Le compte est de
**69 opportunités**, dont 20 sur un catalogue large où une seule correspond au
profil. C'est le résultat honnête d'une source utile mais peu ciblée.

## Résultat attendu

Exemple :

```text
3 opportunités trouvées

1. Master Cybersecurity
   University A
   Germany

2. MSc Network Security
   University B
   Canada

3. MSc Telecommunications
   University C
   Japan
```

---

# V0.3 - Correspondance et score

## Objectif

Comparer les opportunités avec le profil, et expliquer pourquoi.

## À développer

Le module est :

```text
src/matches.py
```

Il ne s'appelle pas `filters.py` parce que le travail n'est pas de garder ou
de supprimer, mais de dire **à quel niveau** une opportunité correspond.

Fait :

* trois paliers de correspondance sur le domaine (`direct`, `strong`, `weak`),
  déclarés dans `config/profile.json` ;
* score, budget des points déclaré dans le module, raison en toutes lettres
  pour chaque critère ;
* étudiants internationaux ;
* financement ;
* langue.

Reste à écrire :

* deadline, **et il n'est pas implémentable aujourd'hui**.

Aucune des quatre sources actives ne publie de date, ce qui a été vérifié page
par page et non déduit : le catalogue EACEA, la fiche projet Erasmus+ et la
page MEXT contiennent zéro occurrence de « deadline » et zéro année. Ce n'est
donc pas un critère difficile à écrire, c'est un critère sans donnée. Écrire un
lecteur de dates sans jamais l'exécuter sur une vraie valeur produirait du code
mort, exactement comme l'extraction de `funding_amount` a été refusée.

Le tableau du cahier des sources annonçait l'inverse. Il a été corrigé, avec
les chiffres de la vérification : `docs/SOURCES.md` §6.3.

Conséquence sur le profil : `preferences.application_deadline_after` n'est
utilisée par rien. Elle est vraie, et le sera dès qu'une source publication des
dates.

**V0.3 est donc terminée à 100 points pour une bourse et 85 atteignables pour un
programme, faute de source qui publie une langue.** Les deux critères manquants
sont documentés comme non implémentables, pas comme oubliés.

## Deux listes de critères, et pourquoi

Un programme et une bourse ne posent pas la même question, donc ils ne sont pas
mesurés de la même façon.

Un programme se juge sur sa **matière** : c'est le domaine qui décide. Une
bourse n'annonce **aucune matière** : elle se juge sur qui peut en bénéficier.
Exiger un domaine d'une bourse écarterait toutes les bourses, ce qui est
exactement le défaut constaté sur la page Scholarship de KAIST, où les trois
bourses étaient rejetées alors que deux d'entre elles sont des prises en charge
complète des frais.

| Type | Critères retenants | Critères qui classent |
| ---- | ------------------ | -------------------- |
| `programs` | `domaine` | `diplome`, `pays` |
| `scholarships` | `niveau`, `international` | `financement`, `pays` |

Ce sont des listes de critères et non un seuil de score : la question n'est pas
« combien » mais « quelle matière » ou « qui peut en bénéficier ».

Le type vient de `config/sources.json` et est recopié sur l'opportunité par le
scraper, pour que la correspondance n'ait pas à relire le registre.

## Le piège du diplôme composé

La page Scholarship de KAIST écrit « Master’s-Ph.D. Integrated programs », ce
qui est un diplôme différent de « Master’s ». Deux règles sont nécessaires,
et chacune a été vérifiée sur un cas réel :

* « Master's-Ph.D. Integrated » est retiré avant de chercher « Master ».
  Sinon une bourse de doctorat passerait pour une bourse de Master, puisque le
  mot Master y figure ;
* « undergraduate » contient « graduate ». Une recherche par sous-chaîne
  ferait passer une bourse de premier cycle pour une bourse de Master. Les
  niveaux de diplôme sont donc cherchés mot entier.

Résultat mesuré sur les 3 bourses KAIST : 2 retenues à 100/100, et la bourse
`KAIST Prestige Scholarship for International Ph.D. Students` rejetée à 60/100
avec la raison « réservée à un niveau doctoral ». C'est le bon résultat : un
étudiant de Master ne peut pas en profiter.

## Résultat attendu

Le programme doit séparer :

```text
Opportunités compatibles, avec leur score et leurs raisons
```

et

```text
Opportunités non compatibles
```

`matched` est la porte, `score` ne classe que parmi les retenues : un
programme sans correspondance de domaine peut obtenir des points de diplôme
et de pays, et ne doit pas pour autant remonter dans la liste. Un score n'a de
sens que rapporté au maximum de son type : 85 sur 100 pour un programme et
100 sur 100 pour une bourse ne se comparent pas.

État mesuré : **9 retenues sur 69** opportunités, 7 programmes et 2 bourses.

Le maximum atteignable d'un programme est 85 sur 100, pas 100 : le critère
`langue` est écrit et fonctionne, mais aucune source ne renseigne `language`.
Les 15 points sont donc invaintables, et c'est dit plutôt que masqué.

## Une limite assumée

Une bourse qui restreint les départements acceptés n'est pas vérifiée sur le
domaine : le critère `domaine` ne fait pas partie du budget `scholarships`.
Aucune source active n'est dans ce cas aujourd'hui, la page KAIST indiquant
« All departments ». Le jour où une bourse nomme des départements, il faudra
lire le département dans la liste `Departments Accepting Applications:` et le
traiter comme un critère supplémentaire. Ce n'est pas fait, et ne doit pas
être deviné.

---

# V0.4 - Sauvegarde

## Objectif

Conserver les informations entre deux exécutions.

## À développer

Créer :

```text
src/storage.py
```

Utiliser JSON.

Fichiers :

```text
data/opportunities.json
data/seen.json
```

Le programme doit pouvoir :

* enregistrer une opportunité ;
* charger les anciennes opportunités ;
* détecter les doublons.

## État mesuré

Les trois points sont faits. `src/storage.py` fait 200 lignes et ne dépend
d'aucune bibliothèque externe.

**Identité : `source` + titre normalisé + diplôme normalisé.** C'est la seule
vraie décision de la version, et elle a été reprise sur une mesure et non sur
un principe. La règle naturelle, `source` + titre, perd une opportunité : TUM
publie deux programmes appelés « Aerospace », un Master of Science et un Bachelor
of Science, et le Bachelor était écrasé par le Master. Mesuré sur les 69
opportunités réelles :

| Règle | Identités distinctes | Opportunités perdues |
| ----- | -------------------- | --------------------- |
| source + titre | 68 | 1 |
| source + titre + diplôme | 69 | 0 |

L'URL est écartée volontairement. Elle est publiée par les 69 opportunités
comme le titre, mais elle est la propriété du site : les 20 URL d'EACEA pointent
vers des sites de programmes tiers, et une identité fondée sur l'URL ferait que
tout semble nouveau dès qu'un site réorganise ses chemins. Pour une veille,
l'erreur grave n'est pas de rater une nouveauté, c'est d'en annoncer soixante.
L'URL reste enregistrée dans chaque fiche.

**Limite connue, écrite dans le module.** KAIST publie trois niveaux pour un même
programme, joints en une seule chaîne par `read_texts`. Si l'ordre de cette liste
change un jour, les 36 identités KAIST changent avec, et ces opportunités
paraîtront nouvelles une fois. Deux collectes consécutives n'ont montré aucune
variation de ce genre, et c'est mesuré, mais la page reste sous le contrôle de
KAIST. C'est le compromis assumé du diplôme dans l'identité : il évite de perdre
une opportunité, au prix d'en pouvoir créer une par accident.

**Les deux fichiers répondent à deux questions différentes.** Une opportunité est
collectée même quand elle ne correspond pas au profil, donc
`opportunities.json` contient des éléments que `seen.json` ne contiendra jamais.
Et changer son profil ne doit pas re-signaler les 69 opportunités déjà vues : ce
garantit `seen.json`, pas `opportunities.json`.

**Un fichier illisible arrête le programme.** `StockageInvalide` est levée si un
fichier de données existe mais n'est pas lisible, et le fichier n'est pas
touché. Repartir d'un historique vide ne se verrait pas : les 69 opportunités
passeraient pour nouvelles, et la veille annoncerait d'un coup tout ce qu'elle
a toujours annoncé. Une erreur visible vaut mieux qu'une inondation fausse. Le
même raisonnement s'applique à une entrée de `seen.json` qui n'est pas une
chaîne : elle est refusée, et non ignorée, pour la même raison.

**Le fichier ne change pas quand rien ne change.** `collected_at` est l'heure
de la collecte, donc il diffère à chaque exécution. Comparer deux fiches sur
tous leurs champs dirait donc que les 69 ont changé, chaque jour, et le fichier
serait réécrit sans raison. Une veille quotidienne produirait alors un changement
par jour quoi qu'il arrive, et on ne distinguerait plus « rien de neuf » d'« une
information mise à jour ». Les deux horodatages sont donc exclus de la
comparaison : une fiche identique n'est pas réécrite, et le fichier est
byte-pour-byte le même. Le coût est une information en moins, la date de dernière
collecte, qui ne sert à rien tant qu'aucun code ne cherche à savoir si une offre
a disparu de sa page. Vérifié : deux exécutions consécutives produisent le même
SHA-256.

**L'écriture est atomique.** Le programme tourne sur un planning et peut être
interrompu. L'écriture se fait dans un fichier `.tmp` puis remplace la
destination, donc un JSON tronqué ne peut pas se retrouver sur le disque. Un
test vérifie qu'aucun `.tmp` ne reste.

**Le fichier reste lisible par un humain** : `ensure_ascii=False` et `indent=2`,
donc les accents sont écrits tels quels et non en `\u00e9`. Un fichier de données
qu'on ne peut pas lire sans outillage ne sert à rien à la relecture.

## Vérification

45 cas de test, tous passants. Ils couvrent le cas nominal et surtout ce qui
brise une sauvegarde : fichier tronqué, JSON valide mais pas une liste,
`seen.json` au mauvais format, première exécution, dossier absent, opportunité
qui change de diplôme, titre accentué ou non, deux sources de même titre, et
deux collectes identiques dont le fichier doit rester identique.

Sur les données réelles : 69 fiches après la première exécution, 69 nouvelles
annoncées, puis 0 nouvelle et 69 fiches à la seconde. Le programme est
idempotent.

## Réserve

Ces tests vivent dans un dossier temporaire, hors du dépôt. Ils ont servi à
construire la version et ils sont reproductibles, mais ils ne sont pas exécutés
automatiquement : rien ne les rejoue à chaque commit. Les mettre dans le dépôt
est un travail à faire, et il n'est pas fait.

---

# V0.5 - Détection des nouvelles opportunités

## Objectif

Ne signaler que les opportunités nouvelles.

Exemple :

```text
Anciennes :
A
B

Nouvelle collecte :
A
B
C
D
```

Le programme doit retourner :

```text
Nouvelles opportunités :

C
D
```

---

# V0.6 - Première notification

## Objectif

Informer automatiquement l'utilisateur.

La première version peut utiliser une méthode simple :

```text
console
```

Puis une notification externe pourra être ajoutée.

Exemples :

* Telegram ;
* email.

La notification doit contenir au minimum :

```text
Nouvelle opportunité

Master Cybersecurity
Université
Pays
Deadline
Financement
Lien
```

---

# V0.7 - Plusieurs sources

## Objectif

Ajouter plusieurs sources.

Les sources à ajouter sont listées dans `docs/SOURCES.md`.

Exemple :

```text
Source 1
Source 2
Source 3
Source 4
```

Chaque source doit produire le même format de données.

Il ne faut pas réécrire tout le programme pour ajouter une nouvelle source.

---

# V0.8 - GitHub Actions

## Objectif

Automatiser l'exécution.

GitHub Actions doit :

1. récupérer le dépôt ;
2. installer Python ;
3. installer les dépendances ;
4. lancer le programme ;
5. sauvegarder les résultats si nécessaire.

Le programme doit pouvoir fonctionner sans intervention humaine.

---

# V0.9 - Veille automatique

## Objectif

Faire tourner automatiquement la veille selon une fréquence définie.

Exemple :

```text
Tous les jours
    ↓
GitHub Actions
    ↓
Python
    ↓
Recherche
    ↓
Filtrage
    ↓
Détection des nouveautés
    ↓
Notification
```

Une exécution manuelle doit également rester possible.

---

# V1.0 - Version fonctionnelle

## Objectif

Obtenir un système réellement utilisable.

La V1.0 doit permettre :

* recherche ;
* collecte ;
* filtrage ;
* sauvegarde ;
* détection des doublons ;
* détection des nouveautés ;
* plusieurs sources ;
* notification ;
* exécution automatique ;
* exécution manuelle.

Architecture :

```text
GitHub Actions
       ↓
main.py
       ↓
scraper.py
       ↓
matches.py
       ↓
storage.py
       ↓
notifier.py
```

---

# V1.1 - Amélioration des informations

Le programme pourra récupérer davantage d'informations :

* conditions d'admission ;
* frais de scolarité ;
* frais de candidature ;
* durée ;
* nombre de places lorsque disponible ;
* documents requis ;
* date d'ouverture ;
* date de fermeture ;
* lien officiel de candidature.

---

# V1.2 - Suivi des deadlines

Le programme pourra surveiller les dates limites.

Exemple :

```text
Deadline dans 60 jours
Deadline dans 30 jours
Deadline dans 14 jours
Deadline dans 7 jours
Deadline demain
```

Une notification pourra être envoyée lorsque la deadline approche.

---

# V2.0 - Analyse avancée

Cette version pourra introduire des fonctionnalités plus avancées :

* analyse automatique des descriptions ;
* extraction des critères d'admission ;
* identification des financements ;
* comparaison avec le profil ;
* résumé automatique.

L'utilisation d'une API d'intelligence artificielle pourra être étudiée uniquement à ce stade.

---

# Règles de développement

## 1. Une version doit fonctionner avant la suivante

Ne pas développer simultanément dix fonctionnalités.

## 2. Pas de complexité inutile

Une fonction Python simple est préférable à une architecture complexe.

## 3. Tester localement avant GitHub Actions

Chaque fonctionnalité doit fonctionner sur l'ordinateur local avant d'être automatisée.

## 4. Ne pas dépendre de l'IA pour les fonctions fondamentales

La collecte, le filtrage et la sauvegarde doivent fonctionner sans IA.

## 5. Conserver les sources

Chaque opportunité doit conserver son URL d'origine.

## 6. Vérification humaine

Le programme aide à trouver les opportunités.

Il ne remplace pas la vérification des informations sur le site officiel.

---

# Ordre obligatoire de développement

```text
V0.1
 ↓
V0.2
 ↓
V0.3
 ↓
V0.4
 ↓
V0.5
 ↓
V0.6
 ↓
V0.7
 ↓
V0.8
 ↓
V0.9
 ↓
V1.0
```

Les versions V1.1 et suivantes sont des améliorations.

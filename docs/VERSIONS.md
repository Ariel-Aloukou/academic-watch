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
* score sur 100, budget des points déclaré dans le module ;
* raisons en toutes lettres, pour que l'étudiant puisse lire pourquoi un
  programme lui est proposé.

Reste à écrire :

* étudiants internationaux ;
* financement ;
* langue ;
* deadline.

Un cas que le filtrage devra traiter à part : les 3 bourses KAIST sont
aujourd'hui écartées, faute de domaine. Une bourse n'annonce pas de matière, et
« est-ce une bourse ? » n'est pas la question que pose un profil de recherche.
La façon de traiter ce cas n'est pas décidée ; elle ne doit pas être tranchée
en même temps que le reste.

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
et de pays, et ne doit pas pour autant remonter dans la liste.

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

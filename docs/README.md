# Academic Watch

## 1. Présentation

**Academic Watch** est un programme de veille académique développé en Python et exécuté automatiquement avec GitHub Actions.

Son objectif est de rechercher régulièrement des opportunités de Master et de bourses correspondant au profil de l'utilisateur, puis de signaler les nouvelles opportunités pertinentes.

Le programme doit permettre de surveiller notamment :

* les Masters ;
* les bourses d'études ;
* les financements ;
* les universités ;
* les programmes internationaux ;
* les dates limites de candidature ;
* les conditions d'éligibilité.

Le projet est principalement destiné à la recherche d'opportunités pour un étudiant international souhaitant poursuivre ses études à l'étranger.

---

# 2. Objectif principal

Le programme doit répondre à une question simple :

> « Quelles nouvelles opportunités correspondant à mon profil sont apparues depuis ma dernière veille ? »

Le programme doit donc :

1. récupérer des opportunités depuis des sources définies ;
2. extraire les informations importantes ;
3. comparer ces informations avec le profil de recherche ;
4. éliminer les opportunités qui ne correspondent pas aux critères ;
5. détecter les nouvelles opportunités ;
6. enregistrer les résultats ;
7. informer l'utilisateur des nouvelles opportunités.

---

# 3. Principe général

Le fonctionnement sera volontairement simple :

```text
Sources Internet
       ↓
Collecte des informations
       ↓
Nettoyage des données
       ↓
Filtrage
       ↓
Comparaison avec le profil
       ↓
Nouvelles opportunités ?
       ↓
Enregistrement
       ↓
Notification
```

Python réalise le traitement.

GitHub Actions déclenche automatiquement le programme.

---

# 4. Technologies utilisées

Le projet doit utiliser principalement :

* Python
* GitHub
* GitHub Actions
* JSON
* Git

Des bibliothèques Python pourront être utilisées lorsque cela simplifie réellement le développement.

La règle générale est :

> Ne pas ajouter une technologie simplement parce qu'elle existe.

Le projet n'a pas besoin au départ de :

* Docker ;
* Kubernetes ;
* PostgreSQL ;
* Redis ;
* API complexe ;
* architecture microservices ;
* framework web ;
* intelligence artificielle obligatoire.

Ces technologies pourraient être ajoutées plus tard uniquement si elles deviennent réellement nécessaires.

---

# 5. Structure minimale du projet

La structure de départ sera :

```text
academic-watch/
│
├── .github/
│   └── workflows/
│       └── veille.yml
│
├── config/
│   ├── profile.json
│   ├── sources.json
│   └── selectors.json
│
├── data/
│   ├── opportunities.json
│   └── seen.json
│
├── src/
│   ├── main.py
│   ├── models.py
│   ├── scraper.py
│   ├── parsers/
│   ├── matches.py
│   ├── storage.py
│   └── notifier.py
│
├── docs/
│   ├── README.md
│   ├── VERSIONS.md
│   ├── GITHUB_PYTHON.md
│   └── SOURCES.md
│
├── requirements.txt
├── .gitignore
└── README.md
```

La structure pourra évoluer, mais elle doit rester compréhensible.

---

# 6. Rôle des fichiers principaux

## `config/profile.json`

Contient le profil et les critères de recherche.

Exemples :

* niveau d'étude ;
* diplôme recherché ;
* domaines ;
* pays ;
* langues ;
* financement ;
* statut d'étudiant international ;
* contraintes de candidature.

Le programme ne doit pas contenir directement ces informations dans son code.

---

## `src/main.py`

C'est le point d'entrée du programme.

Il orchestre les différentes étapes :

```text
collecter
   ↓
évaluer la correspondance avec le profil
   ↓
enregistrer
   ↓
notifier
```

Il doit rester simple.

---

## `src/scraper.py`

Contient les fonctions permettant de récupérer les informations depuis les sources.

Au départ, une seule source pourra être utilisée.

Il sera ensuite possible d'ajouter d'autres sources.

Le module a aussi une fonction de vérification, `test_sources()`, qui parcourt
toutes les URLs déclarées dans `config/sources.json` et mesure ce qu'elles
contiennent réellement. Elle sert à distinguer une vraie liste d'opportunités
d'un simple portail de recherche, car une page qui répond 200 n'est pas
suffisante. Lancer :

```text
python src/scraper.py
```

Le détail de la méthode et des verdicts est dans `docs/SOURCES.md` §1.

---

## `src/matches.py`

Contient les règles permettant de déterminer si une opportunité correspond au
profil.

Le module ne fait pas que **garder ou supprimer**. Il répond à trois questions :
l'opportunité correspond-elle, pourquoi, et à quel niveau. `evaluer()` renvoie
donc `matched`, `score` et `reasons`.

Critères :

```text
Master ?
Domaine compatible ?
Pays compatible ?
Étudiants internationaux acceptés ?
Financement disponible ?
Date limite intéressante ?
```

Sur le domaine, la correspondance se fait en trois paliers, déclarés dans
`config/profile.json` et non déduits d'une similarité de chaînes :

| Palier | Sens | Points |
| ------ | ---- | ------ |
| `direct` | le texte contient un domaine de `fields` | 50 |
| `strong` | le texte contient un terme de `related_terms.strong` | 30 |
| `weak` | le texte contient un terme de `related_terms.weak` | 10 |

Cette séparation a une raison : sans elle, ajouter les mots trouvés sur les
sites au profil ferait du profil un miroir des pages surveillées. `fields` reste
la définition de l'objectif, `related_terms` porte le vocabulaire que les
universités utilisent pour le désigner.

Les critères dépendent du **type** de l'opportunité, déclaré par la source dans
`config/sources.json` et recopié sur l'opportunité. Un programme se juge sur sa
matière, une bourse sur qui peut en bénéficier : exiger un domaine d'une bourse
écarterait toutes les bourses.

| Type | Critères | Total |
| ---- | -------- | ----- |
| `programs` | `domaine` 50, `diplome` 20, `pays` 15, `langue` 15 | 100 |
| `scholarships` | `niveau` 40, `international` 25, `financement` 20, `pays` 15 | 100 |

Le maximum **atteignable** est 85 pour un programme et 100 pour une bourse :
aucune des quatre sources actives ne renseigne `language`, donc 15 points ne
peuvent pas être gagnés. Les poids sont déclarés une fois pour toutes, donc
l'ajout d'un critère plus tard n'attribue pas rétrosactivement des points aux
collectes antérieures.

Le critère `deadline` n'est pas écrit, et pas par oubli : aucune source du
registre ne publie de date, ce qui a été vérifié page par page. Ce serait donc
un lecteur de dates jamais exécuté sur une vraie valeur. Voir
`docs/SOURCES.md` §6.3.

---

## `src/storage.py`

S'occupe de sauvegarder les informations.

Au début, des fichiers JSON suffisent.

Il n'est pas nécessaire d'utiliser une base de données.

---

## `src/notifier.py`

S'occupe des notifications.

Au début, le programme peut simplement afficher les résultats.

Une notification Telegram ou email pourra être ajoutée ensuite.

---

# 7. Données minimales d'une opportunité

Chaque opportunité doit essayer de contenir au minimum :

```text
title
university
country
degree
field
url
source
deadline
funding
language
```

Exemple :

```json
{
  "title": "Master Cybersecurity",
  "university": "Example University",
  "country": "Germany",
  "degree": "Master",
  "field": "Cybersecurity",
  "url": "https://example.edu",
  "source": "University Website",
  "deadline": "2027-03-15",
  "funding": "Fully Funded",
  "language": "English"
}
```

Certaines informations peuvent être absentes.

Le programme ne doit pas inventer une information qui n'a pas été trouvée.

---

# 8. Détection des doublons

Le programme doit mémoriser les opportunités déjà rencontrées.

Exemple :

```text
Jour 1
→ Master Cybersecurity A

Jour 2
→ Master Cybersecurity A
→ Master Network Security B
```

Le programme doit signaler uniquement :

```text
Nouvelle opportunité :
Master Network Security B
```

et ne pas renvoyer continuellement :

```text
Master Cybersecurity A
```

---

# 9. Sources

Les sources doivent être aussi fiables que possible.

Priorité :

1. sites officiels des universités ;
2. sites officiels des gouvernements ;
3. organismes officiels de bourses ;
4. plateformes universitaires reconnues ;
5. autres sources uniquement lorsqu'elles apportent une information utile à vérifier.

Lorsqu'une information importante est trouvée sur une source secondaire, le programme doit idéalement permettre de retrouver la source officielle.

Les sources exactes retenues, leurs URLs et leur statut de vérification sont définis dans `docs/SOURCES.md`. Ce document fait partie du cahier des charges : une source n'est pas codée dans `src/scraper.py` avant d'y être notée.

---

# 10. Fiabilité

Le programme ne doit jamais considérer automatiquement qu'une opportunité est valide simplement parce qu'elle apparaît dans une page Internet.

Il doit distinguer :

```text
Information trouvée
        ≠
Information vérifiée
```

Une opportunité peut donc contenir :

```text
source
url
date de collecte
```

afin de permettre une vérification humaine.

---

# 11. Simplicité du code

Le projet doit respecter les règles suivantes :

* fonctions courtes ;
* noms de variables explicites ;
* peu de dépendances ;
* pas de classes inutiles ;
* pas d'architecture compliquée ;
* commentaires uniquement lorsqu'ils sont utiles ;
* logique facilement compréhensible par un étudiant.

Une solution simple et fonctionnelle doit être préférée à une solution techniquement impressionnante mais difficile à maintenir.

---

# 12. Fonctionnement final

Une fois le projet terminé :

```text
GitHub Actions
      ↓
lance Python
      ↓
Python récupère les nouvelles opportunités
      ↓
Python applique les critères
      ↓
Python compare avec les anciennes données
      ↓
Python détecte les nouveautés
      ↓
Python sauvegarde
      ↓
Python envoie une notification
```

L'utilisateur n'a donc pas besoin de lancer manuellement le programme chaque jour.

---

# 13. Évolution possible

Après la première version fonctionnelle, le projet pourra évoluer vers :

* davantage de sources ;
* notifications Telegram ;
* notifications email ;
* analyse plus avancée des critères ;
* extraction automatique des conditions d'admission ;
* suivi des dates limites ;
* tableau de bord ;
* historique des opportunités ;
* recherche de bourses séparément des Masters ;
* système de recherche plus intelligent.

Ces fonctionnalités ne doivent cependant pas être ajoutées avant que la version de base fonctionne correctement.

---

# 14. Règle fondamentale du projet

Le projet doit toujours suivre cette logique :

> Fonctionner d'abord. Automatiser ensuite. Complexifier seulement lorsque c'est nécessaire.

L'objectif n'est pas de construire le système le plus complexe possible.

L'objectif est de construire un système fiable, compréhensible et réellement utilisable.

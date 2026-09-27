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
├── tests/                    # Ajouté en V0.4, absent de la structure d'origine
│
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
└── README.md
```

La structure pourra évoluer, mais elle doit rester compréhensible.

`tests/` et `requirements-dev.txt` ne figuraient pas dans la structure
d'origine. Ils ont été ajoutés après la V0.4, quand les tests écrits pour
construire les versions ont été mis dans le dépôt. Ils restent séparés des
dépendances de production : le programme n'a pas besoin d'un framework de test
pour fonctionner.

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
choisir ce qui doit être signalé
   ↓
notifier
```

Il doit rester simple.

### Ce que la V0.5 a décidé

L'étape « choisir ce qui doit être signalé » est celle qui décide de ce que
l'étudiant lit. Elle ne porte que sur les opportunités **retenues** : une
opportunité qui ne correspond pas au profil n'est jamais annoncée, même si
elle est nouvelle. Une veille est une sélection, pas un catalogue.

Sont signalées les retenues jamais montrées, et les retenues déjà montrées
dont la fiche a changé depuis la dernière exécution. Les deux listes sont
disjointes par construction, donc rien n'est compté deux fois, et une
opportunité inconnue n'est jamais annoncée comme une mise à jour : ce
serait un mensonge, puisque personne ne l'a jamais vue.

C'est aussi la version où le détail des 69 fiches cesse d'être imprimé. Le
compte reste affiché, et les 69 fiches restent dans `data/opportunities.json`.
Ce qui a été retiré de l'écran est ce qui est mesuré et écrit, pas ce qui
est perdu.

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

### Deux pièges de sous-chaîne, trouvés en même temps

Une recherche par sous-chaîne trouve le mot là où il est, et aussi à l'intérieur
d'un autre mot. Deux fois, cela a produit un résultat faux, et les deux fois
comme un **faux négatif** : l'opportunité disparaissait au lieu d'être signalée à
tort. C'est le sens d'erreur le plus coûteux pour une veille.

| Texte publié | Recherche par sous-chaîne | Recherche par mot entier |
| ------------ | ------------------------- | ----------------------- |
| « undergraduate » | contient « graduate » : une bourse de premier cycle passerait pour une bourse de Master | pas de match, et c'est juste |
| « Open to international students » | contient « national student » : bourse entièrement ouverte comptée comme réservée aux nationaux, 25 points perdus, écartée | pas de match, et c'est juste |

Le second n'a pas été trouvé en relisant le code, mais en écrivant les tests. Les
trois bourses de KAIST y échappaient par hasard, la page écrivant
« applicants ». Une source écrivant « students » l'aurait déclenché.

La règle qui en découle : tout mot qui sert à **exclure** est cherché mot entier.
Un mot qui sert à inclure peut être cherché par sous-chaîne, parce qu'une
inclusion trop large fait remonter une opportunité inutile, ce qui se voit
tout de suite ; une exclusion trop large fait disparaître une opportunité, ce
qui ne se voit jamais.

---

## `src/storage.py`

S'occupe de sauvegarder les informations.

Au début, des fichiers JSON suffisent.

Il n'est pas nécessaire d'utiliser une base de données.

### Ce que la V0.4 a décidé

Deux questions que le cahier des charges posait sans y répondre : *qu'est-ce
qui identifie une opportunité ?* et *pourquoi deux fichiers ?*

**L'identité est `source` + titre normalisé + diplôme normalisé.** Pas l'URL.
L'URL est la propriété du site et non de l'opportunité, et une identité fondée
sur elle ferait que tout semble nouveau dès qu'un site réorganise ses chemins.
Le diplôme a été ajouté après une **collision mesurée** : TUM publie deux
programmes nommés « Aerospace », un Master of Science et un Bachelor of Science,
et sans lui le Bachelor disparaissait de l'historique. L'identité est écrite en
clair dans le fichier, sans hachage, pour qu'une fusion puisse être contestée à
l'œil.

**Les deux fichiers ne sont pas redondants.** `opportunities.json` contient tout
ce qui a été collecté, y compris ce qui ne correspond pas au profil, car une
offre écartée aujourd'hui peut intéresser le jour où le profil change.
`seen.json` contient ce qui a déjà été *montré* à l'utilisateur. Savoir qu'une
opportunité existe et savoir qu'on l'a déjà signalée sont deux informations
différentes, et la seconde est la seule qui évite de la répéter indéfiniment.

### Ce que la V0.5 a décidé

`sauvegarder` rend un `Bilan` à deux champs, `nouvelles` et `modifiees`. Le
second n'a pas demandé une nouvelle lecture du fichier : la comparaison qui le
produit existait déjà dans `sauvegarder`, au point où la version précédente de
la fiche est encore en mémoire. La refaire ailleurs aurait dupliqué
`a_change`, donc créé deux règles capables de diverger en silence.

Deux fonctions lisent ce bilan, et une seule condition chacune :

| Fonction | Ce qu'elle rend |
| -------- | --------------- |
| `nouvelles_depuis` | ce qui n'a jamais été montré |
| `modifiees_depuis` | ce qui a déjà été montré **et** dont la fiche a changé |

La seconde condition n'est pas un détail : sans elle, une opportunité
collectée mais jamais montrée serait annoncée comme une mise à jour.

---

## `tests/`

Contient les tests, lancés par `python -m pytest`.

Ils ne figuraient pas dans la structure d'origine du cahier des charges. Ils
ont été ajoutés après la V0.4, quand les tests qui avaient servi à construire
chaque version ont été mis dans le dépôt au lieu de rester dans un dossier
temporaire.

| Fichier | Ce qu'il surveille |
| ------- | ------------------ |
| `test_storage.py` | la sauvegarde, l'identité, le refus d'un fichier illisible |
| `test_correspondance.py` | les paliers, le diplôme, les bourses, les contrats du module |
| `test_main.py` | ce que la veille affiche, et le cas d'un jour sans nouveauté |
| `test_donnees.py` | la cohérence des deux fichiers versionnés dans `data/` |
| `test_workflow.py` | les choix écrits du workflow, le seul fichier non lançable en local |
| `test_proprete.py` | l'encodage des fichiers et les caractères qui se glissent dedans |

Trois règles, apprises en les écrivant :

* **aucun test ne touche au réseau.** Ce qui dépend d'une page vivante est
  vérifié à la main et écrit dans `docs/SOURCES.md`. Un test qui dépend d'un site
  étranger échoue pour une raison qui n'a rien à voir avec le code ;
* **aucun test n'écrit dans le vrai `data/`.** Un `conftest.py` redirige les
  chemins d'écriture de `storage` vers un dossier temporaire, pour tous les
  tests sans exception ;
* **aucun test de propreté n'impose un style.** Un test de ce type qui échoue
  oblige à reformater des fichiers qu'on n'a pas choisi de reformater, et
  `config/profile.json` est le travail de l'étudiant. `test_proprete.py` ne
  contrôle donc que des défauts qui cassent quelque chose.

Le workflow les exécute avant chaque collecte.

---

## `src/notifier.py`

S'occupe des notifications.

Au début, le programme peut simplement afficher les résultats.

Une notification Telegram ou email pourra être ajoutée ensuite.

### Ce que la V0.6 a décidé

**Email, et un message par jour.** Telegram était cité en premier exemple, et
c'est l'email qui est retenu, parce que c'est le seul canal que la boîte aux
lettres de l'étudiant ouvre déjà. Le résumé d'étape du workflow suppose
d'ouvrir un navigateur ; un email arrive tout seul, et se lit sans connexion.
Un message quotidien, y compris les jours sans nouveauté, afin qu'une absence
de message se voie : un secret périmé est indiscernable d'une veille sans
nouveauté.

**Un seul rendu, deux moyens.** `rendre()` produit le texte une fois, la
console l'affiche et l'email l'envoie. Deux rendus de la même liste
divergeraient au premier champ ajouté, et la divergence se verrait dans la
boîte de réception avant d'être cherchée. Le module est donc coupé en trois
morceaux, chacun testable seul :

| Fonction | Fait | Se teste par |
| -------- | ---- | ------------- |
| `rendre` | le texte | une comparaison de chaînes |
| `message` | les en-têtes et le corps | un dictionnaire de valeurs, sans réseau |
| `envoyer` | le transport | un objet passé en argument, qui note les appels |

Le découpage n'est pas une élégance : les en-têtes sont là où vivent les
erreurs réelles, les accents et l'adresse, et aucun test de cette partie n'a
besoin d'un serveur.

**Publier avant de mémoriser.** L'ordre inverse est plus naturel — on enregistre
ce qui a été montré, donc après — et il perd l'information : une opportunité
déjà marquée comme vue sans avoir été lue ne sera plus jamais annoncée, et
`seen.json` affirmera le contraire. Un doublon se voit ; une perte, non.

**Un envoi qui échoue n'arrête pas la veille.** `publier` ne lève jamais
d'exception : dans le workflow, une exception ferait sauter l'étape qui commite
`data/`, et une veille réussie avec un email non parti coûterait la journée de
données. Le prix est qu'un échec pourrait se perdre ; il est visible deux fois,
dans la ligne de statut et dans le résumé d'étape.

**Ce que le message peut afficher, mesuré sur les 69 fiches.** Titre, université,
pays et lien sont publiés 69 fois sur 69. Le financement 3 fois sur 69, dont 2
des 9 retenues. La date limite **0 fois sur 69** : aucune des quatre sources ne
la publie, c'est mesuré page par page et écrit dans `docs/SOURCES.md` §6.3. Un
champ absent n'est ni remplacé par un tiret ni par `None` : « Financement : — »
ferait croire que la bourse ne finance rien, ce qui n'est pas la même chose que
ne pas le publier.

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

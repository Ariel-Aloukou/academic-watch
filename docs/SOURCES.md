# Sources de la veille

Ce document est le cahier des charges des sources d'Academic Watch.

Les URLs sont définies ici, et dans `config/sources.json`, **avant** d'écrire le
code de `src/scraper.py`.

> Fonctionner d'abord. Automatiser ensuite. Complexifier seulement lorsque c'est
> nécessaire. (docs/README.md §14)

---

# 1. Principe

Les sources sont réparties en trois catégories, par ordre de fiabilité
décroissante (docs/README.md §9) :

```text
1. Sources officielles d'universités
2. Organismes officiels de bourses
3. Portails spécialisés
```

Une source ne peut être scrapée que si elle respecte cinq conditions. Les trois
dernières sont les plus importantes et les plus souvent oubliées.

| # | Condition | Pourquoi |
| - | --------- | -------- |
| 1 | Réponse HTTP 200 stable | Une source qui tombe fait échouer la veille |
| 2 | **Les opportunités sont dans le HTML** | Le programme n'exécute pas de navigateur |
| 3 | **Pas de résultats chargés en JavaScript** | Une page qui n'affiche rien sans navigateur est inutile |
| 4 | Pas de connexion ni de clé d'API | Les secrets ne doivent pas être dans le dépôt |
| 5 | Information vérifiable sur la page officielle | docs §10 : trouvé ≠ vérifié |

## 1.1 La distinction qui compte

Il faut séparer deux types de pages, car ils n'ont pas du tout la même valeur :

| Type de page | Exemple | Utilité pour la veille |
| ------------ | ------- | ---------------------- |
| **Liste d'opportunités** | un catalogue de programmes | exploitable directement |
| **Portail de recherche** | un moteur avec filtres | **inexploitable** sans exécuter du JavaScript |

Une page qui répond 200 n'est donc **pas** une source valide. C'est l'erreur la
plus fréquente, et c'est celle qui a été commise dans la première version de ce
document.

## 1.2 Méthode de validation

Pour chaque source, la procédure est :

1. envoyer une requête HTTP et noter le code, l'URL finale et la taille ;
2. compter les `<table>`, les `<select>` vides et les liens vers des fiches ;
3. **chercher un domaine du profil dans le texte visible** ;
4. si la page est un index, tester une ou deux sous-pages ;
5. ne retenir la source que si des opportunités sont réellement présentes.

**Cette procédure est exécutable** : `python src/scraper.py` parcourt
automatiquement `config/sources.json` et applique ces cinq étapes à chaque URL,
puis affiche un tableau et un bilan. Le programme lit aussi
`config/profile.json` pour l'étape 3, afin que la question posée soit « cette
page parle-t-elle de cybersécurité, de réseaux, de télécommunications ? ».

Le validateur ignore volontairement le champ `enabled` : il cherche à découvrir
quelles sources inscrites au cahier des charges sont réellement lisibles, y
compris celles qui sont désactivées.

## 1.3 Les cinq verdicts

Le statut HTTP ne suffit jamais à conclure. Chaque source reçoit un verdict
déduit de mesures, jamais d'une impression :

| Verdict | Condition | Suite à donner |
| ------- | --------- | -------------- |
| `exploitable` | 2xx, pas de JavaScript, et tableaux ou liens de fiche > 0 | écrire les sélecteurs |
| `a_tester` | 2xx, pas de JavaScript, mais aucune liste | descendre dans les sous-pages ou soumettre le formulaire |
| `javascript` | 2xx, mais marqueur de framework ou `<select>` vide | abandonner, ou passer à un navigateur |
| `bloque` | HTTP 403 ou 412 | injoignable pour un script, peut rester valable pour un humain |
| `injoignable` | timeout, DNS, autre code 4xx/5xx | retester plus tard |

Le bilan chiffré est au chapitre 5. Il n'est pas répété ici : deux copies d'un
chiffre mesuré finissent toujours par diverger, et c'est la moins récente qui
serait lue comme la bonne.

Deux limites honnêtes de cet outil, à connaître avant de lui faire confiance :

* le nombre de liens de fiche est un **indicateur**, pas une preuve. Le motif
  recherché (`detail/`, `fiche/`, `bourses/` suivi d'un identifiant) se trouve
  dans le nom de l'URL, ce qui varie d'un site à l'autre ;
* la détection de JavaScript repose sur quelques marqueurs connus
  (`__NUXT__`, `__NEXT_DATA__`, `ng-version`). Un portail qui charge ses
  résultats en AJAX avec une simple bibliothèque jQuery n'est pas détecté : il
  ressort `a_tester` alors qu'il est bel et bien dynamique. C'est le cas de
  Study in Korea.

---

# 2. Catégorie 1 — Sources officielles d'universités

C'est la catégorie la plus fiable et la plus prioritaire (docs/README.md §9).
Elle était vide au départ : elle a été renforcée avec 5 pages validées, plus TUM
déjà implémentée.

## 2.1 Candidats vérifiés

Ces pages ont été validées : HTTP 200, HTML statique, opportunités présentes
dans la page. Celles qui ne sont pas encore implémentées restent inscrites dans
`config/sources.json` avec `"enabled": false` : elles sont décidées, mais on ne
sait pas encore les lire.

### NTNU — Norwegian University of Science and Technology (Norvège)

| | |
| --- | --- |
| URL | `https://www.ntnu.edu/studies/international/master` |
| Type | Liste des Masters en anglais + Erasmus Mundus |
| Mesures | 200, 94 713 car., 3 tableaux, 41 lignes de programme |
| Statut | **Implémentée en V0.11** |

Correspondance avec le profil : **3 lignes sur 41**, mesurées le 29 septembre
2026 avec le code de production.

| Programme | Score | D'où il vient |
| --------- | ----- | ------------- |
| `Information Security` | 65/100 | tableau 0, ligne 16 |
| `Cybersecurity and Assurance (CYBERSURE)` | 65/100 | tableau 2, ligne 37, Erasmus Mundus |
| `Digital Infrastructure and Cyber Security` | 45/100 | tableau 0, ligne 6 |

Les 38 autres lignes sont lues, comprises et écartées : leurs titres ne
contiennent aucun terme du profil. Ce n'est pas un défaut de lecture, c'est un
domaine qui n'est pas celui de l'étudiant.

**Une affirmation de cette section était fausse.** La version précédente citait
`Engineering and ICT` parmi les programmes correspondants. Ce nom n'existe pas
dans les 41 lignes : c'est une faculté de NTNU, pas un programme. Les quatre
titres qui contiennent le mot *Engineering* sont `Electric Power Engineering`,
`Materials Science and Chemical Engineering`, `Cold Climate Engineering` et
`Coastal and Marine Energy Engineering - CoMEM+`. Une correspondance affirmée
lue à l'œil vaut moins qu'un compte : le compte est 3.

La page distingue les programmes ouverts aux candidats non UE/EEE de ceux
réservés aux candidats UE/EEE. C'est exactement la distinction utile pour un
candidat ivoirien.

Deux limites, mesurées :

* **`degree` n'est publié sur aucune ligne.** La page s'appelle « Master's
  programmes in English » et sa section « International Master's programmes »,
  mais le diplôme n'est écrit ni dans la ligne ni dans le titre. Le critère
  `diplome` retombe donc sur le titre, qui ne dit pas « Master », et affiche
  `titre Information Security, hors de la liste visée`. Les trois
  opportunités perdent 20 points et plafonnent à 65 sur 100. Elles restent
  retenues : seul `domaine` est bloquant. Le programme ne peut pas y remédier,
  `degree` se lit dans la ligne et jamais dans la source ;
* **une deadline est publiée, sans l'année.** Le deuxième tableau s'intitule
  `Deadline` et ne contient qu'une ligne, `Cold Climate Engineering — 1 March`.
  Une date sans année n'est pas une date, elle n'est donc pas extraite. C'est la
  conclusion que §6.2 annonçait déjà pour cette source, et elle se confirme.

### KAIST (Corée du Sud)

Programmes :

| | |
| --- | --- |
| URL | `https://admission.kaist.ac.kr/intl-graduate/Discover/ExplorePrograms` |
| Mesures | 200, 110 Ko, HTML statique, 36 programmes |
| Statut | **Implémentée en V0.2** |

Contient notamment une `Graduate School of Information Security`, ainsi que des
domaines réseau et télécommunications. Correspondance excellente.

La page est un accordéon statique : 5 collèges, 36 programmes. Mesuré le
29 septembre 2026, la réponse du serveur contient **16 balises `<script>`**, dont
13 chargent un fichier — `bootstrap.bundle.min.js`, `jquery.js`, `jstree.min.js`
et l'internationalisation. La phrase précédente de cette section disait « sans
aucun JavaScript » : c'était faux, et c'était faux exactement comme pour NTNU,
quelques lignes plus haut.

Ce qui est vrai, et mesuré : **les 36 programmes sont dans le HTML statique.**
La veille les lit sans navigateur, donc sans exécuter un seul script, et le
compte 36 du tableau ci-dessous vient de là. Les scripts servent à l'accordéon,
à la traduction et aux icônes, pas à la liste.

Le validateur ne compte d'ailleurs pas les balises `script` : il cherche quatre
marqueurs d'hydratation de framework, `__NUXT__`, `__NEXT_DATA__`,
`data-reactroot` et `ng-version`, et il n'en trouve aucun ici. C'est pourquoi il
classe cette source `a_tester` et non `exploitable` : non à cause du
JavaScript, mais parce qu'elle ne présente ni tableau ni lien de fiche.

Les sélecteurs sont dans `config/selectors.json`, et le remplissage a été
mesuré :

| Information | Sélecteur | Remplissage |
| ----------- | --------- | ----------- |
| Programme | `ul.ul-accordion > li` | 36 |
| Titre | `h5.h-accordion-tit span` | 36/36 |
| Diplômes | `.dv-accordion-info ul li span` | 36/36 |
| Domaines | `.dv-researchAreas span` | **26/36** |
| Lien | `a.homeIcon` | 36/36 |

Deux programmes correspondent directement au profil :
`Graduate School of Information Security` (Software Security, Cryptography,
**Network Security**, System Security) et `School of Computing` (**Secure
Computing**).

Trois limites assumées :

* les 10 programmes sans domaines de recherche gardent `field: None`. C'est
  exact, la page ne les publie pas (docs/README.md §7) ;
* le lien est le **site du département** (`https://gsis.kaist.ac.kr/`), pas une
  fiche de programme comme chez TUM. La notification vise donc un département
  entier plutôt qu'un programme : moins précise, mais c'est ce que la page
  publie ;
* le **collège** (Natural Sciences, Life Science, Engineering, Liberal Arts,
  Business) n'est pas extractible : les 5 `<h4>` sont frères du `<ul>` parent,
  hors de portée d'un sélecteur descendant. Aucun parseur dédié n'a été écrit
  pour contourner cela, c'est une décision de V0.7 ;
* le site est **intermittent** : il a répondu 200 puis échoué puis répondu 200
  lors de validations consécutives. Un échec isolé ne prouve pas qu'une source
  est morte.

Conditions d'éligibilité, à traiter comme une seconde source :

| | |
| --- | --- |
| URL | `https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility` |
| Mesures | 200, 71 011 car., contient un tableau |
| Statut | **Validée** |

Seule source de la catégorie 1 qui permet de remplir le champ `eligibility` de
`Opportunity` : nationalité, diplôme requis, score TOEFL ou IELTS minimal.

### UBC — University of British Columbia (Canada)

| | |
| --- | --- |
| URL | `https://grad.ubc.ca/programs/` |
| Mesures | 200, 251 392 car., **212 liens de programmes** |
| Statut | **Validée** |

De loin la source la plus volumineuse. Limite : les programmes sont rangés par
faculté, pas par domaine, et les informations de candidature sont sur des pages
séparées.

### TUM — Technical University of Munich (Allemagne)

| | |
| --- | --- |
| URL | `https://www.tum.de/en/studies/degree-programs` |
| Mesures | 200, 429 684 car., 78 liens de programmes |
| Statut | **Validée mais insuffisante** |

Implémentée en V0.2, avec KAIST.

Limites documentées :

* la page annonce 183 programmes mais n'en expose que 10 dans le HTML ;
* toute query string renvoie 404, la pagination n'est pas accessible en GET ;
* un POST sur `tx_solr[q]` fonctionne mais renvoie 10 résultats sur 22, non
  classés par pertinence.

Conséquence : cette source seule ne peut pas alimenter la veille. Elle sert de
référence technique, pas de couverture.

## 2.2 Piste à explorer

`https://studyinnorway.no/study-opportunities` n'est pas une liste, mais elle
expose 18 catégories, dont **`Information and Communication Technologies`**.
Cette sous-page est la piste la plus prometteuse pour obtenir des programmes
norvégiens complets. À valider avant de l'ajouter.

---

# 3. Catégorie 2 — Organismes officiels de bourses

Sources de `config/sources.json`. **Une seule est exploitable en l'état.**

| Source | Type | Mesures | Verdict |
| ------ | ---- | ------- | ------- |
| **Study in Japan – MEXT** | scholarships | 200, 28 825 car., **3 tableaux** | **Exploitable** |
| Study in Japan – Scholarships | scholarships | 200, 16 861 car., 0 tableau | Index de sous-pages |
| Study in Japan (programmes) | programs | 200, 32 913 car., 0 tableau | Portail, sans données |
| Erasmus Mundus EMJM | scholarships | 200, 194 408 car., 29 liens | Page d'explication |
| Study in Korea – Scholarships | scholarships | 200, 133 859 car., 0 tableau | Chargé en JavaScript |
| Study in Korea | programs | 200, 123 549 car., 0 tableau | Chargé en JavaScript |
| Study in Norway | programs | 200, 57 840 car., 0 tableau | Index, piste à explorer |
| EduCanada – Programmes | programs | 200, 24 Ko, 0 tableau, 0 lien | **Portail de recherche** |
| EduCanada – Bourses | scholarships | 200, 24 Ko, 0 tableau, 1 lien | **Portail de recherche** |
| DAAD – Scholarship Database | scholarships | 200, 22 Ko, 5 `<select>` **remplis** | Formulaire de recherche |
| Campus China | scholarships | erreur de connexion (412 avant) | Injoignable, écarté |
| Study in China – CSC | scholarships | HTTP 412 | Bloqué |

Ces mesures sont produites par `python src/scraper.py`, qui teste chaque URL du
registre et applique les cinq verdicts décrits en §1.3. Elles datent du dernier
exécution : un portail peut changer d'une semaine à l'autre, c'est pourquoi le
test est exécutable et non figé dans ce document.

## 3.1 Détail des verdicts

### Study in Japan – MEXT : la seule source exploitable

`https://www.studyinjapan.go.jp/en/planning/scholarships/mext-scholarships/`

Contient 3 tableaux statiques : montants mensuels, frais de scolarité, frais
d'examen, deux voies de candidature.

Limite : c'est une page de **description de bourse**, pas une liste de
programmes. Elle documentera le financement, pas les études.

Point de vigilance : la candidature passe par l'ambassade du Japon dans le pays
d'origine ou par la recommandation de l'université. **La voie applicable à un
candidat ivoirien reste à vérifier** avant d'extraire cette information.

### EduCanada : un moteur de recherche, mais une exception à ne pas ignorer

Les deux pages répondent 200 et chargent 24 Ko de HTML, ce qui paraît
prometteur. En réalité :

* 0 tableau sur les deux pages ;
* la page des programmes ne contient même pas le mot « Master » ;
* ajouter des paramètres à l'URL ne change rien (24 638 car. dans les deux cas).

C'est un moteur de recherche : la base de programmes d'EduCanada est chargée
après exécution de JavaScript.

**Exception** : la page des bourses contient un lien de fiche réel,
`/scholarships-bourses/non_can/bcdi2030.aspx` (« Canadian International
Development Scholarships 2030 »). Ce lien est un point d'entrée possible vers
des pages de détail statiques. Il a été trouvé par `src/scraper.py`, pas par
l'inspection manuelle initiale : les deux pages d'EduCanada ne se valent donc
pas, et il ne faut pas les écarter ensemble.

### DAAD : formulaire, pas liste

Les 5 `<select>` étaient vides lors du premier relevé : les résultats étaient
injectés par JavaScript. Au dernier test ils sont **remplis**, mais la page
reste un formulaire de recherche (1 `<form>`, 3 `<input>`) dont les résultats ne
sont pas dans le HTML initial. Le constat fait sur `www.daad.de` (application
Nuxt, API interne `api.daad.de` non documentée) est confirmé sur `www2.daad.de`.

Verdict : `a_tester`. Il faut soumettre le formulaire pour aller plus loin, ce
qui n'est pas encore fait.

DAAD reste une source de référence pour un humain, mais pas pour ce programme.

### Erasmus Mundus : bonne page, mauvais type

La page explique très bien les bourses (1 400 € par mois,BJ 1 400 € par mois,
candidatures mondiales), mais les 29 liens sont surtout des variantes de
langue. Le catalogue réel est derrière « Search and apply ».

Le catalogue officiel de l'agence exécutive européenne est plus exploitable :

| | |
| --- | --- |
| URL | `https://www.eacea.ec.europa.eu/scholarships/erasmus-mundus-catalogue_en` |
| Mesures | 200, 184 549 car., HTML statique |
| Statut | **Validée** |

Elle contient des programmes correspondant aux domaines du profil :
cybersécurité, réseau, télécommunications. À ajouter en priorité.

### Chine : deux sources inaccessibles

`campuschina.org` ne résout pas depuis cet environnement.
`studyinchina.csc.edu.cn` répond 412, ce qui correspond à un blocage
anti-robot. À retester avant de conclure définitivement, car cela peut
dépendre du réseau d'origine.

---

# 4. Catégorie 3 — Portails spécialisés

Les deux sources de `config/sources.json` dans cette catégorie sont
inaccessibles. Les portails les plus connus ne sont pas plus utilisables que
les sources officielles, alors qu'ils sont moins fiables (docs §9).

| Portail | URL | Statut | Verdict |
| ------- | --- | ------ | ------- |
| Campus China | `https://www.campuschina.org/` | erreur de connexion | Écarté |
| Study in China – CSC | `https://studyinchina.csc.edu.cn/` | HTTP 412 | Écarté |
| Mastersportal (DAAD) | `https://www.mastersportal.com/` | HTTP 403 | Écarté, bloque les robots |
| ScholarshipOwl | `https://www.scholarshipowl.com/` | 200, application Nuxt | Écarté, JavaScript |
| MasterStudies | `https://www.masterstudies.com/` | HTTP 403 | Écarté, bloque les robots |
| Studyportals | `https://www.studyportals.com/` | 200, quasi vide en statique | Écarté |

**Conclusion de catégorie : les portails spécialisés sont la catégorie la moins
rentable du projet.** Les categories 1 et 2 doivent être renforcées en priorité.

---

# 5. Bilan de la validation

Mesuré le 27 septembre 2026, par quatre exécutions successives de
`python src/scraper.py` le même jour. Les quatre ont donné le même tableau.

| Verdict | Nombre | Sources |
| ------- | ------ | ------- |
| `exploitable` | 7 | TUM, NTNU, KAIST – Eligibility, UBC, EduCanada – Bourses, Study in Japan – MEXT, EACEA |
| `a_tester` | 10 | KAIST – Explore Programs, KAIST – Scholarship, EduCanada – Programmes, DAAD, Study in Japan x2, Study in Korea x2, Study in Norway, Erasmus Mundus |
| `bloque` | 2 | Campus China, Study in China – CSC |
| `injoignable` | 0 | — |

Ce tableau est une **mesure**, pas une propriété permanente. Un site peut
changer de verdict d'un jour à l'autre, et les deux sources chinoises l'ont fait :
elles répondaient `HTTP 412` les quatre fois le 27 septembre, et Campus China ne
répondait plus du tout deux jours plus tôt, sur quatre tentatives et sur les deux
schémas. La sortie de `src/scraper.py` fait foi sur l'état du jour.

Trois nuances que le tableau ne montre pas :

* **Les deux sources chinoises ne sont pas exploitables, quel que soit le
  verdict affiché.** `bloque` signifie qu'un script ne passe pas, `injoignable`
  que le serveur ne répond plus. Aucune des deux situations ne se surveille, et
  un site qui passe de l'une à l'autre ne peut pas être suivi. C'est la situation
  la moins favorable des deux qui compte, donc les deux sont écartées ;

* **Deux sources implémentées sont classées `a_tester` alors qu'elles
  produisent des opportunités.** KAIST – Explore Programs et KAIST –
  Scholarship le sont pour la même raison : le validateur cherche des tableaux
  et des liens de fiche, or KAIST présente ses programmes dans un accordéon et
  ses bourses dans des paragraphes suivis de listes. C'est pourquoi le tableau
  les suit d'une mention `[impl.]` : le verdict décrit la page, pas ce que le
  programme sait faire. Les deux questions sont différentes et ne doivent pas
  être confondues ;
* **EduCanada – Bourses ressort `exploitable`** grâce à un lien de fiche réel
  (`bcdi2030.aspx`) que l'inspection manuelle avait raté. Les deux pages
  EduCanada ne se valent pas.

Sur les 12 sources du registre d'origine, une seule est directement
exploitable. C'est un résultat décevant mais il vaut mieux le savoir maintenant :
ces 10 portails gouvernementaux sont des moteurs de recherche, pas des listes.

---

# 6. Information disponible selon la source

docs/README.md §7 impose de ne pas inventer une information absente. Ce qui
suit sépare donc deux choses qu'il ne faut pas confondre : ce qui a été
**mesuré** en implémentant une source, et ce qui est **attendu** d'après le
validateur pour une source pas encore lue.

## 6.1 Mesuré, sur les sources implémentées

Ces chiffres viennent d'une exécution réelle, pas d'une inspection visuelle.

| Information | TUM (10) | KAIST programmes (36) | KAIST bourses (3) | EACEA (20) | NTNU (41) |
| ----------- | -------- | --------------------- | ----------------- | ---------- | --------- |
| `title` | 10/10 | 36/36 | 3/3 | 20/20 | 41/41 |
| `university` | config | config | config | config | config |
| `country` | config | config | config | config | config |
| `degree` | 10/10 | 36/36 | 0/3 | 0/20 | 0/41 |
| `field` | 0/10 | 26/36 | 0/3 | 0/20 | 0/41 |
| `description` | 10/10 | 0/36 | 3/3 | 20/20 | 0/41 |
| `url` | 10/10 | 36/36 | 3/3 | 20/20 | 41/41 |
| `source` | 10/10 | 36/36 | 3/3 | 20/20 | 41/41 |
| `deadline` | 0/10 | 0/36 | 0/3 | **0/20** | 0/41 |
| `funding_type` | 0/10 | 0/36 | 3/3 | 0/20 | 0/41 |
| `language` | 0/10 | 0/36 | 0/3 | 0/20 | 0/41 |
| `eligibility` | 0/10 | 0/36 | 3/3 | 0/20 | 0/41 |

La colonne NTNU a été mesurée le 29 septembre 2026 sur le HTML téléchargé, en
faisant tourner `src/scraper.py` : 41 lignes, dont 3 lignes d'en-tête sans lien,
donc 41 opportunités. Le titre est lu dans le lien et non dans la cellule, pour
une raison mesurée : dans la cellule, 11 titres sur 41 se terminent par le
marqueur d'une note de bas de page, `²` ou `¹`.

Trois corrections que ces chiffres imposent :

* **`language` n'est publié par aucune source active.** Le critère existe dans
  le code et fonctionne, mais il ne peut pas être validé sur une vraie page
  tant qu'une source ne le renseigne pas ;
* **`deadline` n'est exploitable sur aucune source active.** NTNU en publie
  une, `1 March`, sans l'année. Une date sans année n'est pas une date, et
  l'écrire dans une fiche ferait croire à une date. Voir §6.2 et §2.1 ;
* le `degree` d'EACEA est vide, mais ses titres contiennent « Master ». Le
  critère `diplome` lit donc le titre quand le champ dédié est absent, en
  disant dans la raison lequel des deux il a lu. C'est une information
  publiée, pas une devinette.

Le `degree` de KAIST contient trois valeurs (`Master's`, `Master's-Ph.D.
Integrated`, `Ph.D.`). Ce n'est pas une ambiguïté, c'est ce que la page publie,
et `matches.py` les distingue.

## 6.2 Attendu, sur les sources validées mais pas encore lues

Ces colonnes viennent du validateur, qui compte les tableaux et les liens de
fiche. Elles annoncent ce qu'il faut aller vérifier, pas ce qui est acquis.

NTNU en est sortie : elle est implémentée depuis la V0.11 et sa colonne est
au §6.1. Le tableau ci-dessous annonçait `degree: oui` et `language: oui` pour
elle ; la mesure donne 0/41 sur les deux.

| Information | UBC | MEXT |
| ----------- | --- | ---- |
| `title` | oui | oui |
| `degree` | oui | non |
| `field` | à déduire | non |
| `deadline` | **non** | **non** |
| `funding` | à vérifier | non |
| `language` | à vérifier | oui |
| `eligibility` | non | oui |

## 6.3 La deadline : mesurée, pas supposée

Ce tableau annonçait `deadline: oui` pour EACEA et MEXT. **C'était faux.** La
colonne du validateur comptait la présence de liens, pas la présence de dates.

Deux pistes ont été vérifiées le 2026-09-26. Aucune des deux n'aboutit, mais
elles ne sont pas closes de la même façon, et la distinction compte.

**D'abord, une coquille JavaScript ne se mesure pas comme une page.** Une page
qui répond 200 avec 170 Ko et zéro année peut être soit une page qui ne parle
pas de dates, soit une page dont le contenu n'est pas dans le HTML. La part de
texte visible par rapport à la taille de la page départage les deux.

| Page | HTTP | Ko | Texte visible | Part | Années | Contenu réel |
| ---- | ---- | -- | ------------- | ---- | ------ | ------------- |
| EACEA, catalogue | 200 | 180 | 24 Ko | 13 % | 12 | oui |
| MEXT, page des bourses | 200 | 28 | 10,6 Ko | 37 % | 0 | oui |
| EACEA, fiche projet Erasmus+ | 200 | 167 | 2,7 Ko | 1,6 % | 0 | **non, coquille JS** |
| Erasmus+, opportunities | 200 | 184 | 2,5 Ko | 1,4 % | 0 | **non, coquille JS** |

Les deux premières pages ont un contenu réel et ne publient aucune date limite.
Les deux dernières ne sont pas lisibles par une simple requête, donc leur
« zéro occurrence » ne prouve rien : c'est un artefact de lecture, pas une
propriété de la source. **C'est la correction à retenir de cette section.**

**Ensuite, la piste AUF est fermée.** Les quatre URL testées répondent `HTTP
403` : le portail bloque les requêtes automatisées. Ce n'est pas une piste
prometteuse, c'est une source écartée, comme `MasterStudies` en §4.

**Reste la piste Erasmus+, et elle est partiellement ouverte.** Le service que
la page appelle lui-même a été trouvé en lisant le code de l'app Vue :

```text
https://ec.europa.eu/programmes/service/search/project/search
```

Il répond, sans authentification, avec un corps qui contient un index
(`eplus2021`). Il rend **345 302 projets** avec de vraies dates :

```text
projectName            2024-2-SK02-KA152-YOU-000258278
projectTitle           Staying alive
projectStartDate       2024-09-08T22:00:00.000+0000
projectEndDate         2025-09-07T22:00:00.000+0000
projectPublicationDate 2024-10-15T10:29:49.504+0000
projectCallYear        2024
```

Mais ce sont des **dates de vie d'un projet financé**, pas des dates de
candidature : `projectStartDate` dit quand la mobilité a commencé, pas quand un
étudiant pouvait postuler. Sur ces enregistrements, `dateDeadline` et
`dateOpening` sont **absents**, alors que le modèle de l'app Vue les prévoit :
ils appartiennent aux *appels à projets*, une autre famille d'enregistrements
dont le service n'a pas été trouvé.

Deux raisons de ne pas en faire une source, donc, même si le service
fonctionne :

* ce sont des projets, pas des programmes de Master. Une mobilité de jeunes
  intitulée « Staying alive » n'est pas une opportunité d'études ;
* les seules dates disponibles sont des dates de projet, qui ne rempliraient
  pas le critère `deadline` sans déformer son sens.

**Conclusion, qui n'a pas changé mais qui est maintenant mesurée :** le critère
`deadline` n'est pas implémentable avec le registre actuel. Ce n'est pas un
critère difficile à écrire, c'est un critère sans donnée. Écrire un lecteur de
dates dans ces conditions produirait du code jamais exécuté sur une vraie
valeur, exactement comme l'extraction de `funding_amount` a été refusée.

Conséquence sur le profil : `preferences.application_deadline_after` n'est
donc utilisée par rien. Elle est laissée dans `config/profile.json` parce
qu'elle est vraie et qu'elle le sera le jour où une source publication des
dates.

**La piste qui reste ouverte** est celle des pages qui listent des dates dans
leur HTML : les pages de département d'université, et les portails qui
ressemblent à une liste statique. C'est le profil des sources qui ont déjà
réussi, TUM et KAIST. Elle ne se vérifie pas à l'avance : il faut la
rencontrer.

## Le cas du parseur dédié

Si la structure HTML d'une source est impossible à exprimer en sélecteurs CSS,
c'est le signal qu'il faut un parseur dédié, et non une approximation fragile.
Ce cas s'est présenté, et il n'a pas été contourné.

**La page Scholarship de KAIST** (`KAIST - Scholarship`) écrit chaque bourse
ainsi :

```text
<p>KAIST Global Presidential Scholarship (KGPS)</p>
<ul>
  <li><span>Departments Accepting Applications:</span><span>...</span></li>
  <li><span>Admission Periods:</span><span>...</span></li>
  <li><span>Eligibility Requirements:</span><span>...</span></li>
  <li><span>Benefits:</span><span>...</span></li>
</ul>
```

Le nom et les détails sont deux éléments frères. Aucun sélecteur ne peut les
apparier. La source déclare donc `"parser": "kaist_scholarship"` dans
`config/selectors.json`, et `scraper.py` charge `src/parsers/kaist_scholarship.py`
à la place de la lecture générique. `scraper.py` reste ainsi ignorant du
contenu de la page.

Deux décisions prises pour ce parseur, à ne pas confondre :

* `funding_type` reçoit le texte `Benefits` **tel qu'il est écrit**, montant
  compris : « Full tuition coverage and a monthly stipend of 1,000,000 KRW ».
  `funding_amount` reste `None`. Extraire un nombre d'une phrase demande une
  recherche de motif dans du texte libre, donc du code fragile ; ce sera
  discuté séparément ;
* `deadline` reste `None`. « Admission Periods: Spring/Fall Early/Fall
  Regular » décrit des cycles, pas une date.

Un cas reste ouvert et assumé : le **collège** de KAIST n'est pas extractible.
Il est écrit dans un `<h4>` qui est frère du `<ul>` parent, donc hors de portée
d'un sélecteur. Il n'a pas été deviné.

## Ce que la page Scholarship a appris sur le reste du projet

Cette page a produit trois enseignements qui ne concernent pas KAIST.

**Un critère peut dépendre du type d'opportunité.** Une bourse n'annonce pas de
matière. Exiger un domaine d'une bourse écarte toutes les bourses, ce qui est
arrivé : les 3 bourses étaient rejetées, dont deux sont des prises en charge
complète des frais. La correspondance porte maintenant deux listes de critères,
une par type. Voir `docs/VERSIONS.md` V0.3.

**Les pages n'utilisent pas les mêmes caractères que le code.** KAIST écrit
« Master’s » avec une apostrophe typographique. Une règle construite sur
l'apostrophe ASCII ne s'applique pas à la même chaîne, si bien que la bourse de
Master était rejetée comme doctorale. Les apostrophes sont normalisées avant
toute comparaison.

**Un sous-chaîne n'est pas un mot.** « undergraduate » contient « graduate ».
Une bourse de premier cycle serait passée pour une bourse de Master. Les
niveaux de diplôme sont donc cherchés mot entier.

## Une décision de profil à ne pas défaire

`Infrastructure Security` a pour termes faibles « Resilient Infrastructure » et
« Smart Infrastructure ». Ils font correspondre *Civil and Environmental
Engineering* et *Graduate School of Mobility* à 45 points, qui sont des
programmes de génie civil et non de sécurité.

C'est **voulu** : ces domaines font partie du profil de l'étudiant, et
l'infrastructure est un sujet qu'il suit. Ces correspondances contextuelles
sont signalées comme telles dans les raisons, ce qui permet de les voir et de
les écarter d'un regard. Ne pas les « corriger » en retirant les termes : ce
serait supprimer une décision du profil à cause d'un classement imparfait.

---

# 8. Répartition dans le code

Deux fichiers de configuration, deux rôles. Les séparer permet d'inscrire une
source dans le cahier des charges avant de savoir la lire.

| Fichier | Rôle | Contenu |
| ------- | ---- | ------- |
| `config/sources.json` | le cahier des charges | `name`, `category`, `country`, `type`, `url`, `enabled` |
| `config/selectors.json` | la technique d'extraction | `name`, `university`, `base_url`, `selectors`, et `parser` pour les sources qui ne s'expriment pas en sélecteurs |

`src/scraper.py` croise les deux par le champ `name`. Une source n'est scrapée
que si elle satisfy les deux conditions :

```text
enabled = true   ET   présente dans config/selectors.json
```

Conséquence : les sources sans bloc de sélecteurs sont ignorées sans erreur.
C'est voulu, ce sont des sources décidées mais pas encore lues.

### 8.1.1 Ce que la veille lit aujourd'hui

Mesuré le 29 septembre 2026 sur les deux fichiers de configuration, après
l'activation de NTNU :

| Ensemble | Nombre |
| -------- | ------ |
| sources inscrites au registre | 19 |
| activées | 17 |
| désactivées | 2 |
| avec un bloc dans `config/selectors.json` | 5 |
| activées et sans bloc de sélecteurs | 12 |
| sans bloc de sélecteurs, activées ou non | 14 |

La veille lit donc 5 sources sur 19, et 5 sur 17 activées. Les 14 autres sont
des sources dont l'URL a été vérifiée sans que leur structure HTML l'ait été,
ce que §1.2 explique.

Le compte des 12 activées sans bloc ne bouge pas, et c'est un détail qui
mérite d'être dit : NTNU entre dans les deux ensembles au même moment, comme
source activée et comme source lue. Une source qui n'aurait reçu qu'un bloc
serait passée à 13. C'est aussi pourquoi la ligne de journal ci-dessous est
inchangée alors que trois nombres du tableau viennent de changer.

Depuis la V0.7, la veille écrit ce décompte dans son journal, sur une ligne :

```text
Sources sans sélecteurs : 12 activées et non lues, voir docs/SOURCES.md §8.
```

Avant cette version, rien ne le disait. Une source lue et une source jamais
lue produisaient le même journal, donc la veille pouvait n'en lire qu'une sur
quatre sans que ni les données ni le message du jour ne le montrent.

La catégorie 3 (`portail_specialise`) est vide dans le registre, voir §4.

## 8.1 Les clés d'un bloc de sélecteurs

Toutes les clés sauf `item`, `title` et `url` sont facultatives. Une clé absente
signifie « cette page ne publie pas cette information », jamais « chercher plus
tard ». Le programme ne comble rien (docs/README.md §7).

| Clé | Rôle | Obligatoire | Notes |
| --- | ---- | ----------- | ----- |
| `item` | sélectionne un bloc par programme | oui | TUM `article.list-teaser`, KAIST `ul.ul-accordion > li` |
| `title` | texte du titre | oui | |
| `url` | lien vers le programme | oui | **sans lien, l'opportunité est écartée** |
| `degree` | diplôme(s) | non | plusieurs valeurs possibles, elles sont jointes par une virgule |
| `field` | domaines de recherche | non | KAIST en publie, TUM non |
| `description` | texte libre | non | TUM oui, KAIST non |

Un programme sans `url` est jeté : une opportunité non cliquable ne peut être ni
vérifiée par l'étudiant, ni notifiée utilement. C'est la seule raison pour
laquelle une opportunité est abandonnée au lieu d'être complétée.

---

# 9. Règle de mise à jour

Toute nouvelle source suit la procédure :

1. vérifier l'URL avec une simple requête HTTP ;
2. **vérifier que des opportunités sont présentes dans le HTML**, et pas
   seulement un formulaire de recherche ;
3. vérifier que le mot-clé d'un domaine du profil apparaît dans la page ;
4. si la page est un index, tester une ou deux sous-pages ;
5. noter la source et son statut dans ce document ;
6. inscrire la source dans `config/sources.json` avec `enabled: false` ;
7. seulement ensuite, écrire les sélecteurs dans `config/selectors.json` ;
8. mesurer le remplissage de chaque sélecteur sur la page réelle, et le noter ;
9. passer `enabled` à `true` quand la source a été testée.

Aucune source n'est scrapée avant d'être notée ici.

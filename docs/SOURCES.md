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

Le dernier bilan : 7 sources `exploitable`, 9 `a_tester`, 2 `bloque`.

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
| Mesures | 200, 94 713 car., 3 tableaux, aucun JavaScript |
| Statut | **Validée** |

Correspondance avec le profil : excellente.

* `Digital Infrastructure and Cyber Security` ;
* `Cybersecurity and Assurance` (Erasmus Mundus) ;
* `Engineering and ICT`.

La page distingue les programmes ouverts aux candidats non UE/EEE de ceux
réservés aux candidats UE/EEE. C'est exactement la distinction utile pour un
candidat ivoirien.

Limite : les dates limites ne sont pas dans la page de liste.

### KAIST (Corée du Sud)

Programmes :

| | |
| --- | --- |
| URL | `https://admission.kaist.ac.kr/intl-graduate/Discover/ExplorePrograms` |
| Mesures | 200, 110 Ko, HTML statique, 36 programmes |
| Statut | **Implémentée en V0.2** |

Contient notamment une `Graduate School of Information Security`, ainsi que des
domaines réseau et télécommunications. Correspondance excellente.

La page est un accordéon statique : 5 collèges, 36 programmes, sans aucun
JavaScript. Les sélecteurs sont dans `config/selectors.json`, et le remplissage
a été mesuré :

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
  fiche de programme comme chez TUM. La notificationyclique moins précisément ;
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
| Campus China | scholarships | HTTP 412 | Bloqué |
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

| Verdict | Nombre | Sources |
| ------- | ------ | ------- |
| `exploitable` | 7 | TUM, NTNU, KAIST – Eligibility, UBC, EduCanada – Bourses, Study in Japan – MEXT, EACEA |
| `a_tester` | 10 | KAIST – Explore Programs, KAIST – Scholarship, EduCanada – Programmes, DAAD, Study in Japan x2, Study in Korea x2, Study in Norway, Erasmus Mundus |
| `bloque` | 2 | Campus China, Study in China – CSC |

Deux nuances que le tableau ne montre pas :

* **Trois sources implémentées sont classées `a_tester` alors qu'elles
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

docs/README.md §7 impose de ne pas inventer une information absente. Ce tableau
indique ce que chaque source retenue peut réellement fournir.

| Information | TUM | NTNU | KAIST | EACEA | UBC | MEXT |
| ----------- | --- | ---- | ----- | ----- | --- | ---- |
| `title` | oui | oui | oui | oui | oui | oui |
| `university` | config | config | config | à extraire | config | non |
| `country` | config | config | config | à extraire | config | non |
| `degree` | oui | oui | oui, 3 valeurs | oui | oui | non |
| `field` | non | à déduire | oui, 26/36 | à déduire | à déduire | non |
| `url` | oui | oui | site du département | oui | oui | oui |
| `source` | oui | oui | oui | oui | oui | oui |
| `deadline` | non | non | non | oui | non | oui |
| `funding` | non | à vérifier | à extraire | oui | non | oui |
| `language` | non | oui | oui | oui | à vérifier | oui |
| `eligibility` | non | oui | oui | oui | non | oui |

Deux corrections apportées après implémentation de KAIST :

* `deadline` n'est **pas** sur la page de KAIST. Elle indique que les cycles
  d'admission varient et renvoie vers un tableau d'affichage. Extraire une
  date depuis cette page reviendrait à inventer ;
* `degree` contient trois valeurs (`Master's`, `Master's-Ph.D. Integrated`,
  `Ph.D.`). Le choix se fera en V0.3, pas au moment de l'extraction.

Ce tableau ne couvre pas la page Scholarship de KAIST, qui n'a pas les mêmes
champs : elle ne publie ni domaine, ni diplôme, ni date limite, mais elle
publie `funding` et `eligibility`, que les autres sources donnent plus
rarement. Le détail est dans §7.

Conséquence pour la V0.3 : la correspondance ne peut pas reposer sur `field`
pour TUM et UBC. Elle compare le titre, le domaine et la description aux
domaines du profil. C'est le rôle de `src/matches.py`, écrit, mais qui ne
retient pour l'instant que trois critères : domaine, diplôme et pays.

---

# 7. Ordre d'implémentation recommandé

Une version doit fonctionner avant la suivante (docs/VERSIONS.md).

| Ordre | Source | Raison |
| ----- | ------ | ------ |
| 1 | TUM | **Faite** en V0.2, sert de référence technique |
| 2 | KAIST programmes | **Faite** en V0.2, 36 opportunités, correspondance directe au profil |
| 2 | KAIST bourses | **Faite**, 3 bourses, premier cas de parseur dédié |
| 3 | NTNU | Correspondance optimale, information d'éligibilité UE/EEE |
| 4 | EACEA catalogue | Source officielle, bons rendements |
| 5 | UBC | Le plus gros volume |
| 6 | Study in Japan – MEXT | Seule source de financement déjà validée |
| 7 | Study in Norway, sous-page ICT | Piste non explorée, à valider d'abord |

Les deux premières étapes sont terminées sans une seule ligne de code propre à
un site dans `src/scraper.py` : KAIST n'a demandé qu'un bloc JSON de plus. C'est
la preuve que l'architecture tient.

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

Conséquence : les 16 sources du registre qui n'ont pas encore de sélecteurs sont
ignorées sans erreur. C'est voulu, ce sont des sources décidées mais pas encore
lues.

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

Un programme sans `url` estjeté : une opportunité non cliquable ne peut être ni
vérifiée par l'étudiant, ni notifiée utilement. C'est la seule raison pour
laquelle une opportunity est abandonnée au lieu d'être complétée.

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

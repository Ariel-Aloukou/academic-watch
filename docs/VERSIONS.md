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

## Le piège de « international students »

Le même raisonnement que pour « undergraduate » s'est reproduit sur un autre
mot, et dans l'autre sens. Une bourse qui écrit « Open to international
students » contient, comme sous-chaîne, « national student ». Cherchée à la
sous-chaîne, la restriction nationale était donc trouvée, la bourse perdait ses
25 points, et elle était écartée comme réservée aux nationaux.

C'est le critère `international`, celui qui décide si l'étudiant ivoirien peut
en profiter, qui était le plus fragile des quatre : une erreur le fait manquer
plutôt que de laisser passer à tort une bourse qui ne lui est pas destinée. Les
trois bourses de KAIST y échappaient par chance, la page écrivant
« applicants ».

La correction et sa non-régression sont décrites au chapitre V0.4, qui les a
trouvées. Elle ne change rien aux 69 opportunités réelles.

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

**231 tests**, tous passants, dans `tests/`, lancés par `python -m pytest`. Ils
couvrent le cas nominal et surtout ce qui brise une sauvegarde : fichier tronqué,
JSON valide mais pas une liste, `seen.json` au mauvais format, première
exécution, dossier absent, opportunité qui change de diplôme, titre accentué ou
non, deux sources de même titre, et deux collectes identiques dont le fichier
doit rester identique.

Sur les données réelles : 69 fiches après la première exécution, 69 nouvelles
annoncées, puis 0 nouvelle et 69 fiches à la seconde. Le programme est
idempotent.

## Ce que les tests ont trouvé

Écrire les tests dans le dépôt a immédiatement produit un défaut que la relecture
n'avait pas vu.

**Une bourse entièrement ouverte était comptée comme réservée aux nationaux.**
`mesure_international` cherchait « national student » par sous-chaîne, et
« international students » contient « national student ». La formule la plus
courante du monde était donc confondue avec son contraire, la bourse perdait ses
25 points, et elle était écartée alors qu'elle est ouverte à tout le monde.

Les trois bourses de KAIST y échappaient **par chance** : la page écrit
« Open to international applicants », et « applicants » ne contient pas
« national student ». Le défaut était donc latent, invisible sur les données
réelles, et il aurait mordu au premier site écrivant « students ». La recherche
se fait maintenant par mot entier, comme pour les niveaux de diplôme.

Le test de non-régression et son contre-test sont dans
`tests/test_correspondance.py`. La correction ne change rien aux 69 opportunités
réelles : vérifié par empreinte SHA-256 de `data/`, identique avant et après.

**Un type sans budget était annoncé avec le budget d'un autre.** Le registre
déclare `eligibility` pour « KAIST – Eligibility Requirements », un type qui
n'a pas de budget. La page était notée comme un programme, mais affichée avec le
libellé « eligibility » : un score de 100 maximum et un nom de type qui ne
correspondent pas. `evaluer` renvoie maintenant le type dont le budget a
réellement été appliqué. Le type d'origine reste sur l'opportunité et dans la
fiche sauvegardée, rien n'est perdu.

**`mesure_niveau` avait un repli non documenté.** Elle lisait le diplôme et le
titre en plus de l'éligibilité, sans le dire. C'est désormais écrit dans le
module, avec la même justification que `mesure_diplome` : un diplôme publié est
une information, pas une devinette.

## Les tests sont dans le dépôt

`pytest.ini` déclare `pythonpath = src` et `testpaths = tests`. La première
option évite d'ajouter `sys.path` dans chaque fichier de test, la seconde évite
que pytest aille chercher des tests dans `venv/`. Les dépendances sont dans
`requirements-dev.txt`, **pas** dans `requirements.txt` : le programme n'a pas
besoin de pytest pour fonctionner.

Un `conftest.py` existe malgré tout, pour une seule chose : rediriger les chemins
d'écriture de `storage` vers un dossier temporaire, pour tous les tests sans
exception. Un test qui écrirait dans le vrai `data/` détruirait l'historique du
dépôt, et cela ne se verrait qu'après un commit.

Cinq fichiers, chacun avec une raison d'être :

| Fichier | Ce qu'il surveille |
| ------- | ------------------ |
| `test_storage.py` | la sauvegarde, l'identité, le refus d'un fichier illisible |
| `test_correspondance.py` | les paliers, le diplôme, les bourses, les contrats du module |
| `test_donnees.py` | la cohérence des deux fichiers versionnés |
| `test_workflow.py` | les choix écrits du workflow, le seul fichier non lançable ici |
| `test_proprete.py` | l'encodage et les caractères glissés dans les fichiers |

Aucun test ne touche au réseau. Ce qui dépend d'une page vivante est vérifié à
la main et écrit dans `docs/SOURCES.md` : un test qui dépend d'un site étranger
échoue pour une raison qui n'a rien à voir avec le code.

`tests/test_donnees.py` porte sur les vraies données, et il les relit sans les
modifier. `tests/test_proprete.py` mérite une explication, parce qu'elle est
contre intuitive. Un test de propreté qui échoue oblige à reformater des
fichiers qu'on n'a pas choisi de reformater, et `config/profile.json` est le
travail de l'étudiant : lui imposer une largeur de colonne serait disposer de
son travail. Le fichier ne contient donc que des défauts qui cassent quelque
chose, tous déjà satisfaits par le dépôt. C'est ce qui le rend utilisable comme
garde-fou plutôt que comme prétexte.

Les tests sont exécutés par le workflow avant chaque collecte. C'est un choix
assumé : la veille s'arrête quand le code est cassé, plutôt que d'écrire des
données fausses. Le runner signale l'échec par une notification, donc l'arrêt
reste visible.

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

## La décision : ce qui est signalé

Deux réponses étaient possibles, et la question a été posée plutôt que décidée
dans le code.

**Seulement les retenues jamais montrées.** Le run quotidien affiche « rien de
nouveau » en trois lignes. Son défaut est qu'elle se tait sur ce qui change.

**Les retenues nouvelles, plus celles dont les données ont changé.** C'est celle
qui est implémentée. Une bourse qui publie une date limite ou un montant deux
semaines après son annonce mérite d'être re-signalée : c'est exactement
l'information qu'un étudiant vient chercher, et c'est la seule qu'il ne reverra
pas en relisant la même page.

Une opportunité qui ne correspond pas au profil n'est jamais signalée, même
lorsqu'elle est nouvelle. Une veille est une sélection, pas un catalogue :
`main.py` ne présente donc que les opportunités retenues.

## État mesuré

Trois exécutions réelles sur les 69 fiches, et non un exemple inventé :

| Situation | Sortie |
| --------- | ------ |
| `data/seen.json` vidé | `9 à signaler : 9 nouvelles` |
| exécution suivante, rien n'a bougé | `Rien de nouveau : les 9 opportunités qui correspondent au profil ont déjà été montrées.` |
| une URL modifiée à la main dans `opportunities.json` | `1 à signaler : 1 mise à jour` |

Les trois fois, code de retour 0 et `stderr` vide. Au troisième cas, la donnée
écrite à la main est remplacée par la valeur réellement collectée : le
programme ne fabrique rien, il constate.

Ce que la version précédente affichait sur les mêmes fiches : **768 lignes**,
les 69 opportunités répétées en entier. La version actuelle affiche 11 lignes
après le profil dans le cas courant, et 156 quand les 9 retenues sont
signalées. La réduction ne vient pas d'un filtrage : le détail des 69 fiches
était affiché, il ne l'est plus. Il reste dans `data/opportunities.json`, et le
compte est toujours dit.

## Les trois mensonges que la version doit éviter

Une fonction qui décide ce qu'on annonce se juge sur les phrases qu'elle
produit, pas sur le code qu'elle écrit. Trois cas produisent ici une
affirmation fausse, et les trois sont traités.

**« Mise à jour » sur une opportunité que personne n'a jamais vue.** Une
opportunité collectée la veille, écartée par le profil, et dont la page change
aujourd'hui : elle n'est pas dans `seen.json`, donc rien n'a été mis à jour pour
l'étudiant. Elle est nouvelle. C'est la raison pour laquelle `modifiees_depuis`
exige les deux conditions, déjà montrée *et* modifiée, et les deux listes
sont disjointes par construction : rien n'est compté deux fois.

**Un compte de nouvelles qui serait un compte de collectées.** `sauvegarder`
rend les identités absentes de `opportunities.json`, donc ce que le programme
n'avait jamais *collecté*. C'est un autre compte, et il reste affiché sous son
vrai nom, dans la section « Sauvegarde ».

**Une information perdue parce qu'elle a déjà été affichée.** Le changement est
détecté au moment de la sauvegarde, parce que c'est là que la version précédente
de la fiche existe encore. Le `Bilan` qui le porte est donc consommé avant
l'affichage : si le programme s'arrête entre les deux, la mise à jour est
perdue pour cette fois. Le cas est mesuré et non traité.

## Ce que `sauvegarder` rend désormais

`sauvegarder` ne rendait qu'une liste, celle des nouvelles. Il rend maintenant un
`Bilan` à deux champs, `nouvelles` et `modifiees`. La comparaison qui produit la
seconde existait déjà dans cette fonction, au point où la version précédente de
la fiche est encore en mémoire : la faire ailleurs aurait obligé à relire le
fichier et à dupliquer `a_change`, donc à avoir deux règles qui divergent en
silence. La première divergence serait apparue comme une annonce fausse, sans
erreur.

Quatre tests nouveaux dans `test_storage.py` couvrent la distinction : la
modification d'une fiche déjà montrée est signalée, celle d'une fiche jamais
montrée ne l'est pas, une collecte identique ne signale rien, et les deux
listes ne se recouvrent pas. Les deux derniers sont ceux qui comptent tous
les jours. Trois tests existants ont reçu une assertion sur `modifiees`.

L'affichage a ses dix tests dans `tests/test_main.py`, un fichier créé pour la
V0.5 : c'est la seule version qui change ce que le programme montre, donc la
seule dont la sortie vaut d'être vérifiée. Le cas le plus important est le
plus courant : un jour sans nouveauté ne doit pas réimprimer les fiches déjà
lues, il doit dire qu'il n'y a rien et s'arrêter là.

## Écart avec le cahier des charges

Le cahier annonce un titre, « Nouvelles opportunités ». Le titre retenu est
« À signaler », et l'écart est assumé : une mise à jour n'est pas une nouvelle
opportunité, et l'annoncer sous ce titre serait faux. Le reste de l'exemple est
respecté, seuls les éléments non encore montrés sont listés.

Le cahier ne dit rien de l'ordre dans lequel les signaler. Les nouvelles
passent d'abord, parce que c'est ce que l'étudiant n'attendait pas. Elles
suivent l'ordre de collecte et ne sont pas triées par score : deux types
d'opportunités n'ont pas le même maximum, donc un tri par score brut
comparerait un 85 sur 100 à un 70 sur 100 sans que la comparaison ait un sens.
Trier par score relatif serait une décision à part, et elle n'est pas prise ici.

## Limites assumées

* **Une opportunité qui cesse de correspondre n'est pas signalée.** Changer
  `config/profile.json` peut faire tomber une retenue sous le seuil, et le
  programme ne le dira pas. Rien dans `data/` ne permet de savoir ce qui était
  retenu la dernière fois : `seen.json` ne contient que des identités.
* **Changer le profil signale comme mise à jour.** Le score fait partie de la
  fiche, donc un profil modifié change la fiche des retenues concernées et les
  signale. C'est le comportement voulu, le profil ayant changé l'information
  affichée n'est plus la même, mais le signal parle alors du profil et pas du
  site.
* **La mise à jour est consommée avant l'affichage.** Si le programme s'arrête
  entre la sauvegarde et l'affichage, elle n'est pas rejouée le lendemain.
* **Une fiche dont le titre est reformulé revient comme nouvelle.** C'est la
  conséquence de l'identité en trois champs, écrite en V0.4 et non mesurée
  depuis.

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

## La décision : le canal

Trois réponses étaient possibles, et la question a été posée plutôt que
décidée dans le code.

**Console seule**, ce que le cahier annonce en premier. C'est déjà fait : la
V0.5 affiche le signal et le résumé d'étape du workflow le recopie dans le
navigateur. Écrire `notifier.py` dans ce mode serait déplacer les `print` de
`main.py` vers un module vide.

**Un message externe, Telegram en tête.** Le cahier le cite en premier exemple.

**Un message externe par email.** C'est celui-ci qui est retenu, parce que c'est
le seul que la boîte aux lettres de l'étudiant ouvre déjà. Le résumé d'étape
suppose d'ouvrir un navigateur ; un email arrive tout seul, et il peut être lu
sans connexion.

Le port de soumission 587 est ouvert sur les runners GitHub, le 25 est le seul
bloqué, donc l'envoi fonctionne depuis l'exécution automatique. `smtplib` est
dans la bibliothèque standard : **aucun paquet ajouté**, `requirements.txt` ne
change pas.

L'email part **une fois par exécution, donc une fois par jour**, y compris les
jours où il n'y a rien de nouveau. La décision a été posée, et elle a un
coût : 365 messages par an. Son avantage est qu'un jour sans message se voit,
alors qu'un secret périmé est indiscernable d'une veille sans nouveauté.

## Un seul rendu, deux moyens

La décision de code la plus importante de la version : **le texte est produit
une fois**. `notifier.rendre()` rend le bulletin, la console l'affiche et
l'email l'envoie. Deux rendus de la même liste divergeraient au premier champ
ajouté, et la divergence se verrait dans la boîte de réception bien avant
d'être cherchée.

Le module est donc coupé en trois, et chaque morceau se teste seul :

| Fonction | Fait | Se teste par |
| -------- | ---- | ------------- |
| `rendre` | le texte | comparaison de chaînes, sans rien d'autre |
| `message` | les en-têtes et le corps | un dictionnaire de valeurs, sans réseau |
| `envoyer` | le transport | un objet passé en argument, qui note les appels |

Le découpage n'est pas une élégance. Les en-têtes sont là où vivent les erreurs
réelles : les accents, l'adresse, l'objet. Aucun test de cette partie n'a besoin
d'un serveur, donc aucun ne peut échouer pour une raison qui n'a rien à voir
avec le code. Le transport fait cinq lignes, et on le vérifie en passant un
autre objet en argument.

Le transport est un paramètre, `transport=smtplib.SMTP`, et non un remplacement
de `smtplib.SMTP` pendant les tests. La différence n'est pas de principe : un
`monkeypatch.setattr(notifier.smtplib, "SMTP", ...)` modifie le module de la
bibliothèque standard pour toute la session, et un test qui n'a rien à voir avec
la messagerie en hérite. Un paramètre se voit dans la signature, et le
programme se comporte normalement sans qu'on en parle.

## Ce que le message peut contenir, mesuré

Le cahier demande six champs. Comptés sur les 69 fiches de `data/` :

| Champ du cahier | Champ de la fiche | Publié |
| --------------- | ----------------- | ------ |
| titre | `title` | 69 / 69 |
| université | `university` | 69 / 69 |
| pays | `country` | 69 / 69 |
| deadline | `deadline` | **0 / 69** |
| financement | `funding_type` | 3 / 69, dont 2 des 9 retenues |
| lien | `url` | 69 / 69 |

Le message affiche donc cinq champs sur six, dont un pour deux opportunités sur
neuf. La ligne `Deadline` existe dans le rendu et n'est écrite que si la fiche
en porte une : aucune des quatre sources n'en publie, c'est mesuré page par page
et écrit dans `docs/SOURCES.md` §6.3.

Un champ absent n'est pas remplacé par un tiret, et il n'est pas remplacé par
`None`. Une ligne « Financement : — » ferait croire que la bourse ne finance
rien, ce qui est différent de ne pas le publier.

## L'ordre : notifier avant de mémoriser

`publier` est appelé **avant** `conserver_vus`. L'ordre inverse est plus
naturel — on enregistre ce qui a été montré, donc après l'avoir montré — et il
perdu l'information :

* avec l'ordre retenu, un run qui s'arrête entre les deux renvoie la même
  annonce au run suivant. Le doublon se voit et se corrige ;
* avec l'ordre inverse, l'opportunité est déjà marquée comme vue, personne ne
  l'a lue, et `seen.json` affirme le contraire. La perte ne se voit pas.

Le test qui verrouille cet ordre est dans `tests/test_main.py`. Il ne teste rien
de visible : deux étapes peuvent s'échanger en laissant un journal identique.

## L'échec d'envoi n'arrête pas la veille

Si l'envoi échoue, `publier` écrit une ligne et rend la main. Il ne lève pas
d'exception, et la raison est concrète : dans le workflow, une veille en échec
fait sauter l'étape qui commite `data/`. Une veille qui a réussi et un email
qui n'est pas parti ne doivent pas coûter la journée de données.

Le prix de ce choix est qu'un échec pourrait se perdre. Il est visible deux
fois : la ligne de statut nomme le type de l'erreur, et le workflow la recopie
dans le résumé d'étape.

## État mesuré

| Situation | Sortie |
| --------- | ------ |
| aucun secret défini | `Notification : console seule, il manque SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO` |
| envoi vers un port fermé | `Notification : email non envoyé (ConnectionRefusedError), la veille est complète` |
| 9 retenues à signaler | objet `Academic Watch 2026-09-27 : 9 nouvelles` |
| jour sans nouveauté | objet `Academic Watch 2026-09-27 : rien de nouveau` |

Les deux premiers cas ont été obtenus sur une collecte réelle de 69 fiches, avec
le code de retour 0, `stderr` vide et la section « Sauvegarde » présente. Dans
les deux, les empreintes de `data/` sont restées identiques à la référence
(`2fe23d52d0aa5b3a` et `79d5942237ecabe6`) : la notification n'écrit rien.

Les 308 tests passent en trois secondes, sans réseau. Ils étaient 253. Le
décompte par fichier : `test_notifier.py` 31, nouveau ; `test_main.py` 8, qui
étaient 10 et testaient l'affichage, désormais rendu ailleurs ; `test_workflow.py`
22, qui étaient 17 ; `test_proprete.py` 149, qui étaient 128.

« Sans réseau » n'était qu'une promesse jusqu'ici, tenue par la relecture. Cette
version ajoute un envoi d'email, donc un chemin par lequel un test pouvait se
retrouver à appeler le serveur d'Outlook : la couture existe, mais une couture
cassée est un test qui attend trente secondes avant de dire quelque chose de
faux. Une fixture automatique de `conftest.py` bouche maintenant les trois
sorties — `getaddrinfo`, `create_connection` et `connect` — et un test vérifie
qu'elles sont bouchées, parce qu'un garde-fou qu'on ne vérifie pas peut être
faux sans que personne le sache.

Le garde-fou a été éprouvé par mutation, pas seulement lu : la couture a été
cassée volontairement, une seule ligne, et les quatre tests d'envoi ont échoué
en 1,2 seconde, avec le message du garde-fou, sans `gaierror` et sans délai.
C'est le seul moyen de savoir qu'un garde-fou fonctionne.

## Défauts trouvés en construisant et en relisant la version

**« 1 mise » au lieu de « 1 mise à jour ».** Le compte appelait
`_compte(1, "mise", "mises à jour")` : le singulier passait par « mise » et le
pluriel par « mises à jour », alors que les deux formes s'accordent sur « mise »
et ne diffèrent qu'en « s ». Le pluriel était juste parce qu'il y en avait deux.
Le test qui l'a trouvé est le test au singulier, ajouté après. Il n'existait pas
avant le bug : le pluriel passait, donc le fichier était vert.

**Deux `def main()` dans le même fichier.** Un remplacement de bloc s'est arrêté
à la première occurrence de `def main():` et a laissé l'ancien `main()` sous le
nouveau, encore appelant deux fonctions supprimées. Python prend la seconde
définition sans un mot, le fichier est valide, et l'erreur n'apparaît qu'à
l'exécution sous la forme d'un `NameError` sur une fonction qui a bien été
supprimée. Un test dédié vérifie désormais qu'aucune fonction n'est définie deux
fois dans un même fichier. Il a été vérifié en réintroduisant le doublon : le
test échoue bien, en nommant `{'main': [63, 138]}`.

**Un test qui atteignait les imports du module testé.** La date fixe du test
écrivait `notifier.datetime(...)` et `notifier.timezone.utc` : le test passait
par ce que le module avait importé plutôt que par ce qu'il exposait. Le
fonctionnement était correct, mais la règle écrite à trois lignes plus haut
n'était pas vraie. Corrigé en important les deux classes depuis la bibliothèque
standard.

**Le test qui atteignait la bibliothèque standard.** Pour le faux serveur SMTP,
le test faisait `monkeypatch.setattr(notifier.smtplib, "SMTP", FauxSMTP)`, ce qui
modifie le module `smtplib` lui-même pour toute la session, y compris pour les
tests qui n'ont rien à voir avec la messagerie. C'est ce défaut, et non une
impression, qui a fait ajouter le paramètre `transport` décrit plus haut.

**Un test perdu sans que rien ne le dise.** Une correction d'accent a été écrite
dans un script passé en ligne de commande, où les index de liste sont décalés d'un
par rapport aux numéros de ligne. La ligne `def` d'un test a donc été écrasée par
le commentaire de la ligne du dessous, et `test_le_run_a_le_droit_d_ecrire` a
disparu de la collecte. Le fichier restait du Python valide, les 307 tests
passaient, et aucun avertissement n'était émis : une suite peut perdre une
protection sans que rien ne le signale. Le compte par fichier l'a montré, parce
que 21 tests dans un fichier qui en avait 22 ne voulait rien dire de spécial. Un
test perdu ne se voit que si on compte.

**Un scan qui rendait zéro sans rien lire.** Le scan de contamination lisait chaque
section de documentation entre son titre et le `---` suivant. Le `---` était
cherché depuis le début du fichier, donc il attrapait un séparateur situé bien plus
haut : les deux sections de documentation mesuraient zéro caractère, et le scan
annonçait « 0 signalement » sur du texte qu'il n'avait pas lu. Le résultat était
indiscernable d'un fichier propre. Depuis, la fin se cherche après le début, et un
script vérifie qu'une section fait bien plus de 200 caractères : une section vide
est un défaut de repérage, pas une propreté.

## Écarts avec le cahier des charges

Le titre du cahier est « Nouvelle opportunité ». La section s'appelle
« À signaler », comme en V0.5, pour la même raison : une mise à jour n'est pas
une nouvelle opportunité.

Le cahier annonce Telegram en premier exemple. C'est l'email, parce que c'est
le canal que l'étudiant a. Rien n'empêche d'ajouter Telegram plus tard : il
suffirait d'une fonction de plus dans `notifier.py`, qui prendrait le même
bulletin. C'est pour cela que le module ne fait pas de SMTP directement dans
`publier`.

Le cahier ne dit rien du rythme. Un message quotidien a été choisi, et le
pied de message du bulletin le dit à l'étudiant, pour qu'un jour sans
nouveauté ne soit pas pris pour un message en retard.

## Limites assumées

* **L'envoi réel n'a pas été vérifié.** Aucun test ne parle à un serveur de
  messagerie, par règle du projet, et les six secrets n'existent pas encore. Le
  code a été vérifié avec un faux transport, et l'échec avec un vrai serveur qui
  refuse la connexion. C'est la deuxième chose non vérifiable en local, après le
  workflow lui-même, et elle se vérifie une fois, à la main.
* **Un run manuel envoie aussi le message.** Le message part au premier run qui
  voit la nouveauté, quel qu'il soit. Un `python src/main.py` le jour où le run
  automatique a déjà envoyé produit donc un second message le même jour. C'est
  le prix du choix « celui qui voit, annonce », et c'est utile pour essayer le
  chemin d'envoi.
* **Le port 465 n'est pas traité.** Le rendu ne gère que le port de soumission
  587 avec STARTTLS explicite. Le port implicite 465 n'est pas traité, et
  `starttls` échouerait avec une erreur SMTP peu parlante. Ce port est en clair
  dans la documentation du fournisseur.
* **Aucun mot de passe n'est écrit dans le dépôt.** Les six variables sont lues
  dans l'environnement, et le workflow les passe par `env` et jamais dans la ligne
  de commande. Un test vérifie que les six noms du code sont exactement les six
  noms du workflow : une variable renommée d'un côté et pas de l'autre
  produirait un email qui ne part jamais, sans erreur.
* **La V1.2 ne découle pas de cette version.** Une deadline qui approche ne
  change pas la fiche, donc rien ne se déclenche : notifier sur changement ne
  permet pas de suivre les dates. La V1.2 aura besoin d'une comparaison de
  dates, pas d'une détection de modification. C'est écrit ici parce qu'il vaut
  mieux le savoir avant la V1.2 qu'après.

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

## État mesuré

### Le mécanisme était atteint, l'ajout de sources ne l'était pas

Les deux dernières lignes de l'objectif sont vérifiées depuis la V0.4, et il
fallait le dire : les quatre sources du jour produisent toutes des
`Opportunity`, et aucune n'a nécessité d'écrire dans `src/scraper.py`.
`build_opportunity` ne connaît aucun site, et `tests/test_scraper.py` le vérifie
en faisant passer une page par les sélecteurs génériques et une autre par le
parseur dédié de KAIST, puis en comparant les deux résultats.

| Source | Stratégie de lecture | Fiches |
| ------ | ------------------- | ------ |
| KAIST – Explore Programs | sélecteurs CSS | 36 |
| EACEA – Erasmus Mundus catalogue | sélecteurs CSS | 20 |
| TUM – Degree programs | sélecteurs CSS | 10 |
| KAIST – Scholarship | `src/parsers/kaist_scholarship.py` | 3 |

Mais « ajouter plusieurs sources » n'était pas fait pour autant. Sur le
registre du 28 septembre 2026 :

| Ensemble | Nombre |
| -------- | ------ |
| sources inscrites | 19 |
| activées | 16 |
| désactivées | 3 |
| avec un bloc dans `config/selectors.json` | 4 |
| activées et sans bloc de sélecteurs | 12 |
| sans bloc de sélecteurs, activées ou non | 15 |

Douze sources activées ne produisent rien. Ce n'est pas un oubli : une source
est inscrite au cahier des charges avant de savoir la lire, c'est la raison
d'être des deux fichiers de configuration. Mais cela rendait la veille
**inmesurable**, et c'est le défaut que la version corrige.

### Le défaut : une panne silencieuse

`collect_opportunities` n'affichait quelque chose que sur `requests.RequestException`.
Mesuré sur le run du 27 septembre 2026 : **zéro ligne du journal ne nommait une
source.** Le journal disait « 69 opportunités enregistrées », et il disait
exactement la même chose selon que les quatre sources fonctionnaient ou
qu'aucune ne répondait plus.

Trois situations, un seul silence :

| Situation | Ce qu'elle signifie | Réparation |
| --------- | ------------------- | ---------- |
| pas de bloc de sélecteurs | source décidée, pas encore lue | écrire `config/selectors.json` |
| la lecture a levé une erreur | source en panne ce jour | attendre, ou voir le détail |
| 0 fiche après lecture | **le site a changé** | réécrire les sélecteurs |

La troisième est la plus coûteuse et la moins visible : une page qui répond
toujours, avec un contenu différent. Un programme qui l'ignore perd une saison
de bourses sans qu'aucune donnée ne le montre, parce que les données sont
juste moins nombreuses.

C'est aussi la plus facile à manquer parce que le compte baisse peu : KAIST
passer de 36 programmes à 0 ferait passer le total de 69 à 33, et un total de 33
ne crie pas.

### Trois décisions

**`collect_opportunities` rend une `Recolte`, pas une liste.** Une liste ne dit
rien de sa provenance, et le seul moyen de faire dire à une fonction d'où
viennent ses données était de la changer. Le rendu est :

| Champ | Rôle |
| ----- | ---- |
| `opportunities` | les fiches, comme avant, dans l'ordre des sources |
| `sources` | une `SourceLue` par source lue : `nom`, `nombre`, `erreur`, `detail` |
| `sans_selecteurs` | combien de sources activées n'ont pas été lues |

`erreur` porte le **type** de l'exception et `detail` son **message**. Ce n'est
pas de la redondance, c'est deux lecteurs : `erreur` est ce qui tient sur une
ligne d'email et ce qui distingue une coupure de réseau d'une faute de
configuration, `detail` est ce qu'on ouvre dans le journal quand on cherche
pourquoi une source est tombée, parce qu'il contient l'hôte, le port et le
chemin de l'URL et n'intéresse pas l'étudiant.

Le rapport est écrit par un seul écran, `main.display_sources`, jamais par la
collecte. Une première version écrivait la panne dans les deux, et le journal
la disait donc deux fois — dont deux fois dans le résumé d'étape, puisque le
motif du workflow est justement `^Source`. Le message complet est maintenant
indenté sous sa source : il ne commence pas par « Source », donc le workflow ne
le recopie pas, et il se lit à l'endroit exact où il sert.

**Toutes les exceptions sont rattrapées, pas seulement les erreurs réseau.**
Avant, un nom de `parser` sans module dans `src/parsers/`, ou un bloc de
sélecteurs sans clé `item`, faisaient tomber les 68 fiches des trois autres
sources avec eux : `ModuleNotFoundError` et `KeyError` ne sont pas des
`RequestException`. Les deux se réparent dans deux fichiers différents, donc il
fallait pouvoir les distinguer, et il fallait que l'une ne fasse pas tomber
l'autre. Le type est nommé, donc une `KeyError` se lit au lieu de se déguiser
en coupure de réseau.

**Le rapport est complet dans le journal, et une seule ligne dans l'email.** Le
journal affiche une ligne par source, plus le compte des sources non lues. Le
bulletin n'écrit **rien** quand tout va bien, et une ligne
`Attention : <source> n'a rien produit (<raison>).` par source muette sinon.
C'est la même règle que pour un champ absent dans une fiche, et la même que la
V0.5 a posée : une ligne qui répète que la veille marche comme hier est du bruit
dans un message lu tous les jours. Le compte complet est dans le journal, que le
workflow recopie dans son résumé d'étape.

Le journal se lit ainsi :

```text
=== Profil de recherche ===
...
Source TUM - Degree programs : 10 opportunités extraites
Source KAIST - Explore Programs : 36 opportunités extraites
Source KAIST - Scholarship : 3 opportunités extraites
Source EACEA - Erasmus Mundus catalogue : 20 opportunités extraites
Sources sans sélecteurs : 12 activées et non lues, voir docs/SOURCES.md §8.
```

Le préfixe est en ASCII et ancré au début de la ligne, pour deux raisons : le
workflow s'en sert comme motif `^Source` dans son résumé d'étape, et un motif
accentué ne trouve rien sur un runner réglé dans une locale qui n'est pas UTF-8.
Le même motif couvre les deux formes, donc il n'y a pas deux ancres à faire
diverger.

### Tests

`tests/test_scraper.py` est créé, et c'est le premier du projet qui parle de
`src/scraper.py`. Le module fait plus de 440 lignes et n'avait aucun test : rien
ne garantissait qu'une source qui cesse de répondre serait signalée, et rien ne
garantissait qu'une faute de configuration ne ferait pas tomber la collecte
entière. Le manque est comblé en même temps que la fonction, pas après.

18 tests, dont six qui ne sont pas du tout évidents :

* une coupure de réseau sur une source laisse les trois autres produire leurs
  fiches, et la source en question porte `ConnectionError` ;
* un `parser` absent ne tue plus la veille, et se distingue d'une coupure ;
* un bloc de sélecteurs sans `item` ne tue plus la veille, et se distingue aussi ;
* **la collecte n'écrit rien**, elle rend la panne. Un seul écran écrit le
  rapport, et un écrivain de trop se prouve en vérifiant qu'il se tait. Ce test
  n'a qu'une assertion, et elle est négative ;
* une source laissée réelle est bloquée par la fixture de `conftest.py`, et le
  rapport le dit. Sans ce test, un faux téléchargement oublié donnerait un test
  vert : l'`AssertionError` du garde-fou serait rattrapée comme une coupure de
  réseau, et le test passerait avec un rapport de pannes.

Le quatrième mérite un mot. Une première version écrivait la panne **dans les
deux** écrans : `collect_opportunities` écrivait « Source X : lecture
impossible » puis son détail, et `display_sources` écrivait « Source X : lecture
impossible (KeyError) » pour la même source. Le journal la disait donc deux fois,
et le motif `^Source` du workflow la reprenait deux fois dans le résumé d'étape.
Le test « la collecte n'écrit rien » est la trace de cette faute, et il a été
écrit parce qu'elle a été vue en relisant le journal d'un run réel, pas dans un
test.

Les propriétés ont été éprouvées par mutation : chacune a été cassée
volontairement, et chacune a fait échouer les tests qui la couvrent — huit
mutations pour cette version, dont l'indentation du détail et l'ordre de ses
deux lignes. Un test qui ne peut pas échouer ne prouve rien.

`tests/test_donnees.py` a reçu quatre tests de cohérence du registre, qui
n'existent pas pour la V0.7 mais parce qu'en écrivant les chiffres ci-dessus
ils sont sortis trois fois faux. Ces tests ne fixent aucun nombre — un nombre
fixé serait rouge le jour où l'utilisateur ajoute une source — et vérifient des
propriétés : un bloc de sélecteurs désigne toujours une source inscrite, un nom
n'est pas utilisé deux fois dans un même fichier, une source désactivée n'est
jamais lue, et les sources lues et les sources comptées se partagent exactement
les sources activées.

### Ce que la version ne fait pas

* **Douze sources activées restent non lues.** Les écrire demanderait un bloc de
  `config/selectors.json` par source, donc une modification de `config/`, qui
  n'a pas été autorisée. C'est le travail suivant, et il se fait source par
  source avec mesure, pas en une passe. Voir `docs/SOURCES.md` §6.2 pour les
  candidates, et §5 pour leur verdict réel.
* **`src/scraper.py` n'est pas entièrement testé.** `tests/test_scraper.py`
  couvre le contrat de la version, et pas `test_source`, `classify` ni
  `fetch_page`. Les deux derniers touchent le réseau et demanderaient une
  seconde couture d'injection ; c'est un reste à faire assumé, écrit dans
  l'en-tête du fichier de tests, pour que personne ne croie le module couvert.
* **`deadline` reste à 0 / 69.** Rien dans cette version n'y change, et rien ne
  pouvait : la mesure est dans `docs/SOURCES.md` §6.3.

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

## État mesuré

Le workflow est écrit et vérifié, mais **il n'a jamais été exécuté sur
GitHub**. C'est la seule étape du projet qui ne peut pas être validée en local.
Il sera connu pour vrai au premier run, et il faudra l'activer ou
attendre 07:00 UTC.

Les cinq points sont là. Le cinquième est celui qui manquait, et il n'était pas
évident : **sans commit, `data/` se perd à chaque exécution.** Un runner GitHub
Actions est une machine jetable, détruite à la fin du run. Le programme écrivait
69 fiches correctes, et la machine disparaissait avec. La veille aurait
fonctionné en local et perdu toute mémoire dès le premier run automatique.

C'est aussi pour cela que `data/` est versionné, décision de la V0.4 : il n'y a
rien à sauvegarder si le résultat ne reste pas dans le dépôt.

| Choix | Raison |
| ----- | ------ |
| `permissions: contents: write` au niveau du job | sans lui, `git push` échoue et la veille est perdue chaque jour |
| `fetch-depth: 0` | `git pull --rebase` refuse un dépôt superficiel, et 1 est la profondeur par défaut |
| `concurrency` avec `cancel-in-progress: false` | deux runs ne doivent pas se marcher dessus, et un run annulé laisserait les données à moitié écrites |
| `set -o pipefail` | sans lui, le code de retour de `main.py \| tee` est celui de `tee`, toujours zéro : une veille en échec passerait pour un succès |
| `git diff --cached --quiet` avant de committer | une journée sans nouveauté ne produit aucun commit, grâce à `storage.a_change` |
| `git pull --rebase` avant le push | si quelqu'un a poussé entre-temps, on rebase au lieu d'écraser un commit humain |
| motifs de `grep` en ASCII | un motif accentué dépend de la locale du runner, et le message de commit deviendrait vide sans erreur |
| résumé d'étape, avec `if: always()` | le résultat se lit dans le navigateur, et le résumé existe précisément quand la veille a échoué |
| les tests **avant** la veille | une veille qui écrit des données fausses ne se voit pas ; une veille arrêtée, si |

Le message de commit est relu depuis le journal :

```text
veille du 2026-09-27 : 3 nouvelles

69 opportunités trouvées, 9 correspondent au profil
69 opportunités enregistrées dans data/opportunities.json
0 nouvelles depuis la dernière exécution
9 opportunités déjà montées, dans data/seen.json
```

Le bloc de commit a été testé pour de vrai, dans un dépôt jetable avec un
`origin` local : pas de commit quand `data/` ne bouge pas, commit et push
quand il bouge, et message correct pour 0, 1 et plusieurs nouveautés.

`tests/test_workflow.py` relit le YAML et vérifie ces choix, parce que ce
fichier est le seul du projet que l'on ne peut pas lancer chez soi. Une faute
dedans ne se verrait qu'à 07:00 UTC, dans le navigateur, sans personne devant.

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

## État mesuré

La version est écrite. La planification quotidienne et le déclenchement à la
demande étaient déjà là depuis la V0.8 : le `cron "0 7 * * *"` et le
`workflow_dispatch` n'ont pas été ajoutés ici, et les tests qui les vérifient
sont dans `tests/test_workflow.py`, section 3.

Ce que cette version ajoute tient en une ligne de YAML : le **plafond
d'exécution** du job, `timeout-minutes: 30`. Il faut dire pourquoi, parce que la
raison évidente est fausse.

| Mesure | Valeur |
| ------ | ------ |
| durée d'un run en local, mesurée le 28 septembre 2026 | 17,5 s |
| délai d'une requête réseau, `scraper.TIMEOUT_SECONDS` | 30 s |
| pire cas du réseau, quatre sources lues | 120 s |
| suite de tests, 360 tests | 3,0 s |
| plafond écrit dans le workflow | 30 min |
| défaut de GitHub pour un job | 360 min |

### Le raisonnement qui ne tient pas

L'argument naturel est « un run bloqué ne doit pas faire perdre une journée ». Il
ne tient pas, et il ne doit pas être écrit dans le dépôt.

GitHub n'admet qu'une seule exécution en attente par groupe de concurrence :
*by default, any existing pending job or workflow in the same concurrency group
will be canceled and the new queued job or workflow will take its place.*
Perdre une journée exigerait donc qu'un run bloque plus de vingt-quatre heures.
Or le défaut de GitHub abandonne un job au bout de 360 minutes, soit six heures.
Un blocage isolé ne peut pas faire perdre une journée, et le plafond de trente
minutes n'apporte rien de ce côté-là.

Ce que le plafond apporte est plus modeste, et vrai :

* un run cassé devient rouge dans la matinée, au lieu de l'être six heures plus
  tard ;
* la valeur écrite décrit le job. Un défaut de 360 minutes laissé en place
  affirme qu'un job de dix-sept secondes a le droit de durer six heures ;
* la seule situation où le groupe de concurrence agit vraiment — deux
  exécutions manuelles lancées pendant qu'un run est déjà en cours — a une
  fenêtre qui tombe de six heures à trente minutes.

### Ce que les tests vérifient

Deux tests dans `tests/test_workflow.py`, section 3. Le second ne compare pas à un
nombre écrit en dur : il exige que le plafond reste très au-dessus du délai d'une
seule requête, délai lu dans `scraper.TIMEOUT_SECONDS`. Si ce délai change un jour,
le test suit au lieu de devenir faux.

Quatre mutations ont été éprouvées, chacune devant faire rougir le test qui
couvre la propriété : plafond supprimé, plafond à 400 minutes, plafond à
5 minutes, plafond décimal. Comme GitHub refuse une valeur décimale, ce test
porte aussi une contrainte de validité du workflow. Le fichier a été restauré
à l'octet après l'épreuve, et les 30 tests du fichier repassent au vert.

## Ce que l'exécution automatique ne peut pas garantir

Quatre points : deux viennent de la documentation GitHub, relevée le 28
septembre 2026, et deux sont des faits sur ce projet lui-même. Aucun ne se
répare dans le code, donc ils sont écrits plutôt que présentés comme
résolus.

* **Un dépôt public sans activité pendant soixante jours voit sa planification
  désactivée.** *In a public repository, scheduled workflows are automatically
  disabled when no repository activity has occurred in 60 days.* La règle ne vise
  que les dépôts publics, et celui-ci répond `404` à une requête anonyme, ce qui
  est ce que fait un dépôt privé ; elle ne devrait donc pas le concerner. Cela
  n'a pas été vérifié par un appel authentifié, et c'est le seul point de cette
  version qui repose sur une inférence.
  Le point mérite d'être connu quand même, parce que la veille ne produit pas
  d'activité quotidienne : depuis la V0.8, un jour sans nouveauté ne produit
  aucun commit. Une période de soixante jours sans changement des données
  compterait donc comme une période sans activité. La réactivation se fait dans
  l'onglet Actions, en sélectionnant le workflow puis **Enable workflow**, ou par
  `gh workflow enable Academic Watch`.
* **La planification ne s'exécute que sur la branche par défaut.** C'est `main`,
  où le workflow est écrit, donc le cas est déjà le bon.
* **Aucun email n'est envoyé si le run échoue avant le programme.** L'email part
  de `notifier.publier`, et les tests passent avant la veille : un code cassé
  arrête le run avant qu'aucune ligne Python ne s'exécute. L'étudiant n'en
  apprend rien par courriel et doit ouvrir l'onglet Actions. Corriger cela
  demanderait de mettre les six secrets dans une étape shell, ce que le projet
  refuse par principe : la valeur d'un secret n'est jamais écrite dans une
  commande, dans le workflow comme dans le code.
* **Rien n'a été exécuté sur GitHub.** La version est vérifiée en local, relue
  dans le YAML et éprouvée par mutations, mais le premier run automatique reste
  la seule validation qui manque. Comme en V0.8, il faudra lancer le workflow à
  la main.

---

# V0.10 - Second canal de notification

## Objectif

Ne plus dépendre d'un canal que l'étudiant ne peut pas ouvrir.

La V0.6 a retenu l'email parce que c'est le seul moyen que la boîte aux lettres
de l'étudiant ouvre déjà. Il se heurte à un obstacle qu'aucune ligne de code ne
contourne : Outlook exige un mot de passe d'application, donc une double
authentification, donc une configuration à faire sur un autre appareil que celui
qui fait la veille. Tant qu'elle n'est pas faite, les six secrets existent et
l'email ne part jamais. Le résumé d'étape le dira tous les jours, ce qui est
honnête et inutile.

Un canal ne sert à rien si personne ne peut l'ouvrir. Cette version en ajoute un
second, qui tient en une variable et ne demande rien d'autre.

## La décision : un webhook, et pas un bot

**Un bot Discord.** Il faudrait une application, un jeton, et inviter ce bot dans
le salon. Le jeton serait un secret de plus, la marche à suivre serait plus
longue que celle du webhook, et le bot pourrait faire autre chose que poster un
bulletin.

**Un webhook.** Une URL qui donne le droit d'écrire dans un salon, et rien
d'autre. Discord la génère dans les paramètres du salon, sans compte à créer et
sans authentification à configurer. Sa documentation le dit en une phrase :
*Webhooks are a low-effort way to post messages to channels in Discord. They do
not require a bot user or authentication to use.*

C'est celle-là, et elle a sa contrepartie : l'URL est elle-même une autorisation.
Quiconque la possède peut écrire dans le salon. Elle est donc un secret au même
titre qu'un mot de passe, pour la même raison : ce n'est pas une adresse, c'est
une clé.

## Un seul rendu, deux canaux

Le texte est produit une fois par `rendre`, et `publier` l'affiche puis l'envoie
aux canaux configurés. Les six variables SMTP restent en place, et les cinq
formes de la ligne de statut plus bas montrent le programme avec l'un des deux
canaux, avec les deux, et avec aucun.

`publier` ne lève jamais, et le premier canal n'empêche pas le second. C'est
exactement le cas de l'étudiant : son serveur de messagerie est cassé, et son
bulletin doit quand même partir sur l'autre canal.

## Deux plafonds, et il ne faut pas les confondre

| Plafond | Valeur | D'où il vient |
| ------ | ------ | ------------- |
| `LIMITE_MESSAGE` | 2 000 caractères | une limite de l'API |
| `MESSAGES_MAX` | 5 messages | un choix de lisibilité |

La première est écrite dans la documentation : la page `Execute Webhook`
annonce, pour le champ `content`, « the message contents (up to 2000
characters) ». Elle ne se négocie pas.

La seconde n'est pas une limite de Discord. La documentation ne dit nulle part
combien de messages un salon accepte : elle limite la longueur de chacun, donc
rien n'empêche d'en envoyer cinquante. C'est une décision sur ce qu'un écran de
téléphone peut afficher à 7 h du matin, quand treize messages de 2 000 caractères
se ressembleraient tous. Ce qui ne rentre pas n'est pas perdu : le résumé d'étape
recopie la section « à signaler » entière, l'email n'a pas de limite, et la ligne
de statut compte ce qui a été omis au lieu de passer sous silence.

## Le bulletin est coupé, jamais tronqué

Un bulletin de 3 493 caractères ne tient pas dans un message. Il est coupé sur
les frontières de ligne : rien n'est perdu, et un champ n'est jamais coupé en
deux. La ligne la plus longue du pire cas mesuré fait 375 caractères, donc la
coupure en fin de ligne suffit aujourd'hui. Le débitage au caractère reste écrit
pour le jour où un titre de page dépasserait 2 000 caractères, et il a son test.

## La limite de débit est lue, jamais écrite

*Because rate limits depend on a variety of factors and are subject to change,
rate limits should not be hard coded into your app. Instead, your app should
parse response headers to prevent hitting the limit, and to respond accordingly
in case you do.*

Le programme lit donc `X-RateLimit-Remaining`, et quand il vaut zéro,
`X-RateLimit-Reset-After`, que la documentation décrit comme pouvant « have
decimals ». La pause est plafonnée par `ATTENTE_MAX`, parce qu'un en-tête absent
ou aberrant ne doit pas faire dormir un run. Un 429 n'est pas réessayé : il est
nommé dans la ligne de statut. La documentation le justifie sur un autre point,
qu'il vaut mieux connaître : *If a webhook returns a 404 status you should not
attempt to use it again*.

## Un défaut trouvé après coup, dans la même documentation

Le code envoyait `content` sans le paramètre `wait`. C'est un défaut réel, de la
même famille que celui que `raise_for_status` corrige ailleurs : une réussite
supposée là où il faut une réussite prouvée.

La valeur par défaut de `wait` est `false`, et la documentation écrit que, dans
ce cas, « a message that is not saved does not return an error ». La réponse est
alors un `204 No Content` que la vérification d'erreur laisse passer. Le
programme aurait donc dit « 1 message envoyé » pour un message absent du salon,
et la ligne de statut aurait nommé une veille qui fonctionnait. Aucun test ne
pouvait le voir : il lisait la constante.

Le correctif est un paramètre de requête, `params={"wait": "true"}`, et non un
morceau collé à l'URL, parce que l'URL porte le secret et doit arriver telle
quelle. Avec `wait`, la réponse n'est un succès qu'une fois le message
enregistré, et un refus devient un 4xx que `raise_for_status` voit.

## État mesuré

| Mesure | Valeur |
| ------ | ------ |
| suite de tests, 390 tests | environ 5 s |
| tests ajoutés, de 360 à 390 | +30 |
| tests du canal Discord, section 7 de `test_notifier.py` | 29 |
| tests du workflow, dont celui qui interdit l'URL en clair | 31 |
| mutations éprouvées rouges | 18 |
| secrets lus par le programme | 7 |
| bulletin du 28 septembre 2026 | 3 493 caractères, 2 messages |
| pire cas, 69 fiches toutes retenues | 25 317 caractères, 13 messages |
| journée sans rien à signaler | 346 caractères, 1 message |
| ligne la plus longue du pire cas | 375 caractères |
| limite d'un `content` | 2 000 caractères |
| messages envoyés sans attendre | 5, le reste compte dans la ligne |

Les 18 mutations sont le contrôle qui vaut le plus ici, parce qu'une constante
lue par les tests ne peut pas être prouvée fausse par eux : un test qui compare
à `LIMITE_MESSAGE` passe quelle que soit sa valeur. Chacune des 18 casse le code,
le workflow ou un test, et le fichier est rendu à l'octet après chacune ; la suite
complète repasse au vert ensuite.

## Les cinq formes de la ligne de statut

C'est cette ligne que le workflow recopie dans le résumé d'étape, donc c'est la
seule trace qu'un run automatique a réussi à notifier. Les cinq formes sont
mesurées, sans un seul appel sortant :

```text
A aucun secret
  Notification : console seule, il manque SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO, Discord non configuré
B les six SMTP
  Notification : email non envoyé (OSError), Discord non configuré, la veille est complète
C le webhook seul
  Notification : email non configuré (il manque SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO), Discord, 1 message envoyé
D les sept secrets
  Notification : email non envoyé (OSError), Discord, 1 message envoyé, la veille est complète
E webhook et bulletin trop long
  Notification : email non configuré (il manque SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO), Discord, 5 messages envoyés, 4 messages de plus dans le résumé du run
```

Le cas A est le mode par défaut, et c'est le cas le plus probable le premier
jour : rien n'est configuré, et le programme fonctionne quand même. Le cas C est
celui de l'étudiant. Deux règles se lisent dans ces cinq lignes : « console
seule » n'apparaît que si aucun des deux canaux n'a rien fait, et « la veille
est complète » n'apparaît qu'après un échec.

## Ce que l'exécution automatique ne peut pas garantir

* **L'envoi à Discord n'a pas été vérifié.** Aucun test ne joint Discord, par la
  même règle qui interdit tout accès au réseau. Le programme a été exécuté en
  local, sa sortie est celle du cas A, et `data/` est resté identique à l'octet.
  Ce qui n'est pas vérifié, c'est la réponse du serveur.
* **Le secret est à créer par l'étudiant.** Rien dans le dépôt ne peut le créer :
  le webhook se fait dans les paramètres du salon, puis le secret dans les
  paramètres du dépôt. C'est la seule chose que cette version demande.
* **Une URL de webhook ne doit jamais entrer dans le dépôt.** Elle donne le droit
  d'écrire dans le salon, et une fois committée elle y reste, même effacée
  ensuite. Un test vérifie que le workflow ne contient ni `discord.com/api/webhooks`
  ni `discordapp.com/api/webhooks`, et qu'il lit `DISCORD_WEBHOOK` dans les
  secrets.
* **Rien n'a été exécuté sur GitHub.** Comme en V0.8 et V0.9.

## Écarts

* Le cahier des charges ne prévoit qu'un moyen de notification. Il y en a deux
  maintenant, et le second est celui qui fonctionnera.
* `MESSAGES_MAX` n'est pas dans le cahier. C'est un choix, il est mesuré, et ce
  qui est écarté est compté.

## Limites assumées

* **La limite de 2 000 caractères n'est pas relue par le programme.** Elle est
  écrite dans une constante, et c'est bien. Si Discord la change un jour, la
  constante sera fausse : le code n'a aucun moyen de le savoir avant l'envoi, et
  `raise_for_status` transforme l'erreur en une ligne de statut qui la nomme.
* **Un message omis n'est pas renvoyé le lendemain.** Le programme ne garde que
  ce qui a été montré, pas ce qui a été posté dans le salon. Ce qui dépasse le
  plafond n'est dans le résumé d'étape que le temps de ce run.
* **Le salon est un mur de texte le jour d'une grosse journée.** C'est le choix
  explicite, pas un oubli.

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

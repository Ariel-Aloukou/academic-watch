"""Correspondance entre une opportunité et le profil de recherche.

Ce module répond à trois questions, dans cet ordre :

1. l'opportunité correspond-elle au profil ?
2. pourquoi ? quels termes ont correspondu ?
3. à quel niveau ? une correspondance directe vaut plus qu'un terme
   simplement associé.

Il ne dépend d'aucune source ni d'aucun site. Il ne fait que comparer des
textes et des champs déjà extraits, ce qui le rend réutilisable.

Un principe gouverne tout le module : une information absente ne produit
jamais de correspondance. Si une source ne publie pas l'éligibilité, le filtre
le dit au lieu de le supposer (docs/README.md §7).

## Pourquoi deux listes de critères

Un programme et une bourse ne posent pas la même question.

Un programme se juge sur sa **matière** : c'est le domaine de recherche qui
décide si l'étudiant a envie de l'étudier. Exiger un domaine d'une page qui
n'en publie pas écarterait des programmes parfaitement pertinents.

Une bourse n'annonce **aucune matière**. Elle se juge sur qui peut en
bénéficier : le niveau d'accès, l'ouverture aux étudiants internationaux, le
niveau de financement. Exiger un domaine d'une bourse reviendrait à écarter
toutes les bourses, ce qui est exactement le défaut constaté : les trois
bourses KAIST étaient rejetées alors qu'elles sont des prises en charge
complète des frais de scolarité.

D'où deux budgets. Chacun totalise 100 quand tous ses critères sont écrits, de
sorte que le score reste comparable d'une version à l'autre : ajouter un
critère plus tard n'attribue pas rétrosactivement des points aux collectes
antérieures.
"""

import re

# Poids des critères, par type d'opportunité.
#
# Chaque type totalise 100. Les poids sont déclarés ici une fois pour toutes :
# un critère pas encore écrit n'est pas noté, il ne fait pas grimper le score.
# Le maximum atteignable est donc 85 sur 100 pour un programme tant qu'aucune
# source ne publie `language`.
#   programs      : domaine 50, diplome 20, pays 15, langue 15
#   scholarships  : complet, 100
CRITERES = {
    "programs": {
        "domaine": 50,
        "diplome": 20,
        "pays": 15,
        "langue": 15,
    },
    "scholarships": {
        "niveau": 40,
        "international": 25,
        "financement": 20,
        "pays": 15,
    },
}

# Points du critère domaine, selon le palier atteint.
POINTS_DOMAINE = {"direct": 50, "strong": 30, "weak": 10}

# Étiquette lisible de chaque palier, reprise dans les raisons affichées.
PALIER_LABELS = {
    "direct": "correspondance directe",
    "strong": "terme associé",
    "weak": "contexte",
}

# Critères qui décident si l'opportunité est retenue. Un critère qui n'est pas
# dans cette liste ne retient ni ne rejette : il ne fait que classer.
#
# C'est une liste de critères, et non un seuil de score, parce qu'un seuil
# obligerait à décider d'un cas intermédiaire. Ici, `domaine` vaut 10 comme
# 50 : la question n'est pas « combien » mais « quelle matière ».
CRITERES_RETENUS = {
    "programs": ("domaine",),
    "scholarships": ("niveau", "international"),
}

# Type retenu quand la source ne le déclare pas. Les pages qui décrivent des
# conditions d'admission ne produisent pas d'opportunités : le seul type qui
# reste sans information est celui-ci, où l'on se rabat sur la lecture d'un
# programme.
TYPE_PAR_DEFAUT = "programs"

# « Master's-Ph.D. Integrated » est un diplôme différent de « Master's ».
# Sans cette distinction, une bourse réservée aux doctorants passerait pour une
# bourse de Master, parce que le mot Master y figure. C'est le piège rencontré
# sur la page Scholarship de KAIST, dont deux des trois bourses sont de niveau
# Master et une est de niveau doctoral.
DIPLOMES_COMPOSES = re.compile(r"master'?s?\s*-\s*ph\.?\s*d\.?", re.IGNORECASE)

# Un niveau plus large que le diplôme visé ouvre la porte à ce diplôme. Au
# Royaume-Uni, « graduate programs » commence au Master.
NIVEAUX_LARGES = ("graduate",)

# Une offre de niveau doctoral. Attention : les formes composées ont déjà été
# retirées avant cette recherche, sinon « Master's-Ph.D. Integrated » ferait
# croire à une bourse de Master.
NIVEAUX_DOCTORAUX = ("ph.d", "phd", "doctorate", "doctoral")

# Mots qui réservent une aide à une population du pays d'accueil.
RESTRICTIONS_NATIONALES = ("citizen", "domestic", "national student", "home student")

# Mots qui signalent une prise en charge complète des frais de scolarité.
FINANCEMENT_COMPLET = ("full", "complete", "waiver", "coverage")

# Le profil dit « anglais oui, français non », la page dit « taught in English ».
# Il faut donc traduire la clé du profil en mots que les pages écrivent. La
# liste est courte et vérifiée : c'est le maximum que le code peut faire sans
# demander de comprendre une langue.
TRADUCTIONS_LANGUE = {
    "english_program": ("english", "anglais"),
    "french_program": ("french", "francais", "français"),
}


def variantes(terme):
    """Renvoie les formes acceptables d'un terme.

    KAIST écrit « Telecommunication Technology » quand le profil écrit
    « Telecommunications ». Sans cette étape, une correspondance par
    sous-chaîne laisserait passer ce programme, qui est pourtant pertinent.

    On ne fait pas de stemming complet, seulement deux formes : le mot tel
    qu'il est écrit, et son singulier. C'est volontaire : une règle plus
    sophistiquée serait difficile à justifier, et le pluriel anglais est la
    seule différence constatée sur les sources réelles.
    """
    formes = {terme.lower()}
    if terme.lower().endswith("s"):
        formes.add(terme.lower()[:-1])
    return formes


def contient(texte, terme):
    """Vrai si l'une des formes du terme apparaît dans le texte.

    Le texte peut contenir le terme, ou pas : les deux cas sont normaux. Une
    information absente reste False, elle n'est pas devinée
    (docs/README.md §7).
    """
    if not texte:
        return False

    texte = texte.lower()
    return any(forme in texte for forme in variantes(terme))


def contient_mot(texte, mot):
    """Vrai si le mot apparaît seul, et non au milieu d'un autre mot.

    La différence est décisive sur les niveaux de diplôme : « undergraduate »
    contient « graduate », donc une bourse de premier cycle passerait pour une
    bourse de Master. Une recherche par sous-chaîne ne suffit pas ici.
    """
    if not texte:
        return False
    return re.search(rf"\b{re.escape(mot)}\b", texte.lower()) is not None


# Apostrophes typographiques. Les pages d'universités écrivent « Master’s » là
# où le code écrit « Master's ». Sans normalisation, une règle construite sur
# l'apostrophe ASCII ne s'applique pas à la même chaîne, et une bourse de
# Master est rejetée comme doctorale parce que le mot « Ph.D » de
# « Master’s-Ph.D. » n'a pas été retiré. C'est exactement ce qui arrive sur la
# page Scholarship de KAIST, dont les deux premiers caractères de chaque nom
# de diplôme sont une apostrophe U+2019.
APOSTROPHES_TYPOGRAPHIQUES = ("’", "‘")


def normaliser(texte):
    """Remplace les apostrophes typographiques par l'apostrophe ASCII.

    Cette normalisation est faite dans les fonctions qui en dépendent, et pas
    seulement en amont, pour qu'un appelant ne puisse pas obtenir un résultat
    faux en oubliant de normaliser avant.
    """
    for apostrophe in APOSTROPHES_TYPOGRAPHIQUES:
        texte = texte.replace(apostrophe, "'")
    return texte


def texte_de(*champs):
    """Assemble des champs textuels en une seule chaîne, en ignorant les vides.

    `eligibility` est une liste de phrases, les autres champs sont des chaînes.
    Cette fonction évite d'avoir à le rappeler à chaque mesure, et donc
    d'oublier un jour un champ.

    Les apostrophes sont normalisées : voir `normaliser`.
    """
    morceaux = []
    for champ in champs:
        if not champ:
            continue
        if isinstance(champ, (list, tuple)):
            morceaux.extend(str(item) for item in champ if item)
        else:
            morceaux.append(str(champ))
    return normaliser(" ".join(morceaux))


def correspondent(texte, profil):
    """Renvoie la meilleure correspondance de domaine trouvée dans le texte.

    Le profil donne la définition de l'objectif : `fields` sont les domaines
    principaux, `related_terms` sont les mots que les universités utilisent
    pour les désigner. Un terme associé n'est pas la même chose qu'un domaine
    principal, et le niveau de correspondance doit pouvoir le montrer.

    Retourne None si rien ne correspond, plutôt qu'une correspondance faible
    par défaut : on ne devine pas.
    """
    if not texte:
        return None

    # Correspondance directe : le texte contient un des domaines du profil.
    for champ in profil["fields"]:
        if contient(texte, champ):
            return {
                "palier": "direct",
                "champ": champ,
                "terme": champ,
                "points": POINTS_DOMAINE["direct"],
            }

    # Correspondance associée ou contextuelle. On garde la meilleure : un
    # programme qui correspond faiblement à deux domaines ne vaut pas mieux
    # qu'un programme qui correspond nettement à un seul.
    meilleure = None
    for champ, associes in profil.get("related_terms", {}).items():
        for palier in ("strong", "weak"):
            for terme in associes.get(palier, []):
                if not contient(texte, terme):
                    continue
                points = POINTS_DOMAINE[palier]
                if meilleure is None or points > meilleure["points"]:
                    meilleure = {
                        "palier": palier,
                        "champ": champ,
                        "terme": terme,
                        "points": points,
                    }
    return meilleure


def sans_diplomes_composes(texte):
    """Retire de « Master's-Ph.D. Integrated » la forme qui le distingue.

    Le reste du texte n'est pas touché. C'est ce qui permet de dire ensuite
    qu'une offre ne mentionne « Master » que dans un diplôme composé, et
    qu'elle ne s'adresse donc pas à un étudiant de Master.
    """
    return DIPLOMES_COMPOSES.sub(" ", normaliser(texte or ""))


def niveau_atteignable(texte, cibles):
    """Vrai si le texte propose l'un des diplômes visés, ou un niveau plus large.

    Les formes composées sont retirées avant la recherche, sinon
    « Master's-Ph.D. Integrated » compterait comme une offre de Master.
    """
    reste = sans_diplomes_composes(texte).lower()
    if any(cible.lower() in reste for cible in cibles):
        return True
    return any(contient_mot(reste, niveau) for niveau in NIVEAUX_LARGES)


def mesure_domaine(opportunity, profil, points):
    """Le texte publié mentionne-t-il un domaine du profil ?

    On assemble ce que la page publie. Une source qui n'affiche pas ses
    domaines de recherche, comme TUM, est donc comparée sur son titre et sa
    description : moins de critères, jamais de critères inventés.
    """
    texte = texte_de(opportunity.title, opportunity.field, opportunity.description)
    if not texte:
        return _mesure("domaine", 0, "aucun texte publié par la source")

    trouve = correspondent(texte, profil)
    if trouve is None:
        return _mesure(
            "domaine", 0, "aucun terme du profil dans les informations publiées"
        )

    return _mesure(
        "domaine",
        POINTS_DOMAINE[trouve["palier"]],
        f"{trouve['terme']} ({PALIER_LABELS[trouve['palier']]} a {trouve['champ']})",
    )


def mesure_diplome(opportunity, profil, points):
    """Le diplôme proposé est-il l'un de ceux que le profil recherche ?

    Le champ `degree` est lu en premier. Quand la source ne le publie pas, le
    titre est utilisé à la place : « International Master in Contemporary
    Challenges » est une information publiée, pas une devinette. C'est une
    source plus faible qu'un champ dédié, donc le motif affiché dit lequel des
    deux a été lu.

    KAIST publie trois niveaux pour un même programme. C'est normal : un
    programme qui existe en Master et en doctorat convient à qui vise le
    Master.
    """
    diplome = opportunity.degree
    origine = "diplôme"
    if not diplome:
        diplome = opportunity.title
        origine = "titre"
    if not diplome:
        return _mesure("diplome", 0, "diplôme non publié")

    if niveau_atteignable(diplome, profil["target_degree"]):
        return _mesure("diplome", points, f"{origine} {diplome}")
    return _mesure("diplome", 0, f"{origine} {diplome}, hors de la liste visée")


def mesure_niveau(opportunity, profil, points):
    """La bourse est-elle ouverte au diplôme visé ?

    Une bourse n'annonce pas de matière : ce qui décide de son utilité, c'est
    qui peut en bénéficier. C'est le sens de l'éligibilité publiée, et c'est
    elle qui permet de distinguer une bourse de Master d'une bourse de
    doctorat.
    """
    texte = texte_de(opportunity.eligibility, opportunity.degree, opportunity.title)
    if not texte:
        return _mesure("niveau", 0, "éligibilité non publiée")

    cibles = profil["target_degree"]
    reste = sans_diplomes_composes(texte).lower()
    if not niveau_atteignable(texte, cibles):
        # Deux reasons distinctes : la page ne parle que de doctorat, ou elle
        # parle d'un niveau sans rapport. La première est fréquente et mérite
        # d'être dite clairement, c'est elle qui explique qu'une bourse de
        # Master ne l'est pas.
        if any(contient_mot(reste, niveau) for niveau in NIVEAUX_DOCTORAUX):
            return _mesure("niveau", 0, "réservée à un niveau doctoral")
        return _mesure("niveau", 0, f"niveau publié hors de {', '.join(cibles)}")

    return _mesure("niveau", points, f"ouverte au niveau {', '.join(cibles)}")


def mesure_international(opportunity, profil, points):
    """La bourse est-elle ouverte aux étudiants internationaux ?

    C'est la question que le profil pose en premier : un ressortissant du
    pays d'accueil n'en profite pas de la même façon. Une page qui ne le dit
    pas n'est pas retenue pour autant, elle est signalée comme indéterminée.
    """
    texte = texte_de(opportunity.eligibility, opportunity.description).lower()
    if not texte:
        return _mesure("international", 0, "éligibilité non publiée")

    if any(mot in texte for mot in RESTRICTIONS_NATIONALES):
        return _mesure("international", 0, "réservée à une population nationale")
    if contient_mot(texte, "international"):
        return _mesure("international", points, "ouverte aux étudiants internationaux")
    return _mesure(
        "international", 0, "ouverture aux étudiants internationaux non précisée"
    )


def mesure_financement(opportunity, profil, points):
    """Le niveau de financement correspond-il à ce que le profil accepte ?

    Le profil accepte une bourse partielle, donc une aide partielle reste une
    correspondance. Elle est seulement moins bien classée qu'une prise en
    charge complète, ce qui explique la division des points.
    """
    texte = (opportunity.funding_type or "").lower()
    if not texte:
        return _mesure("financement", 0, "financement non publié")

    if contient_mot(texte, "tuition") and any(
        contient_mot(texte, mot) for mot in FINANCEMENT_COMPLET
    ):
        return _mesure("financement", points, "prise en charge des frais de scolarité")
    if contient_mot(texte, "tuition"):
        return _mesure("financement", points // 2, "prise en charge partielle")
    return _mesure("financement", 0, "aucune prise en charge des frais publiée")


def mesure_pays(opportunity, profil, points):
    """Le pays fait-il partie de ceux que le profil préfère ?

    Un pays absent de la liste n'est pas un refus : une bourse dans un pays non
    listé reste intéressante, elle est seulement mieux classée si le pays
    figure dans les préférences. C'est pourquoi le pays ne retient jamais rien.
    """
    pays = opportunity.country
    if not pays:
        return _mesure("pays", 0, "pays non renseigné")
    if any(pays.lower() == prefere.lower() for prefere in profil["preferred_countries"]):
        return _mesure("pays", points, f"pays {pays}")
    return _mesure("pays", 0, f"pays {pays}, hors de la liste préférée")


def mesure_langue(opportunity, profil, points):
    """La langue d'enseignement est-elle de celles que le profil accepte ?

    Le critère est écrit et vérifié sur des cas de test, mais il ne peut pas
    être validé sur une vraie page tant qu'aucune source ne renseigne
    `language`. Les quatre sources actives la laissent toutes vide. C'est dit ici
    pour que le code et le budget restent d'accord sur ce qui est vérifié et ce
    qui ne l'est pas.
    """
    langue = opportunity.language
    if not langue:
        return _mesure("langue", 0, "langue non publiée")

    for cle, mots in TRADUCTIONS_LANGUE.items():
        if not profil["preferences"].get(cle):
            continue
        if any(contient_mot(langue, mot) for mot in mots):
            return _mesure("langue", points, f"langue {langue}")
    return _mesure("langue", 0, f"langue {langue}, hors de la liste acceptée")


def _mesure(nom, points, raison):
    """Une mesure de critère, dans la forme commune à toutes les mesures.

    `raison` est une phrase et non un booléen : l'étudiant doit pouvoir lire
    pourquoi un programme lui est proposé (docs/README.md §10).
    """
    return {"nom": nom, "points": points, "raison": raison}


# Chaque critère de CRITERES a sa mesure. Ajouter un critère dans CRITERES
# sans écrire sa mesure est une erreur visible au premier lancement.
MESURES = {
    "domaine": mesure_domaine,
    "diplome": mesure_diplome,
    "niveau": mesure_niveau,
    "international": mesure_international,
    "financement": mesure_financement,
    "pays": mesure_pays,
    "langue": mesure_langue,
}


def evaluer(opportunity, profil):
    """Évalue une opportunité et renvoie type, matched, score et reasons.

    `matched` est la porte, `score` ne classe que parmi les retenues. Une
    opportunité non retenue peut avoir un score : un programme sans domaine
    mais dans un pays préféré vaut quand même des points, et les remonter dans
    la liste serait faux.

    Le type d'opportunité est renvoyé avec le reste, parce que le score n'a de
    sens que rapporté au maximum du type : 85 sur 100 pour un programme et
    100 sur 100 pour une bourse ne se comparent pas.
    """
    type_opp = opportunity.type or TYPE_PAR_DEFAUT
    budget = CRITERES.get(type_opp, CRITERES[TYPE_PAR_DEFAUT])
    retenus = CRITERES_RETENUS.get(type_opp, CRITERES_RETENUS[TYPE_PAR_DEFAUT])

    mesures = [MESURES[nom](opportunity, profil, points) for nom, points in budget.items()]

    return {
        "type": type_opp,
        "matched": all(
            mesure["points"] > 0 for mesure in mesures if mesure["nom"] in retenus
        ),
        "score": sum(mesure["points"] for mesure in mesures),
        "score_max": sum(budget.values()),
        "reasons": [mesure["raison"] for mesure in mesures if mesure["raison"]],
    }

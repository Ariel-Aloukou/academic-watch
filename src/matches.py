"""Correspondance entre une opportunité et le profil de recherche.

Ce module répond à trois questions, dans cet ordre :

1. l'opportunité correspond-elle au profil ?
2. pourquoi ? quels termes ont correspondu ?
3. à quel niveau ? une correspondance directe vaut plus qu'un terme
   simplement associé.

Il ne dépend d'aucune source ni d'aucun site. Il ne fait que comparer des
textes, ce qui le rend réutilisable pour l'évaluation comme pour l'extraction.

Un principe gouverne tout le module : une information absente ne produit
jamais de correspondance. Si une source ne publie pas ses domaines de
recherche, le filtre le dit au lieu de le deviner (docs/README.md §7).
"""

# Poids de chaque palier de correspondance, sur 100.
#
# Le score est la somme des critères pondérés. Le budget est déclaré ici pour
# que les scores restent comparables d'une version à l'autre : un critère pas
# encore écrit, comme le financement, ne fait pas grimper le score, il
# l'empêche simplement d'atteindre 100. Sans cette déclaration, un score de 60
# aujourd'hui deviendrait 80 après l'ajout d'un critère, et la lecture
# deviendrait trompeuse.
PALIER_POINTS = {
    "direct": 50,
    "strong": 30,
    "weak": 10,
}

# Étiquette lisible pour chaque palier, utilisée dans les raisons affichées.
PALIER_LABELS = {
    "direct": "correspondance directe",
    "strong": "terme associé",
    "weak": "contexte",
}

# Budget des autres critères. Déclarés ici même s'ils ne sont pas encore
# évalués, pour que l'on sache ce qui manque au score.
POINTS_DIPLOME = 20
POINTS_PAYS = 15


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


def termes_trouves(texte, termes):
    """Renvoie les termes présents dans le texte, dans l'ordre du profil.

    Cette fonction reste la brique de base : elle ne connaît ni les paliers ni
    le profil complet, seulement une liste de termes.
    """
    return [terme for terme in termes if contient(texte, terme)]


def correspondent(texte, profil):
    """Renvoie la meilleure correspondance trouvée dans le texte.

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
                "points": PALIER_POINTS["direct"],
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
                points = PALIER_POINTS[palier]
                if meilleure is None or points > meilleure["points"]:
                    meilleure = {
                        "palier": palier,
                        "champ": champ,
                        "terme": terme,
                        "points": points,
                    }
    return meilleure


def evaluer(opportunity, profil):
    """Évalue une opportunité et renvoie matched, score et reasons.

    Les trois critères évaluables aujourd'hui sont le domaine, le diplôme et le
    pays. Ce sont les seuls que les sources extraites permettent de vérifier ;
    le financement et la date limite viendront plus tard, et le budget du
    module les attend.

    Les raisons sont des phrases, pas des booléens : l'étudiant doit pouvoir
    lire pourquoi un programme lui est proposé (docs/README.md §10).
    """
    reasons = []
    score = 0

    # On assemble ce que la page publie. Une source qui n'affiche pas ses
    # domaines de recherche, comme TUM, est donc comparée sur son titre et sa
    # description : moins de critères, jamais de critères inventés.
    texte = " ".join(
        part
        for part in (opportunity.title, opportunity.field, opportunity.description)
        if part
    )
    correspondance = correspondent(texte, profil)
    if correspondance is not None:
        score += correspondance["points"]
        reasons.append(
            f"{correspondance['terme']} "
            f"({PALIER_LABELS[correspondance['palier']]} a {correspondance['champ']})"
        )

    if "master" in (opportunity.degree or "").lower():
        score += POINTS_DIPLOME
        reasons.append("Diplôme Master")

    pays = (opportunity.country or "").lower()
    if any(pays == prefere.lower() for prefere in profil["preferred_countries"]):
        score += POINTS_PAYS
        reasons.append(f"Pays {opportunity.country}")

    return {
        "matched": correspondance is not None,
        "score": score,
        "reasons": reasons,
    }

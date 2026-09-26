"""Correspondance entre un texte et les domaines du profil.

Un seul concept, réutilisé partout : le filtrage de V0.3, l'extraction d'une
page de domaines de recherche, ou la vérification d'un financement.

Ce module ne dépend d'aucune source ni d'aucun site. Il ne fait que comparer
deux textes.
"""


def variantes(terme):
    """Renvoie les formes acceptables d'un terme du profil.

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
    """Renvoie les termes du profil effectivement présents dans le texte.

    Indispensable pour `src/filters.py` : il doit pouvoir expliquer pourquoi
    une opportunité a été retenue, en citant les termes qui ont correspondu,
    et non en renvoyant un simple vrai ou faux.
    """
    return [terme for terme in termes if contient(texte, terme)]

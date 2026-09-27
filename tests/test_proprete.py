"""Tests de propreté des fichiers du dépôt.

Ce fichier ne teste pas le programme : il teste que les fichiers qu'il lit sont
lisibles. Chaque contrôle porte sur un défaut rencontré en RÉALITÉ pendant la
construction de la V0.3 et de la V0.4, jamais sur une règle de style.

## Des caractères écrits dans une autre écriture que la nôtre

Trois fois pendant la construction, un caractère CJK s'est retrouvé dans un
fichier écrit à la main, au milieu d'une ligne de code ou de commentaire. Le code
continuait de fonctionner : rien ne plantait. Un commentaire en chinois, en
revanche, veut dire qu'un fichier a été écrit par quelque chose qui ne l'avait
pas compris, et c'est exactement le moment où il ne faut pas faire confiance au
reste du fichier. Un caractère chinois s'est glissé une fois dans une chaîne de
recherche de mot-clé, ce qui produit un résultat silencieusement faux : la
recherche ne trouve plus rien, et le code raisonne sur un historique vide sans
le dire.

Le motif est donc plus large que le CJK, et il a été élargi après coup : un
caractère arabe s'est lui aussi glissé dans un commentaire de ce fichier même,
le jour où il a été écrit. Les écritures retenues sont celles qui n'ont aucune
raison de se trouver dans un projet écrit en français : CJK, kana, hangul, arabe,
hébreu, devanagari, thaï, et cyrillique. Le cyrillique y figure pour la même
raison que les autres : aucune source du registre n'est russe.

## `data/` est exclu des écritures

C'est la seule exception, et elle est délibérée. Les fiches de `data/` sont
copiées depuis des pages vivantes : une université coréenne peut publier un
titre en hangul demain, et ce serait une information publiée, pas un défaut. Un
test qui échouerait le jour où cela arrive deterrentait la veille pour une
bonne nouvelle. `data/` est donc seulement soumis à l'encodage.

## L'encodage

Windows écrit par défaut en cp1252. Un accent devient alors illisible, et le
fichier est du Python invalide au premier lancement. Le test lit chaque fichier
en UTF-8 strict : c'est le seul moyen de le savoir avant de l'exécuter.

## Une définition en doublon, le seul défaut que Python accepte

Un fichier peut définir deux fois la même fonction : Python prend la seconde,
sans un mot. Aucun test de syntaxe ne le voit, et l'erreur n'apparaît qu'à
l'exécution, sous la forme d'un `NameError` sur une fonction qui, elle, a bien
été supprimée. Un test dédié le vérifie, parce que c'est arrivé pendant la
construction de la V0.6.

## Pourquoi il n'y a pas de test de longueur de ligne

Un test de propreté qui échoue oblige à reformater des fichiers qu'on n'a pas
choisi de reformater. `config/profile.json` et les documents du cahier des
charges sont le travail de l'étudiant : un test qui impose une largeur de colonne
à ses notes serait un test qui disposerait de son travail. Les contrôles
ci-dessous sont tous des défauts qui cassent quelque chose, et tous sont déjà
satisfaits par le dépôt : ils peuvent donc servir de garde-fou, jamais de
prétexte.
"""

import re
import socket
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
EXTENSIONS = {".py", ".md", ".json", ".yml", ".ini"}

# Les fichiers du programme, et ceux qu'il produit.
COMPOSANTS = ("src", "config", "docs", "tests", ".github", "README.md", "pytest.ini")
DONNEES = ("data",)

# Hanzi, hiragana, katakana, hangul, arabe, hébreu, devanagari, thaï, cyrillique,
# et les formes de pleine largeur.
AUTRES_ECRITURES = re.compile(
    "["
    "\u2e80-\u303f"  # CJK, kana, Hangul
    "\u3040-\u30ff"
    "\u3100-\u312f"
    "\u3400-\u4dbf"
    "\u4e00-\u9fff"
    "\ua960-\ua97f"
    "\uac00-\ud7af"
    "\uf900-\ufaff"
    "\ufe30-\ufe4f"
    "\uff00-\uffef"  # pleine largeur
    "\u0590-\u05ff"  # hébreu
    "\u0600-\u06ff"  # arabe
    "\u0750-\u077f"  # arabe complémentaire
    "\u0900-\u097f"  # devanagari
    "\u0e00-\u0e7f"  # thaï
    "\u0400-\u04ff"  # cyrillique
    "]"
)


def reperes(composants):
    """Les fichiers d'un ensemble de composants, triés, sans doublon."""
    vus = set()
    for composant in composants:
        chemin = RACINE / composant
        if chemin.is_file():
            vus.add(chemin)
        else:
            vus.update(f for f in chemin.rglob("*") if f.is_file() and f.suffix in EXTENSIONS)
    return sorted(vus)


# Le nom est utilisé comme identifiant de paramètre : pytest l'affiche dans
# l'échec, ce qui désigne le fichier sans avoir à le reporter à la main.
@pytest.fixture(scope="module", params=[f.relative_to(RACINE).as_posix() for f in reperes(COMPOSANTS)])
def fichier(request):
    """Un fichier du programme, un par exécution du test."""
    return RACINE / request.param


@pytest.fixture(scope="module", params=[f.relative_to(RACINE).as_posix() for f in reperes(COMPOSANTS + DONNEES)])
def fichier_avec_donnees(request):
    """Un fichier du programme, plus ceux de `data/`."""
    return RACINE / request.param


def intrus(chemin, motif):
    """Renvoie le motif trouvé dans le fichier, avec sa ligne et son contexte."""
    contenu = chemin.read_text(encoding="utf-8")
    trouve = motif.search(contenu)
    if trouve is None:
        return None
    return (
        contenu[: trouve.start()].count("\n") + 1,
        trouve.group(),
        contenu[max(0, trouve.start() - 30) : trouve.start() + 15],
    )


def test_le_fichier_est_du_utf8(fichier_avec_donnees):
    # Lecture stricte : un fichier en cp1252 lève ici, au lieu de produire un
    # accent de travers trois lignes plus loin.
    fichier_avec_donnees.read_text(encoding="utf-8")


def test_pas_de_caractere_dans_une_autre_ecriture(fichier):
    trouve = intrus(fichier, AUTRES_ECRITURES)
    if trouve is None:
        return
    numero, caractere, contexte = trouve
    pytest.fail(
        f"{fichier.relative_to(RACINE)}:{numero} contient "
        f"{caractere!r} (U+{ord(caractere):04X}). Contexte : {contexte!r}"
    )


def test_pas_de_tabulation(fichier_avec_donnees):
    # Python 3 assimile les tabulations, donc le problème ne se voit qu'en
    # exécutant. Les autres fichiers s'en passent très bien.
    contenu = fichier_avec_donnees.read_text(encoding="utf-8")
    lignes = [i for i, l in enumerate(contenu.split("\n"), start=1) if "\t" in l]
    assert lignes == [], f"tabulation(s) ligne(s) {lignes}"


def test_pas_d_espace_en_fin_de_ligne(fichier_avec_donnees):
    # Un espace en fin de ligne ne se voit pas et se retrouve dans chaque
    # version du fichier, sans jamais avoir été écrit volontairement.
    contenu = fichier_avec_donnees.read_text(encoding="utf-8")
    lignes = [i for i, l in enumerate(contenu.split("\n"), start=1) if l != l.rstrip()]
    assert lignes == [], f"espace(s) en fin de ligne {lignes}"


def test_pas_de_ligne_vide_en_fin_de_fichier(fichier_avec_donnees):
    # Un saut de ligne surnuméraire ne se voit pas à l'écran et se voit dans
    # chaque diff du fichier.
    contenu = fichier_avec_donnees.read_text(encoding="utf-8")
    assert not contenu.endswith("\n\n")


# Une définition en doublon, qui est le seul défaut de syntaxe que Python accepte


@pytest.fixture(
    scope="module",
    params=[f.relative_to(RACINE).as_posix() for f in reperes(("src", "tests")) if f.suffix == ".py"],
)
def module_python(request):
    """Un fichier Python du programme, un par exécution du test."""
    return RACINE / request.param


def test_une_fonction_n_est_pas_definie_deux_fois(module_python):
    # Un doublon est le seul défaut que Python ne signale pas : le fichier est
    # valide, la dernière définition écrase la première, et rien ne dit qu'il y
    # en avait deux. L'erreur n'apparaît qu'à l'exécution, sous la forme d'un
    # `NameError` sur une fonction qui a bien été supprimée.
    #
    # C'est arrivé pendant la V0.6 : un remplacement de bloc s'était arrêté à la
    # première occurrence de `def main():`, et avait donc laissé l'ancien
    # `main()` sous le nouveau, encore appelant deux fonctions supprimées.
    # Quelque chose manquait à l'écran, et le fichier ne le disait pas.
    #
    # Seules les définitions de premier niveau comptent : une méthode de classe
    # est indentée, donc hors du motif. C'est volontaire, un `def` indenté dans
    # une classe ou une fonction n'est pas un doublon de portée.
    contenu = module_python.read_text(encoding="utf-8")
    vues = {}
    for numero, ligne in enumerate(contenu.split("\n"), start=1):
        trouve = re.match(r"def ([A-Za-z_]\w*)\(", ligne)
        if trouve:
            vues.setdefault(trouve.group(1), []).append(numero)
    doublons = {nom: numeros for nom, numeros in vues.items() if len(numeros) > 1}
    assert not doublons, f"fonction(s) définie(s) deux fois : {doublons}"


# Le garde-fou qui empêche un test de joindre un serveur


def test_le_garde_fou_du_reseau_bloque_les_trois_chemins():
    # La règle « aucun test ne touche au réseau » ne tient qu'à une fixture de
    # `conftest.py`. Une règle qu'on ne vérifie pas peut être fausse sans que
    # personne ne le sache, donc ce test tente les trois sorties et vérifie
    # qu'elles sont refusées. Il est lui-même soumis au garde-fou : il ne peut
    # donc constater qu'il fonctionne qu'en observant l'échec.
    #
    # Les trois chemins sont essayés parce qu'un seul bouché laisserait passer
    # les deux autres. `smtplib` passe par `create_connection`, un appel HTTP par
    # `connect`, et la résolution du nom par `getaddrinfo`.
    for nom, appel in (
        ("getaddrinfo", lambda: socket.getaddrinfo("smtp.office365.com", 587)),
        ("create_connection", lambda: socket.create_connection(("smtp.office365.com", 587))),
        ("connect", lambda: socket.socket().connect(("smtp.office365.com", 587))),
    ):
        with pytest.raises(AssertionError, match="ne doit pas joindre un serveur"):
            appel()

"""Tests de cohérence des données versionnées : data/opportunities.json et
data/seen.json.

Ces deux fichiers sont commités dans le dépôt, donc ils sont relus à chaque
exécution et par toute personne qui clone le projet. Un fichier de données
corrompu ne casse pas le programme tout de suite : il le casse *silencieusement*,
en faisant passer des opportunités pour nouvelles, ou en perdant l'historique.
C'est le genre de défaut qu'on découvre trois mois plus tard, dans l'historique
Git, sans plus savoir à quelle exécution il appartient.

Ces tests lisent les vraies données et ne les modifient pas. Ils ne valident pas
le contenu des pages, qui est mesuré à la main et écrit dans docs/SOURCES.md :
ils valident que le fichier est ce qu'il prétend être.
"""

import json
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "data"
TYPES_DECLARES = {
    source["type"]
    for source in json.loads((RACINE / "config" / "sources.json").read_text(encoding="utf-8"))["sources"]
    if source.get("type")
}


@pytest.fixture(scope="module")
def opportunities():
    return json.loads((DOSSIER / "opportunities.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def vus():
    return json.loads((DOSSIER / "seen.json").read_text(encoding="utf-8"))


# 1. La forme du fichier


def test_les_deux_fichiers_existent(opportunities, vus):
    # Un dépôt sans données est un dépôt dont la veille n'a jamais tourné. C'est
    # un état possible, pas une erreur : le test vérifie la cohérence, pas
    # l'exécution passée.
    assert isinstance(opportunities, list)
    assert isinstance(vus, list)


def test_chaque_fiche_est_un_objet(opportunities):
    fiches_non_objet = [f for f in opportunities if not isinstance(f, dict)]
    assert fiches_non_objet == []


def test_chaque_fiche_a_une_identite(opportunities):
    sans_identite = [f.get("title") for f in opportunities if not f.get("identite")]
    assert sans_identite == []


def test_chaque_fiche_a_une_premiere_apparition(opportunities):
    # Sans elle, on ne peut pas dire « cela fait trois mois que cette offre est
    # là », et c'est une des raisons d'être de l'historique.
    sans_date = [f.get("identite") for f in opportunities if not f.get("first_seen_at")]
    assert sans_date == []


def test_la_premiere_apparition_precède_la_derniere_collecte(opportunities):
    # Une date de première apparition postérieure à la collecte est impossible.
    inversees = [
        f["identite"] for f in opportunities if f.get("first_seen_at") and f.get("collected_at")
        and f["first_seen_at"] > f["collected_at"]
    ]
    assert inversees == []


def test_chaque_fiche_a_une_source_au_registre(opportunities):
    # Une source écrite à la main dans le code de scraping mais absente du
    # registre, ou l'inverse, signale que l'un des deux a dérivé.
    registre = {
        source["name"] for source in json.loads((RACINE / "config" / "sources.json").read_text(encoding="utf-8"))["sources"]
    }
    hors_registre = sorted({f["source"] for f in opportunities} - registre)
    assert hors_registre == []


def test_le_type_de_chaque_fiche_est_declare(opportunities):
    # Le type vient du registre, il ne peut pas être inventé par un parseur.
    hors_registre = sorted({f.get("type") for f in opportunities} - TYPES_DECLARES)
    assert hors_registre == []


# 2. L'historique tient debout


def test_pas_de_doublon_d_identite(opportunities):
    # C'est la propriété que la règle d'identité garantit, et qu'une collision
    # silencieuse casserait : un doublon signifie une opportunité écrasée, donc
    # perdue. Le cas mesuré qui a fait ajouter le diplôme à l'identité est deux
    # programmes de TUM appelés tous deux « Aerospace ».
    identites = [f["identite"] for f in opportunities]
    doublons = sorted({i for i in identites if identites.count(i) > 1})
    assert doublons == []


def test_vus_est_un_sous_ensemble_de_l_historique(opportunities, vus):
    # Un identifiant dans seen.json qui n'est pas dans opportunities.json
    # signifierait que l'historique a été réécrit sans l'historique des vues, ou
    # l'inverse. Les deux fichiers sont écrits par la même exécution, donc c'est
    # un défaut d'écriture, pas une divergence normale.
    orphelins = sorted(set(vus) - {f["identite"] for f in opportunities})
    assert orphelins == []


def test_vus_ne_contient_que_des_identites_deja_notees(opportunities, vus):
    vus = set(vus)
    retenues = [f for f in opportunities if f.get("matched")]
    jamais_montrees = [f["identite"] for f in retenues if f["identite"] not in vus]
    # Les opportunités retenues doivent avoir été montrées : c'est ce que
    # garantit `conserver_vus` en fin d'exécution.
    assert jamais_montrees == []
    # Et une opportunité écartée n'a aucune raison d'y figurer.
    ecartees_montrees = [f["identite"] for f in opportunities if not f.get("matched") and f["identite"] in vus]
    assert ecartees_montrees == []


def test_vus_est_sans_doublon(vus):
    # Le fichier est écrit par un ensemble trié, donc l'ordre est garanti aussi.
    assert vus == sorted(set(vus))


# 3. Le fichier reste lisible


def test_les_accents_sont_ecrits_tels_que(opportunities):
    # Sans ensure_ascii=False, le fichier contient « R\u00e9seaux » et n'est
    # lisible que par un outillage. C'est dérangeant pour un fichier versionné
    # et destiné à être relu, et surtout relisible par git diff.
    brut = (DOSSIER / "opportunities.json").read_text(encoding="utf-8")
    assert "\\u" not in brut


def test_le_fichier_est_indente(opportunities):
    # Un JSON sur une seule ligne donne un diff illisible : on ne voit pas ce qui
    # a changé, seulement qu'un octet a changé.
    brut = (DOSSIER / "opportunities.json").read_text(encoding="utf-8")
    assert "\n  {" in brut
    assert brut.endswith("\n")

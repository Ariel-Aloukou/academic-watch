"""Tests de la sauvegarde : src/storage.py (docs/VERSIONS.md V0.4).

Le module ne dépend d'aucune bibliothèque externe et ne touche pas au réseau,
donc ces tests sont déterministes et peuvent tourner dans le workflow
quotidien. Ils vérifient le cas nominal, et surtout ce qui *brise* une
sauvegarde : un fichier tronqué, un format inattendu, une première exécution.
Ces cas sont les seuls qui aient réellement cassé quelque chose pendant la
construction de la version.
"""

import json

import pytest

import storage
from models import Opportunity


# 1. L'identité
#
# C'est la seule vraie décision de la V0.4, et elle a été reprise sur une
# mesure : la règle `source + titre` perdait le Bachelor of Science de TUM.


def identite(titre, source="KAIST - Explore Programs", diplome="Master's"):
    return storage.identite(opportunite(titre, source=source, diplome=diplome))


def test_identite_est_ascii_et_lisible():
    # Un identifiant doit pouvoir être écrit dans un fichier et relu sans
    # outillage. Les accents sont retirés par la normalisation, donc il ne
    # reste que de l'ASCII.
    calcul = identite("Master's Programme in Cybersecurity")
    assert calcul == "KAIST - Explore Programs|master s programme in cybersecurity|master s"
    assert all(c.isascii() for c in calcul)


def test_identite_ignore_casse_et_ponctuation():
    assert identite("MASTER'S programme in Cybersecurity!") == identite(
        "Master's Programme in Cybersecurity"
    )


def test_deux_sources_de_meme_titre_ne_fusionnent_pas():
    # C'est le registre qui distingue les sources, pas la page.
    assert identite("Master A", source="S1") != identite("Master A", source="S2")


def test_deux_titres_differents_separent():
    assert identite("Master A") != identite("Master B")


def test_meme_titre_et_diplome_different_ne_fusionnent_pas():
    # La collision mesuree sur le site de TUM : deux programmes appeles
    # "Aerospace", un Master of Science et un Bachelor of Science. Sans le
    # diplome dans l'identite, le Bachelor disparaissait de l'historique.
    msc = identite("Aerospace", source="TUM - Degree programs", diplome="Master of Science (M.Sc.)")
    bsc = identite("Aerospace", source="TUM - Degree programs", diplome="Bachelor of Science (B.Sc.)")
    assert msc != bsc


def test_un_diplome_absent_porte_un_marqueur():
    # Dans une identité, "on ne sait pas" et "la valeur est vide" doivent rester
    # distinguables. Le marqueur "?" est lisible et n'apparait dans aucun titre.
    assert identite("Master A", diplome=None).endswith("|?")
    assert identite("Master A", diplome=None) != identite("Master A", diplome="Master's")


def test_les_accents_sont_normalises():
    assert storage.normaliser_titre("Master en Réseaux et Télécommunications") == storage.normaliser_titre(
        "Master en Reseaux et Telecommunications"
    )


# 2. L'historique
#
# Chaque test travaille dans un dossier à lui, désigné par `sandbox`. Les
# chemins de storage sont des variables de module, donc on les redirige plutôt
# que de tester dans le vrai data/.


@pytest.fixture
def historique(sandbox):
    """Un data/ à part, propre à chaque test."""
    storage.OPPORTUNITES = sandbox / "opportunities.json"
    storage.VUS = sandbox / "seen.json"
    return storage.OPPORTUNITES


def test_premiere_ecriture_signale_tout_comme_nouveau(historique):
    assert len(storage.sauvegarder([opportunite("Master A"), opportunite("Master B")])) == 2
    assert len(storage.lire(historique)) == 2


def test_la_meme_collecte_ne_signale_rien_de_nouveau(historique):
    lot = [opportunite("Master A"), opportunite("Master B")]
    storage.sauvegarder(lot)
    assert storage.sauvegarder(lot) == []
    assert len(storage.lire(historique)) == 2


def test_une_seule_opportunite_neuve_se_fond_dans_l_historique(historique):
    storage.sauvegarder([opportunite("Master A"), opportunite("Master B")])
    nouvelles = storage.sauvegarder([opportunite("Master A"), opportunite("Master B"), opportunite("Master C")])
    assert len(nouvelles) == 1
    assert len(storage.lire(historique)) == 3


def test_chaque_fiche_porte_sa_premiere_apparition(historique):
    storage.sauvegarder([opportunite("Master A", recoltee="2026-09-26T10:00:00+00:00")])
    fiche = storage.lire(historique)[0]
    assert fiche["first_seen_at"] == "2026-09-26T10:00:00+00:00"


def test_la_premiere_apparition_survit_a_une_collecte_ulterieure(historique):
    storage.sauvegarder([opportunite("Master A", recoltee="2026-09-26T10:00:00+00:00")])
    storage.sauvegarder([opportunite("Master A", recoltee="2026-10-01T10:00:00+00:00")])
    assert storage.lire(historique)[0]["first_seen_at"] == "2026-09-26T10:00:00+00:00"


def test_les_donnees_se_rafraichissent(historique):
    storage.sauvegarder([opportunite("Master A", url="https://exemple/avant")])
    storage.sauvegarder([opportunite("Master A", url="https://exemple/apres")])
    fiches = storage.lire(historique)
    assert len(fiches) == 1
    assert fiches[0]["url"] == "https://exemple/apres"


def test_un_diplome_reecrit_cree_une_identite(historique):
    # Limite connue et écrite dans le module : KAIST publie trois niveaux joints
    # en une seule chaine. Si l'ordre change, l'identite change. Ce test verrouille
    # le comportement pour qu'on ne le decouvre pas par surprise.
    storage.sauvegarder([opportunite("Master A", diplome="Master's")])
    nouvelles = storage.sauvegarder([opportunite("Master A", diplome="Master's (reformule)")])
    assert len(nouvelles) == 1
    assert len(storage.lire(historique)) == 2


# 3. Le fichier ne bouge pas quand rien ne bouge
#
# Sans cela, les 69 fiches seraient réécrites chaque jour et la veille
# produirait un changement par jour quoi qu'il arrive.


def test_deux_collectes_identiques_laisissent_le_fichier_intact(historique):
    lot = [opportunite("Master A"), opportunite("Master B")]
    storage.sauvegarder(lot)
    avant = historique.read_bytes()
    storage.sauvegarder([opportunite(o.title, recoltee="2026-10-05T08:00:00+00:00") for o in lot])
    assert historique.read_bytes() == avant


def test_a_change_ignore_les_horodatages():
    fiche = {"url": "u", "collected_at": "2026-09-26T10:00:00+00:00", "first_seen_at": "2026-09-26T10:00:00+00:00"}
    autre_date = {**fiche, "collected_at": "2027-01-01T00:00:00+00:00"}
    assert not storage.a_change(fiche, autre_date)
    assert storage.a_change(fiche, {**fiche, "url": "autre"})


# 4. Ce qui a déjà été montré
#
# seen.json est le fichier qui empêche la veille de répéter. S'il était lu
# comme vide, les 69 opportunités passeraient pour nouvelles à chaque
# exécution : c'est l'erreur qu'un test doit surveiller en priorité.


def test_vus_s_accumulent_sans_se_perdre(historique):
    assert len(storage.conserver_vus([opportunite("Master A")])) == 1
    assert len(storage.conserver_vus([opportunite("Master B")])) == 2
    assert storage.charger_vus() == {identite("Master A"), identite("Master B")}


def test_la_relecture_redonne_le_meme_ensemble(historique):
    storage.conserver_vus([opportunite("Master A")])
    assert storage.charger_vus() == storage.charger_vus()


def test_les_doublons_sont_detectes(historique):
    vus = storage.conserver_vus([opportunite("Master A"), opportunite("Master B")])
    neuves = storage.nouvelles_depuis([opportunite("Master A"), opportunite("Master B"), opportunite("Master Z")], vus)
    assert [o.title for o in neuves] == ["Master Z"]


def test_rien_de_neuf_quand_rien_ne_change(historique):
    vus = storage.conserver_vus([opportunite("Master A")])
    assert storage.nouvelles_depuis([opportunite("Master A")], vus) == []


# 5. Les refus délibérés
#
# Un fichier illisible arrête le programme. Repartir d'un historique vide ne se
# verrait pas : toutes les opportunités passeraient pour nouvelles. Une erreur
# visible vaut mieux qu'une inondation fausse.


def test_un_fichier_corrompu_leve_une_erreur(historique):
    historique.write_text('[{"identite": "a", truq', encoding="utf-8")
    with pytest.raises(storage.StockageInvalide):
        storage.sauvegarder([opportunite("Master A")])


def test_un_fichier_corrompu_n_est_pas_ecrase(historique):
    avant = '[{"identite": "a", truq'
    historique.write_text(avant, encoding="utf-8")
    with pytest.raises(storage.StockageInvalide):
        storage.sauvegarder([opportunite("Master A")])
    assert historique.read_text(encoding="utf-8") == avant


def test_un_json_valide_mais_pas_une_liste_est_refuse(historique):
    historique.write_text('{"identite": "a"}', encoding="utf-8")
    with pytest.raises(storage.StockageInvalide):
        storage.lire(historique)


def test_un_seen_au_mauvais_format_est_refuse_pas_ignore(historique):
    # Des fiches au lieu d'identites : le lire comme vide ferait passer tout pour
    # nouveau. Un format inconnu doit etre bruyant, pas silencieux.
    storage.VUS.write_text('[{"identite": "a"}]', encoding="utf-8")
    with pytest.raises(storage.StockageInvalide):
        storage.charger_vus()


# 6. Les cas ordinaires


def test_un_fichier_absent_n_est_pas_une_erreur(historique):
    assert storage.lire(historique) == []
    assert len(storage.sauvegarder([opportunite("Master A")])) == 1


def test_le_dossier_est_cree_s_il_n_existe_pas(sandbox):
    storage.OPPORTUNITES = sandbox / "sous" / "dossier" / "opportunities.json"
    storage.sauvegarder([opportunite("Master A")])
    assert storage.OPPORTUNITES.exists()


def test_aucune_ecriture_partielle_ne_reste(sandbox):
    storage.OPPORTUNITES = sandbox / "opportunities.json"
    storage.sauvegarder([opportunite("Master A")])
    assert list(sandbox.rglob("*.tmp")) == []


def test_le_fichier_est_lisible_par_un_humain(historique):
    storage.sauvegarder([opportunite("Master en Réseaux")])
    brut = historique.read_text(encoding="utf-8")
    # Sans ensure_ascii=False, les accents partiraient en \u00e9 et le fichier
    # serait illisible sans outillage. Sans indent, il tiendrait sur une ligne.
    assert "\\u" not in brut
    assert "\n  {" in brut
    assert "Réseaux" in brut


# La fabrique
#
# En fin de fichier pour que les tests ci-dessus se lisent sans avoir à sauter
# plus loin. Un Opportunity minimal : la sauvegarde ne lit que l'identité et les
# champs affichés, le reste n'a pas besoin d'être réaliste.


def opportunite(titre, source="KAIST - Explore Programs", diplome="Master's", url="https://exemple/1", recoltee="2026-09-26T10:00:00+00:00"):
    return Opportunity(
        title=titre,
        university="U",
        country="Norway",
        degree=diplome,
        field="Cybersecurity",
        url=url,
        source=source,
        type="programs",
        collected_at=recoltee,
    )

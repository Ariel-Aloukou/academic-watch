"""Tests de la correspondance : src/matches.py (docs/VERSIONS.md V0.3).

Ces tests lisent le vrai `config/profile.json` et non un profil fabriqué. Un
profil d'essai permettrait de valider le moteur sur des cas qui n'existent pas sur
les sources réelles, alors que les pièges de ce module ont tous été trouvés sur
de vraies pages : « undergraduate » qui contient « graduate »,
« Master's-Ph.D. Integrated » qui n'est pas « Master's », l'apostrophe
typographique de KAIST.

Ils ne touchent pas au réseau. Ce qui dépend d'une page vivante est vérifié à la
main et écrit dans docs/SOURCES.md, pas ici : un test qui dépend d'un site
étranger échoue pour une raison qui n'a rien à voir avec le code.
"""

import json
from pathlib import Path

import pytest

import matches
from matches import evaluer
from models import Opportunity

PROFIL = json.loads(
    (Path(__file__).resolve().parent.parent / "config" / "profile.json").read_text(encoding="utf-8")
)


def programme(titre, diplome="Master's", **kwargs):
    """Un programme d'essai, avec les valeurs par défaut des sources actives."""
    return Opportunity(
        title=titre,
        university="U",
        country=kwargs.pop("country", "Germany"),
        degree=diplome,
        field=kwargs.pop("field", None) or "",
        url="https://exemple/1",
        source="Test",
        type=kwargs.pop("type", "programs"),
        collected_at="2026-09-26T10:00:00+00:00",
        **kwargs,
    )


def bourse(diplome="Master's", eligibilite=(), financement=None, **kwargs):
    """Une bourse : elle n'annonce pas de matière, elle annonce qui peut en
    bénéficier. C'est tout le sens de `CRITERES_RETENUS` pour ce type."""
    return Opportunity(
        title=kwargs.pop("title", "Bourse de recherche"),
        university="U",
        country=kwargs.pop("country", "South Korea"),
        degree=diplome,
        field="",
        url="https://exemple/bourse",
        source="Test",
        type="scholarships",
        funding_type=financement,
        eligibility=list(eligibilite),
        collected_at="2026-09-26T10:00:00+00:00",
        **kwargs,
    )


def mesure(opportunite, critere):
    """La mesure d'un critère seul, sous la forme qu'elle a dans le résultat."""
    return matches.MESURES[critere](opportunite, PROFIL, matches.CRITERES[opportunite.type][critere])


# 1. Les trois paliers de domaine
#
# Le poids du domaine change avec le palier atteint : c'est la décision de
# design centrale du profil. Un domaine principal vaut 50, un terme que les
# universités écrivent à sa place vaut 30, un contexte vaut 10. Le palier ne
# décide pas de la retenue : il décide du classement.


def test_un_domaine_du_profil_vaut_le_poids_le_plus_fort():
    resultat = mesure(programme("Master Cybersecurity"), "domaine")
    assert resultat["points"] == 50
    assert "correspondance directe" in resultat["raison"]


def test_un_terme_associe_vaut_moins():
    resultat = mesure(programme("Master Secure Computing"), "domaine")
    assert resultat["points"] == 30
    assert "terme associé" in resultat["raison"]


def test_un_contexte_vaut_moins_encore():
    resultat = mesure(programme("Master Security Engineering"), "domaine")
    assert resultat["points"] == 10
    assert "contexte" in resultat["raison"]


def test_les_trois_paliers_sont_bien_ordonnes():
    # L'ordre des poids est le contrat du profil. S'il s'inversait, un terme
    # associé pourrait se présenter comme une correspondance directe.
    assert matches.POINTS_DOMAINE == {"direct": 50, "strong": 30, "weak": 10}
    assert matches.POINTS_DOMAINE["direct"] > matches.POINTS_DOMAINE["strong"] > matches.POINTS_DOMAINE["weak"]


def test_une_matiere_hors_profil_ne_prend_rien():
    resultat = mesure(programme("Master Marine Biology"), "domaine")
    assert resultat["points"] == 0
    assert "aucun terme du profil" in resultat["raison"]


def test_le_meilleur_palier_gagne():
    # Un texte qui contient à la fois un terme associé et un contexte vaut le
    # terme associé. Deux correspondances faibles ne valent pas mieux qu'une
    # correspondance nette.
    resultat = mesure(programme("Master Cryptography and Secure Computing"), "domaine")
    assert resultat["points"] == 30


def test_le_singulier_tient(compromis=False):
    # KAIST écrit « Telecommunication Technology » quand le profil écrit
    # « Telecommunications ». Sans la variante au singulier, ce programme
    # pertinent serait écarté.
    assert mesure(programme("Telecommunication Technology"), "domaine")["points"] == 50


def test_une_source_sans_texte_ne_produit_pas_de_point():
    resultat = mesure(programme("", diplome=""), "domaine")
    assert resultat["points"] == 0
    assert "aucun texte" in resultat["raison"]


def test_le_champ_domaines_compte_comme_le_titre():
    # TUM n'affiche pas ses domaines de recherche : seuls le titre et la
    # description sont disponibles. La mesure ne perd rien de ce qui existe.
    assert mesure(programme("Master", field="Cybersecurity"), "domaine")["points"] == 50
    assert mesure(programme("Master Cybersecurity", field=""), "domaine")["points"] == 50


def test_la_description_compte_elle_aussi():
    # Le profil est en anglais : une description française n'y correspond pas, et
    # c'est une limite assumée plutôt qu'un bug. Le test porte donc sur une
    # description qui n'apparaît dans aucun autre champ.
    assert (
        mesure(programme("Master", description="Applied cryptography and systems"), "domaine")["points"] == 10
    )


# 2. Le diplôme
#
# Le profil vise « Master ». Douze formes réelles ont été essayées, dont trois
# qui piégeaient : « undergraduate » (contient « graduate »),
# « Master's-Ph.D. Integrated » (contient « Master ») et « graduate » (ouvre la
# porte, aux Pays-Bas comme au Royaume-Uni).


@pytest.mark.parametrize(
    "diplome, attendu",
    [
        ("Master of Science (M.Sc.)", 20),
        ("Master's", 20),
        ("Master", 20),
        ("Master of Arts", 20),
        ("Master's, Graduate", 20),
        ("graduate programs", 20),
        ("Bachelor of Science (B.Sc.)", 0),
        ("Bachelor", 0),
        ("undergraduate", 0),
        ("Ph.D", 0),
        ("Doctoral Program", 0),
        ("Master's-Ph.D. Integrated", 0),
    ],
)
def test_les_douze_formes_de_diplome(diplome, attendu):
    assert mesure(programme("Master X", diplome=diplome), "diplome")["points"] == attendu


def test_le_diplome_non_publie_va_lire_le_titre():
    # EACEA ne publie aucun champ « degree ». Le titre en tient lieu : c'est une
    # information publiée, pas une devinette. Le motif dit lequel des deux a été
    # lu, sinon l'étudiant ne saurait pas d'où vient la correspondance.
    resultat = mesure(programme("Master's Programme in Cybersecurity and Assurance", diplome=""), "diplome")
    assert resultat["points"] == 20
    assert resultat["raison"].startswith("titre ")


def test_le_champ_diplome_prime_sur_le_titre():
    # Quand la source publie les deux, c'est le champ qui fait foi. Un titre
    # parlant de « Bachelor » ne doit pas faire ignorer un « Master of Science ».
    resultat = mesure(programme("Bachelor of Science, Master track", diplome="Master of Science"), "diplome")
    assert resultat["points"] == 20
    assert resultat["raison"].startswith("diplôme ")


def test_un_diplome_hors_liste_dit_pourquoi():
    resultat = mesure(programme("Master X", diplome="Bachelor of Science"), "diplome")
    assert resultat["points"] == 0
    assert "hors de la liste visée" in resultat["raison"]


def test_rien_du_tout_ne_produit_aucun_point():
    resultat = mesure(programme("", diplome=""), "diplome")
    assert resultat["points"] == 0
    assert resultat["raison"] == "diplôme non publié"


def test_une_apostrophe_typographique_ne_trompe_pas():
    # KAIST écrit « Master’s » avec U+2019. Sans normalisation, la forme composée
    # « Master’s-Ph.D. » ne serait pas retirée, et une bourse de doctorat
    # compterait comme une bourse de Master.
    resultat = mesure(programme("X", diplome="Master\u2019s-Ph.D. Integrated"), "diplome")
    assert resultat["points"] == 0


# 3. Le pays
#
# Le pays ne retient jamais rien : il classe. Un pays absent des préférences
# n'est pas un refus.


def test_un_pays_prefere_prend_les_points():
    resultat = mesure(programme("Master X", country="Norway"), "pays")
    assert resultat["points"] == 15
    assert resultat["raison"] == "pays Norway"


def test_un_pays_non_prefere_prend_zero_mais_n_est_pas_refuse():
    resultat = mesure(programme("Master X", country="Europe"), "pays")
    assert resultat["points"] == 0
    assert "hors de la liste préférée" in resultat["raison"]
    # C'est le fait mesuré sur EACEA : country vaut « Europe » pour ses 20
    # programmes, et « Europe » n'est pas dans preferred_countries. Aucun n'est
    # rejeté pour autant.
    assert evaluer(programme("Master Cybersecurity", country="Europe"), PROFIL)["matched"]


def test_un_pays_absent_prend_zero_sans_raison_de_refus():
    resultat = mesure(programme("Master X", country=""), "pays")
    assert resultat["points"] == 0
    assert resultat["raison"] == "pays non renseigné"


# 4. La langue
#
# Le critère est écrit et testé, mais aucune source active ne renseigne
# `language`. Le maximum atteignable d'un programme est donc 85 sur 100, et il
# faut que les tests le disent, sinon quelqu'un lira « 85/100 » comme un bug.


def test_une_langue_acceptee_prend_les_points():
    resultat = mesure(programme("Master X", language="English"), "langue")
    assert resultat["points"] == 15


def test_une_langue_refusee_prend_zero():
    resultat = mesure(programme("Master X", language="Korean"), "langue")
    assert resultat["points"] == 0
    assert "hors de la liste acceptée" in resultat["raison"]


def test_une_langue_non_publiee_prend_zero():
    # C'est le cas des 69 opportunités actuelles. Le maximum atteignable d'un
    # programme est 85, pas 100.
    resultat = mesure(programme("Master X"), "langue")
    assert resultat["points"] == 0
    assert resultat["raison"] == "langue non publiée"


def test_le_maximum_atteignable_est_ce_qui_est_publie():
    resultat = evaluer(programme("Master Cybersecurity"), PROFIL)
    assert resultat["score_max"] == 100
    assert resultat["score"] == 85


# 5. Les bourses
#
# Trois corrections en viennent. Les trois bourses KAIST étaient rejetées parce
# qu'elles n'annoncent pas de matière : exiger un domaine d'une bourse revient à
# écarter toutes les bourses.


def test_une_bourse_ouverte_est_retenue():
    resultat = evaluer(
        bourse(
            diplome="Master's",
            eligibilite=["Open to international students", "Master's students only"],
            financement="Full tuition",
        ),
        PROFIL,
    )
    assert resultat["matched"]
    assert resultat["score"] == 100


def test_une_bourse_doctorale_est_ecartee_et_dit_pourquoi():
    resultat = evaluer(
        bourse(
            diplome="Ph.D",
            eligibilite=["Open to international Ph.D candidates"],
            financement="Full tuition",
        ),
        PROFIL,
    )
    assert not resultat["matched"]
    assert "réservée à un niveau doctoral" in " ".join(resultat["reasons"])


def test_une_bourse_reservee_a_une_population_nationale_est_ecartee():
    resultat = evaluer(
        bourse(
            diplome="Master's",
            eligibilite=["Open to Korean domestic students only"],
            financement="Full tuition",
        ),
        PROFIL,
    )
    assert not resultat["matched"]
    assert "réservée à une population nationale" in " ".join(resultat["reasons"])


def test_une_bourse_sans_mention_d_international_n_est_pas_retenue():
    # Le critère retient, donc une bourse qui n'ouvre rien à l'international ne
    # passe pas. Elle est signalée comme indéterminée, pas refusée.
    resultat = evaluer(bourse(diplome="Master's", eligibilite=["Master's students"]), PROFIL)
    assert not resultat["matched"]
    assert "non précisée" in " ".join(resultat["reasons"])


def test_une_bourse_sans_eligibilite_publiee_prend_zero():
    # Le critère lit l'éligibilité, le diplôme et le titre. Sans aucun des trois,
    # il n'y a rien à mesurer. Un diplôme seul suffit en revanche : c'est une
    # information publiée sur le niveau, et c'est ce que reçoit une bourse dont
    # la page d'éligibilité est vide.
    assert mesure(bourse(diplome="", title=""), "niveau")["raison"] == "éligibilité non publiée"
    assert mesure(bourse(diplome="Master's", title=""), "niveau")["points"] == 40


def test_international_students_n_est_pas_lu_comme_national():
    # Non-régression. « international students » contient « national student »
    # comme sous-chaîne. Une recherche par sous-chaîne classait donc la formule
    # la plus courante du monde comme une bourse réservée aux nationaux, et
    # écartait une bourse entièrement ouverte. Les trois bourses de KAIST
    # échappaient au piège par chance : elles écrivent « applicants ».
    resultat = evaluer(
        bourse(diplome="Master's", eligibilite=["Open to international students"], financement="Full tuition"),
        PROFIL,
    )
    assert resultat["matched"]
    assert "ouverte aux étudiants internationaux" in " ".join(resultat["reasons"])


def test_national_students_est_bien_refuse():
    # Le contre-test du précédent : la borne de mot doit distinguer les deux, et
    # le pluriel doit rester détecté.
    resultat = evaluer(
        bourse(diplome="Master's", eligibilite=["Open to national students only"], financement="Full tuition"),
        PROFIL,
    )
    assert not resultat["matched"]
    assert "réservée à une population nationale" in " ".join(resultat["reasons"])


def test_un_financement_complet_prend_plus_qu_un_partiel():
    complet = mesure(bourse(financement="Full tuition"), "financement")
    partiel = mesure(bourse(financement="Tuition reduction"), "financement")
    assert complet["points"] == 20
    assert partiel["points"] == 10


def test_une_aide_sans_frais_de_scolarite_prend_zero():
    resultat = mesure(bourse(financement="Monthly stipend"), "financement")
    assert resultat["points"] == 0
    assert "aucune prise en charge" in resultat["raison"]


# 6. La porte et le classement
#
# `matched` est la porte, `score` ne classe que parmi les retenues. Confondre
# les deux ferait remonter des programmes hors sujet dès qu'ils cumulent des
# points faciles.


def test_un_contexte_seul_suffit_a_retenir_un_programme():
    # Le palier ne retient pas. Ce qui retient, c'est la matière.
    assert evaluer(programme("Master Cryptography"), PROFIL)["matched"]


def test_sans_matiere_un_programme_n_est_pas_retenu_meme_bien_note():
    # 20 (diplôme) + 15 (pays préféré) = 35 points, et pourtant écarté.
    resultat = evaluer(programme("Master Marine Biology", country="Norway"), PROFIL)
    assert resultat["score"] == 35
    assert not resultat["matched"]


def test_chaque_type_a_son_maximum():
    assert evaluer(programme("Master X"), PROFIL)["score_max"] == 100
    assert evaluer(bourse(), PROFIL)["score_max"] == 100


def test_un_type_inconnu_retombe_sur_les_programmes():
    # « KAIST - Eligibility Requirements » déclare `eligibility`, qui n'a pas de
    # budget. La page est notée comme un programme, donc elle doit être annoncée
    # comme un programme : un score de 100 accompagné du libellé « eligibility »
    # afficherait deux budgeting différents sur la même ligne.
    assert evaluer(programme("Master X", type=None), PROFIL)["type"] == "programs"
    assert evaluer(programme("Master X", type="eligibility"), PROFIL)["type"] == "programs"
    assert evaluer(programme("Master X", type="eligibility"), PROFIL)["score_max"] == 100


# 7. Les contrats que le module s'impose à lui-même
#
# Le module écrit qu'ajouter un critère sans écrire sa mesure est une erreur
# visible au premier lancement. Ces tests la rendent visible au premier `pytest`,
# ce qui est plus tôt et ne dépend d'aucune page.


def test_chaque_critere_a_sa_mesure():
    demandes = {nom for budget in matches.CRITERES.values() for nom in budget}
    assert demandes <= set(matches.MESURES), f"critère sans mesure : {demandes - set(matches.MESURES)}"


def test_chaque_mesure_est_utilisee():
    # Une mesure orpheline est du code mort : elle ferait croire que le critère
    # existe alors qu'il n'entre dans aucun budget.
    utilisees = {nom for budget in matches.CRITERES.values() for nom in budget}
    assert set(matches.MESURES) <= utilisees, f"mesure orpheline : {set(matches.MESURES) - utilisees}"


def test_chaque_critere_retenu_a_sa_mesure():
    retenus = {nom for liste in matches.CRITERES_RETENUS.values() for nom in liste}
    assert retenus <= set(matches.MESURES)


def test_chaque_budget_totalise_cent():
    for nom, budget in matches.CRITERES.items():
        assert sum(budget.values()) == 100, f"{nom} totalise {sum(budget.values())}, pas 100"


def test_chaque_type_a_ses_criteres_retenus():
    assert set(matches.CRITERES) == set(matches.CRITERES_RETENUS)


def test_une_seule_raison_par_critere_et_elle_est_lisible():
    # Les raisons sont des phrases destinées à l'étudiant. Une raison vide
    # laisserait un critère sans explication à l'écran.
    resultat = evaluer(
        programme("Master Cryptography", country="Germany", language="English"), PROFIL
    )
    assert len(resultat["reasons"]) == 4
    assert all(isinstance(r, str) and r for r in resultat["reasons"])

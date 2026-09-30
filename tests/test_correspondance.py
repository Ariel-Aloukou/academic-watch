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
import re
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


# 5 bis. Les autres façons de dire « ouvert aux étudiants étrangers »
#
# Exiger le mot « international » écartait des bourses entièrement ouvertes.
# C'est le défaut inverse de celui corrigé plus haut : là, « international
# students » était lu comme « national student » ; ici, une page qui écrit
# « schools overseas » n'était pas lue du tout. La page MEXT est le cas mesuré.
#
# Chaque forme de la liste est vérifiée par une phrase réelle. C'est ce qui
# interdit qu'une entrée ajoutée à la liste ne soit jamais exercée : une faute
# de frappe y passerait sinon sans qu'aucun test ne le voie.


FORMULES_OUVERTURE = {
    "international": "Open to international students",
    "overseas": "based on their student-exchange agreements with schools overseas",
    "foreign students": "open to foreign students holding a valid residence permit",
}


def test_chaque_formule_de_liste_a_sa_phrase_reelle():
    # Les deux ensembles doivent être le même : ni mot inutilisé, ni phrase
    # testée qui n'est pas dans la liste.
    assert set(FORMULES_OUVERTURE) == set(matches.OUVERTURE_INTERNATIONALE)


@pytest.mark.parametrize("formule", sorted(FORMULES_OUVERTURE))
def test_chaque_formule_d_ouverture_vaut_les_points(formule):
    resultat = evaluer(
        bourse(
            diplome="Master's",
            eligibilite=[FORMULES_OUVERTURE[formule]],
            financement="Full tuition",
        ),
        PROFIL,
    )
    assert resultat["matched"], f"{formule} n'ouvre pas la bourse : {resultat['reasons']}"
    assert "ouverte aux étudiants internationaux" in " ".join(resultat["reasons"])


def test_la_phrase_mext_ouvre_la_bourse():
    # Non-régression, avec la phrase recopiée de la page. Le critère `niveau`
    # passe par « master's program » et le pays est préféré, donc la bourse est
    # retenue pour la bonne raison et non par un hasard de score.
    resultat = evaluer(
        bourse(
            diplome="Master's",
            eligibilite=[
                "You must be under 35 years of age and be eligible for admission "
                "to a master's program or a doctoral program (first or second "
                "stage) at a Japanese graduate school.",
                FORMULES_OUVERTURE["overseas"],
            ],
            financement="Full tuition",
            country="Japan",
        ),
        PROFIL,
    )
    assert resultat["matched"]
    assert "ouverte aux étudiants internationaux" in " ".join(resultat["reasons"])


def test_une_restriction_nationale_l_emporte_sur_overseas():
    # L'ordre des deux listes décide du résultat. « overseas » décrit un
    # parcours, « citizen » réserve la bourse : la restriction doit gagner.
    resultat = evaluer(
        bourse(
            diplome="Master's",
            eligibilite=["Open to citizens of the partner country who studied overseas"],
            financement="Full tuition",
        ),
        PROFIL,
    )
    assert not resultat["matched"]
    assert "réservée à une population nationale" in " ".join(resultat["reasons"])


def test_une_bourse_sans_ouverture_publiee_reste_ecartee():
    # Le contre-test : élargir la liste ne doit pas ouvrir toutes les bourses.
    # C'est ce qui protège le jour où quelqu'un y ajouterait un mot trop large.
    resultat = evaluer(
        bourse(diplome="Master's", eligibilite=["Open to candidates of the university"]),
        PROFIL,
    )
    assert not resultat["matched"]
    assert "non précisée" in " ".join(resultat["reasons"])


def test_un_financement_complet_prend_plus_qu_un_partiel():
    complet = mesure(bourse(financement="Full tuition"), "financement")
    partiel = mesure(bourse(financement="Tuition reduction"), "financement")
    assert complet["points"] == 20
    assert partiel["points"] == 10


def test_une_aide_sans_frais_de_scolarite_prend_zero():
    resultat = mesure(bourse(financement="Monthly stipend"), "financement")
    assert resultat["points"] == 0
    assert "aucune prise en charge" in resultat["raison"]


# 5 ter. Ce que « graduate » désigne : un niveau, ou des personnes
#
# `NIVEAUX_LARGES` contenait « graduate », trouvé seul. Mesuré le 29 septembre
# 2026, cela valait 40 points à cinq phrases sur sept de la page MEXT, dont
# aucune n'offrait de Master : « a graduate of a college », « university or
# college graduates who have practical work experience », « includes prospective
# graduates ». Une bourse de sortants de lycée arrivait en tête de bulletin à
# 90/100.
#
# Les 16 phrases ci-dessous sont les occurrences réelles, entières, pas des
# exemples inventés : 9 du corpus (7 titres KAIST, 1 éligibilité KAIST,
# 1 description TUM) et 7 de phrases relevées dans la V0.12. Chacune est
# déclarée avec le sens qu'elle a, et la propriété est vérifiée deux fois : une
# fois phrase par phrase, une fois sur la liste entière.


# (sens, texte) — « niveau » ouvre, « personnes » n'ouvre pas, « ni l'un ni
# l'autre » ne contient pas le mot et doit rester indifférent.
PHRASES_GRADUATE = [
    ("niveau", "Graduate School of Medical Science and Engineering"),
    ("niveau", "Graduate School of Information Security"),
    ("niveau", "The Kim Jaechul Graduate School of AI"),
    ("niveau", "Graduate School of Data Science"),
    ("niveau", "Cho Chun Shik Graduate School of Mobility"),
    ("niveau", "Graduate School of Culture Technology"),
    ("niveau", "Graduate School of Science and Technology Policy"),
    ("niveau", "Open to international applicants for KAIST graduate programs"),
    ("personnes", "the program is conducted in Singapore and serves to provide graduates with an in-depth knowledge"),
    ("personnes", "high school graduates"),
    ("personnes", "college graduates who have practical work experience"),
    ("personnes", "university graduates with 5 years of teaching experience"),
    ("personnes", "graduates of a high school"),
    ("niveau", "postgraduate programs in engineering"),
    ("niveau", "postgraduate degree"),
    ("ni l'un ni l'autre", "undergraduate students"),
]


@pytest.mark.parametrize("sens, texte", PHRASES_GRADUATE, ids=[t[1][:44] for t in PHRASES_GRADUATE])
def test_chaque_phrase_du_corpus_est_classee_du_bon_cote(sens, texte):
    resultat = mesure(bourse(diplome=None, eligibilite=[texte]), "niveau")
    if sens == "ni l'un ni l'autre":
        # « undergraduate » ne contient pas « graduate » : la règle n'a rien à
        # dire, et le dire est la moitié du travail.
        assert resultat["points"] == 0
    else:
        assert (resultat["points"] == 40) == (sens == "niveau"), (sens, texte, resultat)


def test_chaque_phrase_a_son_sens_declare():
    # La liste et sa déclaration ne peuvent pas diverger en silence : une phrase
    # ajoutée sans sens donnerait un test qui passe pour la mauvaise raison, et
    # c'est exactement ce que le test précédent ne peut pas voir.
    #
    # « ni l'un ni l'autre » ne veut pas dire « sans la lettre » : « undergraduate
    # » contient bien « graduat ». Il veut dire « sans le mot », donc la recherche
    # se fait par mot entier. C'est la distinction que `contient_mot` existe pour
    # garder, et elle est vérifiée ici plutôt que supposée.
    for sens, texte in PHRASES_GRADUATE:
        assert sens in {"niveau", "personnes", "ni l'un ni l'autre"}, (sens, texte)
        assert texte.strip() == texte and texte, texte
        if sens == "ni l'un ni l'autre":
            assert re.search(r"\b(?:graduate|postgraduates?)\b", texte, re.IGNORECASE) is None, texte
            assert "graduat" in texte.lower(), (texte, "ne contient meme pas la lettre")
        else:
            # `\bgraduates?\b` ne verrait pas « postgraduate » : c'est le faux
            # negatif que la V0.13 corrige, donc la verification porte sur les
            # deux mots de `NIVEAUX_LARGES`, au nombre compris.
            alternatives = "|".join(matches.NIVEAUX_LARGES)
            motif = r"\b(?:" + alternatives + r")s?\b"
            assert re.search(motif, texte, re.IGNORECASE) is not None, (
                texte,
                "ne contient aucun des mots de NIVEAUX_LARGES",
            )


def test_le_niveau_ne_vient_pas_du_mot_mais_de_ce_qui_le_suit():
    # Les deux phrases ne contiennent pas le meme nombre d'occurrences du mot,
    # ni les memes formes. Elles ne different que par le mot d'apres, et c'est
    # la seule distinction que la regle utilise.
    college = mesure(
        bourse(diplome=None, eligibilite=["You must be a graduate of a college"]), "niveau"
    )
    ecole = mesure(
        bourse(diplome=None, eligibilite=["Admission to a Japanese graduate school"]), "niveau"
    )
    # Les deux phrases contiennent le mot, une fois chacune, et à la même
    # place. Elles ne diffèrent que par le mot d'après, et c'est la seule
    # distinction que la règle utilise.
    college = mesure(
        bourse(diplome=None, eligibilite=["You must be a graduate of a college"]), "niveau"
    )
    ecole = mesure(
        bourse(diplome=None, eligibilite=["Admission to a Japanese graduate school"]), "niveau"
    )
    assert college["points"] == 0
    assert ecole["points"] == 40

def test_un_niveau_sans_mot_qui_le_suit_n_ouvre_rien():
    # « includes prospective graduates » se termine la. Le mot y est, le niveau
    # n'y est pas, et il n'y a rien derriere quoi le chercher.
    resultat = mesure(
        bourse(diplome=None, eligibilite=["completed 12 years of schooling (includes prospective graduates)"]),
        "niveau",
    )
    assert resultat["points"] == 0


def test_undergraduate_ne_compte_pas_pour_un_niveau_large():
    # Le piege le plus evident, et le plus facile a reintroduire : « undergraduate »
    # contient « graduate ». Une recherche par sous-chaine le ferait passer pour
    # un niveau de Master, donc une bourse de premier cycle deviendrait une
    # bourse de Master.
    resultat = mesure(bourse(diplome=None, eligibilite=["undergraduate course"]), "niveau")
    assert resultat["points"] == 0


# Les mots de liaison qui font faux : ceux que la page écrit après « graduate »
# quand elle parle de personnes. Les inscrire dans la liste d'inclusion
# rétablirait d'un coup les cinq faux positifs, et c'est la faute la plus
# probable de quelqu'un qui trouve un résultat qui ne lui convient pas.
MOTS_DE_LIAISON_MEXT = ("of", "with", "who")


@pytest.mark.parametrize("mot", MOTS_DE_LIAISON_MEXT)
def test_un_mot_de_liaison_ne_peut_pas_entrer_dans_la_liste_des_niveaux(mot):
    assert mot not in matches.MOTS_DE_NIVEAU
    resultat = mesure(bourse(diplome=None, eligibilite=[f"a graduate {mot} a college"]), "niveau")
    assert resultat["points"] == 0, mot


def test_la_liste_des_niveaux_est_ce_qui_decide_et_non_les_niveaux():
    # Les deux listes ne sont pas interchangeables. `NIVEAUX_LARGES` dit quels
    # mots ouvrent une porte, `MOTS_DE_NIVEAU` dit ce qui doit les suivre. Les
    # confondre, ou vider l'une des deux, ramene le defaut qu'elles corrigent.
    assert matches.NIVEAUX_LARGES == ("graduate", "postgraduate")
    assert matches.MOTS_DE_NIVEAU
    assert not set(matches.NIVEAUX_LARGES) & set(matches.MOTS_DE_NIVEAU)


def test_la_recherche_ne_compte_pas_sur_la_maniere_du_caller_de_l_ecrire():
    # Les sept titres de KAIST commencent par une majuscule, et c'est le seul
    # endroit du corpus où « Graduate » n'est pas en minuscule. Appeler la
    # fonction directement, sans passer par `niveau_atteignable` qui met déjà le
    # texte en minuscules, vérifie qu'elle normalise elle-même. Sans ce test, la
    # normalisation pourrait disparaître de la fonction sans qu'on le voie :
    # `niveau_atteignable` la ferait encore, et la suite resterait verte.
    assert matches.niveau_large_mentionne("Graduate School of AI") is True
    assert matches.niveau_large_mentionne("GRADUATE SCHOOL OF AI") is True
    assert matches.niveau_large_mentionne("you must be a Graduate of a college") is False


def test_la_fonction_renvoie_un_booléen_et_pas_une_correspondance():
    # Une fonction de recherche qui renvoyait un objet truthy passerait les
    # tests d'assertion sans dire ce qu'elle répond. Elle est appelée dans une
    # condition, donc un résultat trompeur se propagerait jusqu'à la retenue.
    assert matches.niveau_large_mentionne("graduate programs") is True
    assert matches.niveau_large_mentionne("graduates of a college") is False


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

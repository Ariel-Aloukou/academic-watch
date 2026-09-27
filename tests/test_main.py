"""Tests de l'affichage : src/main.py (docs/VERSIONS.md V0.5).

La V0.5 change ce que le programme montre, et c'est la seule chose qu'elle
change. Le cas le plus important est donc le plus courant : un jour sans
nouveauté ne doit pas réimprimer les 69 fiches, il doit dire qu'il n'y a rien
et s'arrêter là.

Ces tests relisent `display_opportunities()` et `resume()`. Ils ne relancent
pas le programme entier, donc ils ne touchent pas au réseau et n'écrivent rien :
`main()` est la seule fonction qui collecte, et elle est vérifiée en lançant le
programme.
"""

import pytest

import main

# Une évaluation, telle que `evaluer` la rend : un dictionnaire, pas un objet.
# Le minimum utile pour l'affichage, le reste n'est pas imprimé.
RESULTAT = {
    "score": 70,
    "score_max": 100,
    "type": "programs",
    "matched": True,
    "reasons": ["domaine direct"],
}


class Opportunite:
    """Le strict minimum des champs que l'affichage lit.

    Une vraie `Opportunity` ferait l'affaire, mais elle a treize champs, dont
    six que l'affichage ignore. Une classe à trois champs dit plus clairement ce
    qui est testé, et un champ oublié devient une erreur ici plutôt qu'un
    `None` affiché par accident.
    """

    def __init__(self, titre="Master A", diplome="Master of Science"):
        self.title = titre
        self.degree = diplome
        self.university = "Universite A"
        self.country = "Germany"
        self.url = "https://exemple/a"
        self.field = ""
        self.funding_type = None


def signalee(opportunite, etiquette):
    return (opportunite, RESULTAT, etiquette)


# Le cas de tous les jours.


def test_rien_a_signaler_ne_le_dit_une_seule_fois(capsys):
    main.display_opportunities([], 9)
    sortie = capsys.readouterr().out
    assert "Rien de nouveau" in sortie
    assert "9" in sortie
    # Une seule fois : un résumé répété n'est pas un résumé.
    assert sortie.count("Rien de nouveau") == 1


def test_le_compte_des_retenues_est_affiche(capsys):
    main.resume([(Opportunite(), RESULTAT), (Opportunite("Master B"), RESULTAT)])
    sortie = capsys.readouterr().out
    assert "2 opportunités trouvées, 2 correspondent au profil" in sortie


# Les deux étiquettes, et le compte qui les annonce.


def test_les_deux_etiquettes_sont_constantes():
    assert main.NOUVELLE == "nouvelle"
    assert main.MISE_A_JOUR == "mise à jour"


def test_le_singulier_et_le_pluriel_sont_distincts(capsys):
    main.display_opportunities([signalee(Opportunite(), main.NOUVELLE)], 1)
    sortie = capsys.readouterr().out
    assert "1 à signaler : 1 nouvelle" in sortie
    assert "nouvelles" not in sortie


def test_deux_mises_a_jour_sont_au_pluriel(capsys):
    main.display_opportunities(
        [
            signalee(Opportunite("Master A"), main.MISE_A_JOUR),
            signalee(Opportunite("Master B"), main.MISE_A_JOUR),
        ],
        2,
    )
    assert "2 à signaler : 2 mises à jour" in capsys.readouterr().out


def test_nouvelles_puis_mises_a_jour_sont_comptees_separement(capsys):
    main.display_opportunities(
        [
            signalee(Opportunite("Master A"), main.NOUVELLE),
            signalee(Opportunite("Master B"), main.MISE_A_JOUR),
            signalee(Opportunite("Master C"), main.MISE_A_JOUR),
        ],
        3,
    )
    assert "3 à signaler : 1 nouvelle, 2 mises à jour" in capsys.readouterr().out


# Ce que l'affichage ne doit pas inventer.


def test_un_champ_non_publie_n_est_pas_affiche(capsys):
    # domaines vide et financement absent : afficher « None » ferait croire à
    # une valeur (docs/README.md §7).
    main.display_opportunities([signalee(Opportunite(), main.NOUVELLE)], 1)
    sortie = capsys.readouterr().out
    assert "None" not in sortie
    assert "Domaines" not in sortie
    assert "Financement" not in sortie


def test_les_raisons_sont_affichees(capsys):
    main.display_opportunities([signalee(Opportunite(), main.NOUVELLE)], 1)
    assert "- domaine direct" in capsys.readouterr().out


def test_une_opportunite_par_bien_une_seule_ligne_de_titre(capsys):
    main.display_opportunities([signalee(Opportunite(), main.NOUVELLE)], 1)
    sortie = capsys.readouterr().out
    assert sortie.count("[nouvelle]") == 1
    assert "1. [nouvelle] Master A" in sortie


def test_le_titre_du_cahier_des_charges_est_remplace(capsys):
    # Le cahier annonce « Nouvelles opportunités ». Le titre retenu est
    # « À signaler », parce qu'une mise à jour n'est pas une nouvelle
    # opportunité. Le test verrouille l'écart pour qu'il reste choisi.
    main.display_opportunities([signalee(Opportunite(), main.MISE_A_JOUR)], 1)
    assert "=== À signaler ===" in capsys.readouterr().out


if __name__ == "__main__":
    pytest.main([__file__])

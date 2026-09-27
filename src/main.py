"""Point d'entrée du programme Academic Watch.

Orchestration (docs/VERSIONS.md) :

    V0.1  chargement de la configuration   -> display_profile()
    V0.2  collecte des sources             -> collect_opportunities()
    V0.3  correspondance avec le profil    -> matches.py   (evaluer)
    V0.4  sauvegarde                       -> storage.py   (sauvegarder)
    V0.5  détection des nouveautés         -> storage.py, main.py
    V0.6  notification                    -> notifier.py   (publier)

Le programme doit rester simple : main.py ne fait qu'appeler les autres
modules dans le bon ordre (docs/README.md §6).
"""

import json
from pathlib import Path

from matches import evaluer
from notifier import MISE_A_JOUR, NOUVELLE, publier, rendre
from scraper import collect_opportunities
from storage import (
    charger_vus,
    conserver_vus,
    identite,
    modifiees_depuis,
    nouvelles_depuis,
    sauvegarder,
)

# Chemin calculé depuis ce fichier pour fonctionner quel que soit le dossier
# depuis lequel le programme est lancé (localement ou via GitHub Actions).
PROFILE_PATH = Path(__file__).resolve().parent.parent / "config" / "profile.json"


def load_profile():
    """Charge le profil de recherche depuis config/profile.json."""
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def display_values(values):
    """Affiche une section du profil, qu'elle soit un objet ou une liste."""
    if isinstance(values, dict):
        for key, value in values.items():
            print(f"  {key}: {value}")
    else:
        for value in values:
            print(f"  - {value}")


def display_profile(profile):
    """Affiche le profil de recherche chargé.

    C'est le résultat attendu de la V0.1 : le programme se lance et affiche les
    informations de configuration chargées.
    """
    print("=== Profil de recherche ===")
    for section, values in profile.items():
        print(section)
        display_values(values)


def main():
    """Enchaîne les étapes dans l'ordre défini par docs/VERSIONS.md."""
    profile = load_profile()
    display_profile(profile)

    # La correspondance est faite ici, et non dans le scraper : comparer au
    # profil n'est pas extraire une page. Les deux étapes restent séparées.
    paires = []
    for opportunity in collect_opportunities():
        resultat = evaluer(opportunity, profile)
        # L'évaluation est recopiée sur l'opportunité, comme le prévoyait
        # models.py, pour que la sauvegarde n'ait pas à la refaire.
        opportunity.score = resultat["score"]
        opportunity.score_max = resultat["score_max"]
        opportunity.matched = resultat["matched"]
        opportunity.matched_criteria = resultat["reasons"]
        paires.append((opportunity, resultat))

    # V0.4. L'historique enregistre tout ce qui a été collecté, y compris ce
    # qui ne correspond pas au profil : une offre écartée aujourd'hui peut
    # intéresser le jour où le profil change, et l'écarter définitivement
    # serait une information perdue.
    opportunities = [opportunity for opportunity, _ in paires]
    bilan = sauvegarder(opportunities)

    # V0.5. Ce qui est signalé est choisi parmi les opportunités retenues. Une
    # opportunité qui ne correspond pas au profil n'est pas une nouveauté : une
    # veille est une sélection, pas un catalogue.
    #
    # Les deux listes sont disjointes, et c'est `modifiees_depuis` qui le
    # garantit : ce qui n'a jamais été montré est nouveau, jamais une mise à
    # jour. Les nouvelles passent d'abord, parce que c'est ce que l'étudiant
    # n'attendait pas.
    vues = charger_vus()
    resultats = {identite(opportunity): resultat for opportunity, resultat in paires}
    retenues = [opportunity for opportunity in opportunities if opportunity.matched]
    a_signaler = [
        (opportunity, resultats[identite(opportunity)], NOUVELLE)
        for opportunity in nouvelles_depuis(retenues, vues)
    ]
    a_signaler += [
        (opportunity, resultats[identite(opportunity)], MISE_A_JOUR)
        for opportunity in modifiees_depuis(retenues, vues, bilan.modifiees)
    ]

    # V0.6. Le bulletin est rendu une fois et publié par tous les moyens
    # disponibles : la console toujours, l'email si les six variables
    # d'environnement sont là.
    #
    # L'ordre est délibéré. Publier avant `conserver_vus` signifie qu'un run qui
    # s'arrête entre les deux enverra le même message au run suivant, donc un
    # doublon. L'autre ordre perdrait l'opportunité sans qu'aucune trace
    # reste : elle serait déjà marquée comme vue, et plus personne ne
    # l'annoncerait. Le doublon se voit et se corrige, la perte ne se voit pas.
    publier(rendre(a_signaler, len(retenues), len(paires)))

    # `vues` n'est mémorisé qu'après l'affichage, pour qu'une opportunité
    # comptée comme montrée l'ait été. C'est ce qui évite de la re-signaler.
    #
    # Mémoriser toutes les retenues et mémoriser celles qui viennent d'être
    # affichées donnent le même résultat : une retenue qui n'est ni nouvelle ni
    # modifiée a déjà été montrée, donc elle est déjà dans le fichier.
    conservees = conserver_vus(retenues)

    print()
    print("=== Sauvegarde ===")
    print(f"{len(opportunities)} opportunités enregistrées dans data/opportunities.json")
    print(f"{len(bilan.nouvelles)} nouvelles depuis la dernière exécution")
    print(f"{len(conservees)} opportunités déjà montrées, dans data/seen.json")


if __name__ == "__main__":
    main()

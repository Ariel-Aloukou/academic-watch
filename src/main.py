"""Point d'entrée du programme Academic Watch.

Orchestration (docs/VERSIONS.md) :

    V0.1  chargement de la configuration   -> display_profile()
    V0.2  collecte des sources             -> collect_opportunities()
    V0.3  correspondance avec le profil    -> matches.py   (evaluer)
    V0.4  sauvegarde                       -> storage.py   (sauvegarder)
    V0.5  détection des nouveautés         -> storage.py, main.py
    V0.6  notification                    -> notifier.py  (pas encore fait)

Le programme doit rester simple : main.py ne fait qu'appeler les autres
modules dans le bon ordre (docs/README.md §6).
"""

import json
from pathlib import Path

from matches import evaluer
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


# Les deux étiquettes de la V0.5. Ce sont des constantes parce que l'affichage
# les compte et que le programme les attribue : une faute de frappe dans l'une
# des deux n'afficherait rien, sans erreur.
NOUVELLE = "nouvelle"
MISE_A_JOUR = "mise à jour"


def resume(paires):
    """Le compte de ce qui a été collecté, sans le détail.

    C'est le résultat de la V0.2 et de la V0.3, réduit à ce qui survit à la
    V0.5. Le détail des 69 fiches n'est plus imprimé : une veille quotidienne
    qui réaffiche 69 fiches déjà lues n'est plus lisible, et c'est exactement ce
    que la V0.5 vient corriger. Le compte dit ce qui a été vu et coûte une
    ligne. Les 69 fiches restent dans `data/opportunities.json`.

    Renvoie le nombre d'opportunités retenues, dont l'affichage a besoin pour
    sa ligne « rien de nouveau ».
    """
    retenues = sum(1 for _, resultat in paires if resultat["matched"])
    print()
    print("=== Opportunités trouvées ===")
    print(f"{len(paires)} opportunités trouvées, {retenues} correspondent au profil")
    print()
    return retenues


def display_opportunities(a_signaler, retenues):
    """N'affiche que ce qui n'a pas encore été montré.

    C'est le résultat attendu de la V0.5 : ne signaler que les opportunités
    nouvelles. `a_signaler` associe à chaque opportunité son évaluation et
    l'étiquette qui dit pourquoi elle est là, `NOUVELLE` ou `MISE_A_JOUR`.

    Le cahier des charges annonce un titre, « Nouvelles opportunités », et deux
    éléments. Le titre retenu ici est « À signaler », parce qu'une mise à jour
    n'est pas une nouvelle opportunité et qu'annoncer celle-là sous ce titre
    serait faux. Le reste de l'exemple est respecté : seuls les éléments non
    encore montrés sont listés, et rien d'autre.
    """
    print("=== À signaler ===")
    if not a_signaler:
        print(
            f"Rien de nouveau : les {retenues} opportunités qui correspondent au "
            "profil ont déjà été montrées."
        )
        print()
        return

    nouvelles = sum(1 for _, _, etiquette in a_signaler if etiquette == NOUVELLE)
    mises_a_jour = len(a_signaler) - nouvelles
    details = []
    if nouvelles:
        details.append(f"{nouvelles} nouvelle" + ("s" if nouvelles > 1 else ""))
    if mises_a_jour:
        details.append(
            f"{mises_a_jour} mise" + ("s" if mises_a_jour > 1 else "") + " à jour"
        )
    print(f"{len(a_signaler)} à signaler : {', '.join(details)}")
    print()

    for number, (opportunity, resultat, etiquette) in enumerate(a_signaler, start=1):
        print(f"{number}. [{etiquette}] {opportunity.title}")
        print(f"   Université : {opportunity.university}")
        print(f"   Pays        : {opportunity.country}")
        # Une bourse n'annonce pas de diplôme, et certaines pages de programmes
        # n'affichent pas leurs domaines de recherche. Afficher « None » ferait
        # croire à une valeur : la ligne n'est imprimée que si la donnée a été
        # trouvée.
        if opportunity.degree:
            print(f"   Diplôme     : {opportunity.degree}")
        if opportunity.field:
            print(f"   Domaines    : {opportunity.field}")
        if opportunity.funding_type:
            print(f"   Financement : {opportunity.funding_type}")
        # Le score n'a de sens que rapporté au maximum du type : 85 sur 100
        # pour un programme et 100 sur 100 pour une bourse ne se comparent pas.
        print(
            f"   Score       : {resultat['score']} / {resultat['score_max']}"
            f" ({resultat['type']})"
        )
        for raison in resultat["reasons"]:
            print(f"     - {raison}")
        print(f"   Lien        : {opportunity.url}")
        print()


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

    nb_retenues = resume(paires)

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

    display_opportunities(a_signaler, nb_retenues)

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

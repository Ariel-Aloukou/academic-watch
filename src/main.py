"""Point d'entrée du programme Academic Watch.

Orchestration (docs/VERSIONS.md) :

    V0.1  chargement de la configuration   -> display_profile()
    V0.2  collecte des sources             -> collect_opportunities()
    V0.3  correspondance avec le profil    -> matches.py   (evaluer)
    V0.4  sauvegarde                       -> storage.py   (sauvegarder)
    V0.5  détection des nouveautés         -> storage.py   (pas encore fait)
    V0.6  notification                    -> notifier.py  (pas encore fait)

Le programme doit rester simple : main.py ne fait qu'appeler les autres
modules dans le bon ordre (docs/README.md §6).
"""

import json
from pathlib import Path

from matches import evaluer
from scraper import collect_opportunities
from storage import conserver_vus, sauvegarder

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


def display_opportunities(paires):
    """Affiche les opportunités trouvées par le scraper.

    C'est le résultat attendu de la V0.2, complété par la correspondance de la
    V0.3. Les informations absentes ne sont pas affichées plutôt que d'être
    inventées (docs/README.md §7).

    `paires` associe chaque opportunité à son évaluation, pour que le score
    soit lu au même endroit que les données qui l'ont produit.
    """
    retenues = sum(1 for _, resultat in paires if resultat["matched"])
    print()
    print("=== Opportunités trouvées ===")
    print(f"{len(paires)} opportunités trouvées, {retenues} correspondent au profil")
    print()

    for number, (opportunity, resultat) in enumerate(paires, start=1):
        marque = "OUI" if resultat["matched"] else "non"
        print(f"{number}. {opportunity.title}   [{marque}]")
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

    display_opportunities(paires)

    # V0.4. L'historique enregistre tout ce qui a été collecté, y compris ce
    # qui ne correspond pas au profil : une offre écartée aujourd'hui peut
    # intéresser le jour où le profil change, et l'écarter définitivement
    # serait une information perdue.
    opportunities = [opportunity for opportunity, _ in paires]
    nouvelles = sauvegarder(opportunities)
    retenues = [o for o, resultat in paires if resultat["matched"]]

    # `vues` n'est memorise qu'apres l'affichage, pour qu'une opportunite
    # comptee comme montree l'ait ete. C'est ce qui evite de la re-signaler.
    conservees = conserver_vus(retenues)

    print()
    print("=== Sauvegarde ===")
    print(f"{len(opportunities)} opportunités enregistrées dans data/opportunities.json")
    print(f"{len(nouvelles)} nouvelles depuis la dernière exécution")
    print(f"{len(conservees)} opportunités déjà montées, dans data/seen.json")


if __name__ == "__main__":
    main()

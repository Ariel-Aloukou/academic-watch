"""Point d'entrée du programme Academic Watch.

Orchestration (docs/VERSIONS.md) :

    V0.1  chargement de la configuration   -> display_profile()
    V0.2  collecte des sources             -> collect_opportunities()
    V0.3  correspondance avec le profil    -> matches.py   (evaluer)
    V0.4  sauvegarde                       -> storage.py   (pas encore fait)
    V0.5  détection des nouveautés         -> storage.py   (pas encore fait)
    V0.6  notification                    -> notifier.py  (pas encore fait)

Le programme doit rester simple : main.py ne fait qu'appeler les autres
modules dans le bon ordre (docs/README.md §6).
"""

import json
from pathlib import Path

from scraper import collect_opportunities

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


def display_opportunities(opportunities):
    """Affiche les opportunités trouvées par le scraper.

    C'est le résultat attendu de la V0.2. Les informations absentes ne sont pas
    affichées plutôt que d'être inventées (docs/README.md §7).
    """
    print()
    print("=== Opportunités trouvées ===")
    print(f"{len(opportunities)} opportunités trouvées")
    print()

    for number, opportunity in enumerate(opportunities, start=1):
        print(f"{number}. {opportunity.title}")
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
        print(f"   Lien        : {opportunity.url}")
        print()


def main():
    """Enchaîne les étapes dans l'ordre défini par docs/VERSIONS.md."""
    display_profile(load_profile())
    display_opportunities(collect_opportunities())


if __name__ == "__main__":
    main()

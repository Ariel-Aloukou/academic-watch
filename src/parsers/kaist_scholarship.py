"""Parseur de la page Scholarship de KAIST.

Pourquoi un parseur dédié alors que le projet utilise des sélecteurs CSS :

la page ne contient pas de blocs répétés. Chaque bourse est écrite ainsi :

    <p>KAIST Global Presidential Scholarship (KGPS)</p>
    <ul>
      <li><span>Departments Accepting Applications:</span><span>...</span></li>
      <li><span>Admission Periods:</span><span>...</span></li>
      <li><span>Eligibility Requirements:</span><span>...</span></li>
      <li><span>Benefits:</span><span>...</span></li>
    </ul>

Le nom et les détails sont deux éléments frères. Aucun sélecteur CSS ne peut
les apparier, et écrire un sélecteur qui fonctionne quand même serait une
approximation fragile. La règle de docs/SOURCES.md §7 s'applique : si la
structure ne s'exprime pas en sélecteurs, on écrit un parseur.

Ce fichier ne connaît que cette page. Il ne modifie pas scraper.py : c'est
scraper.py qui décide, à partir de la clé "parser" de config/selectors.json,
qu'il faut l'appeler.

Ce qui est extrait, et ce qui ne l'est pas :

* `funding_type` reçoit le texte Benefits tel qu'il est écrit. Un montant
  comme « 1,000,000 KRW » y figure donc en toutes lettres.
* `funding_amount` reste None. Extraire un nombre d'une phrase demande une
  recherche de motif dans du texte libre, donc du code fragile. Ce sera
  discuté séparément, pas décidé ici.
* `deadline` reste None. « Admission Periods: Spring/Fall Early/Fall
  Regular » décrit des cycles, pas une date. Ecrire une date ici serait
  inventer (docs/README.md §7).
"""

from bs4 import BeautifulSoup
from datetime import datetime, timezone

from models import Opportunity


def lire_champs(details):
    """Transforme les <li> d'une bourse en un dictionnaire label -> valeur.

    Chaque <li> contient exactement deux <span> : le libellé et la valeur.
    Un <li> qui n'en a pas deux est ignoré plutôt qu'à moitié lu.
    """
    champs = {}
    for item in details.find_all("li", recursive=False):
        pieces = item.find_all("span", recursive=False)
        if len(pieces) < 2:
            continue
        label = pieces[0].get_text(" ", strip=True).rstrip(":")
        champs[label] = pieces[1].get_text(" ", strip=True)
    return champs


def lire_nom(details):
    """Renvoie le nom de la bourse, ou None.

    Le nom est le paragraphe qui précède immédiatement la liste. Sur la
    première bourse, un paragraphe vide s'intercale et le nom est le titre de
    la page : le cas est traité par l'appelant.
    """
    precedent = details.find_previous_sibling()
    if precedent is None or precedent.name != "p":
        return None
    return precedent.get_text(" ", strip=True) or None


def construire(nom, champs, source):
    """Transforme une bourse en objet Opportunity."""
    return Opportunity(
        title=nom,
        # Une bourse n'est pas un programme : elle n'a ni domaine ni diplôme.
        degree=None,
        field=None,
        # La page ne publie pas de lien par bourse, seulement une page
        # commune. Le lien est donc celui de la source, ce qui est exact.
        url=source["url"],
        university=source["university"],
        country=source["country"],
        source=source["name"],
        # Le texte Benefits est conservé mot pour mot, montant compris.
        funding_type=champs.get("Benefits"),
        funding_amount=None,
        # L'éligibilité est une information que le modèle attend déjà, et que
        # cette page publie explicitement.
        eligibility=[champs["Eligibility Requirements"]] if "Eligibility Requirements" in champs else [],
        # Tout le reste est conservé dans la description : les départements
        # acceptés, les cycles d'admission et les remarques ne sont pas dans
        # un champ du modèle, et les perdre serait perdre de l'information.
        description=" | ".join(f"{label}: {valeur}" for label, valeur in champs.items()),
        collected_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def parse(html, source):
    """Renvoie la liste des bourses annoncées sur la page."""
    soup = BeautifulSoup(html, "html.parser")
    conteneur = soup.select_one(source["selectors"]["container"])
    if conteneur is None:
        return []

    opportunites = []
    for index, details in enumerate(conteneur.find_all("ul")):
        nom = lire_nom(details)
        if nom is None and index == 0:
            # La première bourse porte le nom de la page, écrit dans le titre
            # et non dans un paragraphe.
            titre = soup.find("h2")
            nom = titre.get_text(" ", strip=True) if titre else None
        if nom is None:
            # Aucune bourse après la première ne devrait avoir cette forme. Au
            # lieu de lui attribuer un nom au hasard, on l'ignore.
            continue
        opportunites.append(construire(nom, lire_champs(details), source))

    return opportunites

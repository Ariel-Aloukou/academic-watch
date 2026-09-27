"""Sauvegarde des opportunités entre deux exécutions (docs/VERSIONS.md V0.4).

Deux fichiers, deux questions différentes :

    data/opportunities.json   ce que le programme a vu, en tout, avec la date
                              de première apparition
    data/seen.json            ce qui a déjà été montré à l'utilisateur

Ils ne sont pas redondants, et c'est écrit ici pour qu'on ne les fusionne pas
par mégarde. Une opportunité est collectée même quand elle ne correspond pas au
profil : `opportunities` contient donc des éléments que `seen` ne contiendra
jamais. Inversement, changer son profil ne doit pas re-signaler les 69
opportunités déjà vues : `seen` le garantit, et `opportunities` seul ne le
ferait pas.

## Ce qui sert d'identité à une opportunité

C'est la seule vraie décision de ce module. Le choix est `source` + titre
normalisé + diplôme normalisé, et non l'URL, pour une raison d'asymétrie des
erreurs :

* la source et le titre sont publiés par les 69 opportunités des 4 sources
  actives, mesuré au chapitre 6.1 de docs/SOURCES.md. Aucun des deux ne
  manque ;
* le diplôme est publié par 2 sources sur 4, et par aucune des 20 fiches
  d'EACEA. C'est lui qui distingue les deux programmes de TUM nommés tous
  deux « Aerospace », mesuré à la V0.4 ;
* l'URL est la propriété du site, pas de l'opportunité. Les 20 URL d'EACEA
  pointent vers des sites de programmes tiers, et un site qui réorganise ses
  chemins changerait l'URL sans que l'opportunité change. Si l'identité était
  l'URL, tout semblerait nouveau à chaque réorganisation ;
* un titre reformulé rend une opportunité nouvelle une fois. C'est un
  inconfort, pas une inondation.

Pour une veille, l'erreur à éviter n'est pas de rater une nouveauté, c'est
d'en annoncer soixante. On choisit donc l'identité qui résiste au changement
qu'on ne contrôle pas.

L'URL reste enregistrée dans chaque fiche : c'est elle qui sert à vérifier, et
elle est affichée pour que la fusion puisse être contestée à l'œil.
"""

import json
import unicodedata
from dataclasses import asdict
from pathlib import Path
from typing import NamedTuple

# Chemins calculés depuis ce fichier, comme dans main.py, pour que le programme
# fonctionne quel que soit le dossier depuis lequel il est lancé.
DOSSIER = Path(__file__).resolve().parent.parent / "data"
OPPORTUNITES = DOSSIER / "opportunities.json"
VUS = DOSSIER / "seen.json"

# Les deux horodatages ne disent rien du contenu d'une fiche. Les exclure de la
# comparaison permet de réécrire le fichier seulement quand quelque chose a
# vraiment changé : voir a_change.
IGNORES = {"collected_at", "first_seen_at"}


class StockageInvalide(Exception):
    """Un fichier de données existe mais n'est pas lisible.

    Le programme s'arrête plutôt que de repartir d'un historique vide. Repartir
    de vide ne se verrait pas : les 69 opportunités de la veille passeraient
    pour nouvelles, et la veille annoncerait d'un coup tout ce qu'elle a
    toujours annoncé. Une erreur visible vaut mieux qu'une inondation fausse.
    """


# 1. L'identité


def normaliser_titre(titre):
    """Met un titre dans la forme servant à comparer deux exécutions.

    Minuscules, accents retirés, ponctuation réduite à des espaces, espaces
    regroupés. Un site qui corrige une faute d'accent ou ajoute un trait d'union
    ne doit pas faire apparaître une opportunité nouvelle.

    Ce n'est pas la même normalisation que celle de matches.py, qui ne remplace
    que les apostrophes typographiques pour comparer des phrases. Deux usages,
    deux règles : celle-ci égalise des titres, pas des textes.
    """
    if not titre:
        # Un champ absent devient un marqueur à part, pas une chaîne vide : dans
        # une identité, « on ne sait pas » et « la valeur est vide » doivent
        # rester distinguables. Le symbole est lisible et n'apparaît dans aucun
        # titre réel.
        return "?"
    sans_accent = unicodedata.normalize("NFD", titre)
    sans_accent = "".join(c for c in sans_accent if unicodedata.category(c) != "Mn")
    nettoye = "".join(c if c.isalnum() else " " for c in sans_accent.lower())
    return " ".join(nettoye.split())


def identite(opportunity):
    """L'identifiant stable d'une opportunité, lisible et sans hachage.

    Trois champs, pour trois raisons :

    * `source`, parce que deux sources peuvent légitimement nommer la même
      chose, et que c'est le registre qui les distingue ;
    * le titre normalisé, parce que c'est le champ le plus universellement
      publié, 69 fois sur 69 ;
    * le diplôme normalisé, **ajouté après une collision mesurée**. TUM publie
      deux programmes qui s'appellent tous deux « Aerospace », un Master of
      Science et un Bachelor of Science, avec deux URL différentes. Sans le
      diplôme, le Bachelor disparaissait de l'historique, écrasé par le Master.
      La mesure donne 69 identités distinctes sur 69 opportunités avec le
      diplôme, 68 sans.

    L'URL, elle, n'entre pas dans l'identité. Elle est la propriété du site et
    non de l'opportunité, et les 20 URL d'EACEA pointent vers des sites de
    programmes tiers. Une identité fondée sur l'URL ferait que tout semble
    nouveau dès qu'un site réorganise ses chemins. Elle reste enregistrée dans
    chaque fiche, pour que la fusion puisse être contestée à l'œil.

    Limite connue : KAIST publie trois niveaux pour un même programme, joints en
    une seule chaîne. Si l'ordre de cette liste change un jour, les 36
    identités KAIST changeront avec, et ces opportunités paraîtront nouvelles
    une fois. Deux collectes consécutives n'ont montré aucune variation de ce
    genre, et c'est mesuré, mais la page reste sous le contrôle de KAIST.

    Lisible et non haché volontairement : un fichier de données doit pouvoir
    être ouvert et compris, et deux fiches voisines doivent montrer pourquoi
    elles n'ont pas été fusionnées.
    """
    return (
        f"{opportunity.source}|{normaliser_titre(opportunity.title)}|{normaliser_titre(opportunity.degree)}"
    )


# 2. Lecture et écriture


def lire(chemin):
    """Lit un fichier de données, ou renvoie une liste vide s'il n'existe pas.

    Un fichier absent est normal : c'est la première exécution. Un fichier
    présent mais illisible ne l'est pas, et lève une erreur.
    """
    if not chemin.exists():
        return []
    try:
        contenu = json.loads(chemin.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erreur:
        raise StockageInvalide(
            f"{chemin.name} n'est pas du JSON valide ({erreur}). "
            "Le fichier n'a pas été touché : le corriger ou le supprimer, "
            "en sachant que le supprimer fera passer toutes les opportunités "
            "pour nouvelles."
        ) from erreur

    if not isinstance(contenu, list):
        raise StockageInvalide(f"{chemin.name} contient {type(contenu).__name__}, une liste était attendue.")
    return contenu


def ecrire(chemin, contenu):
    """Écrit un fichier de données sans jamais le laisser à moitié écrit.

    Le programme tourne sur un planning, donc il peut être interrompu. Écrire
    dans le fichier destination directement laisserait un JSON tronqué, et donc
    un historique perdu. On écrit à côté, puis on remplace : le remplacement est
    atomique sur les systèmes de fichiers usuels.
    """
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_name(chemin.name + ".tmp")
    temporaire.write_text(json.dumps(contenu, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporaire.replace(chemin)


# 3. Les opportunités


def fiche(opportunity):
    """L'enregistrement d'une opportunité, prêt à être écrit.

    `identite` est ajouté au modèle, qui ne le porte pas : l'identité sert à la
    sauvegarde, elle n'a pas été lue sur la page.
    """
    enregistrement = asdict(opportunity)
    enregistrement["identite"] = identite(opportunity)
    return enregistrement


def a_change(ancien, nouveau):
    """Ditex si une fiche déjà enregistrée a réellement changé.

    Les deux horodatages sont ignorés. `first_seen_at` ne change jamais, et
    `collected_at` change à chaque collecte par construction : le comparer
    ferait dire qu'une fiche a changé alors qu'elle est identique, et c'est
    précisément ce qu'on veut éviter.
    """
    return {k: v for k, v in ancien.items() if k not in IGNORES} != {
        k: v for k, v in nouveau.items() if k not in IGNORES
    }


class Bilan(NamedTuple):
    """Ce qu'une collecte a apporté de neuf, et ce qu'elle a modifié.

    Deux listes, et non une : une opportunité qui n'avait jamais été
    collectée et une opportunité dont la page a changé ne se signalent pas de
    la même façon. Les confondre ferait annoncer une mise à jour sur une
    opportunité que personne n'a jamais vue. `nouvelles_depuis` et
    `modifiees_depuis` en font deux listes séparées pour l'affichage.
    """

    nouvelles: list
    modifiees: list


def sauvegarder(opportunities):
    """Ajoute les opportunités collectées à l'historique, et le renvoie.

    L'historique s'accumule : il n'est jamais écrasé. Une opportunité déjà vue
    voit ses données mises à jour, mais garde la date de sa première
    apparition, qui est ce qui permet de dire ensuite « cela fait trois mois
    que cette offre est là ».

    Renvoie un `Bilan` : les identités qui n'étaient pas dans l'historique, et
    celles dont la fiche a changé. C'est V0.5 qui s'en sert, et le calcul était
    déjà fait ici : le lire ailleurs obligerait à relire le fichier et à
    dupliquer `a_change`, donc à avoir deux règles qui divergent en silence.
    """
    connues = {r["identite"]: r for r in lire(OPPORTUNITES)}
    nouvelles = []
    modifiees = []

    for opportunity in opportunities:
        cle = identite(opportunity)
        enregistrement = fiche(opportunity)
        ancien = connues.get(cle)

        if ancien is None:
            enregistrement["first_seen_at"] = opportunity.collected_at
            nouvelles.append(cle)
            connues[cle] = enregistrement
            continue

        # Déjà vue. La première apparition est conservée : c'est elle, et non la
        # date du jour, qui dit depuis quand l'opportunité existe.
        enregistrement["first_seen_at"] = ancien.get("first_seen_at") or opportunity.collected_at

        # Une fiche qui n'a changé que son horodatage n'est pas réécrite. Sans
        # cette comparaison, les 69 fiches seraient réécrites à chaque exécution
        # et le fichier changerait tous les jours alors que rien n'a bougé. On ne
        # pourrait plus distinguer « rien de neuf » d'« une information mise à
        # jour », et une veille quotidienne produirait un changement par jour
        # quoi qu'il arrive. Le coût est une information en moins : la date de
        # dernière collecte, qui ne sert à rien tant qu'aucun code ne cherche à
        # savoir si une offre a disparu de sa page.
        #
        # La même comparaison sert à la V0.5, qui doit signaler les fiches
        # modifiées. Elle n'est faite qu'une fois, ici : la refaire ailleurs
        # obligerait à relire le fichier, et deux règles qui divergent en
        # silence ne se verraient qu'à la première annonce fausse. Comme
        # `a_change` ignore les horodatages, une bourse qui publie une date ou
        # un montant plus tard se re-signale, et une collecte identique ne
        # signale rien.
        if a_change(ancien, enregistrement):
            connues[cle] = enregistrement
            modifiees.append(cle)

    ecrire(OPPORTUNITES, list(connues.values()))
    return Bilan(nouvelles, modifiees)


def nouvelles_depuis(opportunities, deja_vus):
    """Les opportunités dont l'identité n'est pas dans `deja_vus`.

    C'est le doublon détecté, au sens de docs/VERSIONS.md : sur une collecte
    neuve, ce qui n'a pas encore été montré à l'utilisateur. Le calcul est fait
    ici et pas en amont, pour que la V0.4 enregistre tout et que la V0.5
    choisisse quoi afficher, sans que les deux aient chacun la même liste.
    """
    return [o for o in opportunities if identite(o) not in deja_vus]


def modifiees_depuis(opportunities, deja_vus, modifiees):
    """Les opportunités déjà montrées dont la fiche a changé.

    Le troisième argument est la liste renvoyée par `sauvegarder` : les
    identités dont la fiche diffère de ce qui était enregistré. C'est un
    calcul fait au moment de la sauvegarde, parce que c'est là que la version
    précédente de la fiche existe encore.

    Les deux conditions sont nécessaires, et chacune écarte un cas qui
    produirait un mensonge à l'écran :

* `deja_vus` exclut ce qui n'a jamais été montré. Une opportunité collectée
  la veille mais écartée par le profil, et dont la page change aujourd'hui,
  n'a pas été mise à jour pour l'étudiant : elle lui est inconnue. Elle
  passe par `nouvelles_depuis`, qui la présente comme nouvelle ;
* l'identité doit être dans `modifiees`, sinon une collecte identique se
  signalerait comme une mise à jour tous les jours.

    Une conséquence à connaître : changer `config/profile.json` change le
    score, qui fait partie de la fiche. Les opportunités retenues dont le
    score bouge seront donc signalées comme mises à jour. C'est le
    comportement voulu : le profil ayant changé, l'information affichée
    n'est plus la même.
    """
    modifiees = set(modifiees)
    return [
        o
        for o in opportunities
        if identite(o) in deja_vus and identite(o) in modifiees
    ]


# 4. Ce qui a déjà été montré


def charger_vus():
    """Les identités déjà montrées à l'utilisateur.

    Le fichier contient des chaînes, pas des fiches : on n'a besoin que de
    savoir ce qui a été montré, pas de le remontrer. Une entrée qui n'est pas
    une chaîne est une erreur signalée, et non une entrée ignorée. L'ignorer
    ferait lire le fichier comme vide, donc annoncerait toutes les opportunités
    comme nouvelles : c'est l'inondation que ce fichier existe pour empêcher.
    """
    entrees = lire(VUS)
    for entree in entrees:
        if not isinstance(entree, str):
            raise StockageInvalide(
                f"{VUS.name} contient une entrée de type "
                f"{type(entree).__name__}, des identités textuelles étaient "
                "attendues. Corriger le format : le lire comme vide ferait "
                "passer toutes les opportunités pour nouvelles."
            )
    return set(entrees)


def conserver_vus(opportunities):
    """Mémorise les opportunités montrées, sans oublier les précédentes.

    L'union avec l'existant est délibérée : un oubli ici ferait ré-annoncer
    indéfiniment la même opportunité, ce qui est le défaut que la veille doit
    précisément éviter.
    """
    vus = charger_vus() | {identite(o) for o in opportunities}
    ecrire(VUS, sorted(vus))
    return vus

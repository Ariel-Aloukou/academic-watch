"""Notification : ce que l'étudiant lit, et par quel moyen.

Ce module ne décide pas *quoi* signaler. C'est la V0.5, dans `main.py`, qui a
déjà choisi parmi les 69 fiches. Ici il n'y a qu'une décision à prendre, et
elle est la seule : ne pas rendre la même information deux fois.

    rendre()     le texte du bulletin, une seule fois
    publier()    la console toujours, l'email si les secrets sont là

Le même texte part dans les deux. Deux rendus de la même liste divergeraient au
premier champ ajouté, et la divergence se verrait dans la boîte de réception
bien avant d'être cherchée.

L'email lui-même est coupé en deux : `message` fait les en-têtes et le
corps, `envoyer` fait le transport. Les en-têtes sont là où vivent les
erreurs — accents, adresse, objet — et aucun test n'a besoin d'un serveur
pour les prouver ; le transport n'est que cinq lignes, et on le teste en
remplaçant `smtplib.SMTP` par un objet qui note les appels.

## Ce que le message contient, et ce qu'il ne peut pas contenir

Le cahier des charges demande six champs. Mesuré sur les 69 fiches, le programme
en publie quatre, et un cinquième pour 2 opportunités sur 9 :

    Nouvelle opportunité
    Master Cybersecurity  titre           69 / 69
    Université            university      69 / 69
    Pays                  country         69 / 69
    Deadline              deadline        0 / 69
    Financement           funding_type    3 / 69, dont 2 des 9 retenues
    Lien                  url            69 / 69

La date limite n'est publiée par aucune des quatre sources : c'est
mesuré page par page et écrit dans docs/SOURCES.md §6.3. Le message
l'affichera le jour où une source la publiera, et ne l'invente pas avant :
une échéance devinée est une échéance fausse, et c'est le genre d'erreur
qui fait postuler à la mauvaise date.

## Les secrets

Six variables d'environnement, optionnelles ensemble :

    SMTP_HOST   SMTP_PORT   SMTP_USER   SMTP_PASSWORD   EMAIL_FROM   EMAIL_TO

Elles sont lues, pas demandées. Au moins une manquante, et le programme affiche
le bulletin sur la console en disant laquelle manque. C'est le mode par défaut,
donc `python src/main.py` fonctionne sans rien configurer, et c'est aussi ce qui
permet d'essayer le code sans avoir de boîte aux lettres.

Le mot de passe se met dans les secrets du dépôt GitHub, jamais dans `config/` et
jamais dans un commit. Il n'est écrit nulle part dans ce dépôt.

## L'échec d'envoi n'arrête pas la veille

Si l'envoi échoue, `publier` le dit et rend la main. Il ne lève pas d'exception,
pour une raison concrète : dans le workflow, une veille en échec fait sauter
l'étape qui commite `data/`. Une veille qui a réussi et un email qui n'est pas
parti ne doivent pas coûter la journée de données.

Le prix de ce choix est qu'un échec pourrait se perdre dans le journal. Il est
visible deux fois : la ligne de statut nomme l'erreur, et le workflow recopie
cette ligne dans le résumé d'étape.
"""

import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import NamedTuple

# Les deux étiquettes de la V0.5. Ce sont des constantes parce que `main.py` les
# attribue et que le rendu les compte : une faute de frappe dans l'une des deux
# afficherait une étiquette qui n'est dans aucune liste, sans erreur.
NOUVELLE = "nouvelle"
MISE_A_JOUR = "mise à jour"

# Les six variables d'environnement, lues ensemble ou pas du tout. Les nommer
# toutes ici évite de les découvrir une par une dans le code.
VARIABLES = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO")

# Le même délai que le scraper. Un serveur SMTP qui ne répond pas doit bloquer la
# veille le temps d'une collecte, pas plus.
DELAI_SECONDES = 30


class Bulletin(NamedTuple):
    """Le message du jour, et les deux comptes dont son titre est fait.

    Les comptes voyagent avec le texte parce que le sujet de l'email les reprend.
    Les recalculer à partir du texte serait fragile, et les faire à deux endroits
    divergerait à la première version qui aurait un cas de plus.
    """

    texte: str
    nouvelles: int
    mises_a_jour: int
    quand: datetime


# 1. Le texte


def _compte(nombre, singulier, pluriel=None):
    """« 1 nouvelle », « 2 nouvelles », « 2 mises à jour ».

    Le pluriel est passé quand il n'est pas le singulier plus un « s », parce
    que « mise à jour » s'accorde sur deux mots.
    """
    pluriel = pluriel or singulier + "s"
    return f"{nombre} {singulier if nombre == 1 else pluriel}"


def _fiche(opportunity, resultat, etiquette, numero):
    """Les lignes d'une opportunité, dans l'ordre du cahier des charges.

    Un champ absent n'est pas remplacé par un tiret : il n'est pas écrit. Une
    ligne « Financement : — » ferait croire que la bourse ne finance rien, ce
    qui est différent de ne pas le publier.
    """
    lignes = [f"{numero}. [{etiquette}] {opportunity.title}"]
    lignes.append(f"   Université : {opportunity.university}")
    lignes.append(f"   Pays        : {opportunity.country}")
    if opportunity.degree:
        lignes.append(f"   Diplôme     : {opportunity.degree}")
    if opportunity.field:
        lignes.append(f"   Domaines    : {opportunity.field}")
    if opportunity.funding_type:
        lignes.append(f"   Financement : {opportunity.funding_type}")
    if opportunity.deadline:
        lignes.append(f"   Deadline    : {opportunity.deadline}")
    # Le score n'a de sens que rapporté au maximum du type : 85 sur 100 pour un
    # programme et 100 sur 100 pour une bourse ne se comparent pas.
    lignes.append(
        f"   Score       : {resultat['score']} / {resultat['score_max']} ({resultat['type']})"
    )
    for raison in resultat["reasons"]:
        lignes.append(f"     - {raison}")
    lignes.append(f"   Lien        : {opportunity.url}")
    lignes.append("")
    return lignes


def rendre(a_signaler, retenues, total, quand=None):
    """Le bulletin du jour : le compte de ce qui a été trouvé, et le signal.

    `a_signaler` vient de la V0.5 et n'est jamais recalculé ici. `retenues` et
    `total` ne servent qu'à la ligne de compte et au cas « rien de nouveau »,
    où il faut savoir de combien d'opportunités on parle.
    """
    quand = quand or datetime.now(timezone.utc)
    nouvelles = sum(1 for _, _, etiquette in a_signaler if etiquette == NOUVELLE)
    mises_a_jour = len(a_signaler) - nouvelles

    lignes = [
        f"Academic Watch - {quand.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
        "=== Opportunités trouvées ===",
        f"{total} opportunités trouvées, {retenues} correspondent au profil",
        "",
        "=== À signaler ===",
    ]

    if not a_signaler:
        lignes.append(
            f"Rien de nouveau : les {retenues} opportunités qui correspondent "
            "au profil ont déjà été montrées."
        )
        # Une ligne vide, comme après la dernière fiche : sans elle le pied de
        # message colle à la ligne du dessus, et c'est le cas le plus fréquent
        # qui est le moins lisible.
        lignes.append("")
    else:
        details = []
        if nouvelles:
            details.append(_compte(nouvelles, "nouvelle"))
        if mises_a_jour:
            details.append(_compte(mises_a_jour, "mise à jour", "mises à jour"))
        lignes.append(f"{len(a_signaler)} à signaler : {', '.join(details)}")
        lignes.append("")
        for numero, (opportunity, resultat, etiquette) in enumerate(a_signaler, start=1):
            lignes.extend(_fiche(opportunity, resultat, etiquette, numero))

    lignes.append(
        "-- Message automatique. Il arrive même quand il n'y a rien de nouveau : "
        "c'est la preuve que la veille tourne encore."
    )

    return Bulletin("\n".join(lignes), nouvelles, mises_a_jour, quand)


# 2. L'email


def configuration():
    """Les six variables d'environnement, et la liste de celles qui manquent.

    Les deux sont rendues ensemble parce que la ligne de statut doit nommer la
    variable manquante : « console seule » sans dire laquelle est un rapport
    d'échec qui ne sert à rien.
    """
    valeurs = {nom: os.environ.get(nom, "").strip() for nom in VARIABLES}
    return valeurs, [nom for nom in VARIABLES if not valeurs[nom]]


def sujet(bulletin):
    """La ligne d'objet, faite des deux comptes du bulletin.

    Une date en format ISO, et non un nom de jour en français. `strftime`
    suit la locale : sur une machine réglée autrement, `%A` écrit
    « Tuesday », et le message partirait avec un jour en anglais au milieu
    d'une phrase française. L'ISO n'a pas cette ambiguïté, et c'est une
    boîte mail, pas une lettre.
    """
    date = bulletin.quand.strftime("%Y-%m-%d")
    if not bulletin.nouvelles and not bulletin.mises_a_jour:
        return f"Academic Watch {date} : rien de nouveau"
    details = []
    if bulletin.nouvelles:
        details.append(_compte(bulletin.nouvelles, "nouvelle"))
    if bulletin.mises_a_jour:
        details.append(_compte(bulletin.mises_a_jour, "mise à jour", "mises à jour"))
    return f"Academic Watch {date} : {', '.join(details)}"


def message(bulletin, valeurs):
    """Le message électronique prêt à envoyer.

    `set_content(..., charset="utf-8")` n'est pas un détail : sans lui, le
    corps part en ASCII et chaque caractère accentué devient
    `=?utf-8?...?=`, illisible dans la plupart des lecteurs. Les titres des
    opportunités sont en anglais mais contiennent des accents, KAIST et
    TUM en publient.
    """
    msg = EmailMessage()
    msg["From"] = valeurs["EMAIL_FROM"]
    msg["To"] = valeurs["EMAIL_TO"]
    msg["Subject"] = sujet(bulletin)
    msg.set_content(bulletin.texte, charset="utf-8")
    return msg


def envoyer(msg, valeurs, transport=smtplib.SMTP):
    """L'envoi. Cinq lignes, et la seule qui parle au réseau.

    Le port est le port de soumission, 587, avec STARTTLS explicite. Le port
    implicite 465 n'est pas traité : `starttls` échouerait avec une erreur SMTP
    peu parlante. Ce port est en clair dans la documentation du fournisseur, donc
    le traiter à l'aveugle n'apporterait rien.

    Les deux méthodes sont appelées dans cet ordre et aucune autre : c'est ce que
    demande Outlook, et un `login` avant le `starttls` enverrait le mot de passe
    en clair.

    `transport` est la couture. Sa valeur par défaut est le vrai serveur, donc le
    programme se comporte normalement sans qu'on en parle ; les tests passent un
    objet qui note les appels, et aucun d'eux n'ouvre une connexion. Passer le
    faux serveur en argument plutôt que remplacer `smtplib.SMTP` évite de
    modifier un module de la bibliothèque standard pour toute la session de
    tests, y compris pour les tests qui ne speak pas de messagerie.
    """
    with transport(
        valeurs["SMTP_HOST"], int(valeurs["SMTP_PORT"]), timeout=DELAI_SECONDES
    ) as serveur:
        serveur.starttls(context=ssl.create_default_context())
        serveur.login(valeurs["SMTP_USER"], valeurs["SMTP_PASSWORD"])
        serveur.send_message(msg)


def publier(bulletin, transport=smtplib.SMTP) -> str:
    """Affiche le bulletin, et l'envoie par email s'il est configuré.

    Renvoie la ligne qui dit ce qui a été fait, et elle est affichée : c'est elle
    que le workflow recopie dans le résumé d'étape, et c'est la seule trace
    qu'un run automatique a réussi à notifier.

    Ne lève jamais. Voir le docstring du module : une exception ici ferait
    sauter le commit de `data/`, donc perdrait une journée de veille qui, elle,
    a réussi.

    `transport` est injecté : les tests le remplacent par un faux, et aucun n'est
    obligé de recourir à `monkeypatch.setattr` sur un module de la bibliothèque
    standard. Le fonctionnement réel garde la valeur par défaut.
    """
    print(bulletin.texte)

    valeurs, manquantes = configuration()
    if manquantes:
        ligne = f"Notification : console seule, il manque {', '.join(manquantes)}"
    else:
        try:
            envoyer(message(bulletin, valeurs), valeurs, transport=transport)
        except Exception as erreur:
            # Tout est rattrapé, y compris une faute de code. Le type de
            # l'exception est nommé, donc une NameError se lirait au lieu de se
            # déguiser en problème de réseau.
            ligne = (
                f"Notification : email non envoyé ({type(erreur).__name__}), "
                "la veille est complète"
            )
        else:
            ligne = f"Notification : email envoyé à {valeurs['EMAIL_TO']}"

    print()
    print(ligne)
    return ligne

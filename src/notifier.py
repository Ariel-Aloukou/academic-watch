"""Notification : ce que l'étudiant lit, et par quel moyen.

Ce module ne décide pas *quoi* signaler. C'est la V0.5, dans `main.py`, qui a
déjà choisi parmi les 69 fiches. Ici il n'y a qu'une décision à prendre, et
elle est la seule : ne pas rendre la même information deux fois.

    rendre()     le texte du bulletin, une seule fois
    publier()    la console toujours, l'email et Discord s'ils sont configurés

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

Discord est le second canal, et il n'a pas la même forme : une seule variable,
lue ou pas lue, jamais à moitié. Elle est venue après l'email parce que le mot de
passe d'application d'Outlook exige une double authentification, et qu'un secret
que l'étudiant ne peut pas créer seul est un canal qui n'existe pas. Les six
variables SMTP restent en place : les deux canaux sont indépendants, et le
programme utilise celui qui est là.

## L'échec d'envoi n'arrête pas la veille

Si l'envoi échoue, `publier` le dit et rend la main. Il ne lève pas d'exception,
pour une raison concrète : dans le workflow, une veille en échec fait sauter
l'étape qui commite `data/`. Une veille qui a réussi et un email qui n'est pas
parti ne doivent pas coûter la journée de données. La règle est la même pour
Discord : les deux canaux sont tentés l'un après l'autre, et l'échec de l'un
n'empêche pas l'autre d'essayer. `publier` renvoie une seule ligne qui nomme les
deux, parce que c'est elle que le workflow recopie dans le résumé d'étape.

Le prix de ce choix est qu'un échec pourrait se perdre dans le journal. Il est
visible deux fois : la ligne de statut nomme l'erreur, et le workflow recopie
cette ligne dans le résumé d'étape.
"""

import os
import smtplib
import ssl
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import NamedTuple

import requests

# Les deux étiquettes de la V0.5. Ce sont des constantes parce que `main.py` les
# attribue et que le rendu les compte : une faute de frappe dans l'une des deux
# afficherait une étiquette qui n'est dans aucune liste, sans erreur.
NOUVELLE = "nouvelle"
MISE_A_JOUR = "mise à jour"

# Les six variables d'environnement, lues ensemble ou pas du tout. Les nommer
# toutes ici évite de les découvrir une par une dans le code.
VARIABLES = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO")

# Le même délai que le scraper. Un serveur SMTP qui ne répond pas doit bloquer la
# veille le temps d'une collecte, pas plus. Il sert aussi à la connexion au
# webhook : la même réponse « attendez » pour deux canaux.
DELAI_SECONDES = 30

# Le canal Discord, et sa seule variable. Elle est lue ou absente, jamais à
# moitié : une URL de webhook tronquée échouerait en 404 à chaque exécution, donc
# mieux vaut qu'elle soit absente, et que le programme dise qu'elle ne l'est pas.
VARIABLE_DISCORD = "DISCORD_WEBHOOK"

# Discord refuse un `content` de plus de 2000 caractères, et c'est une limite de
# l'API, pas un choix : sa page « Execute Webhook » annonce « the message
# contents (up to 2000 characters) », et elle ne se négocie pas. Mesuré sur le
# bulletin du 28 septembre 2026, le texte fait 3493 caractères, donc deux
# messages. Le pire cas du registre entier, les 69 fiches toutes retenues, en
# fait 25317 caractères, donc treize.
LIMITE_MESSAGE = 2000

# Un choix de lisibilité, pas une limite de Discord. Le pire cas du registre
# donnerait treize messages, et treize messages à 7 h du matin transformeraient le
# salon en mur de texte dont l'étudiant n'en lirait aucun.
# Ce qui ne rentre pas n'est pas perdu : le résumé d'étape recopie la section
# « à signaler » entière, et l'email n'a pas de limite.
MESSAGES_MAX = 5

# Le plafond d'attente entre deux messages. La documentation de Discord dit de ne
# pas écrire la limite de débit en dur, mais de lire les en-têtes de réponse ; ce
# que fait `_attendre_avant_le_suivant`. Ce plafond n'existe que pour qu'un
# `X-RateLimit-Reset-After` absent ou aberrant ne fasse pas dormir le run.
ATTENTE_MAX = 5.0


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


def compte(nombre, singulier, pluriel=None):
    """« 1 nouvelle », « 2 nouvelles », « 2 mises à jour ».

    Le pluriel est passé quand il n'est pas le singulier plus un « s », parce
    que « mise à jour » s'accorde sur deux mots.

    La fonction est publique et non underscore parce que `main.display_sources`
    écrit aussi un compte en français, et qu'un accord calculé à deux endroits
    finit par diverger : l'un dit « 1 opportunité extraite » et l'autre
    « 1 opportunités extraites », et rien ne dit lequel des deux est le bon.
    Un accord se calculant en un seul endroit ne peut pas diverger.
    """
    pluriel = pluriel or singulier + "s"
    return f"{nombre} {singulier if nombre == 1 else pluriel}"


def _alertes_sources(sources):
    """Les lignes d'avertissement sur les sources qui n'ont rien donné.

    **Aucune ligne quand tout va bien**, et c'est le choix qui compte. Le
    bulletin est lu tous les jours : une ligne qui répète ce que la veille
    fonctionnait normalement la veille passée est du bruit, et c'est le bruit
    que la V0.5 a passé sa version à supprimer. Le compte complet par source est
    écrit dans le journal, que le workflow recopie dans son résumé d'étape — la
    ligne d'avertissement est un coup de sémaphore, le journal est le dossier.

    La source est nommée, jamais simplement « une source » : l'étudiant ne peut
    pas réparer une page qu'il ne connaît pas. Et la raison est entre
    parenthèses, parce que « n'a rien produit » se répare différemment selon
    qu'il s'agit d'un site hors service ou d'un site qui a changé de HTML.

    Les sources activées sans sélecteurs ne sont pas citées. Elles ne sont pas
    une panne : ce sont des sources inscrites au cahier des charges et pas
    encore lues, et les annoncer tous les jours ferait crier au problème ce
    qui est un état normal.
    """
    lignes = []
    for source in sources:
        if not source.silencieuse:
            continue
        raison = source.erreur or "aucun bloc trouvé"
        lignes.append(f"Attention : {source.nom} n'a rien produit ({raison}).")

    if lignes:
        # La ligne vide, pour la même raison qu'après la dernière fiche : sans
        # elle le « === À signaler === » colle à l'avertissement.
        lignes.append("")
    return lignes


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


def rendre(a_signaler, retenues, total, sources=(), quand=None):
    """Le bulletin du jour : le compte de ce qui a été trouvé, et le signal.

    `a_signaler` vient de la V0.5 et n'est jamais recalculé ici. `retenues` et
    `total` ne servent qu'à la ligne de compte et au cas « rien de nouveau »,
    où il faut savoir de combien d'opportunités on parle.

    `sources` vient de la V0.7 : la liste des `SourceLue` que la collecte a
    rendues. Il n'est pas obligatoire, et il ne produit une ligne que si une
    source n'a rien donné. Voir `_alertes_sources` pour pourquoi le silence
    est le cas normal.
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
    ]

    lignes.extend(_alertes_sources(sources))

    lignes.append("=== À signaler ===")

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
            details.append(compte(nouvelles, "nouvelle"))
        if mises_a_jour:
            details.append(compte(mises_a_jour, "mise à jour", "mises à jour"))
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
        details.append(compte(bulletin.nouvelles, "nouvelle"))
    if bulletin.mises_a_jour:
        details.append(compte(bulletin.mises_a_jour, "mise à jour", "mises à jour"))
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
    tests, y compris pour les tests qui n'ont rien à voir avec la messagerie.
    """
    with transport(
        valeurs["SMTP_HOST"], int(valeurs["SMTP_PORT"]), timeout=DELAI_SECONDES
    ) as serveur:
        serveur.starttls(context=ssl.create_default_context())
        serveur.login(valeurs["SMTP_USER"], valeurs["SMTP_PASSWORD"])
        serveur.send_message(msg)


def _taille(lignes):
    """La longueur du texte que le collage produirait, sans le construire.

    Mesurer avant de construire évite d'assembler un message pour le jeter
    ensuite parce qu'il est trop long, et évite l'erreur d'un caractère : compter
    la ligne et son retour à la ligne ferait déborder un message d'exactement un
    caractère, tous les jours, sans qu'aucune erreur ne le dise.
    """
    if not lignes:
        return 0
    return sum(len(ligne) for ligne in lignes) + len(lignes) - 1


def decouper(texte, limite=LIMITE_MESSAGE):
    """Le bulletin en messages de `limite` caractères au plus, coupés aux fins
    de ligne.

    Couper entre deux lignes et non au milieu d'une ligne est ce qui rend le
    message lisible : une coupure au milieu d'un champ « Domaines » laisserait le
    champ sans sa valeur, et rien ne dirait que le texte est incomplet. Mesuré
    sur le registre du 28 septembre 2026, la ligne la plus longue fait 375
    caractères, donc ce chemin suffit aujourd'hui.

    Il ne suffirait pas toujours. Une source qui publierait un titre de trois
    mille caractères produirait une ligne plus longue que la limite, et il n'y a
    alors plus de frontière à couper. Cette ligne est donc débitée au caractère,
    ce qui est la seule découpe qui reste : elle abîme la mise en forme, mais
    elle envoie tout, alors qu'une ligne refusée ferait perdre tout le message.
    """
    messages = []
    courant = []
    for ligne in texte.split("\n"):
        morceaux = [ligne[i:i + limite] for i in range(0, len(ligne), limite)] or [""]
        for morceau in morceaux:
            if courant and _taille(courant) + 1 + len(morceau) > limite:
                messages.append("\n".join(courant))
                courant = []
            courant.append(morceau)
    if courant:
        messages.append("\n".join(courant))
    return messages


def messages_discord(texte, maximum=MESSAGES_MAX):
    """Les messages à poster, et le nombre de ceux qui n'y entrent pas.

    Le second nombre est rendu pour qu'il soit dit, pas pour être comparé : un
    message non envoyé sans qu'on le dise se lit comme un message envoyé.
    """
    tous = decouper(texte)
    retenus = tous[:maximum]
    # Le nombre de ceux qui n'entrent pas est la différence avec ce qui a été
    # retenu, et non avec le plafond. Il serait négatif pour un bulletin court,
    # et un nombre négatif est vrai : la ligne de statut dirait qu'il manque
    # moins de zéro messages.
    return retenus, len(tous) - len(retenus)


def _attendre_avant_le_suivant(reponse, dormeur):
    """Une pause, et seulement si Discord dit qu'il en faut une.

    La documentation de Discord est explicite : écrire la limite de débit en dur
    est une faute, parce qu'elle change sans prévenir. Elle demande de lire
    `X-RateLimit-Remaining` et, quand il vaut zéro, `X-RateLimit-Reset-After`.
    C'est tout ce que fait cette fonction, et rien d'autre.

    Un en-tête absent ne fait pas attendre : la réponse est alors peut-être venue
    d'un serveur intermédiaire, et dormir au hasard coûterait plus de temps
    qu'il n'en évite. Une valeur illisible non plus : elle vaut une seconde, ce
    qui est l'ordre de grandeur utile, et `publier` reste le filet au cas où
    l'envoi échouerait quand même.
    """
    if reponse.headers.get("X-RateLimit-Remaining", "1") != "0":
        return
    try:
        secondes = float(reponse.headers.get("X-RateLimit-Reset-After", "1"))
    except ValueError:
        secondes = 1.0
    dormeur(min(max(secondes, 0.0), ATTENTE_MAX))


def envoyer_discord(messages, webhook, transport=requests.post, dormeur=time.sleep):
    """L'envoi à Discord : une requête par message, sur l'URL du webhook.

    L'URL porte le secret. Elle n'est donc jamais journalisée, jamais mise dans
    `config/`, et l'erreur que `publier` nomme est le type d'exception, pas son
    message, qui contient l'URL.

    `raise_for_status` est appelé parce que la bibliothèque HTTP ne lève pas sur
    un 404 : sans lui, un webhook supprimé depuis les paramètres du salon se
    lirait comme un envoi réussi, tous les jours, en silence.

    `wait` est demandé pour la même raison, par un chemin différent. Sa valeur par
    défaut est `false`, et la documentation est explicite sur ce que cela
    autorise : « when `false` a message that is not saved does not return an
    error ». La réponse est alors un 204 que la vérification d'erreur laisse
    passer. Sans `wait`, un message que Discord refuse d'enregistrer se lirait
    « 1 message envoyé » alors que le salon est vide. Avec `wait`, la réponse
    n'est un succès qu'une fois le message enregistré, et un refus est un 4xx.
    C'est un paramètre de requête et non un morceau collé à l'URL, parce que
    l'URL porte le secret et doit arriver telle quelle.

    `transport` et `dormeur` sont des coutures, comme `transport` dans
    `envoyer` : le programme se comporte normalement sans qu'on en parle, et les
    tests passent un faux, donc aucun n'attend et aucun n'ouvre de connexion.
    """
    for position, message in enumerate(messages):
        reponse = transport(
            webhook,
            params={"wait": "true"},
            json={"content": message},
            timeout=DELAI_SECONDES,
        )
        reponse.raise_for_status()
        if position + 1 < len(messages):
            _attendre_avant_le_suivant(reponse, dormeur)
    return len(messages)


def _par_email(bulletin, transport, manquantes) -> str:
    """Ce que l'email a fait, en une phrase, sans jamais lever.

    La phrase est celle du canal, pas celle de la console. « console seule »
    serait faux ici dès que Discord a envoyé quelque chose, et `publier` ne la
    garde que pour le cas où aucun des deux canaux n'a rien fait.
    """
    valeurs = {nom: os.environ.get(nom, "").strip() for nom in VARIABLES}
    if manquantes:
        return f"email non configuré (il manque {', '.join(manquantes)})"
    try:
        envoyer(message(bulletin, valeurs), valeurs, transport=transport)
    except Exception as erreur:
        # Tout est rattrapé, y compris une faute de code. Le type de
        # l'exception est nommé, donc une NameError se lirait au lieu de se
        # déguiser en problème de réseau.
        return f"email non envoyé ({type(erreur).__name__})"
    return f"email envoyé à {valeurs['EMAIL_TO']}"


def _par_discord(bulletin, transport, dormeur) -> str:
    """Ce que Discord a fait, en une phrase, sans jamais lever.

    Absente, la variable n'est pas une erreur : c'est le mode par défaut. Elle est
    nommée quand même, pour qu'un jour où l'on croyait Discord configuré se voie.
    """
    webhook = os.environ.get(VARIABLE_DISCORD, "").strip()
    if not webhook:
        return "Discord non configuré"
    try:
        messages, manques = messages_discord(bulletin.texte)
        envoyes = envoyer_discord(
            messages, webhook, transport=transport, dormeur=dormeur
        )
    except Exception as erreur:
        return f"Discord non envoyé ({type(erreur).__name__})"
    etat = f"Discord, {compte(envoyes, 'message envoyé', 'messages envoyés')}"
    if manques:
        etat += (
            f", {compte(manques, 'message de plus', 'messages de plus')}"
            " dans le résumé du run"
        )
    return etat


def publier(
    bulletin, transport=smtplib.SMTP, transport_http=requests.post, dormeur=time.sleep
) -> str:
    """Affiche le bulletin, et l'envoie par email et Discord s'ils sont configurés.

    Renvoie la ligne qui dit ce qui a été fait, et elle est affichée : c'est elle
    que le workflow recopie dans le résumé d'étape, et c'est la seule trace
    qu'un run automatique a réussi à notifier.

    Ne lève jamais, et n'interrompt pas le canal suivant non plus : les deux sont
    tentés l'un après l'autre, donc un serveur de messagerie cassé n'empêche pas
    le webhook de partir. Voir le docstring du module : une exception ici ferait
    sauter le commit de `data/`, donc perdrait une journée de veille qui, elle,
    a réussi.

    Les trois paramètres sont des coutures, injectées pour qu'aucun test n'ait
    ni à joindre un serveur ni à attendre : `transport` pour le SMTP,
    `transport_http` pour le webhook, `dormeur` pour la pause entre deux
    messages. Aucun test n'est obligé de recourir à `monkeypatch.setattr` sur un
    module de la bibliothèque standard. Le fonctionnement réel garde les valeurs
    par défaut.
    """
    print(bulletin.texte)

    _, manquantes = configuration()
    email_part = _par_email(bulletin, transport, manquantes)
    discord_part = _par_discord(bulletin, transport_http, dormeur)

    if manquantes and discord_part == "Discord non configuré":
        # Le mode par défaut : rien n'est sorti, et la console a tout affiché.
        # La phrase est celle que la documentation annonce, et elle nomme les six
        # variables parce qu'un « console seule » sans dire lesquelles ne sert
        # à rien. Elle ne vaut que si le second canal n'a rien fait non plus,
        # sinon la ligne affirmerait « console seule » et « 1 message envoyé »
        # dans la même phrase.
        # Le second canal est nommé lui aussi. Il n'a rien fait, donc son absence
        # ne contredit pas la phrase ; c'est au contraire la moitié de ce que
        # l'étudiant doit savoir pour configure la veille.
        ligne = (
            f"Notification : console seule, il manque {', '.join(manquantes)}"
            f", {discord_part}"
        )
    else:
        ligne = f"Notification : {email_part}, {discord_part}"
    # « la veille est complète » n'est ajouté que si un envoi a échoué. Mis
    # toujours, il allongerait chaque ligne d'un run sans incident, et surtout il
    # ne voudrait rien dire : on ne prouve pas qu'une veille est complète parce
    # qu'elle a été notifiée.
    if "non envoyé" in ligne:
        ligne += ", la veille est complète"

    print()
    print(ligne)
    return ligne

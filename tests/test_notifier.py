"""Tests de la notification : src/notifier.py (docs/VERSIONS.md V0.6).

Aucun test ne touche au réseau, et c'est la règle du projet : un test qui dépend
d'une boîte mail échoue pour une raison qui n'a rien à voir avec le code, et
échouerait tous les jours où le réseau tombe. Ce qui dépend d'une page vivante
est vérifié à la main et écrit dans docs/SOURCES.md ; ce qui dépend de la
boîte de l'étudiant sera vérifié une fois, de sa main.

Le test de l'envoi passe un faux serveur en argument, et vérifie que
`starttls` passe avant `login`. Cet ordre n'est pas une convention : à l'envers,
le mot de passe part en clair. Une fixture de `conftest.py` interdit à tous les
tests de joindre un serveur, donc cette couture ne protège pas seulement des
tests d'envoi.

Quatre choses sont testées séparément, et c'est le découpage qui rend le module
testable :

* `rendre` produit le texte, et ne dépend que de la V0.5 ;
* `message` produit les en-têtes et le corps, et ne dépend que du texte ;
* `envoyer` fait le transport SMTP, et ne dépend que du message ;
* `envoyer_discord` fait le transport du webhook, et ne dépend que du texte.

Les deux canaux partagent le même texte et le même `publier`, donc ce que reçoit
l'un est rigoureusement ce que reçoit l'autre. Ce n'est pas re-vérifié ici : ce
qui les sépare est la limite de longueur, et c'est mesuré dans la section 7.
"""

from datetime import datetime, timezone

import pytest

import notifier
from scraper import SourceLue

# Une évaluation, telle que `evaluer` la rend : un dictionnaire, pas un objet.
# Le minimum utile pour le rendu, le reste n'est pas imprimé.
RESULTAT = {
    "score": 70,
    "score_max": 100,
    "type": "programs",
    "matched": True,
    "reasons": ["domaine direct"],
}

# L'heure est fixée, sinon chaque exécution produirait un bulletin différent et
# aucun test ne pourrait comparer une date. Les deux classes viennent de la
# bibliothèque standard et non de `notifier` : un module testé ne doit pas être
# atteint par ce qu'il a importé, seulement par ce qu'il expose.
QUAND = datetime(2026, 9, 26, 7, 7, tzinfo=timezone.utc)


class Opportunite:
    """Le strict minimum des champs que le rendu lit.

    Une vraie `Opportunity` ferait l'affaire, mais elle a treize champs, dont
    six que le rendu ignore. Une classe à quelques champs dit plus clairement ce
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
        self.deadline = None


def signalee(opportunite, etiquette):
    return (opportunite, RESULTAT, etiquette)


def rendue(*etiquettes, retenues=1, total=1):
    """Un bulletin de N opportunités, étiquetées dans l'ordre donné.

    Les titres sont numérotés et non tirés de l'étiquette : ce qui est testé ici
    est le rendu, pas le lien entre une étiquette et un titre.
    """
    lettres = "ABCDEFGHIJ"
    return notifier.rendre(
        [
            signalee(Opportunite(f"Master {lettres[i]}"), etiquette)
            for i, etiquette in enumerate(etiquettes)
        ],
        retenues,
        total,
        quand=QUAND,
    )


# 1. Le texte


def test_le_compte_de_cequi_a_ete_trouve_est_en_tete():
    # C'est la première ligne du message quotidien : elle dit que la veille a
    # tourné et qu'elle a lu les 4 sources, même quand il n'y a rien à signaler.
    bulletin = notifier.rendre([], 9, 69, quand=QUAND)
    assert bulletin.texte.startswith("Academic Watch - 2026-09-26 07:07 UTC")
    assert "69 opportunités trouvées, 9 correspondent au profil" in bulletin.texte


def test_rien_a_signaler_le_dit_en_une_ligne():
    bulletin = notifier.rendre([], 9, 69, quand=QUAND)
    assert "Rien de nouveau" in bulletin.texte
    assert "9" in bulletin.texte
    # Une seule fois : un résumé répété n'est pas un résumé.
    assert bulletin.texte.count("Rien de nouveau") == 1


def test_les_deux_comptes_voyagent_avec_le_texte():
    # Le sujet de l'email les reprend. Les recalculer depuis le texte serait
    # fragile, et les calculer à deux endroits divergerait à la première
    # version qui aurait un cas de plus.
    bulletin = rendue(notifier.NOUVELLE, notifier.MISE_A_JOUR)
    assert (bulletin.nouvelles, bulletin.mises_a_jour) == (1, 1)


def test_une_seule_nouvelle_est_au_singulier():
    assert "1 à signaler : 1 nouvelle" in rendue(notifier.NOUVELLE).texte


def test_deux_mises_a_jour_sont_au_pluriel():
    texte = rendue(notifier.MISE_A_JOUR, notifier.MISE_A_JOUR).texte
    assert "2 à signaler : 2 mises à jour" in texte


def test_une_seule_mise_a_jour_est_au_singulier():
    # « 1 mise à jour », et pas « 1 mise » : les deux formes s'accordent sur
    # « mise » et ne diffèrent qu'en « s ». Un test au pluriel seul ne pouvait
    # pas l'attraper, c'est le nombre un qui compose le mot.
    assert "1 à signaler : 1 mise à jour" in rendue(notifier.MISE_A_JOUR).texte


def test_l_objet_au_singulier_dit_la_forme_entiere():
    # L'objet est la troisième fois où le compte est recomposé, donc la troisième
    # fois où il pouvait être faux. Il est fait des mêmes nombres que le corps.
    assert notifier.sujet(rendue(notifier.MISE_A_JOUR)) == (
        "Academic Watch 2026-09-26 : 1 mise à jour"
    )


def test_nouvelles_puis_mises_a_jour_sont_comptees_separement():
    texte = notifier.rendre(
        [
            signalee(Opportunite("Master A"), notifier.NOUVELLE),
            signalee(Opportunite("Master B"), notifier.MISE_A_JOUR),
            signalee(Opportunite("Master C"), notifier.MISE_A_JOUR),
        ],
        3,
        3,
        quand=QUAND,
    ).texte
    assert "3 à signaler : 1 nouvelle, 2 mises à jour" in texte


def test_les_nouvelles_passent_avant_les_mises_a_jour():
    # Elles restent dans l'ordre de la V0.5, et l'ordre n'est pas re-trié ici.
    texte = notifier.rendre(
        [
            signalee(Opportunite("Master A"), notifier.NOUVELLE),
            signalee(Opportunite("Master B"), notifier.MISE_A_JOUR),
        ],
        2,
        2,
        quand=QUAND,
    ).texte
    assert texte.index("Master A") < texte.index("Master B")


def test_les_raisons_et_le_score_sont_affiches():
    # Le score est ce qui rend le signal vérifiable : sans lui, l'étudiant doit
    # croire le programme sur parole.
    texte = rendue(notifier.NOUVELLE).texte
    assert "- domaine direct" in texte
    assert "70 / 100 (programs)" in texte


# Ce que le message ne doit pas inventer.


def test_un_champ_non_publie_n_est_pas_affiche():
    # Domaines vide, financement absent, deadline absente : afficher « None »
    # ferait croire à une valeur (docs/README.md §7).
    texte = rendue(notifier.NOUVELLE).texte
    assert "None" not in texte
    for label in ("Domaines", "Financement", "Deadline"):
        assert label not in texte


def test_une_deadline_publiee_est_affichee():
    # Aucune des 4 sources n'en publie, mesuré à la V0.3. Le jour où l'une
    # d'elles le fera, la ligne doit exister déjà, sinon il faudra reprendre le
    # rendu et les tests.
    opportunite = Opportunite()
    opportunite.deadline = "2026-10-15"
    texte = notifier.rendre(
        [signalee(opportunite, notifier.NOUVELLE)], 1, 1, quand=QUAND
    ).texte
    assert "Deadline    : 2026-10-15" in texte


def test_les_deux_etiquettes_sont_constantes():
    # `main.py` les attribue et le rendu les compte : une faute de frappe dans
    # l'une des deux afficherait une étiquette qui n'est dans aucune liste.
    assert notifier.NOUVELLE == "nouvelle"
    assert notifier.MISE_A_JOUR == "mise à jour"


# 2. L'email


VALEURS = {
    "SMTP_HOST": "smtp.office365.com",
    "SMTP_PORT": "587",
    "SMTP_USER": "veille@outlook.com",
    "SMTP_PASSWORD": "un-mot-de-passe",
    "EMAIL_FROM": "veille@outlook.com",
    "EMAIL_TO": "etudiant@outlook.com",
}


def test_les_en_tetes_viennent_des_secrets():
    msg = notifier.message(rendue(notifier.NOUVELLE), VALEURS)
    assert msg["From"] == "veille@outlook.com"
    assert msg["To"] == "etudiant@outlook.com"


def test_l_objet_porte_la_date_et_les_comptes():
    assert notifier.sujet(rendue(notifier.NOUVELLE)) == (
        "Academic Watch 2026-09-26 : 1 nouvelle"
    )
    assert notifier.sujet(rendue(notifier.MISE_A_JOUR, notifier.MISE_A_JOUR)).endswith(
        "2 mises à jour"
    )


def test_l_objet_d_un_jour_sans_nouveaute_le_dit():
    # Une boîte mail triée par objet : « rien de nouveau » doit se lire sans
    # ouvrir le message, donc être dans l'objet et pas seulement dans le corps.
    assert notifier.sujet(notifier.rendre([], 9, 69, quand=QUAND)) == (
        "Academic Watch 2026-09-26 : rien de nouveau"
    )


def test_la_date_de_l_objet_est_en_iso():
    # Un nom de jour en français dépend de la locale, donc il serait en anglais
    # sur une machine réglée autrement. L'ISO n'a pas cette ambiguïté.
    assert "2026-09-26" in notifier.sujet(rendue(notifier.NOUVELLE))
    assert not any(
        jour in notifier.sujet(rendue(notifier.NOUVELLE))
        for jour in ("lundi", "mardi", "Wednesday", "Friday")
    )


def test_le_corps_porte_le_bulletin_entier():
    # Le même texte que la console. Deux rendus divergeraient au premier champ
    # ajouté, et la divergence se verrait dans la boîte de réception.
    bulletin = rendue(notifier.NOUVELLE)
    msg = notifier.message(bulletin, VALEURS)
    assert msg.get_content().rstrip() == bulletin.texte


def test_les_accents_survivent_a_la_conversion():
    # Sans `charset="utf-8"`, le corps part en ASCII et chaque caractère accentué
    # devient `=?utf-8?...?=`, illisible dans la plupart des lecteurs. TUM et
    # KAIST publient des titres accentués.
    opportunite = Opportunite("Master en Génie des Systèmes")
    bulletin = notifier.rendre(
        [signalee(opportunite, notifier.NOUVELLE)], 1, 1, quand=QUAND
    )
    msg = notifier.message(bulletin, VALEURS)
    assert "Génie" in msg.get_content()
    assert msg.get_content_type() == "text/plain"
    # Ce qui compte est ce que le serveur SMTP reçoit : c'est cette ligne qui
    # dit au lecteur comment décoder. `get_charset()` rendrait None, parce que
    # la politique moderne range le corps dans une sous-part.
    assert 'charset="utf-8"' in msg.as_string()


def test_un_seul_recipient_sans_copie_ni_cc():
    # Une adresse en dur dans le dépôt, ce serait l'adresse de quelqu'un
    # d'autre, versionnée et publique.
    msg = notifier.message(rendue(notifier.NOUVELLE), VALEURS)
    assert msg["Cc"] is None
    assert msg["Bcc"] is None


# 3. La configuration


def test_les_six_variables_sont_nommees_ensemble():
    # Elles sont lues ensemble ou pas du tout : une moitié suffit à tenter un
    # envoi qui échoue, alors que la console marche déjà très bien sans.
    assert notifier.VARIABLES == (
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "EMAIL_FROM",
        "EMAIL_TO",
    )


def test_une_seule_variable_manquante_bloque_tout(monkeypatch):
    for nom in notifier.VARIABLES:
        monkeypatch.setenv(nom, "valeur")
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    valeurs, manquantes = notifier.configuration()
    assert manquantes == ["SMTP_PASSWORD"]
    assert set(valeurs) == set(notifier.VARIABLES)


def test_aucune_variable_ne_veut_dire_console_seule(monkeypatch):
    for nom in notifier.VARIABLES:
        monkeypatch.delenv(nom, raising=False)
    _, manquantes = notifier.configuration()
    assert len(manquantes) == len(notifier.VARIABLES)


def test_une_variable_vide_vaut_une_variable_absente(monkeypatch):
    # Un secret défini mais vide est un secret absent. Les traiter différemment
    # ferait tenter un envoi vers un serveur vide.
    for nom in notifier.VARIABLES:
        monkeypatch.setenv(nom, "   ")
    _, manquantes = notifier.configuration()
    assert len(manquantes) == len(notifier.VARIABLES)


# 4. L'envoi


class FauxSMTP:
    """Le serveur SMTP, remplacé par quelque chose qui note au lieu d'appeler.

    `serveur` est nécessaire parce que `smtplib.SMTP` s'utilise comme contexte
    dans `envoyer`, donc il doit se comporter comme tel.
    """

    instances = []

    def __init__(self, hote, port, timeout=None):
        self.hote = hote
        self.port = port
        self.timeout = timeout
        self.appels = []
        # Le contexte de chiffrement est mémorisé à part : c'est lui qui décide
        # si le certificat du serveur est vérifié, et il ne se voit pas dans la
        # liste des appels.
        self.contexte = None
        FauxSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self, context=None):
        self.appels.append("starttls")
        self.contexte = context

    def login(self, user, password):
        self.appels.append(("login", user, password))

    def send_message(self, msg):
        self.appels.append(("send_message", msg["Subject"]))


@pytest.fixture
def faux_smtp():
    """Un faux serveur SMTP, prêt à être passé en `transport`.

    Il n'est pas installé par `monkeypatch`. Le programme accepte le transport en
    argument, donc le test le lui donne : un module de la bibliothèque standard
    n'a pas à être modifié pour que le test passe.
    """
    FauxSMTP.instances = []
    return FauxSMTP


def test_l_envoi_passe_par_le_port_de_soumission(faux_smtp):
    notifier.envoyer(
        notifier.message(rendue(notifier.NOUVELLE), VALEURS), VALEURS, faux_smtp
    )
    serveur = faux_smtp.instances[0]
    assert serveur.hote == "smtp.office365.com"
    assert serveur.port == 587
    assert serveur.timeout == notifier.DELAI_SECONDES


def test_le_chiffrement_precede_le_mot_de_passe(faux_smtp):
    # L'ordre n'est pas une convention : à l'envers, le mot de passe part en
    # clair sur la connexion.
    notifier.envoyer(
        notifier.message(rendue(notifier.NOUVELLE), VALEURS), VALEURS, faux_smtp
    )
    appels = faux_smtp.instances[0].appels
    assert appels[0] == "starttls"
    assert [a[0] for a in appels[1:]] == ["login", "send_message"]


def test_le_certificat_du_serveur_est_verifie(faux_smtp):
    # Un `starttls()` sans contexte accepte n'importe quel certificat, donc un
    # nom de domaine usurpé pourrait recevoir le mot de passe de la boîte.
    notifier.envoyer(
        notifier.message(rendue(notifier.NOUVELLE), VALEURS), VALEURS, faux_smtp
    )
    contexte = faux_smtp.instances[0].contexte
    assert contexte is not None
    assert contexte.check_hostname is True
    assert contexte.verify_mode.name == "CERT_REQUIRED"


# 5. Ce que fait `publier`, qui est la seule fonction qui ne lève jamais


def test_sans_secret_la_console_seule_et_la_raison(monkeypatch, capsys):
    for nom in notifier.VARIABLES:
        monkeypatch.delenv(nom, raising=False)
    for nom in notifier.VARIABLES + (notifier.VARIABLE_DISCORD,):
        monkeypatch.delenv(nom, raising=False)
    ligne = notifier.publier(rendue(notifier.NOUVELLE))
    sortie = capsys.readouterr().out
    assert "Master A" in sortie
    # La ligne nomme la variable manquante : « console seule » sans dire
    # laquelle est un rapport d'échec qui ne sert à rien.
    assert ligne.startswith("Notification : console seule")
    assert "SMTP_HOST" in ligne
    # C'est le seul cas où la phrase est exacte : aucun des deux canaux n'a rien
    # fait. Dès que l'un des deux envoie, la ligne abandonne la phrase et dit
    # ce que chaque canal a fait, comme le vérifie
    # `test_console_seule_n_estdit_qu_avec_aucun_canal_configure`.
    assert "Discord non configuré" in ligne


def test_avec_secret_la_ligne_confirme_le_destinataire(monkeypatch, faux_smtp, capsys):
    for nom in notifier.VARIABLES:
        monkeypatch.setenv(nom, VALEURS[nom])
    ligne = notifier.publier(rendue(notifier.NOUVELLE), faux_smtp)
    # Les deux canaux sont nommés, y compris celui qui n'a rien fait : une ligne
    # qui ne parlerait que de l'email laisserait croire que Discord a réussi.
    assert ligne == (
        "Notification : email envoyé à etudiant@outlook.com, "
        "Discord non configuré"
    )
    assert faux_smtp.instances[0].appels[-1][1] == "Academic Watch 2026-09-26 : 1 nouvelle"


def test_un_envoi_qui_echoue_ne_coute_pas_la_veille(monkeypatch, capsys):
    # Si `publier` levait, le workflow sauterait l'étape qui commite `data/`.
    # Une veille qui a réussi et un email non parti ne doivent pas coûter la
    # journée de données.

    def casse(*args, **kwargs):
        raise OSError("Connexion réinitialisée")

    for nom in notifier.VARIABLES:
        monkeypatch.setenv(nom, VALEURS[nom])
    monkeypatch.setattr(notifier, "envoyer", casse)

    ligne = notifier.publier(rendue(notifier.NOUVELLE))
    assert "email non envoyé (OSError)" in ligne
    assert "la veille est complète" in ligne
    # Le bulletin a quand même été affiché : l'étudiant a la veille, même si
    # elle n'a pas pu partir.
    assert "Master A" in capsys.readouterr().out


def test_une_faute_de_code_ne_se_deguise_pas_en_probleme_de_reseau(monkeypatch, capsys):
    # Tout est rattrapé, y compris une faute de code. Le type est nommé, donc une
    # NameError se lit au lieu de passer pour un serveur injoignable.
    def casse(*args, **kwargs):
        raise NameError("SMTP_HOT")

    for nom in notifier.VARIABLES:
        monkeypatch.setenv(nom, VALEURS[nom])
    monkeypatch.setattr(notifier, "envoyer", casse)

    assert "NameError" in notifier.publier(rendue(notifier.NOUVELLE))


# 6. Les sources muettes, qui n'écrivent que lorsqu'il y a à dire


def test_rien_n_est_ecrit_quand_toutes_les_sources_ont_produit():
    # Le bulletin est lu tous les jours. Une ligne qui répète que la veille
    # marche comme hier est du bruit, et c'est le bruit que la V0.5 a passé sa
    # version à supprimer. Le compte par source est dans le journal, qui est lu
    # quand on cherche une panne.
    sources = [SourceLue("Alpha", 3), SourceLue("Beta", 36)]
    texte = notifier.rendre([], 9, 69, sources, quand=QUAND).texte
    assert "Attention" not in texte


def test_une_source_muette_est_nommee():
    # Nommée, et pas « une source » : l'étudiant ne peut pas réparer une page
    # qu'il ne connaît pas.
    sources = [SourceLue("Alpha", 3), SourceLue("Beta", 0)]
    texte = notifier.rendre([], 9, 69, sources, quand=QUAND).texte
    assert "Attention : Beta n'a rien produit (aucun bloc trouvé)." in texte
    assert "Alpha" not in texte


def test_seule_la_source_muette_est_nommee():
    # Une source qui a produit ne doit jamais apparaître dans les alertes. Le
    # jour où la condition s'inverserait, l'étudiant lirait « Alpha n'a rien
    # produit » le jour où Alpha a produit 36 programmes.
    sources = [SourceLue("Alpha", 0), SourceLue("Beta", 12)]
    texte = notifier.rendre([], 9, 69, sources, quand=QUAND).texte
    assert "Alpha n'a rien produit" in texte
    assert "Beta" not in texte


    coupure = notifier.rendre(
        [], 9, 69, [SourceLue("Beta", 0, "ConnectionError")], quand=QUAND
    ).texte
    assert "(ConnectionError)" in coupure
    assert "aucun bloc trouvé" not in coupure

    # Une source qui a répondu sans contenu n'a pas de type d'exception, et le
    # bulletin ne doit pas lui en inventer un.
    sans_bloc = notifier.rendre([], 9, 69, [SourceLue("Beta", 0)], quand=QUAND).texte
    assert "(aucun bloc trouvé)" in sans_bloc
    assert "Error" not in sans_bloc


def test_l_alerte_ne_colle_pas_a_la_section_suivante():
    # La ligne vide après les alertes. Sans elle, « === À signaler === »
    # commence à la fin de la ligne d'avertissement, et c'est le cas le moins
    # lisible du message.
    texte = notifier.rendre(
        [], 9, 69, [SourceLue("Beta", 0)], quand=QUAND
    ).texte
    lignes = texte.split("\n")
    index = next(i for i, ligne in enumerate(lignes) if ligne.startswith("Attention"))
    assert lignes[index + 1] == ""
    assert lignes[index + 2] == "=== À signaler ==="


def test_les_alertes_viennent_apres_le_compte_et_avant_le_signal():
    # L'ordre se lit : le compte dit combien, l'alerte dit que ce nombre est
    # peut-être incomplet, et le signal vient après. Le workflow extrait la
    # section « À signaler » par un `sed` à ancres fixes, donc l'alerte doit
    # être avant.
    texte = notifier.rendre(
        [], 9, 69, [SourceLue("Beta", 0)], quand=QUAND
    ).texte
    assert (
        texte.index("opportunités trouvées")
        < texte.index("Attention :")
        < texte.index("=== À signaler ===")
    )


def test_compte_accorde_au_singulier_et_au_pluriel():
    # `compte` est public parce que `main.display_sources` s'en sert aussi. Une
    # source écrite « 1 opportunités » au journal et « 1 nouvelle » dans le
    # bulletin serait deux règles d'accord dans un projet qui s'en est donné une.
    assert notifier.compte(1, "opportunité", "opportunités") == "1 opportunité"
    assert notifier.compte(3, "opportunité", "opportunités") == "3 opportunités"
    # Le pluriel par défaut, et celui qui s'accorde sur deux mots.
    assert notifier.compte(2, "nouvelle") == "2 nouvelles"
    assert notifier.compte(2, "mise à jour", "mises à jour") == "2 mises à jour"


# 7. Le canal Discord


# Il tient en une variable là où l'email en demande six, et il ne demande aucune
# double authentification. Ce que la V0.6 a coûté à l'étudiant ne se rattrape pas
# dans le code : c'est pour cela que ce canal existe.
#
# Les tests reprennent la couture de la section 4. Le client HTTP est remplacé par
# un objet qui note les appels, et `time.sleep` par un objet qui note les durées,
# parce qu'un test qui attendrait cinq secondes serait un test de cinq secondes.
# Aucun de ces deux objets n'ouvre de connexion, donc la garde de `conftest.py` ne
# voit rien.


WEBHOOK = "https://discord.com/api/webhooks/123456/toute-cette-url-est-un-secret"


class FauxReponse:
    """La réponse HTTP, réduite à ce que le code lit.

    Deux choses seulement : les en-têtes, lus par `_attendre_avant_le_suivant`, et
    `raise_for_status`, que la bibliothèque HTTP n'appelle pas d'elle-même.
    """

    def __init__(self, restant="4", reset="1", erreur=None):
        self.headers = {
            "X-RateLimit-Remaining": restant,
            "X-RateLimit-Reset-After": reset,
        }
        self.verifications = 0
        self.erreur = erreur

    def raise_for_status(self):
        self.verifications += 1
        if self.erreur is not None:
            raise self.erreur


class FauxHTTP:
    """Le client HTTP, remplacé par quelque chose qui note au lieu d'appeler.

    Le rôle est celui de `FauxSMTP`, et pour la même raison : le programme accepte
    le transport en argument, donc le test le lui donne. Une valeur de `restant`
    à zéro simule un seau de débit vide, c'est-à-dire la réponse que Discord
    renvoie quand elle veut que l'on patiente.
    """

    def __init__(self, restant="4", reset="1", erreur=None):
        self.restant = restant
        self.reset = reset
        self.erreur = erreur
        self.appels = []
        self.reponses = []

    def __call__(self, url, json=None, timeout=None, params=None):
        # La signature épingle l'appel réel : ajouter un argument au code sans
        # l'ajouter ici fait échouer le test sur une TypeError, qui dit quoi
        # changer, au lieu d'un test vert qui accepte n'importe quoi.
        self.appels.append(
            {"url": url, "json": json, "timeout": timeout, "params": params}
        )
        reponse = FauxReponse(self.restant, self.reset, self.erreur)
        self.reponses.append(reponse)
        return reponse


class Dormeuse:
    """Le remplacement de `time.sleep`, qui note au lieu d'attendre.

    Elle est appelable, comme la fonction qu'elle remplace : c'est le contrat de
    `dormeur`, et une fausse qui ne l'est pas ferait échouer le test sur une
    TypeError au lieu de vérifier la durée demandée.
    """

    def __init__(self):
        self.dures = []

    def __call__(self, secondes):
        self.dures.append(secondes)


@pytest.fixture(autouse=True)
def _discord_absent_par_defaut(monkeypatch):
    """Retire la variable Discord avant chaque test de ce fichier.

    Sans cela, un `DISCORD_WEBHOOK` posé sur la machine de l'étudiant ferait
    qu'un test écrive dans son vrai salon, et le résultat dépendrait de l'heure.
    La garde de `conftest.py` l'interdit de toute façon, mais elle interromprait
    un test sans dire qu'un secret local a été trouvé.
    """
    monkeypatch.delenv(notifier.VARIABLE_DISCORD, raising=False)


@pytest.fixture
def faux_http():
    """Une instance, pas la classe.

    Le code appelle `transport(...)`, il ne l'instancie pas : contrairement au
    SMTP, où c'est `envoyer` qui construit le serveur, la classe ne conviendrait
    pas ici. Les assertions regardent donc `appels` et `reponses` de cette
    instance, qui est vide tant que rien n'a été envoyé.
    """
    return FauxHTTP()


@pytest.fixture
def dormeuse():
    return Dormeuse()


def texte_de(nombre, largeur=90):
    """Un texte de `nombre` lignes, toutes de la même longueur.

    Des lignes égales rendent la coupe prévisible sans écrire la taille des
    messages en dur, donc sans que le test casse quand la limite change.
    """
    return "\n".join(f"ligne {i} " + "x" * largeur for i in range(nombre))


# 7.1 Le découpage


def test_un_texte_court_ne_donne_qu_un_message():
    assert notifier.decouper("un titre\nun lien") == ["un titre\nun lien"]


def test_le_decoupage_ne_perd_aucun_caractere():
    # La propriété qui compte : recoller les messages redonne le texte exact. Un
    # découpage qui perdrait un caractère enverrait un bulletin amputé, et la
    # ligne de statut dirait quand même que tout est parti.
    texte = texte_de(60)
    assert "\n".join(notifier.decouper(texte)) == texte


def test_aucun_message_ne_depasse_la_limite():
    messages = notifier.decouper(texte_de(60))
    assert len(messages) > 1
    assert all(len(message) <= notifier.LIMITE_MESSAGE for message in messages)


def test_un_message_peut_atteindre_la_limite_sans_la_depasser():
    # Le cas limite est le vrai piège : Discord refuse 2001 caractères, il accepte
    # 2000. Compter la ligne et son retour à la ligne ferait perdre ce message et
    # le suivant, donc une fiche entière, tous les jours.
    limite = notifier.LIMITE_MESSAGE
    assert len(notifier.decouper("x" * limite)[0]) == limite
    assert len(notifier.decouper("y" * (limite - 1) + "\n" + "z" * limite)) == 2


def test_la_coupe_tombe_entre_deux_lignes_et_non_dans_une():
    # Une coupure au milieu d'un champ laisserait « Domaines : » sans sa valeur,
    # sans qu'aucune ligne dise que le texte est incomplet.
    texte = texte_de(60)
    lignes = set(texte.split("\n"))
    for message in notifier.decouper(texte)[:-1]:
        assert all(partie in lignes for partie in message.split("\n"))


def test_une_ligne_plus_longue_que_la_limite_est_debitee():
    # Mesuré sur le registre du 28 septembre 2026, la ligne la plus longue fait
    # 375 caractères : ce cas n'arrive pas aujourd'hui. Il est traité quand même,
    # parce qu'un titre de trois mille caractères ne serait pas refusé par le
    # programme : il produirait un message que Discord refuse, et tout le
    # bulletin partirait avec.
    texte = "z" * (notifier.LIMITE_MESSAGE * 2 + 7)
    messages = notifier.decouper(texte)
    assert len(messages) == 3
    assert all(len(message) <= notifier.LIMITE_MESSAGE for message in messages)
    # Aucun caractère perdu. Les coupures deviennent des fins de message, donc
    # le texte se recolle sans les séparateurs.
    assert "".join(messages) == texte


def test_le_plafond_de_messages_est_un_plafond_et_son_reste_est_compte():
    texte = texte_de(200)
    tous = notifier.decouper(texte)
    messages, manques = notifier.messages_discord(texte, maximum=2)
    assert messages == tous[:2]
    assert manques == len(tous) - 2


def test_un_bulletin_qui_tient_ne_signale_rien_manquant():
    messages, manques = notifier.messages_discord(texte_de(10))
    assert len(messages) == 1
    assert manques == 0


# 7.2 L'envoi


def test_l_envoi_poste_le_bulletin_entier(faux_http):
    bulletin = rendue(notifier.NOUVELLE)
    assert notifier.envoyer_discord([bulletin.texte], WEBHOOK, transport=faux_http) == 1
    assert faux_http.appels[0]["json"] == {"content": bulletin.texte}


def test_l_envoi_passe_sur_l_url_du_webhook_et_avec_le_delai_du_scraper(faux_http):
    notifier.envoyer_discord(["un message"], WEBHOOK, transport=faux_http)
    appel = faux_http.appels[0]
    assert appel["url"] == WEBHOOK
    # Le même délai que la collecte et que l'email : un canal lent doit bloquer la
    # veille le temps d'une collecte, pas la nuit entière.
    assert appel["timeout"] == notifier.DELAI_SECONDES


def test_il_y_a_autant_de_requetes_que_de_messages(faux_http, dormeuse):
    envoyes = notifier.envoyer_discord(
        ["un", "deux", "trois"], WEBHOOK, transport=faux_http, dormeur=dormeuse
    )
    assert envoyes == 3
    assert len(faux_http.appels) == 3


def test_la_reponse_est_verifiee_sur_chaque_message(faux_http):
    # Une propriété du faux, pas une exception forgée : ce qui est vérifié est
    # que le programme appelle la vérification, pas qu'une exception existe
    # quelque part dans le test.
    notifier.envoyer_discord(["un", "deux"], WEBHOOK, transport=faux_http)
    verifications = [r.verifications for r in faux_http.reponses]
    assert verifications == [1, 1]


def test_un_webhook_supprime_est_une_erreur_et_non_un_envoi_reussi(faux_http):
    # La bibliothèque HTTP ne lève pas sur un 404. Sans `raise_for_status`, un
    # webhook supprimé depuis les paramètres du salon se lirait comme un envoi
    # réussi, tous les jours, en silence.
    def faux(url, json=None, timeout=None, params=None):
        return FauxReponse(erreur=OSError("404 Client Error"))

    with pytest.raises(OSError):
        notifier.envoyer_discord(["un message"], WEBHOOK, transport=faux)


def test_discord_doit_confirmer_l_envoi_avant_qu_on_le_dise_reussi(faux_http):
    # La documentation de Discord, sur l'end-point `Execute Webhook`, dit que
    # `wait` vaut `false` par défaut et qu'alors « a message that is not saved
    # does not return an error ». La réponse est un 204 que la vérification
    # d'erreur laisse passer. Sans `wait`, un message que Discord refuse
    # d'enregistrer se lirait « 1 message envoyé » alors que le salon est vide :
    # c'est précisément ce que la ligne de statut ne doit pas pouvoir dire.
    notifier.envoyer_discord(["un message"], WEBHOOK, transport=faux_http)
    assert faux_http.appels[0]["params"] == {"wait": "true"}


# 7.3 La pause, lue dans les en-têtes et non écrite en dur


def test_une_pause_seulement_si_discord_annonce_que_le_seau_est_vide(dormeuse):
    notifier.envoyer_discord(
        ["un", "deux"], WEBHOOK, transport=FauxHTTP(), dormeur=dormeuse
    )
    assert dormeuse.dures == []


def test_un_seau_vide_provoque_une_pause_de_la_duree_annoncee(dormeuse):
    # La documentation de Discord demande de lire les en-têtes et de ne pas
    # écrire la limite en dur. Un test qui attendrait une seconde fixe prouverait
    # au contraire que la limite est écrite en dur.
    notifier.envoyer_discord(
        ["un", "deux"],
        WEBHOOK,
        transport=FauxHTTP(restant="0", reset="0.4"),
        dormeur=dormeuse,
    )
    assert dormeuse.dures == [0.4]


def test_le_plafond_d_attente_limite_une_duree_aberrante(dormeuse):
    # Une durée de dix minutes dépasserait le plafond de trente minutes du job,
    # et le run serait tué en ayant déjà notifié la moitié du bulletin.
    notifier.envoyer_discord(
        ["un", "deux"],
        WEBHOOK,
        transport=FauxHTTP(restant="0", reset="600"),
        dormeur=dormeuse,
    )
    assert dormeuse.dures == [notifier.ATTENTE_MAX]


def test_une_duree_illisible_vaut_une_seconde(dormeuse):
    notifier.envoyer_discord(
        ["un", "deux"],
        WEBHOOK,
        transport=FauxHTTP(restant="0", reset="dans un instant"),
        dormeur=dormeuse,
    )
    assert dormeuse.dures == [1.0]


def test_une_duree_negative_ne_fait_pas_dormir(dormeuse):
    # `max(..., 0.0)` : dormir d'une durée négative lèverait, et l'exception
    # lèverait depuis la conversion et non depuis le réseau.
    notifier.envoyer_discord(
        ["un", "deux"],
        WEBHOOK,
        transport=FauxHTTP(restant="0", reset="-3"),
        dormeur=dormeuse,
    )
    assert dormeuse.dures == [0.0]


def test_aucune_pause_apres_le_dernier_message(dormeuse):
    # Le dernier message n'a personne derrière lui, donc l'attendre ne sert à
    # rien : une pause de trop coûterait une seconde par jour, pour rien.
    notifier.envoyer_discord(
        ["un", "deux", "trois"],
        WEBHOOK,
        transport=FauxHTTP(restant="0", reset="1"),
        dormeur=dormeuse,
    )
    assert len(dormeuse.dures) == 2


# 7.4 Ce que dit la ligne de statut


def test_console_seule_n_estdit_qu_avec_aucun_canal_configure(
    monkeypatch, faux_http, faux_smtp, dormeuse
):
    # La phrase « console seule » est vraie tant que rien n'est sorti. Dès que
    # l'un des deux canaux a envoyé, elle serait fausse, et la ligne dirait dans
    # la même phrase que rien n'est parti et qu'un message est parti.
    monkeypatch.setenv(notifier.VARIABLE_DISCORD, WEBHOOK)
    ligne = notifier.publier(rendue(notifier.NOUVELLE), faux_smtp, faux_http, dormeuse)
    assert "console seule" not in ligne
    assert "email non configuré" in ligne
    assert "Discord, 1 message envoyé" in ligne


def test_sans_secret_discord_le_programme_le_dit(monkeypatch, faux_http, faux_smtp, dormeuse):
    for nom in notifier.VARIABLES:
        monkeypatch.setenv(nom, VALEURS[nom])
    ligne = notifier.publier(rendue(notifier.NOUVELLE), faux_smtp, faux_http, dormeuse)
    assert "Discord non configuré" in ligne
    # Aucune requête : une variable absente ne doit rien déclencher.
    assert faux_http.appels == []


def test_un_secret_discord_vide_vaut_un_secret_absent(monkeypatch, faux_http, faux_smtp, dormeuse):
    # La même règle que pour l'email : un secret défini mais vide est un secret
    # absent. Le traiter autrement ferait poster vers une URL tronquée.
    monkeypatch.setenv(notifier.VARIABLE_DISCORD, "   ")
    ligne = notifier.publier(rendue(notifier.NOUVELLE), faux_smtp, faux_http, dormeuse)
    assert "Discord non configuré" in ligne
    assert faux_http.appels == []


def test_le_compte_de_messages_va_au_singulier(monkeypatch, faux_http, faux_smtp, dormeuse):
    for nom in notifier.VARIABLES:
        monkeypatch.setenv(nom, VALEURS[nom])
    monkeypatch.setenv(notifier.VARIABLE_DISCORD, WEBHOOK)
    ligne = notifier.publier(rendue(notifier.NOUVELLE), faux_smtp, faux_http, dormeuse)
    assert "Discord, 1 message envoyé" in ligne


def test_un_bulletin_trop_long_pour_le_salon_le_dit(monkeypatch, faux_http, faux_smtp, dormeuse):
    # Le plafond existe pour le cas où le bulletin est plus long que ce qu'un
    # salon supporte. Ce qui ne rentre pas n'est pas perdu — le résumé d'étape
    # recopie la section entière — mais il doit être dit, sinon le dernier
    # message s'arrête au milieu d'une fiche sans que rien ne le signale.
    for nom in notifier.VARIABLES:
        monkeypatch.setenv(nom, VALEURS[nom])
    monkeypatch.setenv(notifier.VARIABLE_DISCORD, WEBHOOK)
    texte = texte_de(200)
    total = len(notifier.decouper(texte))
    assert total > notifier.MESSAGES_MAX

    ligne = notifier.publier(
        notifier.Bulletin(texte, 0, 0, QUAND), faux_smtp, faux_http, dormeuse
    )
    assert f"Discord, {notifier.MESSAGES_MAX} messages envoyés" in ligne
    reste = total - notifier.MESSAGES_MAX
    assert f"{reste} messages de plus dans le résumé du run" in ligne
    assert len(faux_http.appels) == notifier.MESSAGES_MAX


def test_un_discord_qui_echoue_ne_coute_pas_la_veille(monkeypatch, capsys):
    monkeypatch.setenv(notifier.VARIABLE_DISCORD, WEBHOOK)

    def casse(url, json=None, timeout=None, params=None):
        raise OSError("Connexion réinitialisée")

    ligne = notifier.publier(rendue(notifier.NOUVELLE), transport_http=casse)
    assert "Discord non envoyé (OSError)" in ligne
    assert "la veille est complète" in ligne
    # Le bulletin a quand même été affiché : l'étudiant a la veille, même si
    # elle n'a pas pu partir.
    assert "Master A" in capsys.readouterr().out


def test_les_deux_canaux_sont_tentes_meme_si_le_premier_echoue(
    monkeypatch, faux_http, dormeuse
):
    # C'est le cas de l'étudiant qui n'a pas su créer le mot de passe
    # d'application : son serveur de messagerie est cassé, et le bulletin doit
    # quand même partir sur l'autre canal.
    for nom in notifier.VARIABLES:
        monkeypatch.setenv(nom, VALEURS[nom])
    monkeypatch.setenv(notifier.VARIABLE_DISCORD, WEBHOOK)

    def casse(*args, **kwargs):
        raise OSError("Connexion réinitialisée")

    ligne = notifier.publier(rendue(notifier.NOUVELLE), casse, faux_http, dormeuse)
    assert "email non envoyé (OSError)" in ligne
    assert "Discord, 1 message envoyé" in ligne
    assert len(faux_http.appels) == 1


def test_une_faute_de_code_ne_se_deguise_pas_en_probleme_de_reseau_non_plus(
    monkeypatch, faux_smtp, dormeuse
):
    for nom in notifier.VARIABLES:
        monkeypatch.setenv(nom, VALEURS[nom])
    monkeypatch.setenv(notifier.VARIABLE_DISCORD, WEBHOOK)

    def casse(url, json=None, timeout=None, params=None):
        raise NameError("VARIABLE_DISCORD")

    ligne = notifier.publier(
        rendue(notifier.NOUVELLE), faux_smtp, casse, dormeuse
    )
    assert "Discord non envoyé (NameError)" in ligne
    # L'email a réussi, et le test le vérifie : sans lui, une fonction qui lève
    # pour les deux canaux ferait passer le test pour la mauvaise raison.
    assert "email envoyé" in ligne


def test_la_veille_complete_n_est_ajoutee_qu_apres_un_echec(
    monkeypatch, faux_http, faux_smtp, dormeuse
):
    # « la veille est complète » dirait qu'une notification prouve que la
    # collecte a réussi. C'est faux : la ligne ne parle que des envois, et la
    # collecte est terminée depuis bien avant.
    for nom in notifier.VARIABLES:
        monkeypatch.setenv(nom, VALEURS[nom])
    monkeypatch.setenv(notifier.VARIABLE_DISCORD, WEBHOOK)
    ligne = notifier.publier(rendue(notifier.NOUVELLE), faux_smtp, faux_http, dormeuse)
    assert "non envoyé" not in ligne
    assert "la veille est complète" not in ligne


if __name__ == "__main__":
    pytest.main([__file__])

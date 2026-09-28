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

Trois choses sont testées séparément, et c'est le découpage qui rend le module
testable :

* `rendre` produit le texte, et ne dépend que de la V0.5 ;
* `message` produit les en-têtes et le corps, et ne dépend que du texte ;
* `envoyer` fait le transport, et ne dépend que du message.
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
    ligne = notifier.publier(rendue(notifier.NOUVELLE))
    sortie = capsys.readouterr().out
    assert "Master A" in sortie
    # La ligne nomme la variable manquante : « console seule » sans dire
    # laquelle est un rapport d'échec qui ne sert à rien.
    assert ligne.startswith("Notification : console seule")
    assert "SMTP_HOST" in ligne


def test_avec_secret_la_ligne_confirme_le_destinataire(monkeypatch, faux_smtp, capsys):
    for nom in notifier.VARIABLES:
        monkeypatch.setenv(nom, VALEURS[nom])
    ligne = notifier.publier(rendue(notifier.NOUVELLE), faux_smtp)
    assert ligne == "Notification : email envoyé à etudiant@outlook.com"
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


if __name__ == "__main__":
    pytest.main([__file__])

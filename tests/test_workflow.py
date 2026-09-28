"""Tests du workflow : .github/workflows/veille.yml

Le workflow est le seul fichier du projet qu'on ne peut pas lancer chez soi. Une
faute dedans ne se voit pas au développement : elle se révèle à 07:00 UTC, dans
le navigateur, sans personne devant. Ces tests relisent le YAML et vérifient
les invariants dont dépend le fonctionnement quotidien.

Ils ne vérifient pas la syntaxe, que fait le validateur de GitHub lui-même, mais
les choix écrits, qui sont ceux qu'on casse par mégarde en éditant le fichier.
"""

import re
from pathlib import Path

import pytest
import yaml

import main
import notifier
from scraper import Recolte, SourceLue, TIMEOUT_SECONDS

CHEMIN = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "veille.yml"


@pytest.fixture(scope="module")
def workflow():
    # `True` est la clé : YAML 1.1 lit `on` comme le booléen vrai. C'est une
    # particularité de PyYAML, pas du workflow, que GitHub lit correctement.
    brut = yaml.safe_load(CHEMIN.read_text(encoding="utf-8"))
    return brut


@pytest.fixture(scope="module")
def declenchements(workflow):
    return workflow[True] if True in workflow else workflow["on"]


@pytest.fixture(scope="module")
def job(workflow):
    return workflow["jobs"]["veille"]


@pytest.fixture(scope="module")
def etapes(job):
    return {etape["name"]: etape for etape in job["steps"] if "name" in etape}


# 1. Ce qui fait que les données survivent au run


def test_le_run_a_le_droit_d_ecrire(job):
    # Sans cela, `git push` échoue et la veille est perdue, chaque jour. Le
    # défaut d'un dépôt peut être en lecture seule, il ne faut pas compter
    # dessus.
    assert job["permissions"]["contents"] == "write"


def test_le_droit_d_ecrire_est_donne_a_un_seul_job(workflow):
    # La permission est au niveau du job, pas du workflow : un jour où un second
    # job de lecture serait ajouté, il n'hériterait pas du droit de pousser.
    for nom, autre in workflow["jobs"].items():
        if nom != "veille":
            assert "write" not in autre.get("permissions", {}), nom


def test_les_donnees_sont_versionnees(etapes):
    assert "Enregistrer les résultats" in etapes
    bloc = etapes["Enregistrer les résultats"]["run"]
    assert "git add -A data/" in bloc
    assert "git commit" in bloc
    assert "git push" in bloc


def test_rien_ne_bouge_ne_produit_pas_de_commit(etapes):
    # C'est une propriété de `storage.a_change` que le workflow exploite. Si on
    # retire la garde, la veille produit un commit par jour quoi qu'il arrive, et
    # l'historique du dépôt cesse d'avoir un sens.
    bloc = etapes["Enregistrer les résultats"]["run"]
    assert "git diff --cached --quiet -- data/" in bloc


def test_un_push_concurrent_ne_ecrase_pas_de_commit(etapes):
    bloc = etapes["Enregistrer les résultats"]["run"]
    assert "git pull --rebase" in bloc
    assert "--force" not in bloc and "-f " not in bloc


def test_la_branche_vient_du_contexte_pas_d_une_chaine_ecrite(etapes):
    # Une branche écrite en dur dans le workflow cassera le jour du premier fork
    # ou du premier changement de branche par défaut.
    bloc = etapes["Enregistrer les résultats"]["run"]
    assert "${{ github.ref_name }}" in bloc
    assert "origin main" not in bloc and "origin master" not in bloc


# 2. Ce qui fait que le résultat est lisible


def test_les_tests_passent_avant_la_veille(etapes, job):
    noms = [etape["name"] for etape in job["steps"] if "name" in etape]
    assert noms.index("Vérifier que le code tient") < noms.index("Lancer la veille")


def test_une_veille_en_echec_ne_passe_pas_pour_un_succes(etapes):
    # `python src/main.py | tee` renvoie le code de `tee`, toujours zéro. Sans
    # `pipefail`, une veille en échec committerait quand même le fichier.
    assert "set -o pipefail" in etapes["Lancer la veille"]["run"]


def test_le_resume_est_produit_meme_si_la_veille_echoue(etapes):
    # `always()` : sinon le résumé disparaît précisément quand on en a le plus
    # besoin, c'est-à-dire quand la veille n'a pas produit de résultat.
    assert etapes["Résumé de la veille"]["if"] == "always()"


def test_les_motifs_du_message_ne_contiennent_pas_d_accent(etapes):
    # Un motif accentué dépend de la locale du runner. Sur une locale non UTF-8,
    # il ne trouve rien, et le message de commit devient vide sans erreur. Les
    # motifs retenus sont donc des extraits sans accent.
    bloc = etapes["Enregistrer les résultats"]["run"]
    for motif in (
        "correspondent au profil",
        "nouvelles depuis",
        "dans data/",
        "Rien de nouveau",
    ):
        assert motif.isascii()
        assert motif in bloc


def test_le_resume_recopie_la_section_a_signaler(etapes):
    # C'est le résultat de la V0.5. Sans cette section, le run automatique
    # affiche « 0 nouvelles depuis la dernière exécution » et l'étudiant doit
    # ouvrir le journal pour savoir ce qui a été trouvé.
    resume = etapes["Résumé de la veille"]["run"]
    assert "signaler ===" in resume
    assert "Sauvegarde ===" in resume
    assert "GITHUB_STEP_SUMMARY" in resume


def test_les_ancres_de_la_section_sont_en_ascii(etapes):
    # Même raison que les motifs de grep : une ancre accentuée ne trouve rien
    # sur une locale non UTF-8, et le résumé serait vide sans erreur.
    resume = etapes["Résumé de la veille"]["run"]
    for ancre in ("signaler ===", "Sauvegarde ==="):
        assert ancre.isascii()
        assert ancre in resume


def test_le_resume_ne_echoue_pas_sans_journal(etapes):
    # L'étape s'exécute aussi quand la veille a échoué, donc quand journal.txt
    # n'existe pas. Sans `|| true`, l'échec de `sed` ferait échouer le résumé,
    # qui existe justement pour dire que la veille n'a rien produit.
    resume = etapes["Résumé de la veille"]["run"]
    sed = [ligne for ligne in resume.split("\n") if "sed -n" in ligne]
    assert len(sed) == 1
    assert sed[0].rstrip().endswith("|| true")


# 3. Le planning, qui est une décision et non un réglage


def test_la_collecte_est_quotidienne(declenchements):
    assert declenchements["schedule"] == [{"cron": "0 7 * * *"}]


def test_le_declenchement_a_la_demande_est_possible(declenchements):
    # Indispensable pour vérifier un changement sur un vrai run, et pour rattraper
    # un jour où l'exécution planifiée a échoué.
    assert "workflow_dispatch" in declenchements


def test_deux_executions_ne_se_marchent_pas_dessus(workflow):
    assert workflow["concurrency"]["cancel-in-progress"] is False


def test_l_historique_complet_est_recupere(etapes):
    # `git pull --rebase` refuse un dépôt superficiel, et la profondeur par
    # défaut de `actions/checkout` est de 1.
    assert etapes["Récupérer le dépôt"]["with"]["fetch-depth"] == 0


# Le délai après lequel GitHub abandonne un job. C'est le défaut de la
# plateforme, recopié ici pour que l'assertion dise pourquoi la valeur du
# workflow est acceptable, et pas seulement qu'elle existe.
PLAFORD_PAR_DEFAUT = 360

# Marge exigée entre le plafond du job et le délai d'une seule requête réseau.
# Vingt fois 30 secondes font 10 minutes : le programme garde de la place pour
# les requêtes lentes et pour l'installation, tout en restant loin du plafond
# de la plateforme. La marge est dérivée de TIMEOUT_SECONDS et non écrite en dur,
# pour que le test suive le code si ce délai change un jour.
MARGE_SUR_UNE_REQUETE = 20


def test_le_job_a_un_plaford_d_execution(job):
    # Sans plafond, un run bloqué reste en cours pendant les 360 minutes du
    # défaut de GitHub. Ce job en met dix-sept secondes : un run qui dure des
    # heures est cassé, et le dire tot évite une nuit d'attente pour rien.
    plafond = job["timeout-minutes"]
    # GitHub refuse une valeur décimale, donc le type est aussi une contrainte
    # de validité du workflow, pas seulement une commodité de test.
    assert isinstance(plafond, int) and not isinstance(plafond, bool)
    assert 0 < plafond < PLAFORD_PAR_DEFAUT, plafond


def test_le_plaford_ne_tombe_pas_pendant_une_collecte_normale(job):
    # Le programme est déjà borné requête par requête, donc le plafond du job ne
    # doit jamais tomber pendant une collecte dont un seul site est lent. La
    # veille sur les sources actuelles tient en 17,5 secondes, et le pire cas du
    # réseau reste quelques minutes même si tous les sites répondent mal.
    plafond = job["timeout-minutes"]
    assert plafond * 60 > MARGE_SUR_UNE_REQUETE * TIMEOUT_SECONDS


# 4. La notification, qui ne se voit pas sans le navigateur

# Ces tests lisent `notifier.VARIABLES` au lieu de recopier la liste. C'est le
# seul moyen d'attraper le cas qui fait le dégât : renommer une variable dans
# `notifier.py` sans toucher au workflow. Aucun test ne le verrait, parce que les
# deux fichiers resteraient valides, et le résultat serait un email qui ne part
# jamais, en silence, tous les jours.


def test_les_variables_du_code_sont_toutes_dans_le_workflow(etapes):
    # Un secret en plus dans le workflow ne sert à rien, un secret en moins fait
    # que l'envoi n'est jamais tenté, et le programme ne dit que la console.
    assert set(etapes["Lancer la veille"]["env"]) == set(notifier.VARIABLES)


def test_chaque_secret_est_lue_dans_les_secrets_du_depot(etapes):
    # `${{ secrets.X }}` et non la valeur : une valeur écrite dans le YAML serait
    # dans le dépôt, donc publique, et versionnée.
    env = etapes["Lancer la veille"]["env"]
    for nom in notifier.VARIABLES:
        assert env[nom] == "${{ secrets." + nom + " }}"


def test_le_mot_de_passe_n_est_jamais_dans_la_commande(etapes):
    # Passer par `env` n'est pas une préférence de style. Le masquage de GitHub
    # remplace la valeur dans le journal quand elle apparaît telle quelle, mais
    # pas une valeur que le shell reconstitue, ni un caractère interprété. Dans
    # `env`, la valeur n'est jamais écrite dans le run.
    commande = etapes["Lancer la veille"]["run"]
    for nom in notifier.VARIABLES:
        assert nom not in commande


def test_le_resume_dit_si_l_email_est_parti(etapes):
    # C'est la seule trace qu'un run automatique a notifié, ou qu'il a tenté et
    # échoué. Sans elle, un mot de passe expiré se voit exactement comme un jour
    # sans nouveau.
    assert "Notification" in etapes["Résumé de la veille"]["run"]


def test_le_message_de_commit_reste_en_une_ligne(etapes):
    # Le commit se lit dans une liste de commits. Y mettre le statut de
    # l'email allongerait chaque ligne de la page d'accueil du dépôt pour dire
    # la même chose que le résumé d'étape.
    assert "Notification" not in etapes["Enregistrer les résultats"]["run"]


# 5. Le rapport par source, dont la seule trace lisible est le résumé d'étape


def motif_du_grep(etapes, etape="Résumé de la veille"):
    """L'alternation du `grep` de l'étape, telle qu'écrite dans le YAML.

    C'est l'alternation qui est lue, et non le texte de l'étape : un
    commentaire qui mentionne un motif est légitime, et le faire échouer
    obligerait à supprimer une phrase utile pour satisfaire un test.
    """
    ligne = [l for l in etapes[etape]["run"].split("\n") if "grep -aE" in l]
    assert len(ligne) == 1, f"{etape} doit avoir un seul grep de motifs"
    return ligne[0].split("'")[1]


def test_le_resume_recopie_le_rapport_par_source(etapes):
    # Sans ce motif, le rapport par source n'apparaît que dans le journal, et le
    # résumé d'étape afficherait « 69 opportunités trouvées » sans dire d'où
    # elles viennent. C'est le défaut que la V0.7 corrige, et sa correction doit
    # se voir à l'endroit que l'étudiant regarde en premier.
    assert "^Source" in motif_du_grep(etapes)


def test_le_motif_du_rapport_est_en_ascii(etapes):
    # Un motif accentué ne trouve rien sur un runner réglé dans une locale qui
    # n'est pas UTF-8, et une recherche sans résultat ne se voit pas. Le préfixe
    # écrit par `main.display_sources` est en ASCII justement pour cela.
    assert motif_du_grep(etapes).isascii()


def test_le_motif_du_rapport_est_ancre(etapes):
    # Ancré, sinon un titre d'opportunité qui contiendrait le mot serait recopié
    # dans le résumé. Aucune autre ligne du journal ne commence par « Source » :
    # les fiches sont numérotées, le profil commence par ses clés de section, et
    # le bulletin par « Academic Watch ».
    assert "^Source" in motif_du_grep(etapes).split("|")


def test_le_motif_recopie_exactement_ce_que_main_ecrit(etapes, capsys):
    # Le motif et le journal sont deux fichiers : ils peuvent diverger sans
    # qu'aucun des deux soit invalide, et le résumé se contente alors d'être
    # vide, en silence, comme avant la V0.7. On produit donc les trois lignes
    # que `main` écrit et on leur applique le motif extrait du workflow.
    main.display_sources(
        Recolte([], [SourceLue("Alpha", 0), SourceLue("Beta", 36)], 10)
    )
    lignes = [l for l in capsys.readouterr().out.split("\n") if l.strip()]
    assert len(lignes) == 3, lignes
    motif = re.compile(motif_du_grep(etapes))
    for ligne in lignes:
        assert motif.search(ligne), ligne


def test_une_panne_est_recopiee_une_fois_et_son_detail_pas(etapes, capsys):
    # La règle qui tient le résumé d'étape : une ligne `^Source` par source, et
    # rien d'autre. Le détail d'une panne est indenté, donc le motif ne le prend
    # pas — et il ne doit pas le prendre, le détail se lit dans le journal.
    #
    # Ce test existait déjà sans la panne, et il ne l'aurait pas vue : les trois
    # lignes de `display_sources` passaient toutes le motif, et rien ne
    # signalait qu'une quatrième, identique, pouvait en être copiée deux fois.
    main.display_sources(
        Recolte(
            [],
            [
                SourceLue("Alpha", 10),
                SourceLue("Beta", 0, "ConnectionError", "hôte exemple.test"),
                SourceLue("Gamma", 0),
            ],
            12,
        )
    )
    lignes = [l for l in capsys.readouterr().out.split("\n") if l.strip()]
    rapport = [l for l in lignes if l.startswith("Source")]
    details = [l for l in lignes if not l.startswith("Source")]

    assert rapport == [
        "Source Alpha : 10 opportunités extraites",
        "Source Beta : lecture impossible (ConnectionError)",
        "Source Gamma : aucun bloc trouvé",
        "Sources sans sélecteurs : 12 activées et non lues, voir docs/SOURCES.md §8.",
    ], rapport
    assert details == ["   ConnectionError : hôte exemple.test"], details

    motif = re.compile(motif_du_grep(etapes))
    for ligne in rapport:
        assert motif.search(ligne), ligne
    for ligne in details:
        assert not motif.search(ligne), ligne


def test_le_message_de_commit_ne_recopie_pas_le_rapport(etapes):
    # Un commit par jour qui porterait quatre lignes de compte de sources
    # encombrerait l'historique de `data/` sans rien apprendre de plus. Le
    # rapport est dans le résumé d'étape, lu une fois ; l'historique est lu en
    # permanence.
    assert "Source" not in motif_du_grep(etapes, "Enregistrer les résultats")

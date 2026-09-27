"""Tests du workflow : .github/workflows/veille.yml

Le workflow est le seul fichier du projet qu'on ne peut pas lancer chez soi. Une
faute dedans ne se voit pas au développement : elle se révèle à 07:00 UTC, dans
le navigateur, sans personne devant. Ces tests relisent le YAML et vérifient
les invariants dont dépend le fonctionnement quotidien.

Ils ne vérifient pas la syntaxe, que fait le validateur de GitHub lui-même, mais
les choix écrits, qui sont ceux qu'on casse par mégarde en éditant le fichier.
"""

from pathlib import Path

import pytest
import yaml

import notifier

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

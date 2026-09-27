"""Tests du workflow : .github/workflows/veille.yml

Le workflow est le seul fichier du projet qu'on ne peut pas lancer chez soi. Une
faute dedans ne se voit pas au developpement : elle se revele a 07:00 UTC, dans
le navigateur, sans personne devant. Ces tests relisent le YAML et verifient les
invariants dont depend le fonctionnement quotidien.

Ils ne verifient pas la syntaxe, que fait le validateur de GitHub lui-meme, mais
les choix ecrits, qui sont ceux qu'on casse par megarde en editant le fichier.
"""

from pathlib import Path

import pytest
import yaml

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
    # Sans cela, `git push` echoue et la veille est perdue, chaque jour. Le
    # defaut d'un depot peut etre en lecture seule, il ne faut pas compter
    # dessus.
    assert job["permissions"]["contents"] == "write"


def test_le_droit_d_ecrire_est_donne_a_un_seul_job(workflow):
    # La permission est au niveau du job, pas du workflow : un jour où un second
    # job de lecture serait ajoute, il n'hriterait pas du droit de pousser.
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
    # `python src/main.py | tee` renvoie le code de `tee`, toujours zero. Sans
    # `pipefail`, une veille en echec committerait quand meme le fichier.
    assert "set -o pipefail" in etapes["Lancer la veille"]["run"]


def test_le_resume_est_produit_meme_si_la_veille_echoue(etapes):
    # `always()` : sinon le resume disparait precisement quand on en a le plus
    # besoin, c'est-a-dire quand la veille n'a pas produit de resultat.
    assert etapes["Résumé de la veille"]["if"] == "always()"


def test_les_motifs_du_message_ne_contiennent_pas_d_accent(etapes):
    # Un motif accentué dépend de la locale du runner. Sur une locale non UTF-8,
    # il ne trouve rien, et le message de commit devient vide sans erreur. Les
    # motifs retenus sont donc des extraits sans accent.
    bloc = etapes["Enregistrer les résultats"]["run"]
    for motif in ("correspondent au profil", "nouvelles depuis", "dans data/"):
        assert motif.isascii()
        assert motif in bloc


# 3. Le planning, qui est une décision et non un réglage


def test_la_collecte_est_quotidienne(declenchements):
    assert declenchements["schedule"] == [{"cron": "0 7 * * *"}]


def test_le_declenchement_a_la_demande_est_possible(declenchements):
    # Indispensable pour vérifier un changement sur un vrai run, et pour rattraper
    # un jour ou l'execution planifiee a echoue.
    assert "workflow_dispatch" in declenchements


def test_deux_executions_ne_se_marchent_pas_dessus(workflow):
    assert workflow["concurrency"]["cancel-in-progress"] is False


def test_l_historique_complet_est_recupere(etapes):
    # `git pull --rebase` refuse un depot superficiel, et la profondeur par
    # defaut de `actions/checkout` est de 1.
    assert etapes["Récupérer le dépôt"]["with"]["fetch-depth"] == 0

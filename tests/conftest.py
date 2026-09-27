"""Fixtures partagées par les tests.

La fixture `sandbox` existe, et la fixture automatique qui l'accompagne existe
pour une raison précise : `storage` écrit dans `data/` par defaut. Un test
qui oublie d'affecter les chemins de module, ou écrit directement, écrase
les vraies données du dépôt. Ce n'est pas un risque théorique, c'est le genre
d'accident qui n'apparaît qu'après un commit, quand le fichier a déjà changé.

La redirection est donc automatique et appliquée à tous les tests, sans
exception. Un test qui veut écrire ailleurs n'a rien à demander.
"""

import pytest

import storage


@pytest.fixture(autouse=True)
def _dossier_de_donnees_isole(tmp_path, monkeypatch):
    """Redirige l'écriture de `storage` vers un dossier à elle.

    `monkeypatch` remet les chemins d'origine à la fin du test, donc l'ordre des
    tests n'a pas d'importance et aucun ne peut voir les données d'un autre.
    """
    monkeypatch.setattr(storage, "OPPORTUNITES", tmp_path / "opportunities.json")
    monkeypatch.setattr(storage, "VUS", tmp_path / "seen.json")


@pytest.fixture
def sandbox(tmp_path):
    """Le dossier de données du test en cours, isolé du dépôt."""
    return tmp_path

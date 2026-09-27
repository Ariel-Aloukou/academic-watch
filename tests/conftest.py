"""Fixtures partagées par les tests.

La fixture `sandbox` existe, et la fixture automatique qui l'accompagne existe
pour une raison précise : `storage` écrit dans `data/` par defaut. Un test
qui oublie d'affecter les chemins de module, ou écrit directement, écrase
les vraies données du dépôt. Ce n'est pas un risque théorique, c'est le genre
d'accident qui n'apparaît qu'après un commit, quand le fichier a déjà changé.

La redirection est donc automatique et appliquée à tous les tests, sans
exception. Un test qui veut écrire ailleurs n'a rien à demander.

La seconde fixture automatique empêche les tests de joindre un serveur. La règle
du projet est qu'aucun test ne parle au réseau, et elle ne tenait qu'à la
relecture : la V0.6 a introduit un envoi d'email, donc une couture par laquelle
un test pouvait se retrouver à appeler le vrai serveur d'Outlook. Le garde-fou
rend la règle mécanique, et il s'applique à tous les tests, pas seulement à ceux
qui parlent de messagerie.
"""

import socket

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


@pytest.fixture(autouse=True)
def _reseau_coupe(monkeypatch):
    """Refuse toute connexion sortante, pour tous les tests.

    Trois points sont bouchés, parce que trois chemins mènent au réseau :
    `getaddrinfo` transforme un nom en adresse, et c'est déjà une requête au
    résolveur ; `connect` ouvre le canal ; `create_connection` fait les deux et
    c'est par là que passe `smtplib`. En bloquer un seul laisserait passer les
    deux autres.

    L'erreur dit ce qu'elle est : un test qui la rencontre sait qu'il a voulu
    joindre un serveur, et non que la machine est en panne.
    """

    def refuse(*args, **kwargs):
        raise AssertionError(
            "un test ne doit pas joindre un serveur ; "
            "injecte un faux, par exemple avec l'argument `transport` de notifier"
        )

    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)


@pytest.fixture
def sandbox(tmp_path):
    """Le dossier de données du test en cours, isolé du dépôt."""
    return tmp_path

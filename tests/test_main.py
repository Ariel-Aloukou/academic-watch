"""Tests de l'orchestration : src/main.py (docs/VERSIONS.md V0.6).

`main()` est la seule fonction qui collecte, donc la seule qui touche au
réseau. Ces tests la rendent inoffensive à deux endroits : la collecte et
l'évaluation sont simulées, et `conftest` redirige les chemins d'écriture de
`storage` vers un dossier à elle. Aucun de ces tests ne contacte une page,
aucun n'écrit dans `data/`, et aucun n'envoie d'email — `publier` est remplacé
ici, donc un run sur GitHub où les secrets seraient présents ne pourrait pas
partir depuis un test.

Ce qui est testé n'est pas le rendu, il est dans `tests/test_notifier.py`, mais
l'ordre des étapes et le contrat entre elles : qui reçoit quoi, et dans quel
ordre. L'ordre est une décision de la V0.6 et non un détail d'écriture.
Publier avant de mémoriser une opportunité comme vue est ce qui empêche qu'une
se perde quand l'envoi échoue ; l'inverse empêcherait qu'une soit annoncée deux
fois. Aucune des deux propriétés ne se voit dans la sortie, donc il faut les
regarder ailleurs.
"""

import pytest

import main
import storage
from models import Opportunity


def opportunite(titre, diplome="Master of Science"):
    """Une vraie `Opportunity`, avec les sept champs que `identite` lit.

    Une vraie classe et non une fabrique de tests : `identite` se sert de la
    source, du titre et du diplôme, donc une classe à trois champs ferait échouer
    le test pour une raison qui n'a rien à voir avec l'orchestration.
    """
    return Opportunity(
        title=titre,
        university="Universite A",
        country="Germany",
        degree=diplome,
        field="Cybersecurity",
        url=f"https://exemple/{titre.replace(' ', '-')}",
        source="Source A",
    )


def evaluation(resultats):
    """Une évaluation, telle que `evaluer` la rend : un dictionnaire.

    Elle est simulée parce que `matches.py` a ses propres tests et que le
    profile réel n'est pas ce qu'on teste ici. Les sept clés sont présentes,
    parce que `main()` les recopie une par une sur l'opportunité.
    """

    def evaluer(opportunity, profile):
        score, matched = resultats[opportunity.title]
        return {
            "score": score,
            "score_max": 100.0,
            "type": "programs",
            "matched": matched,
            "reasons": ["domaine direct"] if matched else [],
        }

    return evaluer


def lancer(monkeypatch, resultats, *opportunites):
    """Lance `main()` sur une collecte simulée, et rend l'ordre des étapes.

    Chaque étape est enregistrée avec ce qu'elle a reçu, donc un test peut lire
    le bulletin tel que `main` l'a construit. `publier` se contente d'imprimer
    le texte qu'il reçoit : c'est la part de `main`, et l'email est testé dans
    `tests/test_notifier.py`.
    """
    etapes = []
    vrai_sauvegarder = main.sauvegarder

    def sauvegarder(opportunities):
        etapes.append(("sauvegarder", opportunities))
        return vrai_sauvegarder(opportunities)

    def publier(bulletin):
        etapes.append(("publier", bulletin))
        print(bulletin.texte)

    def memoriser(retenues):
        etapes.append(("memoire", retenues))
        return []

    monkeypatch.setattr(main, "collect_opportunities", lambda: list(opportunites))
    monkeypatch.setattr(main, "evaluer", evaluation(resultats))
    monkeypatch.setattr(main, "sauvegarder", sauvegarder)
    monkeypatch.setattr(main, "publier", publier)
    monkeypatch.setattr(main, "conserver_vus", memoriser)
    main.main()
    return etapes


def noms(etapes):
    return [nom for nom, _ in etapes]


def bulletin_de(etapes):
    return next(valeur for nom, valeur in etapes if nom == "publier")


# Ce que la V0.5 décide, et que la V0.6 ne doit pas redécider.


def test_le_bulletin_ne_contient_que_les_retenues(monkeypatch):
    # Une veille est une sélection, pas un catalogue. Les opportunités qui ne
    # correspondent pas au profil ne doivent pas apparaître dans le message,
    # même une fois.
    etapes = lancer(
        monkeypatch,
        {"Master retenu": (70, True), "Master ecarte": (10, False)},
        opportunite("Master retenu"),
        opportunite("Master ecarte"),
    )
    texte = bulletin_de(etapes).texte
    assert "Master retenu" in texte
    assert "Master ecarte" not in texte


def test_le_compte_du_bulletin_vient_des_deux_listes(monkeypatch):
    # Le total est ce qui a été collecté, les retenues ce qui correspond au
    # profil. Les confondre ferait annoncer « 2 correspondent » alors qu'une
    # seule compte, et le message serait faux d'une unité.
    etapes = lancer(
        monkeypatch,
        {"Master A": (70, True), "Master B": (20, False), "Master C": (70, True)},
        opportunite("Master A"),
        opportunite("Master B"),
        opportunite("Master C"),
    )
    assert "3 opportunités trouvées, 2 correspondent au profil" in bulletin_de(etapes).texte


def test_une_opportunite_signalee_ne_recoit_qu_une_etiquette(monkeypatch):
    # Si le disjoint des deux listes se perdait, une même fiche serait comptée
    # deux fois et le total affiché dépasserait le nombre d'opportunités.
    etapes = lancer(monkeypatch, {"Master A": (70, True)}, opportunite("Master A"))
    texte = bulletin_de(etapes).texte
    assert texte.count("[nouvelle]") + texte.count("[mise à jour]") == 1
    assert "1 à signaler : 1 nouvelle" in texte


def test_les_nouvelles_passent_avant_les_mises_a_jour(monkeypatch):
    # Le cas réel d'une mise à jour : la fiche existait, a été montrée, et sa
    # page a changé depuis. Le score fait partie de la fiche, donc le passer de
    # 70 à 85 suffit — c'est mesuré et écrit dans `storage.a_change`.
    vue = opportunite("Master vue")
    vue.score, vue.score_max, vue.matched = 70.0, 100.0, True
    storage.sauvegarder([vue])
    storage.conserver_vus([vue])

    # La collecte rend la modifiée avant la neuve : sans le remaniement de la
    # V0.5, la mise à jour sortirait en premier.
    etapes = lancer(
        monkeypatch,
        {"Master vue": (85, True), "Master neuve": (70, True)},
        opportunite("Master vue"),
        opportunite("Master neuve"),
    )
    texte = bulletin_de(etapes).texte
    assert "2 à signaler : 1 nouvelle, 1 mise à jour" in texte
    assert texte.index("Master neuve") < texte.index("Master vue")


# La décision d'ordre de la V0.6.


def test_publier_avant_de_memoriser_comme_vue(monkeypatch):
    # C'est l'invariant de la V0.6, et il ne se voit pas dans la sortie. À
    # l'inverse, un run qui s'arrêterait entre les deux aurait déjà marqué
    # l'opportunité comme vue alors que personne ne l'a lue : elle ne serait
    # plus jamais annoncée, et `seen.json` dirait le contraire.
    etapes = lancer(monkeypatch, {"Master A": (70, True)}, opportunite("Master A"))
    assert noms(etapes) == ["sauvegarder", "publier", "memoire"]


def test_les_retenues_memorisees_sont_les_retenues_signalees(monkeypatch):
    # Mémoriser plus large que le bulletin perdurait des opportunités, mémoriser
    # plus étroit les ferait ré-signaler. Les deux listes viennent des mêmes
    # retenues, jamais du signal affiché.
    etapes = lancer(
        monkeypatch,
        {"Master A": (70, True), "Master ecarte": (10, False)},
        opportunite("Master A"),
        opportunite("Master ecarte"),
    )
    memoire = next(valeur for nom, valeur in etapes if nom == "memoire")
    assert [o.title for o in memoire] == ["Master A"]


# Ce que le workflow relit dans le journal.


def test_la_section_sauvegarde_reste_affichee(monkeypatch, capsys):
    # Trois lignes, et le workflow en dépend : le chemin de l'historique, celui
    # du fichier de mémoire, et le compte des nouvelles depuis la dernière
    # exécution, qui est le motif du commit.
    lancer(monkeypatch, {"Master A": (70, True)}, opportunite("Master A"))
    sortie = capsys.readouterr().out
    assert "=== Sauvegarde ===" in sortie
    assert "opportunités enregistrées dans data/opportunities.json" in sortie
    assert "nouvelles depuis la dernière exécution" in sortie
    assert "opportunités déjà montrées, dans data/seen.json" in sortie


def test_les_sections_du_journal_restent_dans_l_ordre(monkeypatch, capsys):
    # Le résumé d'étape du workflow extrait la section « À signaler » avec un
    # `sed` qui s'arrête à « Sauvegarde ». Si l'ordre changeait, l'extraction
    # prendrait le mauvais bloc, silencieusement.
    lancer(monkeypatch, {"Master A": (70, True)}, opportunite("Master A"))
    sortie = capsys.readouterr().out
    assert sortie.index("=== Profil de recherche ===") < sortie.index("Academic Watch")
    assert sortie.index("Academic Watch") < sortie.index("=== À signaler ===")
    assert sortie.index("=== À signaler ===") < sortie.index("=== Sauvegarde ===")


if __name__ == "__main__":
    pytest.main([__file__])

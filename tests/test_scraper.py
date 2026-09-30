"""Tests de la collecte : src/scraper.py (docs/VERSIONS.md V0.7).

Ce fichier est le premier du projet qui parle de `scraper.py`. Le module fait
plus de 440 lignes, extrait 69 opportunités et alimente toute la veille, et
aucun test ne l'atteignait : rien ne garantissait qu'une source qui cesse de
répondre serait signalée, ni qu'une faute de configuration dans `config/` ne
ferait pas tomber la collecte entière. Le manque est comblé en même temps que
la fonction, pas après.

## Ce qui est couvert, et ce qui ne l'est pas

Couvert ici : le contrat de `collect_opportunities`, c'est-à-dire ce qu'elle
rend et ce qu'elle fait quand une source échoue. C'est ce que la V0.7 a changé.

Non couvert : `test_source` et `classify`, qui n'ont rien à voir avec la V0.7 et
appartiennent à un autre travail. Ils touchent le réseau, donc les tester
demanderait une seconde couture d'injection pour un module dont le reste
fonctionne, et dont les fonctions de mesure sont déjà vérifiées à la main et
écrites dans `docs/SOURCES.md` §5. Ne pas les couvrir ici est un reste à faire
assumé, pas un oubli : les écrire dans ce fichier ferait croire que le module
entier est testé, et il ne l'est pas.

`fetch_page` était dans cette liste jusqu'à la V0.13, qui l'a corrigé : il rendait
`response.text`, qui suit l'en-tête `Content-Type` et non la page. Un défaut qui
se voyait à l'œil sur une page réelle et qui n'était pas testé, alors même que
la couture existait déjà — voir la section 3 plus bas.

## Aucun test ne touche au réseau

`fetch_page` est remplacé dans chaque test qui appelle `collect_opportunities`.
Ce n'est pas une précaution de style : la fixture automatique de `conftest.py`
bouche `socket.getaddrinfo`, donc une source laissée réelle lèverait une
`AssertionError` — que `collect_opportunities` rattrape comme une coupure de
réseau, puisque toutes les exceptions sont rattrappées. Le rapport serait un
rapport de pannes et le test passerait quand même, pour la mauvaise raison. Un
test qui passe pour la mauvaise raison est pire qu'un test absent, et c'est
exactement ce que vérifie `test_une_source_non_simulee_est_bloquee`.
"""

import pytest
import requests

import scraper
from scraper import Recolte, SourceLue


def source(nom, **extra):
    """Une source simulée, avec le jeu de sélecteurs le plus simple possible.

    Un seul bloc par programme, un titre et un lien : c'est le strict minimum
    qu'une source doit publier, donc le strict minimum qu'un test doit fournir.
    Les sélecteurs sont volontairement différents de ceux des quatre sources
    réelles : un test qui marche avec les sélecteurs de TUM ne prouverait pas
    que `build_opportunity` est générique, il prouverait qu'il connaît TUM.
    """
    return {
        "name": nom,
        "university": "Universite A",
        "country": "Germany",
        "type": "programs",
        "url": f"https://exemple.test/{nom}",
        "base_url": "https://exemple.test",
        "selectors": {
            "item": "div.carte",
            "title": "h2",
            "url": "a",
        },
        **extra,
    }


def html(nombre, avec_lien=True):
    """Une page qui contient `nombre` blocs de programme.

    `avec_lien=False` produit des blocs que `build_opportunity` doit écarter :
    un programme sans lien ne peut être ni vérifié ni cliqué, et cette raison
    est écrite dans docs/SOURCES.md §8.1.
    """
    lien = "<a href='/fiche'>voir</a>" if avec_lien else ""
    corps = "".join(
        f"<div class='carte'><h2>Master {i}</h2>{lien}</div>" for i in range(1, nombre + 1)
    )
    return f"<html><body>{corps}</body></html>"


# La page Scholarship de KAIST, réduite à ce que le parseur lit. Deux bourses,
# dont la première prend son nom dans le titre de la page : c'est le cas que
# `kaist_scholarship.parse` traite à part, et le donner tel quel évite d'écrire
# un second HTML qui ne prouverait rien de plus.
PAGE_BOURSES = """<div class="board_wrap">
  <h2>KAIST Scholarships</h2>
  <p></p>
  <ul>
    <li><span>Admission Periods:</span><span>Spring 2027</span></li>
    <li><span>Benefits:</span><span>Full tuition coverage</span></li>
  </ul>
  <p>KAIST Global Presidential Scholarship</p>
  <ul>
    <li><span>Admission Periods:</span><span>Fall 2027</span></li>
    <li><span>Benefits:</span><span>Monthly stipend of 1,000,000 KRW</span></li>
  </ul>
</div>"""


def installer(monkeypatch, sources, activees=None, pages=None):
    """Remplace le registre et le téléchargement par des valeurs simulées.

    `sources` est la liste des sources que la collecte croira actives.
    `activees` est la liste des sources que le registre dira activées, et sert
    au compte `sans_selecteurs` : par défaut, les mêmes, donc zéro. `pages`
    associe un fragment d'URL à son HTML ; une source absente de `pages` reçoit
    une page vide, ce qui produit 0 opportunité.
    """
    pages = pages or {}

    def faux_fetch(url):
        for fragment, contenu in pages.items():
            if fragment in url:
                return contenu
        return "<html><body></body></html>"

    monkeypatch.setattr(scraper, "load_active_sources", lambda: list(sources))
    monkeypatch.setattr(
        scraper,
        "load_enabled_sources",
        lambda: list(sources if activees is None else activees),
    )
    monkeypatch.setattr(scraper, "fetch_page", faux_fetch)


def recolte_de(monkeypatch, sources, **kwargs):
    """Installe le registre simulé, collecte, et rend la `Recolte`."""
    installer(monkeypatch, sources, **kwargs)
    return scraper.collect_opportunities()


def par_nom(recolte):
    return {lue.nom: lue for lue in recolte.sources}


# 1. Ce que la collecte rend


def test_la_collecte_rend_les_fiches_et_le_rapport(monkeypatch):
    # Avant la V0.7, la fonction rendait une liste et n'avait aucun mot à dire
    # sur sa provenance. C'était le défaut : le journal ne nommait aucune
    # source, donc « 69 opportunités » se lisait pareil selon que les quatre
    # sources marchaient ou qu'aucune ne marchait plus.
    recolte = recolte_de(monkeypatch, [source("Alpha")], pages={"Alpha": html(2)})
    assert isinstance(recolte, Recolte)
    assert [o.title for o in recolte.opportunities] == ["Master 1", "Master 2"]
    assert [lue.nom for lue in recolte.sources] == ["Alpha"]
    assert recolte.sources[0].nombre == 2
    assert recolte.sources[0].erreur == ""


def test_le_compte_par_source_suit_les_fiches_reellement_produites(monkeypatch):
    # Le compte est mesuré sur la liste renvoyée, pas compté à part. Les deux
    # pourraient diverger : un compteur qui afficherait 3 pour 2 fiches ferait
    # croire que la veille en a trouvé une de plus qu'il n'y en a, et rien ne
    # le rattraperait plus tard.
    recolte = recolte_de(
        monkeypatch,
        [source("Alpha"), source("Beta")],
        pages={"Alpha": html(3), "Beta": html(1)},
    )
    assert {lue.nom: lue.nombre for lue in recolte.sources} == {"Alpha": 3, "Beta": 1}
    assert len(recolte.opportunities) == 4


def test_une_source_vide_est_ecrite_avec_un_compte_de_zero(monkeypatch):
    # Le cas qui ne se voyait pas avant. Zéro n'est pas une absence
    # d'information : c'est la mesure qui distingue une page lue sans contenu
    # d'une page injoignable, et les deux se réparent dans deux fichiers
    # différents.
    recolte = recolte_de(monkeypatch, [source("Alpha")], pages={"Alpha": html(0)})
    assert recolte.opportunities == []
    assert recolte.sources[0].nombre == 0
    assert recolte.sources[0].erreur == ""
    assert recolte.sources[0].silencieuse is True


def test_les_blocs_sans_lien_donnent_aussi_zero(monkeypatch):
    # Deux zéros de causes différentes, et les deux sont des pannes. Le rapport
    # ne les distingue pas — il n'a pas de quoi — donc il ne doit pas inventer
    # une raison : le compte est 0, sans cause, et c'est ce que le bulletin
    # écrit. La distinction est dans docs/SOURCES.md §8.1, pas dans le rapport.
    recolte = recolte_de(
        monkeypatch, [source("Alpha")], pages={"Alpha": html(2, avec_lien=False)}
    )
    assert recolte.sources[0].nombre == 0
    assert recolte.sources[0].erreur == ""


def test_une_source_sans_fiches_n_est_pas_une_erreur(monkeypatch, capsys):
    # Une source qui répond n'est pas une panne : rien ne doit être écrit
    # comme une erreur, sinon le journal mélangerait « lecture impossible » et
    # « la page ne contenait rien » sous le même mot.
    recolte_de(monkeypatch, [source("Alpha")], pages={"Alpha": html(0)})
    assert "lecture impossible" not in capsys.readouterr().out


def test_une_source_sans_bloc_elle_meme_est_comptee(monkeypatch):
    # Un conteneur absent n'est pas une erreur non plus. Le parseur de KAIST
    # renvoie une liste vide dans ce cas, et c'est le compte qui doit le dire.
    bourse = source(
        "Beta", parser="kaist_scholarship", selectors={"container": ".absent"}
    )
    recolte = recolte_de(monkeypatch, [bourse], pages={"Beta": PAGE_BOURSES})
    assert par_nom(recolte)["Beta"].nombre == 0
    assert par_nom(recolte)["Beta"].erreur == ""


# 2. Une source qui échoue n'arrête pas les autres


def test_une_coupure_de_reseau_est_nommee_sans_tuer_la_veille(monkeypatch):
    # Le réseau tombe pour une source, pas pour les autres. C'est le cas le plus
    # banal, et avant la V0.7 il se traduisait par 68 fiches au lieu de 69 et
    # rien d'autre : l'étudiant lisait un total plausible et ne pouvait pas savoir
    # qu'il manquait une source.
    installer(monkeypatch, [source("Alpha"), source("Beta")], pages={"Beta": html(1)})

    def fetch_rompu(url):
        if "Alpha" in url:
            raise requests.ConnectionError("connexion réinitialisée")
        return html(1)

    monkeypatch.setattr(scraper, "fetch_page", fetch_rompu)

    recolte = scraper.collect_opportunities()
    assert par_nom(recolte)["Alpha"].nombre == 0
    assert par_nom(recolte)["Alpha"].erreur == "ConnectionError"
    # Beta a été lue malgré l'échec d'Alpha, et ses fiches sont là.
    assert par_nom(recolte)["Beta"].nombre == 1
    assert [o.title for o in recolte.opportunities] == ["Master 1"]


def test_un_parseur_absent_ne_tue_plus_la_veille(monkeypatch):
    # Une faute de configuration, pas une panne de réseau. Un nom de `parser`
    # sans module dans `src/parsers/` levait `ModuleNotFoundError`, qui n'est pas
    # une `RequestException` : elle remontait, et les 68 fiches des trois autres
    # sources tombaient avec elle. Les deux se réparent dans deux fichiers
    # différents, donc il faut pouvoir les distinguer.
    recolte = recolte_de(monkeypatch, [source("Alpha", parser="parseur_absent")])
    assert recolte.sources[0].erreur == "ModuleNotFoundError"
    assert recolte.sources[0].nombre == 0


def test_un_bloc_de_selecteurs_incomplet_ne_tue_plus_la_veille(monkeypatch):
    # Clé `item` absente : `parse_source` lève `KeyError`. Même raison que
    # ci-dessus, et la distinction se voit dans le rapport : `KeyError` se lit,
    # il ne se confond pas avec un site hors service.
    incomplete = source("Alpha")
    del incomplete["selectors"]["item"]
    recolte = recolte_de(
        monkeypatch, [incomplete, source("Beta")], pages={"Beta": html(2)}
    )
    assert par_nom(recolte)["Alpha"].erreur == "KeyError"
    assert par_nom(recolte)["Beta"].nombre == 2


def test_le_type_de_l_erreur_est_copie_dans_le_rapport(monkeypatch):
    # Le type, et non le message. Le message d'une `requests` contient l'hôte,
    # le port et le chemin de l'URL, il fait 250 caractères, et il n'intéresse
    # pas l'étudiant : ce qui l'intéresse est de savoir si le site est tombé ou
    # si la configuration est fausse.
    installer(monkeypatch, [source("Alpha")])

    def fetch_rompu(url):
        raise requests.Timeout("délai dépassé")

    monkeypatch.setattr(scraper, "fetch_page", fetch_rompu)
    recolte = scraper.collect_opportunities()
    assert recolte.sources[0].erreur == "Timeout"
    assert "délai" not in recolte.sources[0].erreur


def test_la_collecte_n_ecrit_rien_elle_rend_la_panne(monkeypatch, capsys):
    # Un seul endroit écrit le rapport, donc celui-ci se tait. Avant cette
    # version, il écrivait la panne et `main.display_sources` l'écrivait aussi :
    # le journal la disait deux fois, et le motif `^Source` du workflow la
    # reprenait deux fois dans le résumé d'étape.
    #
    # Un écrivain de trop se prouve en vérifiant qu'il se tait, pas en
    # vérifiant ce qu'il écrit. Ce test ne peut pas passer pour la mauvaise
    # raison : il n'a qu'une assertion, et elle est négative.
    installer(monkeypatch, [source("Alpha")])

    def fetch_rompu(url):
        raise requests.ConnectionError("hôte exemple.test introuvable")

    monkeypatch.setattr(scraper, "fetch_page", fetch_rompu)
    recolte = scraper.collect_opportunities()
    assert capsys.readouterr().out == ""
    # La panne n'est pas perdue pour autant : elle est rendue, message complet
    # compris, et c'est `display_sources` qui l'écrit.
    assert recolte.sources[0].erreur == "ConnectionError"
    assert "hôte exemple.test introuvable" in recolte.sources[0].detail


def test_une_faute_de_configuration_ne_se_lit_pas_comme_une_panne(monkeypatch, capsys):
    # Le journal nomme le type de l'exception, donc une `KeyError` ne se lit
    # pas comme une coupure de réseau. C'est la même règle que celle que
    # `notifier.publier` applique à l'envoi d'email, appliquée ici à la collecte.
    installer(monkeypatch, [source("Alpha")])

    def fetch_rompu(url):
        raise KeyError("item")

    monkeypatch.setattr(scraper, "fetch_page", fetch_rompu)
    assert scraper.collect_opportunities().sources[0].erreur == "KeyError"


# 3. Les sources activées et jamais lues


def test_les_sources_sans_selecteurs_sont_comptees(monkeypatch):
    # Sur le registre réel, 12 sources sont activées et n'ont pas de bloc dans
    # `config/selectors.json`. Ce n'est pas une panne : c'est ce qui permet
    # d'inscrire une source au cahier des charges avant de savoir la lire. Mais
    # sans ce compte, elles sont indiscernables d'une source qui ne répond plus,
    # et c'est la confusion que la V0.7 corrige.
    recolte = recolte_de(
        monkeypatch,
        [source("Alpha")],
        activees=[source("Alpha")] + [source(f"Non lue {i}") for i in range(12)],
        pages={"Alpha": html(1)},
    )
    assert recolte.sans_selecteurs == 12


def test_le_compte_des_sources_non_lues_vaut_zero_quand_toutes_sont_lues(monkeypatch):
    recolte = recolte_de(monkeypatch, [source("Alpha")], pages={"Alpha": html(1)})
    assert recolte.sans_selecteurs == 0


# 4. Le format, qui est la propriété que la V0.7 demande


def test_les_deux_strategies_de_lecture_produisent_le_meme_format(monkeypatch):
    # C'est l'invariant central de la V0.7 : une source de plus ne doit rien
    # changer en aval. Les sources d'aujourd'hui se lisent de deux façons — par
    # sélecteurs CSS, ou par le parseur dédié de la page Scholarship de KAIST —
    # et les deux doivent rendre des `Opportunity` interchangeables. Si elles
    # divergeaient, ajouter une source obligerait à modifier `matches.py`, ce
    # que la version interdit.
    generique = recolte_de(
        monkeypatch, [source("Alpha")], pages={"Alpha": html(2)}
    ).opportunities

    bourse = source(
        "KAIST - Scholarship",
        type="scholarships",
        parser="kaist_scholarship",
        selectors={"container": ".board_wrap"},
    )
    dedie = scraper.parse_source(PAGE_BOURSES, bourse)

    assert len(generique) == 2
    assert len(dedie) == 2
    assert {type(o) for o in generique} == {type(o) for o in dedie}
    # Le même modèle, donc les mêmes champs disponibles pour `matches.py`, sans
    # que celui-ci ait à savoir d'où viennent les fiches.
    assert set(generique[0].__dataclass_fields__) == set(dedie[0].__dataclass_fields__)


def test_une_source_de_plus_ne_change_ni_les_autres(monkeypatch):
    # Le registre croît, les résultats des sources déjà là ne bougent pas. Sans
    # cette propriété, la veille n'aurait qu'à ajouter une source pour que les
    # 69 fiches d'aujourd'hui changent de contenu, et personne ne verrait quelle
    # source en est responsable.
    premier = recolte_de(
        monkeypatch, [source("Alpha")], pages={"Alpha": html(2)}
    ).opportunities
    second = recolte_de(
        monkeypatch,
        [source("Alpha"), source("Beta")],
        pages={"Alpha": html(2), "Beta": html(1)},
    ).opportunities

    assert [o.title for o in second[:2]] == [o.title for o in premier]
    assert len(second) == 3


# 5. Le garde-fou réseau, qui attrape aussi les tests oublieux


def test_une_source_non_simulee_est_bloquee_par_le_garde_fou(monkeypatch):
    # Ce test ne teste pas `scraper`, il teste la suite de tests. Comme toutes
    # les exceptions sont rattrapees, une source laissée réelle ne ferait pas
    # échouer le test : `requests` lèverait sur le garde-fou de `conftest.py`,
    # l'erreur serait notée comme une coupure, et le test passerait avec un
    # rapport de pannes. Sans cette vérification, un test oublié de faux
    # téléchargement deviendrait un test vert qui ne teste rien.
    monkeypatch.setattr(scraper, "load_active_sources", lambda: [source("Reelle")])
    monkeypatch.setattr(scraper, "load_enabled_sources", lambda: [source("Reelle")])

    recolte = scraper.collect_opportunities()
    # Ce n'est pas le site qui a répondu : c'est la fixture de `conftest.py`.
    assert recolte.sources[0].erreur == "AssertionError"
    assert recolte.opportunities == []


def test_silencieuse_ne_vaut_que_zero():
    # La condition est nommée parce que deux modules l'utilisent, le journal et
    # le bulletin. Si elle incluait autre chose que zéro, l'un des deux
    # afficherait une source qui a très bien produit.
    assert SourceLue("A", 0).silencieuse is True
    assert SourceLue("A", 1).silencieuse is False
    assert SourceLue("A", 0, "ConnectionError").silencieuse is True


# 3. Le jeu de caractères d'une page
#
# `fetch_page` rendait `response.text`, qui ne lit pas la page : il suit
# l'en-tête `Content-Type`, et pour un `text/html` sans charset il retombe sur
# ISO-8859-1. Les trois pages de studyinjapan.go.jp sont dans ce cas, et leur
# texte arrivait en charabia, montants compris.
#
# Le défaut était invisible parce que les 14 autres sources actives déclarent
# leur charset dans l'en-tête. Une source qui marche masque la source qui ne
# marche pas.
#
# Ces tests ne touchent pas au réseau : la couture est `scraper.requests.get`,
# la même que celle utilisée plus haut pour remplacer `fetch_page`.

# L'en-tête exact que studyinjapan.go.jp renvoie pour ses trois pages, mesuré le
# 29 septembre 2026 : `text/html`, sans charset, alors que la page en déclare un.
ENTETE_SANS_CHARSET = "text/html"


class ReponseFactice:
    """Ce que `fetch_page` utilise d'une réponse : statut, en-têtes, octets."""

    def __init__(self, content_type, content, status=200):
        self.headers = {"Content-Type": content_type} if content_type else {}
        self.content = content
        self.status_code = status
        self.encoding = None

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def reponse(monkeypatch, content_type, content, status=200):
    """Fait répondre `requests.get` par une réponse faite main."""
    factice = ReponseFactice(content_type, content, status)
    monkeypatch.setattr(scraper.requests, "get", lambda *a, **k: factice)
    return factice


def test_le_jeu_de_l_entete_l_emporte_sur_celui_de_la_page():
    # Un serveur qui déclare sait ce qu'il a envoyé : sa déclaration passe
    # avant celle du document, même si le document en porte une autre.
    octets = b"<meta charset='utf-8'><p>Master</p>"
    assert scraper.nom_du_jeu_de_caracteres("text/html; charset=windows-1252", octets) == "windows-1252"


def test_sans_charset_dans_l_entete_la_declaration_de_la_page_est_suivie():
    # Le cas mesuré sur studyinjapan.go.jp.
    octets = b"<html><head><meta charset='UTF-8'></head><body><p>x</p>"
    assert scraper.nom_du_jeu_de_caracteres(ENTETE_SANS_CHARSET, octets) == "utf-8"


def test_sans_une_seule_declaration_utf8_est_retenu():
    assert scraper.nom_du_jeu_de_caracteres("text/html", b"<p>Master</p>") == "utf-8"
    assert scraper.nom_du_jeu_de_caracteres("", b"<p>Master</p>") == "utf-8"


def test_suivre_la_page_ce_nest_pas_deviner_utf8():
    # La distinction qui compte, et que le cas précédent ne voit pas : une page
    # peut déclarer autre chose que UTF-8. Un repli sur « utf-8 » au lieu de
    # « la déclaration » donnerait la même réponse ici, et une page Latin-1
    # serait alors jugée illisible alors qu'elle est parfaitement lisible.
    #
    # Ce test a été ajouté après une épreuve de mutations : il manquait, et la
    # mutation « plus de repli sur la déclaration » passait la suite entière.
    octets = "<meta charset='iso-8859-1'><p>café</p>".encode("iso-8859-1")
    assert scraper.nom_du_jeu_de_caracteres("text/html", octets) == "iso-8859-1"


def test_suivre_la_page_ce_nest_pas_lire_au_dela_de_la_fenetre():
    # Symétrique du précédent, trouvé par la même épreuve. Une fenêtre trop
    # courte ferait ignorer une page qui déclare son jeu à 100 octets, c'est-à-dire
    # normalement ; le test suivant ne le verrait pas, il ne verrait qu'un repli
    # qui fonctionne.
    declaration_normale = b"<p>" + b"x" * 100 + b"<meta charset='iso-8859-1'>"
    assert scraper.nom_du_jeu_de_caracteres("text/html", declaration_normale) == "iso-8859-1"


def test_une_declaration_tardive_ne_compte_pas():
    # La spécification du HTML réserve les 2048 premiers octets à cette
    # recherche. Une déclaration plus loin peut venir d'un commentaire, et la
    # prendre reviendrait à croire une phrase qui n'est pas une declaration.
    tardive = b"<p>" + b"x" * 3000 + b"<meta charset='iso-8859-1'>"
    assert scraper.nom_du_jeu_de_caracteres("text/html", tardive) == "utf-8"


def test_une_page_sans_charset_dans_l_entete_est_lue_sans_charabia(monkeypatch):
    # La non-regression du défaut. L'octet 0xC2 suivi de 0xA5 est le yen : lu
    # en Latin-1 il devient deux caractères accentués, et le montant passe de
    # « ¥143,000 » à « Â¥143,000 » sans lever la moindre erreur.
    octets = "<p>\u00a5143,000 par mois</p>".encode("utf-8")
    reponse(monkeypatch, ENTETE_SANS_CHARSET, octets)

    html = scraper.fetch_page("https://exemple.test/")

    assert "\u00a5143,000" in html
    assert "\u00c2" not in html, "la page a ete relue en Latin-1"


def test_le_jeu_de_l_entete_gagne_quand_la_page_en_declare_un_autre(monkeypatch):
    # Le cas de 14 sources actives. Leur résultat doit être inchangé, sinon le
    # correctif aurait cassé ce qui marche pour réparer ce qui ne marche pas.
    octets = "caf\u00e9".encode("utf-8")
    reponse(monkeypatch, "text/html; charset=utf-8", b"<meta charset='windows-1252'>" + octets)

    assert scraper.fetch_page("https://exemple.test/").count("caf\u00e9") == 1


def test_le_decodage_est_strict_et_nomme_le_jeu_dans_son_erreur(monkeypatch):
    # `response.text` aurait remplacé l'octet douteux par U+FFFD et rendu une
    # page à moitie lisible, sans rien dire. Ici la source est signalée, et le
    # message nomme le jeu : sans lui, un octet douteux se confond avec une
    # panne réseau et la source disparaît sans trace.
    reponse(monkeypatch, "text/html; charset=utf-8", b"<p>caf\xe9</p>")

    with pytest.raises(ValueError) as echec:
        scraper.fetch_page("https://exemple.test/")

    assert "utf-8" in str(echec.value)


@pytest.mark.parametrize(
    "content_type, octets, jeu",
    [
        # Des octets invalides pour le jeu annonce.
        ("text/html; charset=utf-8", b"<p>caf\xe9</p>", "utf-8"),
        # Un jeu que Python ne connait pas. `nom_du_jeu_de_caracteres` le rend
        # tel quel, volontairement : c'est le decodage qui doit dire qu'il est
        # inutilisable, pas une liste de noms devinette a l'avance.
        ("text/html; charset=latin-9-inconnu", b"<p>Master</p>", "latin-9-inconnu"),
    ],
)
def test_les_deux_causes_d_echec_ont_le_meme_forme(monkeypatch, content_type, octets, jeu):
    # `collect_opportunities` enregistre le type de l'exception, pas son texte.
    # Deux causes qui lèvent deux types différents inscriraient deux pannes
    # distinctes dans le journal alors que c'est la même : la page est
    # illisible. Une seule forme, et un message qui commence par nommer le jeu
    # retenu.
    #
    # Le test vérifie aussi que l'erreur n'est *pas* l'exception d'origine.
    # `UnicodeDecodeError` hérite de `ValueError`, donc `pytest.raises(ValueError)`
    # passerait aussi sans le `from erreur` : c'est le préfixe du message qui
    # distingue les deux.
    reponse(monkeypatch, content_type, octets)

    with pytest.raises(ValueError) as echec:
        scraper.fetch_page("https://exemple.test/")

    message = str(echec.value)
    assert message.startswith("page illisible en " + jeu), message
    assert not isinstance(echec.value, (LookupError, UnicodeDecodeError))


def test_une_page_lu_ne_contient_jamais_de_caractere_de_remplacement(monkeypatch):
    # Propriete, pas un cas : quelle que soit la page, aucun U+FFFD ne doit
    # atteindre `data/`. C'est la consequence de la strictesse, et elle se
    # verifie sur plusieurs encodages, pas sur un seul.
    pages = [
        ("text/html; charset=utf-8", "Master in \u00c9lectronique".encode("utf-8")),
        ("text/html; charset=windows-1252", "Master in \u00c9lectronique".encode("windows-1252")),
        (ENTETE_SANS_CHARSET, "<p>\u4e2d\u6587</p>".encode("utf-8")),
    ]
    for content_type, octets in pages:
        reponse(monkeypatch, content_type, octets)
        assert "\ufffd" not in scraper.fetch_page("https://exemple.test/")


def test_un_erreur_http_est_relayee_avant_toute_decodage(monkeypatch):
    # L'ordre compte : un 412 sur une page illisible doit dire 412, pas
    # « page illisible ». Le code HTTP est le fait le plus utile.
    reponse(monkeypatch, "text/html; charset=utf-8", b"<p>caf\xe9</p>", status=412)

    with pytest.raises(requests.HTTPError):
        scraper.fetch_page("https://exemple.test/")


if __name__ == "__main__":
    pytest.main([__file__])

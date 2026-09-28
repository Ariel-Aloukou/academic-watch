"""Collecte des opportunités sur les sources définies dans docs/SOURCES.md.

Deux fichiers de configuration travaillent ensemble :

* config/sources.json    le registre des sources retenues (le cahier des
  charges). Il porte l'intention : quelles sources font partie de la veille.
* config/selectors.json  les règles d'extraction. Il porte la technique : où
  se trouvent les informations dans le HTML.

Les deux sont séparés pour qu'une source puisse être décidée dans le registre
avant d'avoir ses sélecteurs écrits.

Ce module a deux rôles distincts :

* valider le registre, avec test_sources(), pour savoir si une URL est
  réellement lisible (voir docs/SOURCES.md §1) ;
* extraire les opportunités des sources qui le sont, avec
  collect_opportunities().

Et un troisième rôle, moins visible : dire ce que chaque source a apporté.
Il est né d'un défaut mesuré, décrit dans `collect_opportunities`.

La correspondance avec le profil arrive en V0.3 (matches.py), la sauvegarde
en V0.4 (storage.py), voir docs/VERSIONS.md.

Une source dont la structure ne s'exprime pas en sélecteurs CSS déclare un
"parser" dans config/selectors.json. Le module correspondant est alors
appelé à la place de la lecture générique ; c'est le cas de la page
Scholarship de KAIST. Voir src/parsers/kaist_scholarship.py.

Règle importante de docs/README.md §9 : une source doit être aussi fiable que
possible. On privilégie donc les sites officiels des universités.
"""

import importlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from models import Opportunity

# Chemins calculés depuis ce fichier pour fonctionner quel que soit le dossier
# depuis lequel le programme est lancé (localement ou via GitHub Actions).
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config"
REGISTRY_PATH = CONFIG_PATH / "sources.json"
PARSING_PATH = CONFIG_PATH / "selectors.json"
PROFILE_PATH = CONFIG_PATH / "profile.json"

# Délai maximal d'attente d'une source. Sans cela, une source lente bloque
# l'exécution complète du programme.
TIMEOUT_SECONDS = 30

# Certains sites refusent les requêtes sans navigateur identifiable.
USER_AGENT = "Mozilla/5.0 (compatible; AcademicWatch/0.2)"

# Signatures d'une page dont le contenu est construit par JavaScript. Si l'une
# d'elles est présente, le HTML téléchargé ne contient pas les résultats de
# recherche : le navigateur les injecte après le chargement.
JAVASCRIPT_MARKERS = ("__NUXT__", "__NEXT_DATA__", "data-reactroot", "ng-version")

# Codes HTTP qui signifient que le site a identifié l'automate et l'a bloqué,
# et non que la page est introuvable. La nuance compte : une source bloquée
# peut rester parfaitement exploitable pour un humain.
BLOCKED_CODES = (403, 412)

# Indice de la présence d'une liste d'opportunités : un lien vers une page de
# détail contient un mot-clé suivi d'un identifiant. L'identifiant n'est pas
# toujours dans le chemin : TUM place le sien dans le fragment, sous la forme
# /en/studies/detail/ai-in-biomedicine-msc#course-559. C'est un indicateur et
# non une preuve : le nombre affiché sert à orienter la lecture, pas à conclure
# seul.
DETAIL_LINK_PATTERN = re.compile(
    r"(detail|fiche|programmes?|scholarships?|bourses?)/\S*\d", re.IGNORECASE
)


class SourceLue(NamedTuple):
    """Ce qu'une source a donné pendant une collecte.

    Une source qui répond avec zéro opportunité, une source injoignable et une
    source dont la lecture a levé une erreur sont trois pannes différentes.
    Les traiter comme une seule les rendrait indiscernables, et c'est
    exactement le défaut que ce type corrige : avant lui, une source qui
    cessait de produire produisait un journal identique à celui d'une veille
    normale.

    Les deux champs d'erreur ne sont pas redondants, ils ont deux lecteurs :

    * `erreur` est le type de l'exception, « ConnectionError »,
      « ModuleNotFoundError », « KeyError ». C'est ce qui tient sur une ligne
      d'email, et c'est ce qui distingue une coupure de réseau d'une faute de
      configuration : les deux doivent se traiter différemment et sans que
      l'étudiant ait à ouvrir un journal pour le savoir ;
    * `detail` est le message complet, que `collect_opportunities` écrit dans
      le journal au moment où il a encore du sens. Le garder ici obligerait
      l'email à le porter, et il contient des détails internes — hôte, port,
      chemin de l'URL — qui n'intéressent pas l'étudiant.
    """

    nom: str
    nombre: int
    erreur: str = ""
    detail: str = ""

    @property
    def silencieuse(self):
        """Dit si la source n'a rien donné.

        La condition est nommée parce qu'elle est utilisée à deux endroits, le
        journal et le bulletin, et que « nombre == 0 » écrit deux fois
        finirait par diverger : l'un dirait « lecture impossible » et l'autre
        « aucun bloc trouvé », et les deux parleraient de la même panne.
        """
        return self.nombre == 0


class Recolte(NamedTuple):
    """Le résultat d'une collecte : les fiches, et ce que chaque source a donné.

    `opportunities` reste une liste d'`Opportunity`, exactement comme avant.
    C'est la propriété que la V0.7 demande : une source de plus produit le
    même format que les autres, donc rien en aval n'a à savoir qu'elle
    existe. `sources` est la partie nouvelle, et elle n'est lue par personne
    en aval non plus — elle sert au journal et au bulletin, donc à l'étudiant.

    `sans_selecteurs` compte les sources activées dans le registre et jamais
    lues, faute de bloc dans `config/selectors.json`. C'est un état normal et
    non une panne : une source est inscrite au cahier des charges avant de
    savoir la lire, c'est la raison d'être des deux fichiers de configuration.
    Le compter permet de le dire, et de ne pas le confondre avec une source
    qui ne répond plus.
    """

    opportunities: list
    sources: list
    sans_selecteurs: int = 0


def load_sources():
    """Retourne le registre des sources, tel que défini dans le cahier des charges."""
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["sources"]


def load_parsing_rules():
    """Retourne les règles d'extraction des sources effectivement implémentées."""
    return json.loads(PARSING_PATH.read_text(encoding="utf-8"))["sources"]


def load_enabled_sources():
    """Les sources du registre qui sont activées, qu'elles soient lisibles ou non.

    Séparée de `load_active_sources` parce que la V0.7 a besoin de compter les
    sources activées que la collecte n'a pas lues : sans ce nombre, une source
    inscrite et jamais implémentée est indiscernable d'une source qui ne répond
    plus.
    """
    return [source for source in load_sources() if source.get("enabled")]


def load_active_sources():
    """Croise le registre et les règles d'extraction.

    Une source n'est scrapée que si elle est active dans le registre ET qu'elle
    dispose de sélecteurs. Les sources sans sélecteurs sont donc ignorées sans
    provoquer d'erreur : c'est ce qui permet d'inscrire une source dans le
    cahier des charges avant de savoir la lire.

    L'ordre de la liste est celui de `config/selectors.json`, donc le rapport
    de collecte est le même d'un jour à l'autre. Un rapport qui changerait
    d'ordre à chaque exécution serait illisible, et le jour où deux sources
    portent le même nom de famille, on ne saurait plus laquelle est laquelle.
    """
    actives = {source["name"]: source for source in load_enabled_sources()}

    return [
        {**actives[regles["name"]], **regles}
        for regles in load_parsing_rules()
        if regles["name"] in actives
    ]


def load_profile_fields():
    """Retourne les domaines du profil, pour juger la pertinence d'une page.

    Une page est utile à la veille si elle parle des domaines étudiés, pas
    seulement si elle répond 200. La lecture est faite ici et non importée
    depuis main.py : main.py importe scraper.py, l'inverse créerait un cycle
    d'import.
    """
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    return profile["fields"]


def test_source(source, fields):
    """Teste une source et retourne uniquement ce qui a été mesuré.

    Contrairement à fetch_page, aucune erreur n'est masquée : un timeout, un
    403 ou un 412 sont des résultats, pas des accidents. Les signaler est
    exactement le rôle de ce test.
    """
    mesures = {
        "name": source["name"],
        "http": None,
        # Adresse finale après redirections : certaines sources redirigent
        # vers une URL de session, ce qui change la nature de la réponse.
        "url_finale": None,
        "ko": 0,
        "tables": 0,
        "selects_vides": 0,
        "liens_detail": 0,
        "champs_profil": [],
        "javascript": False,
        "erreur": None,
    }

    try:
        response = requests.get(
            source["url"],
            timeout=TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        )
    except requests.RequestException as error:
        mesures["erreur"] = str(error)
        return mesures

    mesures["http"] = response.status_code
    mesures["url_finale"] = response.url
    # Taille arrondie au Ko, car elle n'est affichée que pour comparer deux
    # sources entre elles.
    mesures["ko"] = round(len(response.content) / 1024)

    soup = BeautifulSoup(response.text, "html.parser")
    mesures["tables"] = len(soup.find_all("table"))
    # Un <select> sans <option> est la signature d'un menu rempli par
    # JavaScript : la requête HTTP ne reçoit que la coquille du formulaire.
    mesures["selects_vides"] = sum(
        1 for menu in soup.find_all("select") if not menu.find("option")
    )
    mesures["liens_detail"] = sum(
        1 for lien in soup.find_all("a", href=True)
        if DETAIL_LINK_PATTERN.search(lien["href"])
    )
    mesures["javascript"] = any(
        marqueur in response.text for marqueur in JAVASCRIPT_MARKERS
    )

    # Recherche des domaines du profil dans le texte visible, et non dans le
    # code source : une mention dans un script ne prouve rien pour l'étudiant.
    texte = soup.get_text(" ", strip=True).lower()
    mesures["champs_profil"] = [
        champ for champ in fields if champ.lower() in texte
    ]

    return mesures


def classify(mesures):
    """Déduit un verdict à partir des mesures.

    docs/SOURCES.md §1.1 : une page qui répond 200 n'est pas une source
    valide. Le statut HTTP ne suffit donc jamais à lui seul, c'est le cœur de
    ce test.
    """
    if mesures["erreur"] is not None:
        return "injoignable"
    if mesures["http"] in BLOCKED_CODES:
        return "bloque"
    if not 200 <= mesures["http"] < 300:
        return "injoignable"
    if mesures["javascript"] or mesures["selects_vides"]:
        return "javascript"
    if mesures["tables"] or mesures["liens_detail"]:
        return "exploitable"
    # La page répond et n'est pas en JavaScript, mais elle ne contient aucune
    # liste : c'est un index ou un formulaire de recherche, il faut descendre
    # dans ses sous-pages ou simuler la requête pour aller plus loin.
    return "a_tester"


def test_sources():
    """Teste une par une toutes les sources du registre et affiche le bilan.

    Le champ enabled est ignoré volontairement : le but est de découvrir
    lesquelles des sources inscrites au cahier des charges sont lisibles, y
    compris celles qui sont désactivées parce qu'elles ne le sont pas encore.
    """
    fields = load_profile_fields()
    sources = load_sources()
    # Le verdict mesure ce que contient la page, pas ce que le programme sait
    # faire. KAIST est ainsi classée a_tester alors qu'elle est déjà
    # implémentée : ses liens sont des sites de département, qui ne resemble
    # pas à des liens de fiche. On le signale pour que la lecture soit juste.
    regles = {source["name"] for source in load_parsing_rules()}

    print(f"Test de {len(sources)} sources declarees dans config/sources.json")
    print(f"Domaines du profil recherches : {', '.join(fields)}")
    print("Colonnes : tab = tableaux, sel = <select> vides (JavaScript)")
    print("Verdicts : exploitable = liste presente, a_tester = index ou")
    print("           formulaire a explorer, javascript = liste injectee,")
    print("           bloque = anti-robot, injoignable = pas de reponse")
    print("           [impl.] = selecteurs deja ecrits dans selectors.json\n")

    entete = (
        f"{'#':>2}  {'source':38} {'HTTP':>4} {'Ko':>5} {'tab':>3} "
        f"{'sel':>3} {'liens':>5} {'profil':>6}  verdict"
    )
    print(entete)
    print("-" * len(entete))

    verdicts = {}
    for numero, source in enumerate(sources, start=1):
        mesures = test_source(source, fields)
        brut = classify(mesures)
        # Le décompte final se fait sur le verdict brut : la mention
        # d'implémentation ne doit pas créer une catégorie supplémentaire.
        verdicts[brut] = verdicts.get(brut, 0) + 1
        verdict = f"{brut} [impl.]" if source["name"] in regles else brut

        # Une source injoignable n'a produit aucune mesure : on affiche des
        # tirets plutôt que des zéros, qui signifieraient « page vide ».
        if mesures["erreur"] is not None:
            print(
                f"{numero:>2}  {mesures['name'][:38]:38} {'---':>4} {'---':>5} "
                f"{'---':>3} {'---':>3} {'---':>5} {'---':>6}  {verdict}"
            )
        else:
            print(
                f"{numero:>2}  {mesures['name'][:38]:38} {mesures['http']:>4} "
                f"{mesures['ko']:>5} {mesures['tables']:>3} "
                f"{mesures['selects_vides']:>3} {mesures['liens_detail']:>5} "
                f"{len(mesures['champs_profil']):>6}  {verdict}"
            )

    print("\nBilan")
    for verdict in ("exploitable", "a_tester", "javascript", "bloque", "injoignable"):
        print(f"  {verdict:12} {verdicts.get(verdict, 0)}")

    return verdicts


def fetch_page(url):
    """Télécharge une page et retourne son contenu HTML.

    Lève une erreur en cas de problème réseau ou de code HTTP non attendu :
    une source en panne ne doit pas passer silencieusement pour une source
    sans résultat.
    """
    response = requests.get(
        url,
        timeout=TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response.text


def read_text(element, selector):
    """Retourne le texte du premier élément trouvé, ou None.

    Un sélecteur absent est un cas normal : toutes les sources n'affichent pas
    les mêmes informations. KAIST n'a pas de description par exemple. On
    renvoie alors None, et non une valeur inventée (docs/README.md §7).
    """
    if element is None or not selector:
        return None

    found = element.select_one(selector)
    if found is None:
        return None

    text = found.get_text(" ", strip=True)
    return text or None


def read_texts(element, selector):
    """Retourne tous les éléments trouvés, joints par une virgule, ou None.

    Certaines pages répètent l'information. KAIST liste par exemple 3
    diplômes et jusqu'à 14 domaines de recherche pour un même programme. Les
    joindre garde l'information au lieu de n'en garder que le premier élément.
    """
    if element is None or not selector:
        return None

    texts = [
        found.get_text(" ", strip=True)
        for found in element.select(selector)
    ]
    return ", ".join(texts) or None


def read_link(element, selector):
    """Retourne l'adresse d'un lien, ou None s'il n'existe pas.

    On utilise l'attribut href et non le texte du lien : le texte affiché
    sur la page est souvent un simple « read more ».
    """
    if element is None or not selector:
        return None

    found = element.select_one(selector)
    if found is None:
        return None

    return found.get("href") or None


def build_opportunity(element, source):
    """Transforme un bloc HTML de programme en objet Opportunity.

    Cette fonction ne connaît aucune source en particulier. Tout ce qui est
    propre à un site est décrit dans config/selectors.json, ce qui permet
    d'ajouter des sources sans modifier ce fichier (docs/VERSIONS.md V0.7).
    """
    selectors = source["selectors"]
    link = read_link(element, selectors.get("url"))
    if link is None:
        # Sans lien, l'opportunité ne peut pas être vérifiée ni cliquée : elle
        # est écartée plutôt que produite incomplète.
        return None

    return Opportunity(
        title=read_text(element, selectors.get("title")),
        # TUM n'annonce qu'un diplôme, KAIST en annonce trois : read_texts
        # renvoie la même chose dans les deux cas.
        degree=read_texts(element, selectors.get("degree")),
        description=read_text(element, selectors.get("description")),
        # KAIST publie ses domaines de recherche, TUM n'affiche pas la filière.
        # Le sélecteur décide de ce qui est lisible : rien n'est comblé.
        field=read_texts(element, selectors.get("field")),
        # Les liens de la page sont relatifs : on les rend absolus pour que la
        # notification puisse être cliquée.
        url=urljoin(source["base_url"], link),
        # L'université et le pays ne sont pas écrits sur la page, ils sont
        # propres à la source : ils viennent de config/sources.json.
        university=source["university"],
        country=source["country"],
        source=source["name"],
        # Ce que l'opportunité est. La correspondance ne pose pas les mêmes
        # questions à un programme et à une bourse, et elle ne doit pas relire
        # le registre pour le savoir.
        type=source["type"],
        # docs/README.md §10 : on conserve la date de collecte pour permettre
        # une vérification humaine plus tard.
        collected_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def charger_parseur(nom):
    """Charge un parseur dédié depuis src/parsers/.

    Un parseur n'est nécessaire que lorsque la structure HTML ne peut pas
    être exprimée en sélecteurs CSS. La page Scholarship de KAIST en est
    l'exemple : le nom de la bourse et ses détails sont deux éléments
    frères, et aucun sélecteur ne peut les apparier.

    Le parseur est choisi par son nom dans config/selectors.json, jamais
    comparé ici : c'est ce qui permet d'ajouter une source qui pose problème
    sans modifier ce fichier.
    """
    return importlib.import_module(f"parsers.{nom}").parse


def parse_source(html, source):
    """Transforme le HTML d'une source en liste d'opportunités.

    Deux chemins, choisis par la configuration et non par le code :

    * par défaut, la lecture générique par sélecteurs CSS ;
    * si la source déclare un "parser", un module dédié de src/parsers/ est
      appelé à sa place.
    """
    if "parser" in source:
        return charger_parseur(source["parser"])(html, source)

    soup = BeautifulSoup(html, "html.parser")
    return [
        opportunity
        for element in soup.select(source["selectors"]["item"])
        if (opportunity := build_opportunity(element, source)) is not None
    ]


def scrape_source(source):
    """Récupère et transforme une seule source."""
    return parse_source(fetch_page(source["url"]), source)


def collect_opportunities():
    """Collecte toutes les sources prêtes à être lues, et rend ce qu'elles ont donné.

    Toutes les sources produisent le même format de données
    (docs/VERSIONS.md V0.7). Ajouter une source revient donc à écrire un bloc
    dans config/selectors.json, sans modifier ce fichier.

    ## Pourquoi la fonction rend une `Recolte` et non une liste

    Une liste ne dit rien de son origine. Sur le run du 27 septembre 2026, le
    journal disait « 69 opportunités enregistrées » et ne nommait aucune
    source : il était impossible de distinguer une veille qui marche d'une
    veille dont la moitié des sources a cessé de répondre, parce que les deux
    écrivaient la même ligne. Sur les 19 sources du registre, 4 seulement
    sont lues ; parmi les 15 autres, 12 sont activées et ne produisent rien, et
    rien ne le disait. C'est le pire mode de panne possible pour une veille :
    il ne se voit pas dans les données, et il se découvre une saison de
    bourses plus tard.

    Le compte par source est donc rendu, et il est rendu même quand il vaut
    zéro. Zéro n'est pas une absence d'information, c'est la mesure qui
    distingue la panne la plus coûteuse du projet.

    ## Pourquoi toutes les exceptions sont rattrapées

    Une source qui échoue ne doit ni interrompre les autres, ni faire échouer
    la veille. Avant cette version, seules les erreurs réseau étaient
    rattrapeées, et une faute de configuration — un nom de `parser` sans
    module dans `src/parsers/`, un bloc de sélecteurs sans clé `item` — faisait
    tomber les 68 fiches des trois autres sources avec elle. Le type de
    l'exception est nommé dans `erreur`, donc une `KeyError` se lit au lieu de
    se déguiser en coupure de réseau, et les deux se réparent différemment.
    """
    actives = load_active_sources()
    opportunities = []
    sources = []

    for source in actives:
        try:
            trouvees = scrape_source(source)
        except Exception as erreur:
            # `Exception` et non `requests.RequestException` : voir le docstring.
            #
            # Rien n'est écrit ici. La fonction rend la panne, elle ne la
            # raconte pas : `main.display_sources` est le seul endroit qui
            # écrit le rapport. Les deux écrivaient la même panne, et le
            # journal la disait donc deux fois, dont deux fois dans le résumé
            # d'étape du workflow puisque le motif y est `^Source`.
            trouvees = []
            lue = SourceLue(source["name"], 0, type(erreur).__name__, str(erreur))
        else:
            lue = SourceLue(source["name"], len(trouvees))
        sources.append(lue)
        opportunities.extend(trouvees)

    return Recolte(
        opportunities,
        sources,
        len(load_enabled_sources()) - len(actives),
    )


if __name__ == "__main__":
    # Vérification du registre : chaque URL déclarée est testée une par une.
    # docs/SOURCES.md §1.2 : une page qui répond 200 n'est pas une source
    # valide, il faut vérifier ce que le HTML contient réellement.
    # docs/GITHUB_PYTHON.md §14 : tester localement avant GitHub Actions.
    # La collecte, elle, se teste avec : python src/main.py
    test_sources()

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Opportunity:
    title: str
    university: str
    country: str

    degree: str
    field: str

    url: str
    source: str

    # Ce que l'opportunité est : un programme, une bourse, une page de
    # conditions. La source le déclare dans config/sources.json et le recopie
    # ici, pour que matches.py n'ait pas à relire le registre.
    type: Optional[str] = None

    deadline: Optional[str] = None

    funding_type: Optional[str] = None
    funding_amount: Optional[str] = None

    language: Optional[str] = None

    eligibility: list[str] = field(default_factory=list)

    description: Optional[str] = None

    collected_at: Optional[str] = None

    score: float = 0.0
    matched_criteria: list[str] = field(default_factory=list)

    # Renseignés par matches.py, pas par le scraping : ils sont le résultat de
    # la comparaison avec le profil, pas une information lue sur la page.
    matched: bool = False
    score_max: float = 0.0
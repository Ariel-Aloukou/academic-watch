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

    deadline: Optional[str] = None

    funding_type: Optional[str] = None
    funding_amount: Optional[str] = None

    language: Optional[str] = None

    eligibility: list[str] = field(default_factory=list)

    description: Optional[str] = None

    collected_at: Optional[str] = None

    score: float = 0.0
    matched_criteria: list[str] = field(default_factory=list)
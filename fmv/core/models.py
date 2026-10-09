from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class SourceFact:
    metric: str
    value: float
    unit: str
    period_end: str
    filed: str
    accession: str
    form: str
    source: str

@dataclass(frozen=True)
class TaskInput:
    ticker: str
    fcf: float
    shares: float
    cash: float
    debt: float
    discount_rate: float
    terminal_growth: float
    growth_rates: tuple[float,...]
    reference: str = 'user-supplied'

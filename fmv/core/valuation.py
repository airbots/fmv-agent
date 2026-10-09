from dataclasses import dataclass, asdict
from typing import Sequence

@dataclass(frozen=True)
class Assumptions:
    discount_rate: float
    terminal_growth: float
    growth_rates: tuple[float, ...]

@dataclass(frozen=True)
class ValuationResult:
    enterprise_value: float
    equity_value: float
    fair_value_per_share: float
    explicit_pv: float
    terminal_pv: float
    projected_fcf: tuple[float, ...]

def dcf(free_cash_flow: float, shares: float, cash: float, debt: float, a: Assumptions) -> ValuationResult:
    if shares <= 0: raise ValueError('shares must be positive')
    if a.discount_rate <= a.terminal_growth: raise ValueError('discount_rate must exceed terminal_growth')
    if a.discount_rate <= -1: raise ValueError('invalid discount rate')
    if not a.growth_rates: raise ValueError('at least one forecast year required')
    fcf = free_cash_flow
    forecast=[]
    for growth in a.growth_rates:
        if growth <= -1: raise ValueError('growth rate must exceed -100%')
        fcf *= 1 + growth
        forecast.append(fcf)
    explicit = sum(x / (1+a.discount_rate)**(i+1) for i,x in enumerate(forecast))
    terminal = fcf * (1+a.terminal_growth) / (a.discount_rate-a.terminal_growth)
    terminal_pv = terminal/(1+a.discount_rate)**len(forecast)
    ev=explicit+terminal_pv
    equity=ev+cash-debt
    return ValuationResult(ev,equity,equity/shares,explicit,terminal_pv,tuple(forecast))

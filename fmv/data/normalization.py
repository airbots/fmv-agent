"""Conservative XBRL normalization: reject ambiguous and unavailable facts."""
from dataclasses import dataclass, asdict
from datetime import date
from fmv.data.sec_client import select_facts

@dataclass(frozen=True)
class SourcedValue:
    value: float
    taxonomy: str
    tag: str
    unit: str
    start: str | None
    end: str
    filed: str
    form: str
    accession: str

class MissingFinancialData(ValueError): pass

def _pick(facts, tags, unit, as_of, duration):
    options=[]
    for tag in tags:
        for r in select_facts(facts,'us-gaap',tag,unit=unit,as_of=as_of):
            if duration:
                if not r.get('start') or r['form'] != '10-K': continue
                try: days=(date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days
                except ValueError: continue
                if not 330 <= days <= 380: continue
            elif r.get('start'): continue
            options.append((r,tag))
    if not options: raise MissingFinancialData('No suitable SEC XBRL fact for '+', '.join(tags))
    # Most recent reporting period, then most recently filed amendment for that period.
    r,tag=max(options,key=lambda item:(item[0].get('end',''), item[0].get('filed',''), item[0].get('accn','')))
    return SourcedValue(float(r['val']),'us-gaap',tag,unit,r.get('start'),r['end'],r.get('filed') or '',r.get('form') or '',r.get('accn') or '')

def extract_financials(facts, as_of=None):
    """Latest annual historical FCF and latest reported instant balance sheet.
    Does not assume quarterly cash-flow fields are standalone periods.
    """
    ocf=_pick(facts,['NetCashProvidedByUsedInOperatingActivities'],'USD',as_of,True)
    capex=_pick(facts,['PaymentsToAcquirePropertyPlantAndEquipment'],'USD',as_of,True)
    if ocf.start != capex.start or ocf.end != capex.end:
        raise MissingFinancialData('Operating cash flow and capex have different fiscal periods')
    cash=_pick(facts,['CashAndCashEquivalentsAtCarryingValue'],'USD',as_of,False)
    shares=_pick(facts,['CommonStockSharesOutstanding'],'shares',as_of,False)
    # Total debt tags are inconsistent across issuers; refuse to silently label zero debt.
    debt_components=[]
    for tags in (['LongTermDebtNoncurrent','LongTermDebt'], ['LongTermDebtCurrent','LongTermDebtAndCapitalLeaseObligationsCurrent']):
        try: debt_components.append(_pick(facts,tags,'USD',as_of,False))
        except MissingFinancialData: pass
    if not debt_components:
        raise MissingFinancialData('No recognized SEC debt fields; manual review required (cannot assume zero)')
    # Avoid mixing annual FCF with a balance sheet older than the annual report.
    if cash.end < ocf.end or shares.end < ocf.end or shares.end != cash.end:
        raise MissingFinancialData('Cash/shares older than annual FCF; manual review required')
    if any(x.end != cash.end for x in debt_components):
        raise MissingFinancialData('Debt and cash periods differ; manual review required')
    annual_fcf=ocf.value-capex.value
    if annual_fcf <= 0:
        raise MissingFinancialData('Annual FCF <= 0; standard perpetual-growth DCF not appropriate; analyst review required')
    return {
        'fcf':annual_fcf,'shares':shares.value,'cash':cash.value,
        'debt':sum(x.value for x in debt_components),
        'financial_period':ocf.end,'balance_sheet_period':cash.end,
        'sources': { 'operating_cash_flow':asdict(ocf), 'capex':asdict(capex),
           'cash':asdict(cash),'shares':asdict(shares),
           'debt_components':[asdict(x) for x in debt_components]},
        'warnings':['Uses annual historical FCF, not TTM',
                    'Common shares outstanding is not weighted-average diluted share count',
                    'Debt extraction is conservative and may omit issuer-specific instruments']
    }

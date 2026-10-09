"""Compatibility layer for legacy and new valuation reports.
Missing evidence is never upgraded to verified or replaced with numeric zero.
"""
from collections.abc import Mapping
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class ReportView:
    schema_version: int
    ticker: str
    kind: str
    label: str
    fair_value_per_share: float | None
    financial_data: dict | None
    provenance: str
    research: str | None
    review: str | None
    warnings: tuple[str, ...]
    assumptions: dict | None
    raw: dict


def normalize_report(raw, fallback_ticker='UNKNOWN'):
    if not isinstance(raw, Mapping):
        raise ValueError('Report must be a JSON object')
    raw = dict(raw)
    financial = raw.get('financial_data')
    if not isinstance(financial, dict):
        financial = None
    val = raw.get('valuation')
    val = val if isinstance(val, dict) else {}
    estimate = val.get('fair_value_per_share', raw.get('fair_value_per_share'))
    if isinstance(estimate, bool) or not isinstance(estimate, (int, float)) or not math.isfinite(estimate):
        estimate = None
    warnings = raw.get('warnings')
    warnings = tuple(str(x) for x in warnings) if isinstance(warnings, list) else ()
    source = raw.get('source_status')
    source = source if isinstance(source, str) and source.strip() else 'Unknown / not recorded'
    version = raw.get('schema_version', 1)
    version = version if isinstance(version, int) and version > 0 else 1
    is_user_supplied = 'user supplied' in source.lower() or 'demo' in str(raw.get('ticker', '')).lower()
    kind = 'Supplied/demo' if is_user_supplied else ('SEC-derived (unverified)' if financial else 'Legacy / incomplete')
    if version == 1 and financial is None:
        kind = 'Legacy / incomplete'
    return ReportView(
        schema_version=version,
        ticker=str(raw.get('ticker') or fallback_ticker),
        kind=kind,
        label='Needs analyst review' if raw.get('human_review_required', True) else 'Review status not established',
        fair_value_per_share=float(estimate) if estimate is not None else None,
        financial_data=financial,
        provenance=source,
        research=str(raw['research']) if raw.get('research') is not None else None,
        review=str(raw['review']) if raw.get('review') is not None else None,
        warnings=warnings,
        assumptions=raw.get('assumptions') if isinstance(raw.get('assumptions'), dict) else None,
        raw=raw,
    )

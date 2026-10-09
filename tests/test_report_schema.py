import pytest
from fmv.reports.schema import normalize_report

@pytest.mark.parametrize('raw', [
    {'valuation': {'fair_value_per_share': 10}},
    {'ticker': 'DEMO', 'valuation': {'fair_value_per_share': 5}, 'research': 'abc'},
    {'source_status': 'SEC XBRL', 'financial_data': {'cash': 10}, 'valuation': {'fair_value_per_share': 12}},
    {'schema_version': 3, 'warnings': ['unverified'], 'valuation': {}},
    {},
])
def test_report_never_crashes_for_missing_optional_fields(raw):
    view = normalize_report(raw)
    assert view.provenance
    assert view.label


def test_bad_estimates_are_not_displayed():
    for value in ('oops', float('nan'), None, True):
        assert normalize_report({'valuation': {'fair_value_per_share': value}}).fair_value_per_share is None


def test_missing_source_is_not_verified():
    view = normalize_report({'ticker':'MU','valuation':{'fair_value_per_share':50}})
    assert 'not recorded' in view.provenance.lower()
    assert view.financial_data is None


def test_non_object_rejected():
    with pytest.raises(ValueError): normalize_report(['wrong'])

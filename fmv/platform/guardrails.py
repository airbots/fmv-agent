"""Hard validation gates separate deterministic evidence from hypotheses."""
import math

def check_assumptions(a):
    try:
        d=float(a['discount_rate']); t=float(a['terminal_growth']); g=[float(x) for x in a['growth_rates']]
    except (KeyError,ValueError,TypeError) as exc: raise ValueError('Invalid assumptions') from exc
    if not (math.isfinite(d) and math.isfinite(t) and d>t and .03<=d<=.40 and -.05<=t<=.08 and 1<=len(g)<=15 and all(math.isfinite(x) and -.90<x<=1.0 for x in g)):
        raise ValueError('Assumption failed numeric guardrails')
    return True

def assess_evidence(evidence):
    if not isinstance(evidence.get('sources'),dict) or not evidence['sources']:
        return 'UNVERIFIED', ['Missing underlying traceable SEC evidence']
    issues=list(evidence.get('warnings',[]))
    if evidence.get('fcf',0)<=0: issues.append('FCF is nonpositive')
    if evidence.get('shares',0)<=0: issues.append('Share count invalid')
    # More comprehensive issuer-specific financial disclosure validation is required.
    return 'NEEDS_ANALYST_REVIEW',issues

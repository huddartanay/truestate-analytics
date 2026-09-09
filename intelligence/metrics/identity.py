"""Stable identities with exact, non-exponential Decimal serialization."""
from decimal import Decimal
from intelligence.events.identity import digest


def decimal_text(value):
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError('Finite Decimal required')
    text = format(value, 'f')
    return (text.rstrip('0').rstrip('.') if '.' in text else text) if value else '0'


def result_id(event_result_id, version):
    return digest([event_result_id, version])


def observation_id(data):
    return digest({k: decimal_text(v) if isinstance(v, Decimal) else v
                   for k,v in sorted(data.items()) if k != 'observation_id'})

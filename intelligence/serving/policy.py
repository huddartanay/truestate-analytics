"""Versioned policy; descriptive magnitude labels, not statistical significance."""
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal


def identity(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()


class ComponentError(ValueError):
    """Safe component label; original exception text never enters run logs."""
    def __init__(self,component):
        super().__init__('Stage 13 component failed')
        self.component=component


@dataclass(frozen=True)
class MovementPolicy:
    stable: Decimal = Decimal('0.5')
    strong: Decimal = Decimal('10')
    precision: int = 50
    version: str = 'stage13-thresholds-v1'

    def __post_init__(self):
        if (not isinstance(self.stable,Decimal) or not isinstance(self.strong,Decimal)
            or not self.stable.is_finite() or not self.strong.is_finite()
            or not 0 <= self.stable < self.strong or type(self.precision) is not int or not 28 <= self.precision <= 200
            or not isinstance(self.version,str) or not self.version.strip() or not 1 <= len(self.version) <= 64):
            raise ValueError('Invalid movement policy')

    @property
    def policy_id(self):
        return identity((self.version,self.stable,self.strong,self.precision,'ROUND_HALF_EVEN'))

    def classify(self,value):
        if not isinstance(value,Decimal) or not value.is_finite():
            raise ValueError('Finite Decimal required')
        if value >= self.strong: return 'STRONG_INCREASE'
        if value <= -self.strong: return 'STRONG_DECREASE'
        if value.copy_abs() <= self.stable: return 'STABLE'
        return 'INCREASE' if value > 0 else 'DECREASE'


POLICY = MovementPolicy()

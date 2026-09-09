"""Resolve explicit observation evidence only. Publication time is not an input."""
import re
from dataclasses import dataclass

MONTHS = ('january','february','march','april','may','june','july','august','september','october','november','december')


@dataclass(frozen=True)
class Period:
    frequency: str
    year: int
    position: int

    @property
    def ordinal(self):
        return self.year * {'MONTHLY':12,'QUARTERLY':4,'ANNUAL':1}[self.frequency] + self.position - 1

    @property
    def label(self):
        if self.frequency == 'ANNUAL': return str(self.year)
        if self.frequency == 'QUARTERLY': return f'{self.year}-Q{self.position}'
        return f'{self.year}-{self.position:02d}'


def resolve_period(text):
    if not isinstance(text,str): return None
    text = re.sub(r'\s+',' ',text.strip().lower())
    text = re.sub(r'^(?:in|during|for) ','',text)
    match = re.fullmatch(r'('+'|'.join(MONTHS)+r') ([1-9][0-9]{3})',text)
    if match: return Period('MONTHLY',int(match[2]),MONTHS.index(match[1])+1)
    match = re.fullmatch(r'q([1-4]) ([1-9][0-9]{3})',text)
    if match: return Period('QUARTERLY',int(match[2]),int(match[1]))
    if re.fullmatch(r'[1-9][0-9]{3}',text): return Period('ANNUAL',int(text),1)
    return None

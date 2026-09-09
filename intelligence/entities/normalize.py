"""Deterministic alias normalization with original clean-text character maps."""
import unicodedata


def mapped_normalize(text):
    chars, spans = [], []
    for offset, char in enumerate(text):
        if unicodedata.category(char).startswith('M') or char == '\u0640':
            if spans:spans[-1]=(spans[-1][0],offset+1)
            continue
        pieces=unicodedata.normalize('NFKD',char).casefold()
        for value in pieces:
            if unicodedata.category(value).startswith('M'):
                continue
            value=value if value.isalnum() or value=='_' else ' '
            if value==' ' and (not chars or chars[-1]==' '):
                if spans and chars[-1]==' ':spans[-1]=(spans[-1][0],offset+1)
                continue
            chars.append(value);spans.append((offset,offset+1))
    if chars and chars[-1]==' ':chars.pop();spans.pop()
    return ''.join(chars),tuple(spans)


def normalize(text):
    return mapped_normalize(text)[0]

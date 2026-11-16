"""Plain-text chart annotations, never trading signals or evaluable levels."""
import re

KINDS = ('text', 'note', 'price_label')


def annotation_text(kind, value):
    if not isinstance(value, str):
        raise ValueError('INVALID_ANNOTATION_TEXT')
    value = value.replace('\r\n', '\n').replace('\r', '\n')
    if (len(value) > (80 if kind == 'price_label' else 1000)
            or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', value)
            or len(value.split('\n')) > (1 if kind == 'price_label' else 8)
            or any(len(line) > 256 for line in value.split('\n'))
            or kind != 'price_label' and not value.strip()):
        raise ValueError('INVALID_ANNOTATION_TEXT')
    return value

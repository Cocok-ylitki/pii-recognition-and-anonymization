"""Правила для восьми структурированных атрибутов варианта 13."""

import re
from itertools import chain
from urllib.parse import urlsplit

from .validators import inn_ok, luhn_ok, passport_ok, phone_ok, snils_ok

H = r"[ \t\u00a0\u202f]"
DASH = r"[-–]"
SEP = rf"(?:{H}|{DASH})"
HOST_LABEL = r"[^\W_](?:[^\W_]|-(?=[^\W_]))*"
BARE_ZONE = r"ru|рф|su|com|org|net|info|biz|io|edu|gov|by|kz|ua|example"
URL = re.compile(
    rf"(?<![\w@./-])(?:"
    rf"(?:https?|ftp)://(?:{HOST_LABEL}\.)+{HOST_LABEL}"
    rf"|(?:{HOST_LABEL}\.)+(?:{BARE_ZONE}))"
    r"(?![\w-]|\.[\w-])(?::[0-9]+)?(?:[/?#][^\s<>\"«»“”]*)?",
    re.IGNORECASE,
)
INN = re.compile(r"(?<![\w+:-])(?:[0-9]{12}|[0-9]{10})(?![\w:-])")
PASSPORT = re.compile(
    rf"(?<![\w+:-])(?:[0-9]{{2}}{H}?[0-9]{{2}})"
    rf"(?:{H}*(?:№|N[oо]?\.?|номер){H}*|{H}+)?[0-9]{{6}}(?![\w:-])",
    re.IGNORECASE,
)
CARD = re.compile(
    rf"(?<![\w+:-])(?:[0-9]{{13,19}}"
    rf"|[0-9]{{4}}{SEP}[0-9]{{6}}{SEP}[0-9]{{5}}"
    rf"|[0-9]{{4}}(?:{SEP}[0-9]{{4}}){{2}}{SEP}[0-9]{{1,4}}(?:{SEP}[0-9]{{1,3}})?"
    rf"|[0-9]{{3}}(?:{SEP}[0-9]{{4}}){{3}}{SEP}[0-9]{{4}})(?![\w:-])"
)
SNILS = re.compile(
    rf"(?<![\w+:-])(?:[0-9]{{3}}{SEP}[0-9]{{3}}{SEP}[0-9]{{3}}{SEP}[0-9]{{2}}"
    r"|[0-9]{11})(?![\w:-])"
)
PHONE = re.compile(
    rf"(?<![\w+:-])(?:(?:\+7|8|7){SEP}?)?"
    rf"(?:\([0-9]{{3}}\)|[0-9]{{3}}){SEP}?[0-9]{{3}}{SEP}?[0-9]{{2}}{SEP}?[0-9]{{2}}"
    r"(?![\w:-])"
)
MARRIAGE = re.compile(
    rf"(?<![\w-])[IVXLCDM]{{1,8}}{H}*[-–—]{H}*[А-ЯЁ]{{2}}"
    rf"(?:{H}*(?:№|N[oо]?\.?){H}*|{H}+)[0-9]{{6}}(?![\w-])"
)
CADASTRAL = re.compile(
    r"(?<![\w:])([0-9]{2}):([0-9]{2}):([0-9]{1,9}):([0-9]{1,12})(?![\w:])"
)
CUE = re.compile(
    r"(?P<PASSPORT>\b(?:паспорт\w*|пасп\.|серия\s+паспорта))"
    r"|(?P<INN>\b(?:инн|налогоплательщик\w*)\b)"
    r"|(?P<SNILS>\b(?:снилс|страхов\w*\s+номер)\b)"
    r"|(?P<PHONE>\b(?:телефон\w*|тел\.?|моб\.?|звон\w*|контакт\w*)\b)"
    r"|(?P<CARD>\b(?:карт[аыеуой]|card)\b)"
    r"|(?P<MARRIAGE>\b(?:брак\w*|загс\w*|бракосочетани\w*)\b)"
    r"|(?P<CADASTRAL>\b(?:кадастр\w*|кад\.)\b)",
    re.IGNORECASE,
)
CONTEXT_BREAK = re.compile(r"[\n;!?]|\.(?=\s+[А-ЯЁ])")


def _cue(text, start, end):
    """Ближайший маркер слева, иначе справа, в пределах фразы."""
    before = CONTEXT_BREAK.split(text[max(0, start - 70):start])[-1]
    after = CONTEXT_BREAK.split(text[end:end + 28])[0]
    left = list(CUE.finditer(before))
    right = CUE.match(after.lstrip(" \t(),–—:"))
    return left[-1].lastgroup if left else right.lastgroup if right else None


def _urls(text):
    for match in URL.finditer(text):
        value = match.group().rstrip(".,;:!?…")
        while value and value[-1] in ")]}":
            close = value[-1]
            opening = {")": "(", "]": "[", "}": "{"}[close]
            if value.count(opening) >= value.count(close):
                break
            value = value[:-1].rstrip(".,;:!?…")
        scheme = value if "://" in value else "//" + value
        try:
            port = urlsplit(scheme).port
        except ValueError:
            continue
        if port != 0:
            yield "URL", match.start(), match.start() + len(value), 110


def _accepted(label, raw, digits, cue, match):
    if label == "INN":
        return cue not in {"PASSPORT", "PHONE"} and inn_ok(digits)
    if label == "PASSPORT":
        return (cue == label or not raw.isdigit()) and cue != "INN" and passport_ok(digits)
    if label == "CARD":
        return luhn_ok(digits)
    if label == "SNILS":
        return (cue == label or not raw.isdigit()) and snils_ok(digits)
    if label == "PHONE":
        number = "7" + digits if len(digits) == 10 else digits
        explicit = raw.startswith(("+7", "(")) or not raw.isdigit()
        return (explicit or cue == label or len(digits) == 11) and phone_ok(number)
    if label == "MARRIAGE":
        return cue == label and digits != "000000"
    return cue == label or 5 <= len(match[3]) <= 7


def _candidates(text):
    rules = (
        ("INN", INN, 53), ("PASSPORT", PASSPORT, 40), ("CARD", CARD, 70),
        ("SNILS", SNILS, 66), ("PHONE", PHONE, 50),
        ("MARRIAGE", MARRIAGE, 94), ("CADASTRAL", CADASTRAL, 95),
    )
    for label, pattern, priority in rules:
        for match in pattern.finditer(text):
            raw = match.group()
            digits = re.sub(r"[^0-9]", "", raw)
            cue = _cue(text, *match.span())
            if _accepted(label, raw, digits, cue, match):
                yield label, *match.span(), priority + 15 * (cue == label)


def resolve_overlaps(candidates):
    chosen = []
    for label, start, end, _ in sorted(
        candidates, key=lambda item: (-item[3], item[1] - item[2], item[1])
    ):
        if all(end <= left or start >= right for _, left, right in chosen):
            chosen.append((label, start, end))
    return sorted(chosen, key=lambda item: item[1])


def find_structured(text):
    return chain(_urls(text), _candidates(text))

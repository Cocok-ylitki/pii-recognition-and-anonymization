"""Токенизация текста и преобразование между символьными спанами и BIO-разметкой."""
import re

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
SENT_END = {".", "!", "?"}


def tokenize(text):
    """Возвращает список (токен, start, end); end — исключительно."""
    return [(m.group(), m.start(), m.end()) for m in TOKEN_RE.finditer(text)]


def spans_to_bio(tokens, spans):
    """spans: [(label, start, end)]. Токен получает B-, если он начинает спан, I- — если продолжает.

    Каждый токен принадлежит не более чем одному спану (первому подходящему).
    """
    tags = ["O"] * len(tokens)
    for label, s, e in sorted(spans, key=lambda x: x[1]):
        first = True
        for i, (_, ts, te) in enumerate(tokens):
            if ts >= s and te <= e and tags[i] == "O":
                tags[i] = ("B-" if first else "I-") + label
                first = False
    return tags


def bio_to_spans(tokens, tags):
    """Склеивает BIO-теги обратно в [(label, start, end)] в символьных индексах."""
    spans, cur = [], None
    for (_, ts, te), tag in zip(tokens, tags):
        if tag == "O":
            if cur:
                spans.append(tuple(cur))
                cur = None
            continue
        prefix, label = tag.split("-", 1)
        if prefix == "B" or cur is None or cur[0] != label:
            if cur:
                spans.append(tuple(cur))
            cur = [label, ts, te]
        else:
            cur[2] = te
    if cur:
        spans.append(tuple(cur))
    return spans


def split_sentences(tokens, max_words=100):
    """Режет список токенов на куски по концу предложения, каждый не длиннее max_words.

    Возвращает список (i_from, i_to) — диапазоны индексов токенов.
    """
    chunks, start = [], 0
    for i, (tok, _, _) in enumerate(tokens):
        is_initial = i > 0 and len(tokens[i - 1][0]) == 1 and tokens[i - 1][0].isupper()  # «Иванов И. И.»
        if (tok in SENT_END and i + 1 - start >= 5 and not is_initial) or i + 1 - start >= max_words:
            chunks.append((start, i + 1))
            start = i + 1
    if start < len(tokens):
        chunks.append((start, len(tokens)))
    return chunks

"""Считает метрики BIO и совпадения символьных границ."""

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

from pdrec.recognizer import ATTRIBUTES, MODEL_DIR, PDRecognizer
from pdrec.tokenization import spans_to_bio, tokenize

DATA = Path(__file__).resolve().parent / "data"
SOURCES = ("factrueval", "synthetic", "hand")


def load_data(data_dir):
    for source in SOURCES:
        with (data_dir / f"{source}.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                yield json.loads(line)


def scores(tp, fp, fn):
    return dict(
        tp=tp, fp=fp, fn=fn, support=tp + fn,
        precision=tp / (tp + fp) if tp + fp else 0.0,
        recall=tp / (tp + fn) if tp + fn else 0.0,
        f1=2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
    )


class Quality:
    def __init__(self):
        self.tp, self.fp, self.fn = Counter(), Counter(), Counter()

    def update(self, gold, pred):
        gold, pred = set(gold), set(pred)
        self.tp.update(item[0] for item in gold & pred)
        self.fp.update(item[0] for item in pred - gold)
        self.fn.update(item[0] for item in gold - pred)

    def report(self):
        per_attribute = {
            a: scores(self.tp[a], self.fp[a], self.fn[a]) for a in ATTRIBUTES
        }
        micro = scores(sum(self.tp.values()), sum(self.fp.values()), sum(self.fn.values()))
        present = [row for row in per_attribute.values() if row["support"]]
        macro, weighted = {}, {}
        for metric in ("precision", "recall", "f1"):
            macro[metric] = sum(row[metric] for row in present) / len(present) if present else 0.0
            weighted[metric] = (sum(row["support"] * row[metric] for row in present)
                                / micro["support"] if present else 0.0)
        return dict(per_attribute=per_attribute, micro=micro, macro=macro, weighted=weighted)


def indexed_bio(tags):
    for i, tag in enumerate(tags):
        if tag != "O":
            yield tag[2:], i, tag[0]


class CorpusEvaluation:
    def __init__(self):
        self.bio = Quality()
        self.spans = Quality()
        self.texts = self.tokens = 0
        self.texts_with_attribute = Counter()
        self.errors = []

    def update(self, row, prediction):
        tokens = tokenize(row["text"])
        gold = set(map(tuple, row["spans"]))
        pred = set(prediction)
        self.texts += 1
        self.tokens += len(tokens)
        self.texts_with_attribute.update({s[0] for s in gold})
        self.bio.update(indexed_bio(spans_to_bio(tokens, gold)),
                        indexed_bio(spans_to_bio(tokens, pred)))
        self.spans.update(gold, pred)
        if gold != pred:
            self.errors.append(dict(
                id=row["id"], source=row["source"],
                missed=sorted(gold - pred, key=lambda item: item[1]),
                extra=sorted(pred - gold, key=lambda item: item[1]),
            ))

    def report(self):
        return dict(
            texts=self.texts, tokens=self.tokens, texts_with_errors=len(self.errors),
            texts_with_attribute={a: self.texts_with_attribute[a] for a in ATTRIBUTES},
            bio=self.bio.report(), exact_spans=self.spans.report(),
        )


def evaluate(recognizer, rows, progress=False):
    groups = {source: CorpusEvaluation() for source in (*SOURCES, "all")}
    for start in range(0, len(rows), 24):
        batch = rows[start:start + 24]
        for row, prediction in zip(batch, recognizer.recognize_many([r["text"] for r in batch])):
            groups[row["source"]].update(row, prediction)
            groups["all"].update(row, prediction)
        if progress:
            print(f"Обработано {start + len(batch)} из {len(rows)}", file=sys.stderr, flush=True)
    return {k: group.report() for k, group in groups.items()}, groups["all"].errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--output", type=Path, help="Подробный отчёт в JSON")
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR, help="Локальная папка модели")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--device", default="cpu", choices=("cpu", "cuda"))
    parser.add_argument("--threads", default=4, type=int)
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("--threads должен быть положительным")

    recognizer = PDRecognizer(args.device, args.threads, model_dir=args.model_dir)
    report, errors = evaluate(recognizer, list(load_data(args.data_dir)), args.progress)
    bio = report["all"]["bio"]
    spans = report["all"]["exact_spans"]
    print(f"{'Атрибут':<12} {'Токены':>7} {'Спаны':>7} {'P BIO':>8} {'R BIO':>8}"
          f" {'F1 BIO':>8} {'F1 спанов':>10}")
    for attr in ATTRIBUTES:
        b, s = bio["per_attribute"][attr], spans["per_attribute"][attr]
        print(f"{attr:<12} {b['support']:7} {s['support']:7} {b['precision']:8.4f} {b['recall']:8.4f}"
              f" {b['f1']:8.4f} {s['f1']:10.4f}")
    for key in ("micro", "macro", "weighted"):
        print(f"{key:<12} {bio[key]['f1']:49.4f} {spans[key]['f1']:10.4f}")
    if args.output is not None:
        detailed = dict(groups=report, errors=errors)
        args.output.write_text(json.dumps(detailed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

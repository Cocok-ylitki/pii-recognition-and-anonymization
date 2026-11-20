"""Дообучение DeepPavlov/rubert-base-cased для token classification (SURNAME / NAME / PATRONYMIC, схема BIO).

Запуск: python train.py [--epochs 4] [--base DeepPavlov/rubert-base-cased]
Результат: models/retrained/ (веса и токенизатор).
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "DeepPavlov/rubert-base-cased"
OUT = ROOT / "models" / "retrained"
LABELS = ["O", "B-SURNAME", "I-SURNAME", "B-NAME", "I-NAME", "B-PATRONYMIC", "I-PATRONYMIC"]
L2I = {l: i for i, l in enumerate(LABELS)}


def read_jsonl(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream]


def train(epochs, base, out):
    import torch
    from datasets import Dataset
    from seqeval.metrics import f1_score
    from transformers import (
        AutoModelForTokenClassification, AutoTokenizer, DataCollatorForTokenClassification,
        Trainer, TrainingArguments, set_seed,
    )

    set_seed(42)
    tok = AutoTokenizer.from_pretrained(base)

    def encode(batch):
        enc = tok(batch["tokens"], is_split_into_words=True, truncation=True, max_length=256)
        all_labels = []
        for i, tags in enumerate(batch["tags"]):
            prev, labels = None, []
            for wid in enc.word_ids(i):
                # метка только на первом сабтокене слова, остальные игнорируются (-100)
                labels.append(-100 if wid is None or wid == prev else L2I[tags[wid]])
                prev = wid
            all_labels.append(labels)
        enc["labels"] = all_labels
        return enc

    data = {}
    for name in ("train", "val"):
        ds = Dataset.from_list(read_jsonl(ROOT / "data" / f"{name}.jsonl"))
        data[name] = ds.map(encode, batched=True, remove_columns=ds.column_names)

    def metrics(p):
        logits, labels = p
        pred = logits.argmax(-1)
        true_tags, pred_tags = [], []
        for pr, lb in zip(pred, labels):
            keep = lb != -100
            true_tags.append([LABELS[x] for x in lb[keep]])
            pred_tags.append([LABELS[x] for x in pr[keep]])
        return {"f1": f1_score(true_tags, pred_tags)}

    model = AutoModelForTokenClassification.from_pretrained(
        base, num_labels=len(LABELS), id2label=dict(enumerate(LABELS)), label2id=L2I)
    args = TrainingArguments(
        output_dir=str(out / "checkpoints"), num_train_epochs=epochs, learning_rate=3e-5,
        per_device_train_batch_size=16, per_device_eval_batch_size=32, weight_decay=0.01, warmup_steps=0.1,
        eval_strategy="epoch", save_strategy="epoch", save_total_limit=1, load_best_model_at_end=True,
        metric_for_best_model="f1", fp16=torch.cuda.is_available(), logging_steps=50, report_to="none")
    trainer = Trainer(model=model, args=args, train_dataset=data["train"], eval_dataset=data["val"],
                      data_collator=DataCollatorForTokenClassification(tok), compute_metrics=metrics)
    trainer.train()
    trainer.save_model(str(out))
    tok.save_pretrained(out)
    print("saved to", out, "| val:", trainer.evaluate())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--base", default=BASE, help="Модель Hugging Face или локальная папка")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("--epochs должен быть положительным")
    train(args.epochs, args.base, args.output)


if __name__ == "__main__":
    main()

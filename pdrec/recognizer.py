"""Локальное распознавание ПДн с помощью правил и RuBERT."""

from pathlib import Path

from .rules import find_structured, resolve_overlaps
from .tokenization import bio_to_spans, split_sentences, tokenize

ATTRIBUTES = (
    "SURNAME", "NAME", "INN", "PASSPORT", "CARD", "SNILS",
    "URL", "PHONE", "MARRIAGE", "CADASTRAL",
)
MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "fio-rubert"


class PDRecognizer:
    """Находит тройки (тип, начало, конец) с полуоткрытыми границами."""

    def __init__(self, device="cpu", threads=4, batch_size=24, model_dir=MODEL_DIR):
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        if device == "cpu":
            torch.set_num_threads(threads)
        self.torch = torch
        self.device = device
        self.batch_size = batch_size
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_dir, dtype=torch.float32, local_files_only=True
        ).to(device).eval()
        self.id2label = self.model.config.id2label

    def _predict_tags(self, documents):
        tags = [["O"] * len(tokens) for tokens in documents]
        chunks = []
        for doc_id, tokens in enumerate(documents):
            for start, end in split_sentences(tokens):
                chunks.append((doc_id, start, [token[0] for token in tokens[start:end]]))
        chunks.sort(key=lambda chunk: len(chunk[2]))

        for index in range(0, len(chunks), self.batch_size):
            batch = chunks[index:index + self.batch_size]
            encoding = self.tokenizer(
                [words for _, _, words in batch],
                is_split_into_words=True, max_length=256, truncation=True,
                return_overflowing_tokens=True, stride=32, padding=True,
                return_tensors="pt",
            )
            model_inputs = {
                name: encoding[name].to(self.device)
                for name in self.tokenizer.model_input_names if name in encoding
            }
            with self.torch.inference_mode():
                predictions = self.model(**model_inputs).logits.argmax(-1).cpu().tolist()

            seen = [set() for _ in batch]
            for i, sample in enumerate(encoding["overflow_to_sample_mapping"].tolist()):
                doc_id, start, _ = batch[sample]
                for word_id, prediction in zip(encoding.word_ids(i), predictions[i]):
                    if word_id is not None and word_id not in seen[sample]:
                        tags[doc_id][start + word_id] = self.id2label[prediction]
                        seen[sample].add(word_id)
        return tags

    def recognize_many(self, texts):
        """Обрабатывает группу текстов, сохраняя их порядок."""
        documents = [tokenize(text) for text in texts]
        results = []
        for text, tokens, tags in zip(texts, documents, self._predict_tags(documents)):
            candidates = list(find_structured(text))
            candidates.extend(
                (label, start, end, 0)
                for label, start, end in bio_to_spans(tokens, tags)
                if label in {"SURNAME", "NAME"}
            )
            results.append(resolve_overlaps(candidates))
        return results

    def recognize(self, text):
        return self.recognize_many([text])[0]

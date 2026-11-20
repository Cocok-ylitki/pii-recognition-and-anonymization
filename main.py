"""Выводит найденные атрибуты как JSON с символьными координатами."""

import argparse
import json
import sys
from pathlib import Path

from pdrec.recognizer import PDRecognizer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("text", nargs="?", help="Текст в командной строке")
    inputs.add_argument("--file", type=Path, help="Текстовый файл в UTF-8")
    args = parser.parse_args()
    if args.file is not None:
        with args.file.open(encoding="utf-8-sig", newline="") as source:
            text = source.read()
    elif args.text is not None:
        text = args.text
    else:
        sys.stdin.reconfigure(encoding="utf-8", newline="")
        text = sys.stdin.read()
    print(json.dumps(PDRecognizer().recognize(text), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

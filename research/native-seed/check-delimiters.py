#!/usr/bin/env python3
"""Cheap delimiter preflight before the canonical BL reader/compiler gate."""
from pathlib import Path

BASE = Path(__file__).resolve().parent


def check(path):
    text = path.read_text()
    stack, line, index = [], 1, 0
    pairs = {")": "(", "]": "[", "}": "{"}
    while index < len(text):
        char = text[index]
        if char == ";":
            end = text.find("\n", index)
            index = len(text) if end < 0 else end
            continue
        if char == '"':
            index += 1
            while index < len(text):
                if text[index] == "\\":
                    index += 2
                    continue
                if text[index] == '"':
                    break
                line += text[index] == "\n"
                index += 1
            assert index < len(text), f"{path}:{line}: unterminated string"
        elif char == "\\":
            index += 1
            assert index < len(text), f"{path}:{line}: incomplete character"
            index += 1
            while index < len(text) and text[index].isalnum():
                index += 1
            continue
        elif char in "([{":
            stack.append((char, line))
        elif char in pairs:
            assert stack and stack[-1][0] == pairs[char], f"{path}:{line}: unexpected {char}"
            stack.pop()
        line += char == "\n"
        index += 1
    assert not stack, f"{path}: unclosed delimiters {stack}"


if __name__ == "__main__":
    paths = list(BASE.glob("*.bl"))
    for directory in ["src", "direct", "fixtures", "corpus"]:
        paths.extend((BASE / directory).rglob("*.bl"))
    failures = []
    for path in sorted(paths):
        try:
            check(path)
        except AssertionError as error:
            failures.append(str(error))
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"BL delimiter preflight: {len(paths)} files")

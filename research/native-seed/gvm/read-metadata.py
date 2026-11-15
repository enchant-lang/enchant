#!/usr/bin/env python3
"""Decode bootstrap/data's finite metadata constructors without Scheme eval.

This accepts only literal metadata, never Source, ANF or executable bodies.
The whitelist is the wire format authored by native.bootstrap/data.
"""
import argparse
import json
from pathlib import Path
import re


class Symbol(str):
    pass


def decode(text):
    if len(text.encode("utf-8")) > 33554432:
        raise ValueError("metadata exceeds the retained byte bound")
    position, remaining = 0, 1000000

    def value(depth=0):
        nonlocal position, remaining
        remaining -= 1
        if remaining < 0 or depth > 128:
            raise ValueError("metadata structural budget exceeded")
        while position < len(text) and text[position].isspace():
            position += 1
        if position >= len(text):
            raise ValueError("unexpected metadata EOF")
        c = text[position]
        position += 1
        if c == '(':
            items = []
            while True:
                while position < len(text) and text[position].isspace():
                    position += 1
                if position >= len(text):
                    raise ValueError("unclosed metadata constructor")
                if text[position] == ')':
                    position += 1
                    break
                items.append(value(depth + 1))
            if not items or not isinstance(items[0], Symbol):
                raise ValueError("metadata must use a named data constructor")
            name, args = items[0], items[1:]
            if name == 'list':
                return args
            if name in ('bl-vec', 'bl-tuple', 'bl-set') and len(args) == 1 and isinstance(args[0], list):
                return args[0]
            if name == 'bl-key' and len(args) == 1 and type(args[0]) is str:
                return args[0]
            if name == 'bl-map' and len(args) % 2 == 0:
                result = {}
                for key, item in zip(args[::2], args[1::2]):
                    if type(key) is not str or key in result:
                        raise ValueError("metadata map keys must be unique strings/keywords")
                    result[key] = item
                return result
            raise ValueError("unadmitted metadata constructor: " + name)
        if c == '"':
            out = []
            while position < len(text):
                c = text[position]
                position += 1
                if c == '"':
                    return ''.join(out)
                if c == '\\':
                    if position >= len(text):
                        raise ValueError("truncated metadata string escape")
                    c = text[position]
                    position += 1
                    if c == 'x':
                        end = text.find(';', position)
                        digits = text[position:end] if end >= 0 else ''
                        if not re.fullmatch('[0-9a-fA-F]{1,6}', digits):
                            raise ValueError("invalid metadata hexadecimal escape")
                        out.append(chr(int(digits, 16)))
                        position = end + 1
                        continue
                    escapes = {'n': '\n', 'r': '\r', 't': '\t', '\\': '\\', '"': '"'}
                    if c not in escapes:
                        raise ValueError("unadmitted metadata string escape")
                    c = escapes[c]
                out.append(c)
            raise ValueError("unclosed metadata string")
        start = position - 1
        while position < len(text) and not text[position].isspace() and text[position] not in '()':
            position += 1
        atom = text[start:position]
        if atom == '#t': return True
        if atom == '#f': return False
        if atom == 'bl-nil': return None
        if re.fullmatch('-?[0-9]+', atom): return int(atom)
        if atom in ('list', 'bl-vec', 'bl-tuple', 'bl-set', 'bl-key', 'bl-map'):
            return Symbol(atom)
        raise ValueError("unadmitted metadata atom: " + atom[:80])

    result = value()
    if text[position:].strip():
        raise ValueError("metadata must contain exactly one constructor datum")
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(decode(args.input.read_text()), indent=2) + '\n')

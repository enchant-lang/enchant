"""Apply the comparison edit to an owned native Source overlay."""

from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_bytes()
if sys.argv[2] == "--arity":
    body = b'(Enum/join (cons "v" (Enum/map (unicode/characters_to_list s) (fn [c] (code-text c)))) "")'
    before = b'(defn ident [s]\n ' + body + b')'
    after = b'(defn ident\n ([s] ' + body + b')\n ([s prefix] (str prefix (ident s))))'
else:
    before = b'(Enum/join (cons "v" (Enum/map (unicode/characters_to_list s)'
    after = b'(Enum/join (cons "w" (Enum/map (unicode/characters_to_list s)'
assert source.count(before) == 1, "the retained emitter body does not match the edit fixture"
path.write_bytes(source.replace(before, after, 1))

"""Derive a candidate image directory by applying host-source edits to a qualified image.

Usage: python3 derive-image.py QUALIFIED_IMAGE OUT_DIR [BASE_REV]

The host Scheme in research/native-seed/host/*.scm is copied verbatim into an
image's host.scm, prelude.scm, stage1.scm and every self-emitted stageN.scm.
For each run of top-level host forms that differs between HEAD and the working
tree (or BASE_REV, default HEAD), replace that exact text in those files. The qualified image must have been
built from BASE_REV's host sources; each replaced text must occur exactly once.
Every other input is symlinked. The derived directory records each replacement
so the Chez qualification can check the candidate against it."""
import difflib, hashlib, json, re, subprocess, sys
from pathlib import Path

HOST = Path(__file__).resolve().parents[1] / 'native-seed/host'
TEXT_FILES = ('host.scm', 'prelude.scm', 'stage1.scm', 'stage2.scm', 'stage3.scm')


def top_level_forms(text):
    """Yield (name, exact text) of '(define (name' / '(define name' forms starting at column 0."""
    starts = [m.start() for m in re.finditer(r'(?m)^\(define[ (]', text)] + [len(text)]
    for a, b in zip(starts, starts[1:]):
        chunk = text[a:b]
        depth, end, i, in_str = 0, None, 0, False
        while i < len(chunk):
            c = chunk[i]
            if in_str:
                if c == '\\': i += 1
                elif c == '"': in_str = False
            elif c == '"': in_str = True
            elif c == ';':
                while i < len(chunk) and chunk[i] != '\n': i += 1
            elif c == '#' and chunk[i:i+2] == '#\\': i += 2
            elif c == '(': depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0: end = i + 1; break
            i += 1
        form = chunk[:end]
        m = re.match(r'\(define \(?([^\s()]+)', form)
        yield m.group(1), form


def main():
    image, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    base = sys.argv[3] if len(sys.argv) > 3 else 'HEAD'
    out.mkdir(parents=True)
    image_host = (image / 'host.scm').read_text()
    edits = []
    root = HOST.parents[2]
    changed = subprocess.check_output(['git', 'diff', '--name-only', base, '--', str(HOST)], cwd=root, text=True).split()
    for rel in changed:
        before = subprocess.check_output(['git', 'show', f'{base}:{rel}'], cwd=root, text=True)
        after = (root / rel).read_text()
        old_forms = [f for _, f in top_level_forms(before)]
        new_forms = [f for _, f in top_level_forms(after)]
        matcher = difflib.SequenceMatcher(a=old_forms, b=new_forms, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
            if i1 == i2:
                sys.exit(f'{rel}: pure insertion without an anchoring changed form is not supported')
            edits.append({'name': re.match(r'\(define \(?([^\s()]+)', old_forms[i1]).group(1), 'file': rel,
                          'old': '\n'.join(old_forms[i1:i2]), 'new': '\n'.join(new_forms[j1:j2])})
    for e in edits:
        if image_host.count(e['old']) != 1:
            sys.exit(f"{e['name']}: qualified host text is not unique")
    receipt = {'qualified_image': str(image), 'base': subprocess.check_output(['git', 'rev-parse', base], cwd=root, text=True).strip(), 'edits': [], 'files': {}}
    for f in sorted(image.iterdir()):
        if f.name in TEXT_FILES:
            text = f.read_text()
            for e in edits:
                if text.count(e['old']) != 1:
                    sys.exit(f"{e['name']}: {f.name} does not contain the qualified text exactly once")
                text = text.replace(e['old'], e['new'])
            (out / f.name).write_text(text)
            receipt['files'][f.name] = hashlib.sha256(text.encode()).hexdigest()
        else:
            (out / f.name).symlink_to(f)
    receipt['edits'] = [{'name': e['name'], 'file': e['file'],
                         'old_sha256': hashlib.sha256(e['old'].encode()).hexdigest(),
                         'new_sha256': hashlib.sha256(e['new'].encode()).hexdigest()} for e in edits]
    (out / 'derived.json').write_text(json.dumps(receipt, indent=1))
    print(json.dumps({'edits': [e['name'] for e in edits], 'files': list(receipt['files'])}))


if __name__ == '__main__':
    main()

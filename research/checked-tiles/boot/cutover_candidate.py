"""Identity checks for a complete native self-hosting qualification."""
import hashlib
import json


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualified(build):
    receipt_path = build/'full-fixpoint.json'
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    required = (
        'stage2-stage3-byte-equal', 'stage3-built-and-executed',
        'stage1-stage2-stage3-source-corpus-equal',
        'stage1-stage2-stage3-original-actor-corpus-equal', 'all-actor-budgets',
    )
    if receipt['status'] != 'qualified' or any(not receipt[k] for k in required):
        raise ValueError(f'{build} lacks a completed native fixed point')
    stage2 = receipt['source_results']['stage2']
    image = stage2['image_sha256']
    macros = stage2['prepared_eval_bundle_sha256']
    if (image != receipt['source_results']['stage3']['image_sha256']
            or image != digest(build/'stage2') or macros != digest(build/'eval-prepared.scm')):
        raise ValueError(f'Native candidate bytes disagree with {receipt_path}')
    identity = build/'identity.json'
    expected = receipt['inputs'].get(str(identity))
    if expected is None or digest(identity) != expected:
        raise ValueError(f'Native compiler Source identity disagrees with {receipt_path}')
    providers = {row['path']: row['sha256'] for row in json.loads(identity.read_text())['providers']}
    return dict(image=image, bundle=macros, compiler_source=providers['priv/boot/compiler.bl'],
                reader_source=providers['priv/boot/reader.bl'],
                qualification=hashlib.sha256(receipt_bytes).hexdigest())

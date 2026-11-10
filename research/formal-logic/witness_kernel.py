"""Check a concrete typed-term SAT witness using the pinned constructive checker.

Names remain data. Closed constructor source is independently decoded before
Lean checks every original assertion and the constructive existence theorem.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import term_refutation as t

k = t.k
P = k.PROJECT
require = k.require


def canonical_identity(packet):
    data = dict(packet)
    for name in ['profile', 'semantics', 'mode', 'completion', 'identity-profile']:
        data[name] = k.Keyword(data[name])
    data['assertions'] = [t.typed_term(term) for term in data['assertions']]
    data['bindings'] = [[name, [k.Keyword(sort[0])], value] for name, sort, value in data['bindings']]
    del data['identity']
    wire = b'\x83' + k.etf(('bl/canonical-formal-data-v1', t.normal(data)))
    require(len(wire) <= k.MAX_BYTES, 'witness canonical capacity')
    import hashlib
    return hashlib.sha256(wire).hexdigest()


def validate(packet):
    require(type(packet) is dict and set(packet) == {'formal/term-witness', 'profile', 'semantics', 'mode', 'question', 'assertions', 'bindings', 'completion', 'identity-profile', 'identity'}, 'witness packet fields')
    require(type(packet['formal/term-witness']) is int and packet['formal/term-witness'] == 1, 'witness packet version')
    require(packet['profile'] == 'bl/typed-term-witness-v1' and packet['semantics'] == 'bl/partial-mathematical-int-bool-v1', 'witness profile/semantics')
    require(packet['mode'] == 'sat' and packet['completion'] == 'zero-false-outside-bindings', 'witness mode/completion')
    require(packet['identity-profile'] == 'bl/canonical-formal-data-v1', 'witness identity profile')
    require(all(type(packet[key]) is str and k.HEX.fullmatch(packet[key]) for key in ['identity', 'question']), 'witness digests')
    require(type(packet['assertions']) is list and len(packet['assertions']) <= 4096, 'witness assertion capacity')
    variables = t.validate_roots(packet['assertions'])
    require(type(packet['bindings']) is list and len(packet['bindings']) <= 4096, 'witness binding capacity')
    names = []
    for row in packet['bindings']:
        require(type(row) is list and len(row) == 3, 'witness binding row')
        name, sort, value = row
        require(type(name) is str and name in variables and sort == [variables[name]], 'witness binding name/sort')
        require(type(value) is (int if sort == ['int'] else bool), 'witness concrete value kind')
        names.append(name)
    require(names == sorted(variables), 'witness needs exactly one sorted binding for every assertion input')
    require(canonical_identity(packet) == packet['identity'], 'witness canonical identity mismatch')
    return sorted(n for n, s in variables.items() if s == 'int'), sorted(n for n, s in variables.items() if s == 'bool')


HEADER = 'import Witness\nset_option maxRecDepth 5000\nset_option maxHeartbeats 2000000\nopen FormalTerms FormalWitness\n\ndef originalContext : Context :=\n'
WITNESS = '\n\ndef suppliedWitness : Witness :=\n'
TAIL = '''

theorem packetAccepted : accepts originalContext suppliedWitness = true := by decide
theorem originalContextHolds : contextSatisfied originalContext suppliedWitness.integerEnv suppliedWitness.booleanEnv :=
  checked_context_holds originalContext suppliedWitness packetAccepted
theorem originalContextSatisfiable : satisfiable originalContext :=
  checked_witness_satisfiable originalContext suppliedWitness packetAccepted
#print axioms packetAccepted
#print axioms originalContextHolds
#print axioms originalContextSatisfiable
'''


def values(packet, integers, booleans):
    assignment = {name: value for name, _, value in packet['bindings']}
    return [assignment[n] for n in integers], [assignment[n] for n in booleans]


def source(packet, integers, booleans):
    ints, bools = values(packet, integers, booleans)
    return (HEADER + k.emit_list([t.emit_term(node, integers, booleans) for node in packet['assertions']]) + WITNESS
            + '(Witness.mk ' + k.emit_list([k.emit_int(value) for value in ints]) + ' '
            + k.emit_list([str(value).lower() for value in bools]) + ')' + TAIL)


def verify_source(text, packet, integers, booleans):
    require(text.startswith(HEADER) and text.endswith(TAIL), 'witness source template')
    context, witness = text[len(HEADER):-len(TAIL)].split(WITNESS)
    parser = t.TermDecoder(context)
    roots = parser.list(parser.term)
    require(parser.at == len(parser.tokens), 'trailing witness context data')
    require(len(roots) == len(packet['assertions']) and all(t.faithful(node, ast, integers, booleans) for node, ast in zip(packet['assertions'], roots)), 'generated witness terms differ from original')
    parser = k.Decoder(witness)
    parser.take('('); parser.take('Witness.mk')
    ints = parser.list(parser.int)
    def boolean():
        value = parser.take(); require(value in {'true', 'false'}, 'generated witness Boolean')
        return value == 'true'
    bools = parser.list(boolean)
    parser.take(')'); require(parser.at == len(parser.tokens), 'trailing witness values')
    require((ints, bools) == values(packet, integers, booleans), 'generated concrete values differ from supplied witness')


def run(path, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / 'Check.olean').unlink(missing_ok=True)
    (output / 'result.json').unlink(missing_ok=True)
    require(path.stat().st_size <= k.MAX_BYTES, 'witness packet byte capacity')
    packet = k.load_packet(path)
    integers, booleans = validate(packet)
    text = source(packet, integers, booleans)
    verify_source(text, packet, integers, booleans)
    tool = json.loads((P / 'metatheory/tool-pin.json').read_text())
    lean = Path(tool['path']) / 'bin/lean'
    require(k.sha(lean) == tool['binary_sha256'], 'Lean executable pin')
    pins = [json.loads((P / ('metatheory/' + name + '-pin.json')).read_text()) for name in ['refutation', 'terms', 'witness']]
    require(k.sha(P / 'metatheory/refutation-pin.json') == pins[1]['normalized_kernel_pin_sha256'], 'term normalized dependency pin')
    require(k.sha(P / 'metatheory/terms-pin.json') == pins[2]['typed_term_pin_sha256'], 'witness typed dependency pin')
    for pin in pins:
        for key in ['source', 'compiled']:
            require(k.sha(P / pin[key]['path']) == pin[key]['sha256'], 'witness/model/kernel artifact pin')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'Check.lean').write_text(text)
    (output / 'Check.olean').unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='enchant-witness-') as temporary:
        work = Path(temporary); library = work / 'library'; library.mkdir()
        for pin, module in zip(pins, ['Refutation', 'Terms', 'Witness']):
            shutil.copyfile(P / pin['compiled']['path'], library / (module + '.olean'))
        check = work / 'Check.lean'; check.write_text(text)
        with (output / 'lean.txt').open('w') as log:
            completed = subprocess.run([str(lean), '--root=' + str(work), '-o', str(work / 'Check.olean'), str(check)], cwd=work,
                                       env=dict(os.environ, LEAN_PATH=str(library)), text=True, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        transcript = (output / 'lean.txt').read_text()
        require(completed.returncode == 0 and 'sorryAx' not in transcript and 'warning:' not in transcript, 'Lean did not accept typed-term witness')
        audits = {}
        for line in transcript.splitlines():
            match = re.fullmatch(r"'([^']+)' (?:does not depend on any axioms|depends on axioms: \[(.*)\])", line)
            require(match is not None and match[1] not in audits, 'unexpected witness theorem audit')
            audits[match[1]] = match[2].split(', ') if match[2] else []
        require(set(audits) == {'packetAccepted', 'originalContextHolds', 'originalContextSatisfiable'}, 'witness theorem audit names')
        require(all(set(deps) <= {'propext', 'Quot.sound'} for deps in audits.values()), 'constructive witness axiom dependency')
        shutil.copyfile(work / 'Check.olean', output / 'Check.olean')
    result = {'schema': 'enchant.formal.typed-term-witness-execution.v1', 'status': 'checked-term-satisfiability',
              'packet': packet['identity'], 'question': packet['question'], 'semantics': packet['semantics'],
              'assertions': len(packet['assertions']), 'integer_bindings': len(integers), 'boolean_bindings': len(booleans),
              'proof_source_sha256': k.sha(output / 'Check.lean'), 'proof_olean_sha256': k.sha(output / 'Check.olean'),
              'witness_model_source_sha256': pins[2]['source']['sha256'], 'witness_model_olean_sha256': pins[2]['compiled']['sha256'],
              'axioms': audits, 'allowed_axioms': ['propext', 'Quot.sound'], 'canonical_packet_identity': 'independently-recomputed',
              'source_data': 'independently-decoded-and-compared', 'existence': 'explicit-total-environments-satisfy-every-original-assertion',
              'full_query_connection': 'requires-fresh-BL-question-reconstruction', 'backend_attestation': 'not-established',
              'term_data_model_correspondence': 'reviewed-data-semantics-bridge', 'source_compiler_preservation': 'not-established',
              'runtime_attestation': 'local-checker-observation-not-cryptographic-attestation', 'compiler_proof_authority': False}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.packet, args.output)
        print(json.dumps({'status': result['status'], 'packet': result['packet'], 'compiler_proof_authority': False}))
    except (ValueError, OSError, subprocess.TimeoutExpired, RecursionError, IndexError) as error:
        args.output.mkdir(parents=True, exist_ok=True)
        result = {'status': 'not-accepted', 'reason': str(error), 'compiler_proof_authority': False}
        (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result)); raise SystemExit(1)


if __name__ == '__main__':
    main()

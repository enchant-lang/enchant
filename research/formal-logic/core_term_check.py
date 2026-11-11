"""Check a particular Core tree against its exported symbolic outcome in Lean."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import term_refutation as terms
import witness_kernel as proof_tools
from obligation_proof import data_digest, digest

P, k, require = terms.P, terms.k, terms.require
SCALARS = (['int'], ['bool'])
INTEGER_OPS = {'add', 'sub', 'mul', 'quot', 'rem', 'mod'}
COMPARISONS = {'lt', 'le', 'gt', 'ge'}


def record(sort):
    return sort[0] == 'record'


def validate_sort(sort, depth=0):
    require(depth <= 8 and type(sort) is list and bool(sort), 'Core sort shape')
    if sort in SCALARS:
        return
    require(len(sort) == 2 and record(sort) and type(sort[1]) is list and len(sort[1]) <= 16, 'closed record sort')
    names = []
    for field in sort[1]:
        require(type(field) is list and len(field) == 2 and type(field[0]) is str, 'record field declaration')
        names.append(field[0])
        validate_sort(field[1], depth + 1)
    require(names == sorted(set(names)), 'canonical ordered record fields')


def typed_sort(sort):
    return ([k.Keyword('record'), [[name, typed_sort(child)] for name, child in sort[1]]]
            if record(sort) else [k.Keyword(sort[0])])


def typed_core(node):
    return {**node, 'sort': typed_sort(node['sort']), 'op': k.Keyword(node['op']),
            'data': k.Keyword(node['data']) if node['op'] == 'raise' else node['data'],
            'args': [typed_core(child) for child in node['args']]}


def typed_payload(sort, value):
    if record(sort):
        return [[name, typed_payload(child, entry[1])] for (name, child), entry in zip(sort[1], value)]
    return terms.typed_term(value)


def typed_packet(packet):
    data = dict(packet)
    for field in ['profile', 'semantics', 'core-profile', 'input-encoding', 'identity-profile']:
        data[field] = k.Keyword(data[field])
    data['body'] = typed_core(data['body'])
    data['subject'] = {**data['subject'], 'kind': k.Keyword(data['subject']['kind'])}
    data['inputs'] = [[name, typed_sort(sort), typed_payload(sort, value)] for name, sort, value in data['inputs']]
    data['errors'] = [[k.Keyword(name), code] for name, code in data['errors']]
    data['outcome'] = {'ok': terms.typed_term(data['outcome']['ok']), 'error': terms.typed_term(data['outcome']['error']),
                       'value': typed_payload(packet['body']['sort'], data['outcome']['value'])}
    return data


def canonical_identity(packet):
    data = typed_packet(packet)
    del data['identity']
    return data_digest(data)


def name_ok(name):
    return type(name) is str and bool(name) and '\0' not in name


def validate_core(root, declarations, errors):
    visits = 0
    has_records = any(record(sort) for sort in declarations.values())

    def visit(node, env, depth):
        nonlocal visits, has_records
        visits += 1
        require(depth <= 128 and visits <= 4096, 'Core syntax capacity')
        require(type(node) is dict and set(node) == {'core/node', 'op', 'sort', 'args', 'data'}, 'Core node fields')
        require(type(node['core/node']) is int and node['core/node'] == 1, 'Core node version')
        op, sort, args, data = (node[field] for field in ['op', 'sort', 'args', 'data'])
        require(type(op) is str and type(args) is list, 'Core operation and arguments')
        validate_sort(sort)
        has_records = has_records or record(sort)
        if op == 'const':
            require(not args and ((sort == ['int'] and type(data) is int) or (sort == ['bool'] and type(data) is bool)), 'Core literal kind')
        elif op == 'local':
            require(not args and name_ok(data) and env.get(data) == sort, 'Core lexical name and sort')
        elif op == 'raise':
            require(not args and type(data) is str and data in errors, 'Core named error')
        elif op == 'let':
            require(len(args) == 2 and name_ok(data), 'Core binding shape')
            bound = visit(args[0], env, depth + 1)
            require(visit(args[1], {**env, data: bound}, depth + 1) == sort, 'Core binding result')
        else:
            children = [visit(child, env, depth + 1) for child in args]
            if op == 'record':
                require(type(data) is list and all(type(key) is str for key in data) and len(data) == len(children) == len(set(data))
                        and sort == ['record', [[key, child] for key, child in sorted(zip(data, children))]], 'ordered record construction')
            elif op == 'field':
                require(len(children) in {1, 2} and type(data) is str and record(children[0])
                        and dict(children[0][1]).get(data) == sort, 'Core projection or eager default')
            elif op == 'record-assoc':
                require(bool(children) and record(sort) and children[0] == sort and type(data) is list and len(data) == len(children) - 1
                        and all(type(key) is str and dict(sort[1]).get(key) == child for key, child in zip(data, children[1:])), 'ordered record updates')
            else:
                require(data is None, 'Core primitive has no payload')
                if op == 'if':
                    require(children == [['bool'], sort, sort], 'Core conditional sorts')
                elif op == 'do':
                    require(bool(children) and children[-1] == sort, 'Core sequence result')
                elif op in INTEGER_OPS:
                    require(sort == ['int'] and children == [['int'], ['int']], 'Core integer operation')
                elif op == 'neg':
                    require(sort == ['int'] and children == [['int']], 'Core negation')
                elif op in COMPARISONS:
                    require(sort == ['bool'] and children == [['int'], ['int']], 'Core comparison')
                elif op == 'eq':
                    require(sort == ['bool'] and len(children) == 2 and children[0] == children[1], 'Core equality sorts')
                elif op == 'not':
                    require(sort == ['bool'] and children == [['bool']], 'Core Boolean negation')
                else:
                    require(op in {'and', 'or'} and sort == ['bool'] and all(child == ['bool'] for child in children), 'Core Boolean operation')
        return sort

    visit(root, declarations, 0)
    return 'bl/core-record-outcomes-v2' if has_records else 'bl/core-int-bool-outcomes-v1'


def payload_leaves(sort, value, prefix=None):
    if not record(sort):
        yield sort[0], value, prefix
        return
    require(type(value) is list and len(value) == len(sort[1]), 'record payload layout')
    for (field, child), entry in zip(sort[1], value):
        require(type(entry) is list and len(entry) == 2 and entry[0] == field, 'canonical named payload field')
        path = component(prefix, '/field/', field) if prefix is not None else None
        yield from payload_leaves(child, entry[1], path)


def component(prefix, separator, name):
    encoded = name.encode('utf-8').hex()
    return f'{prefix}{separator}{len(encoded)}:{encoded}'


def validate(packet):
    require(type(packet) is dict and set(packet) == {'formal/core-term-data', 'profile', 'semantics', 'core-profile', 'core',
            'body', 'subject', 'prefix', 'input-encoding', 'inputs', 'errors', 'outcome', 'identity-profile', 'identity'}, 'Core term packet fields')
    require(type(packet['formal/core-term-data']) is int and packet['formal/core-term-data'] == 1, 'Core term packet version')
    require(packet['profile'] == 'bl/core-term-data-v1' and packet['semantics'] == 'bl/partial-mathematical-int-bool-v1'
            and packet['identity-profile'] == 'bl/canonical-formal-data-v1', 'Core term packet profile')
    digest(packet['core'], 'Core body')
    digest(packet['identity'], 'Core term packet')
    subject = packet['subject']
    require(type(subject) is dict and set(subject) == {'kind', 'identity', 'question'} and subject['kind'] in ['core', 'contract'], 'Core term subject fields')
    digest(subject['identity'], 'subject')
    if subject['kind'] == 'contract':
        digest(subject['question'], 'contract question')
    else:
        require(subject['identity'] == packet['core'] and subject['question'] is None, 'direct Core subject')
    errors = {}
    require(type(packet['errors']) is list and len(packet['errors']) <= 4096, 'Core error catalogue capacity')
    for row in packet['errors']:
        require(type(row) is list and len(row) == 2 and name_ok(row[0]) and row[0] not in errors
                and type(row[1]) is int and row[1] > 0, 'Core error name and code')
        errors[row[0]] = row[1]
    require(list(errors) == sorted(errors) and len(set(errors.values())) == len(errors) and errors.get('zero-divisor') == 1, 'unique Core error codes')
    encoding = packet['input-encoding']
    require(encoding in ['legacy', 'record-paths-v2'] and type(packet['prefix']) is str, 'Core symbolic input encoding')
    declarations, roots = {}, []
    require(type(packet['inputs']) is list and len(packet['inputs']) <= 1024, 'Core input declaration capacity')
    for row in packet['inputs']:
        require(type(row) is list and len(row) == 3 and name_ok(row[0]) and row[0] not in declarations, 'Core input name and payload')
        name, sort, payload = row
        validate_sort(sort)
        declarations[name] = sort
        prefix = packet['prefix'] + '.' + name if encoding == 'legacy' else component(packet['prefix'], '.input/', name)
        for leaf_sort, node, expected_name in payload_leaves(sort, payload, prefix):
            require(type(node) is dict and node.get('op') == 'var' and node.get('data') == expected_name, 'exact named symbolic input leaf')
            roots.append((leaf_sort, node, expected_name))
    require(list(declarations) == sorted(declarations), 'canonical Core input order')
    core_profile = validate_core(packet['body'], declarations, errors)
    require(packet['core-profile'] == core_profile and (encoding != 'legacy' or core_profile == 'bl/core-int-bool-outcomes-v1'), 'Core profile and record input encoding')
    layout = {name: sort for sort, _, name in roots}
    require(len(layout) == len(roots), 'unique scalar input leaves')
    out = packet['outcome']
    require(type(out) is dict and set(out) == {'ok', 'error', 'value'}, 'symbolic Core outcome fields')
    roots += [('bool', out['ok'], None), ('int', out['error'], None), *payload_leaves(packet['body']['sort'], out['value'])]
    names = terms.validate_roots([node for _, node, _ in roots], [sort for sort, _, _ in roots])
    require(names == layout, 'symbolic outcome variables belong to the declared input layout')
    require(canonical_identity(packet) == packet['identity'], 'canonical Core term packet identity mismatch')
    return sorted(n for n, s in layout.items() if s == 'int'), sorted(n for n, s in layout.items() if s == 'bool')


def core_sort(sort):
    if not record(sort):
        return 'BeamLispCore.Ty.' + sort[0]
    result = 'BeamLispCore.Ty.unit'
    for _, child in reversed(sort[1]):
        result = ('BeamLispCore.Ty.prod', core_sort(child), result)
    return result


def local(sort, index):
    slot = 'Var.zero'
    for _ in range(index):
        slot = ('Var.succ', slot)
    return ('localExpr', core_sort(sort), slot)


def project_field(base, sort, field):
    for name, _ in sort[1]:
        if name == field:
            return ('Expr.first', base)
        base = ('Expr.second', base)
    raise ValueError('missing projection field')


def ordered_operands(args, scope, errors):
    return [core_expr(child, [None] * index + scope, errors) for index, child in enumerate(args)]


def bind_operands(operands, result):
    for operand in reversed(operands):
        result = ('Expr.bind', operand, result)
    return result


def product(sort, value, pair, empty):
    result = empty
    for name, child in reversed(sort[1]):
        result = (pair, value(name, child), result)
    return result


def core_expr(node, scope, errors):
    op, sort, args, data = (node[field] for field in ['op', 'sort', 'args', 'data'])
    if op == 'const':
        return ('intLit', int_data(data)) if sort == ['int'] else ('boolLit', data)
    if op == 'local':
        return local(sort, scope.index(data))
    if op == 'raise':
        return ('raiseExpr', core_sort(sort), errors[data])
    if op == 'let':
        return ('Expr.bind', core_expr(args[0], scope, errors), core_expr(args[1], [data, *scope], errors))
    if op in {'record', 'record-assoc'}:
        positions = {name: len(data) - 1 - index for index, name in enumerate(data)}
        base = local(sort, len(data))
        def field(name, child):
            if name in positions:
                return local(child, positions[name])
            return project_field(base, sort, name)
        return bind_operands(ordered_operands(args, scope, errors), product(sort, field, 'Expr.pair', 'unitLit'))
    if op == 'field':
        base = core_expr(args[0], scope, errors)
        if len(args) == 1:
            return project_field(base, args[0]['sort'], data)
        eager = core_expr(args[1], [None, *scope], errors)
        selected = project_field(local(args[0]['sort'], 0), args[0]['sort'], data)
        return ('Expr.bind', base, ('Expr.seq', eager, selected))
    children = [core_expr(arg, scope, errors) for arg in args]
    if op in {'do', 'and', 'or'}:
        result = children.pop() if op == 'do' else ('boolLit', op == 'and')
        for child in reversed(children):
            result = ('Expr.seq', child, result) if op == 'do' else ('Expr.boolOp', 'BoolOp.' + op, child, result)
        return result
    if op in INTEGER_OPS:
        return ('Expr.intOp', 'IntOp.' + op, *children)
    if op in COMPARISONS:
        return ('Expr.comparison', 'Comparison.' + op, *children)
    if op == 'eq':
        return ('Expr.equal', core_sort(args[0]['sort']), *children)
    return ({'neg': 'Expr.neg', 'not': 'Expr.boolNot', 'if': 'Expr.cond'}[op], *children)


def int_data(value):
    return ('Int.ofNat', value) if value >= 0 else ('Int.negSucc', -value - 1)


def render(data):
    if type(data) is tuple:
        return '(' + ' '.join(map(render, data)) + ')'
    if type(data) is list:
        return k.emit_list(map(render, data))
    if type(data) is bool:
        return str(data).lower()
    return str(data)


class Decoder(terms.TermDecoder):
    def data(self):
        token = self.take()
        if token == '(':
            values = []
            while self.tokens[self.at] != ')':
                values.append(self.data())
            self.take(')')
            return tuple(values)
        if token == '[':
            self.at -= 1
            return self.list(self.data)
        if token.isdecimal():
            return int(token)
        if token in {'true', 'false'}:
            return token == 'true'
        return token

    def payload(self, sort, value, integers, booleans):
        if record(sort):
            for (_, child), entry in zip(sort[1], value):
                self.take('('); self.take('Payload.pair')
                self.payload(child, entry[1], integers, booleans)
            self.take('Payload.unit')
            for _ in sort[1]:
                self.take(')')
        else:
            self.take('('); self.take('Payload.integer' if sort == ['int'] else 'Payload.boolean')
            require(terms.faithful(value, self.term(), integers, booleans), 'generated payload term differs from original')
            self.take(')')


def input_env(packet, integers, booleans):
    def value(sort, payload):
        if record(sort):
            fields = dict(payload)
            return product(sort, lambda name, child: value(child, fields[name]), 'Prod.mk', 'Unit.unit')
        names, env = (integers, 'i') if sort == ['int'] else (booleans, 'b')
        return (env, names.index(payload['data']))
    result = 'Env.nil'
    for _, sort, payload in reversed(packet['inputs']):
        result = ('Env.cons', value(sort, payload), result)
    return result


def emit_payload(sort, value, integers, booleans):
    if record(sort):
        fields = dict(value)
        result = 'Payload.unit'
        for name, child in reversed(sort[1]):
            result = '(Payload.pair ' + emit_payload(child, fields[name], integers, booleans) + ' ' + result + ')'
        return result
    tag = 'integer' if sort == ['int'] else 'boolean'
    return '(Payload.' + tag + ' ' + terms.emit_term(value, integers, booleans) + ')'


HEADER = '''import CoreTerms

set_option maxRecDepth 5000
set_option maxHeartbeats 6000000
set_option linter.unusedSimpArgs false
set_option linter.unusedVariables false
open BeamLispCore FormalTerms FormalRefutation CoreTerms
'''
TAIL = '''

theorem errorCatalogueRoundTrip : errorCodes.all (fun code => errorCode errorCodes (errorName code) == Int.ofNat code) = true := by decide

private theorem representedErrorCode (code : Nat) (present : code ∈ errorCodes) :
    errorCode errorCodes (errorName code) = Int.ofNat code :=
  beq_iff_eq.mp (List.all_eq_true.mp errorCatalogueRoundTrip code present)

private theorem zeroDivisorCode : errorCode errorCodes "zero-divisor" = 1 :=
  representedErrorCode 1 (by decide)

theorem coreTermCorrespondence : ∀ (i : Nat → Int) (b : Nat → Bool),
    agrees (BeamLispCore.eval originalProgram (originalInputs i b))
      (symbolicOK.eval i b) (symbolicValue.eval i b) (symbolicError.eval i b) (errorCode errorCodes) := by
  intro i b
  simp [originalProgram, originalInputs, symbolicOK, symbolicValue, symbolicError,
    BeamLispCore.eval, Env.lookup, Outcome.bind, Payload.eval, eval_choice,
    Term.eval.eq_1, Term.eval.eq_2, Term.eval.eq_3, Term.eval.eq_4, Term.eval.eq_5,
    Term.eval.eq_6, Term.eval.eq_7, Term.eval.eq_8, Term.eval.eq_9, Term.eval.eq_10,
    Term.eval.eq_11, Term.eval.eq_12, Term.eval.eq_13, Term.eval.eq_14, Term.eval.eq_15,
    Term.eval.eq_16, Term.eval.eq_17, Term.eval.eq_18, Term.eval.eq_19,
    apply_quot, apply_rem, apply_mod, Comparison.apply, BoolOp.apply, valueEq]
  all_goals try simp [IntOp.apply, Outcome.bind, divide, modulus,
    known_and, known_or, known_not, quotientValue, remainderValue, modulusValue, zeroDivisorCode]
  all_goals try dsimp (config := { instances := true }) only [FormalTerms.Ty.Value, BeamLispCore.Value] at *
  all_goals repeat' (split <;> simp_all [IntOp.apply, Outcome.bind, divide, modulus,
    known_and, known_or, known_not, quotientValue, remainderValue, modulusValue, zeroDivisorCode])
  all_goals try simp (disch := decide) [representedErrorCode, zeroDivisorCode]
  all_goals try dsimp (config := { instances := true }) only [FormalTerms.Ty.Value, BeamLispCore.Value] at *
  all_goals try simp_all
  all_goals first | rfl | decide | omega

#print axioms coreTermCorrespondence
#print axioms errorCatalogueRoundTrip
'''


def sections(packet, integers, booleans):
    context = render([core_sort(sort) for _, sort, _ in packet['inputs']])
    result = render(core_sort(packet['body']['sort']))
    return [('originalProgram : Expr ' + context + ' ' + result,
             core_expr(packet['body'], [name for name, _, _ in packet['inputs']], dict(packet['errors']))),
            ('originalInputs (i : Nat → Int) (b : Nat → Bool) : Env ' + context, input_env(packet, integers, booleans)),
            ('errorCodes : List Nat', sorted(code for _, code in packet['errors'])),
            ('symbolicOK : Term FormalTerms.Ty.boolean', None),
            ('symbolicValue : Payload ' + result, None),
            ('symbolicError : Term FormalTerms.Ty.integer', None)]


def source(packet, integers, booleans, *, namespace=None):
    out = packet['outcome']
    values = [terms.emit_term(out['ok'], integers, booleans), emit_payload(packet['body']['sort'], out['value'], integers, booleans),
              terms.emit_term(out['error'], integers, booleans)]
    values = iter(values)
    opening, closing = proof_scope(namespace)
    return HEADER + opening + ''.join('\n\ndef ' + name + ' :=\n' + (render(data) if data is not None else next(values))
                                      for name, data in sections(packet, integers, booleans)) + TAIL + closing


def proof_scope(namespace):
    require(namespace in {None, 'BeforeCore', 'AfterCore'}, 'supported Core proof scope')
    if namespace is None:
        return '', ''
    return f'\nnamespace {namespace}\n', f'\nend {namespace}\n'


def verify_source(text, packet, integers, booleans, *, namespace=None):
    opening, closing = proof_scope(namespace)
    header, tail = HEADER + opening, TAIL + closing
    require(text.startswith(header) and text.endswith(tail), 'fixed Core theorem template')
    definitions = text[len(header):-len(tail)].split('\n\ndef ')
    require(definitions.pop(0) == '', 'Core definitions start')
    layout = sections(packet, integers, booleans)
    require(len(definitions) == len(layout), 'exact Core declarations')
    for definition, (name, data) in zip(definitions, layout):
        header = name + ' :=\n'
        require(definition.startswith(header), 'Core declaration type')
        decoder = Decoder(definition[len(header):])
        if data is not None:
            require(decoder.data() == data, 'generated Core expression, layout or catalogue differs')
        elif name.startswith('symbolicValue'):
            decoder.payload(packet['body']['sort'], packet['outcome']['value'], integers, booleans)
        else:
            node = packet['outcome']['ok' if name.startswith('symbolicOK') else 'error']
            require(terms.faithful(node, decoder.term(), integers, booleans), 'generated outcome term differs from original')
        require(decoder.at == len(decoder.tokens), 'trailing Core declaration data')


def checked_kernel():
    pin = json.loads((P / 'metatheory/core-terms-pin.json').read_text())
    tool = json.loads((P / 'metatheory/tool-pin.json').read_text())
    lean = Path(tool['path']) / 'bin/lean'
    require(k.sha(lean) == tool['binary_sha256'], 'Lean binary pin')
    libraries = {}
    for module, dependency in pin['libraries'].items():
        file = P / dependency['pin']
        require(k.sha(file) == dependency['sha256'], 'Core model dependency pin')
        libraries[module] = json.loads(file.read_text())
    libraries['CoreTerms'] = pin
    require(set(libraries) == {'Refutation', 'Terms', 'Core', 'CoreTerms'}, 'exact Core term model library set')
    for record_pin in libraries.values():
        for key in ['source', 'compiled']:
            require(k.sha(P / record_pin[key]['path']) == record_pin[key]['sha256'], 'Core term model artifact pin')
    return lean, libraries


def copy_library(library, libraries):
    library.mkdir()
    for module, pin in libraries.items():
        shutil.copyfile(P / pin['compiled']['path'], library / (module + '.olean'))


def run(path, output, axiom_policy='lean-standard', *, module='Check'):
    require(axiom_policy in terms.AXIOM_POLICIES, 'supported Core term axiom policy')
    require(module in {'Check', 'CoreCheck', 'BeforeCore', 'AfterCore'}, 'Core term check module')
    namespace = module if module in {'BeforeCore', 'AfterCore'} else None
    output.mkdir(parents=True, exist_ok=True)
    (output / 'Check.olean').unlink(missing_ok=True)
    (output / 'result.json').unlink(missing_ok=True)
    require(path.stat().st_size <= k.MAX_BYTES, 'Core term packet byte capacity')
    packet = k.load_packet(path)
    integers, booleans = validate(packet)
    text = source(packet, integers, booleans, namespace=namespace)
    verify_source(text, packet, integers, booleans, namespace=namespace)
    lean, libraries = checked_kernel()
    (output / 'Check.lean').write_text(text)
    with tempfile.TemporaryDirectory(prefix='enchant-core-terms-') as temporary:
        work = Path(temporary)
        library = work / 'library'
        copy_library(library, libraries)
        check = work / (module + '.lean')
        check.write_text(text)
        with (output / 'lean.txt').open('w') as log:
            completed = subprocess.run([str(lean), '--root=' + str(work), '-o', str(work / 'Check.olean'), str(check)],
                                       cwd=work, env=dict(os.environ, LEAN_PATH=str(library)), stdout=log,
                                       stderr=subprocess.STDOUT, timeout=120)
        transcript = (output / 'lean.txt').read_text()
        require(completed.returncode == 0 and 'sorryAx' not in transcript and 'warning:' not in transcript, 'Lean did not accept Core term correspondence')
        prefix = namespace + '.' if namespace else ''
        audits = proof_tools.theorem_audits(transcript, {prefix + 'coreTermCorrespondence', prefix + 'errorCatalogueRoundTrip'})
        require(all(set(deps) <= terms.AXIOM_POLICIES[axiom_policy] for deps in audits.values()), 'Core term axioms exceed policy')
        shutil.copyfile(work / 'Check.olean', output / 'Check.olean')
    result = {'schema': 'enchant.formal.core-term-execution.v1', 'status': 'checked-core-term-correspondence',
              'packet': packet['identity'], 'core': packet['core'], 'subject': packet['subject'],
              'scope': 'all-typed-inputs-of-this-contained-core-and-exact-symbolic-outcome',
              'source_sha256': k.sha(output / 'Check.lean'), 'olean_sha256': k.sha(output / 'Check.olean'),
              'axioms': audits, 'axiom_policy': axiom_policy,
              'source_data': 'independently-decoded-and-compared', 'core_data_model_codec': 'reviewed',
              'subject_connection': 'requires-fresh-BL-reconstruction', 'source_compiler_preservation': 'not-established',
              'compiler_proof_authority': False}
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packet', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--axiom-policy', choices=sorted(terms.AXIOM_POLICIES), default='lean-standard')
    args = parser.parse_args()
    try:
        result = run(args.packet, args.output, args.axiom_policy)
        print(json.dumps({key: result[key] for key in ['status', 'packet', 'axioms']}))
    except (ValueError, OSError, subprocess.TimeoutExpired, RecursionError, IndexError) as error:
        result = {'status': 'not-accepted', 'reason': str(error), 'compiler_proof_authority': False}
        (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result))
        raise SystemExit(1)


if __name__ == '__main__':
    main()

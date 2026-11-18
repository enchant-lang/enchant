#!/usr/bin/env python3
"""Rank the A3 attribution outputs. Starts no process.

  analyze.py native RUN_DIR      -> RUN_DIR/native-summary.json + text tables
  analyze.py beam RUN_DIR        -> RUN_DIR/beam-summary.json + text tables

Native: STACK rows (sampling pass) give shares; COUNT/EDGE rows (counting
pass) give exact call counts. A compiled BL frame is "sub:UNIT#:ID" (its
return point inside its unit); CODE rows give each linked definition's entry
id, and a return point belongs to the definition whose entry precedes it in
the unit's numbering (direction chosen by the read-phase check below).
"""
import bisect
import collections
from functools import cache
import json
import re
import sys
from pathlib import Path

HOST_CATEGORIES = [
    # (category, regex over host procedure names), first match wins
    ('tick', r'^h-tick$'),
    ('keyword-build', r'^(bl-key|native-key-intern|native-scalar-keyword-intern|##string->symbol|##make-interned-symbol|string->symbol|##symbol-hash|##string=\?-hash|native-utf16-fragment\?)$'),
    ('key-compare', r'^(bl-key-compare|native-scalar-string-compare-from|native-key-rank|native-key-compare-ranked|native-colon-symbol\?|native-scalar-key\?|native-compare-.*|native-term-compare|native-compare-atoms|bl-key-equal\?)$'),
    ('map', r'^(bl-get|bl-assoc|bl-map|bl-empty-map|bl-dissoc|bl-set-.*|native-(tree|small-map|map|set|raw-map|height|left|right|node|balance|rotate|struct-fields|assert-map|pdict).*|kernel-leaf-(maps?|is-map-key).*|h-set-.*|h-map-.*)$'),
    ('arith', r'^(native-num|native-arith-.*|native-decimal\?|native-struct-module|native-number\?|native-ratio|native-erlang-number\?|bl-arithmetic|h-is-int|native-number-compare)$'),
    ('equality', r'^(kernel-.*equal\?|kernel-simple-equal|bl-equal\?|native-erlang-equal\?|kernel-leaf-(==|=:=|/=|=/=))$'),
    ('call-dispatch', r'^(bl-invoke|native-resolve-call|native-multi-callable\?|##apply|apply|native-arity-entry|native-callable-accepts\?|bl-nth|bl-count|native-take|native-drop|bl-is-nil|bl-tag\?)$'),
    ('text', r'^(##wr.*|native-join|##string-append.*|string-append|native-utf8.*|native-byte-slice|native-utf16.*|native-binary-.*|native-scalar-to-str|h-to-str|h-str-.*|native-string-.*|native-char-data|list->string|string->list|##write.*|##display.*|number->string|##number->string|native-text.*|native-graphemes|string=\?|substring|##substring)$'),
    ('list', r'^(length|reverse|append|list->vector|vector->list|##length|##reverse|##append|kernel-leaf-reverse|native-with-matches|list-ref|kernel-list-to-tuple)$'),
]


LEAF_CATEGORIES = [
    ('map', r'^leaf:(maps|Elixir\.Map|Elixir\.MapSet|Elixir\.BeamLisp\.(Set|Sorted|Transient))/'),
    ('equality', r'^leaf:erlang/(=:=|==|/=|=/=)/'),
    ('text', r'^leaf:(unicode|binary|string|Elixir\.String|Elixir\.IO|Elixir\.Regex|Elixir\.Kernel|erlang/(iolist|list_to_binary|binary_to|atom_to_binary|integer_to_binary|byte_size))'),
    ('list', r'^leaf:(lists|Elixir\.Enum|Elixir\.List|erlang/(list_to_tuple|tuple_to_list|length|hd|tl|element|setelement|tuple_size|make_tuple|append_element))'),
    ('keyword-build', r'^leaf:(erlang/(binary_to_atom|list_to_atom|binary_to_existing_atom)|Elixir\.BeamLisp\.AtomGuard)'),
    ('runtime-state', r'^leaf:(persistent_term|atomics|erlang/(get|put|erase)|Elixir\.Process|Elixir\.BeamLisp\.(Env|Loader|Link|CompilerData))'),
]


def host_category(name):
    if name is None:
        return None
    if name.startswith('leaf:'):
        for cat, rx in LEAF_CATEGORIES:
            if re.match(rx, name):
                return cat
        return 'leaf-other'
    if name.startswith('host-lambda:'):
        return 'host-lambda'
    for cat, rx in HOST_CATEGORIES:
        if re.match(rx, name):
            return cat
    if name.startswith('##'):
        return 'gambit-runtime'
    return 'host-other'


def category_counts(c):
    out = collections.Counter()
    for k, v in c.items():
        if k.startswith('host:'):
            out[host_category(k[5:])] += v
        elif k.startswith('leaf:'):
            out[host_category(k)] += v
    return dict(out.most_common())


def parse_native(log):
    rows = collections.defaultdict(list)
    for line in log.read_text(errors='replace').splitlines():
        tag, _, rest = line.partition('\t')
        if tag in ('STACK', 'COUNT', 'EDGE', 'CODE', 'SAMPLES', 'SELF', 'CALIB'):
            rows[tag].append(rest.split('\t'))
    return rows


class CodeMap:
    """Return-point id -> enclosing linked BL definition.

    Gambit numbers a unit's subprocedures so that a lambda's return points
    follow its entry (CALIB rows: the return point after the entry (h-tick)
    is always entry+2..entry+N). So the owner of a return id is the nearest
    entry at or below it. The topmost entry of a unit has no upper neighbour;
    above it lies the unit's host Scheme (unnamed host lambdas), so its range
    is capped at the largest calibrated offset of any definition + slack."""
    def __init__(self, code_rows, calib_rows=()):
        self.units = collections.defaultdict(list)
        for label, where in code_rows:
            unit, _, ident = where.rpartition(':')
            self.units[unit].append((int(ident), label))
        for v in self.units.values():
            v.sort()
        self.exact = {}
        entry = {label[3:]: int(where.rpartition(':')[2]) for label, where in code_rows if label.startswith('bl:')}
        span = 0
        for key, label, _ in calib_rows:
            if label.startswith('slot:'):
                name = label[5:].rpartition('/')[0]
                rid = int(key.rpartition(':')[2])
                self.exact.setdefault(key[4:], 'bl:' + name)
                if name in entry and 0 < rid - entry[name] < 400:
                    span = max(span, rid - entry[name])
        self.cap = max(span, 16) * 2
        self.direction = 'below'

    def lookup(self, unit, ident, direction=None):
        direction = direction or self.direction
        entries = self.units.get(unit)
        if not entries:
            return None
        ids = [e[0] for e in entries]
        if direction == 'below':
            # owner entry id <= return id: nearest smaller-or-equal
            i = bisect.bisect_right(ids, ident) - 1
            if i < 0:
                return None
            if i == len(entries) - 1 and entries[i][1].startswith('bl:') and ident - entries[i][0] > self.cap:
                return None
            return entries[i][1]
        i = bisect.bisect_left(ids, ident)
        return entries[i][1] if i < len(entries) else None


NAMED_BINDING = re.compile(r"(lv|v)_([0-9]+(?:_[0-9]+)*)(?:\$(?:[0-9]+|v|g))?$")


@cache
def named_frame(raw):
    match = NAMED_BINDING.fullmatch(raw)
    if match:
        prefix, spelling = match.groups()
        name = ''.join(chr(int(code)) for code in spelling.split('_'))
        if '/' in name:
            return ('host', 'leaf:' + name) if prefix == 'lv' else ('bl', name)
    return None


def frame(raw, codes, direction=None):
    if raw.startswith('sub:'):
        body = raw[4:]
        unit, _, ident = body.rpartition(':')
        name = codes.exact.get(body) if direction is None else None
        name = name or codes.lookup(unit, int(ident), direction)
        if not name:
            return ('host', 'host-lambda:' + unit)
        kind, _, rest = name.partition(':')
        return ('bl', rest) if kind == 'bl' else ('host', name if kind == 'leaf' else rest)
    if raw.startswith('A-') or raw.startswith('##interp'):
        return ('driver', raw)
    if raw.startswith(('v_', 'lv_')):
        decoded = named_frame(raw)
        if decoded:
            return decoded
    return ('host', raw)


def ns_of(defn):
    return defn.rpartition('/')[0] if '/' in defn else defn


# Pipeline buckets for the ranking: a sample's innermost host run (the host
# operation BL code invoked) and the BL frame that invoked it decide.
NATIVE_BUCKETS = [
    ('quoted set literal rebuilt on every call', 'N1', lambda run, op, bl: any(f in ('native-set-from-list', 'bl-set-from-list') for f in run)),
    ('struct/kind test on a set or vector materialises its fields', 'V2b', lambda run, op, bl: 'native-struct-fields' in run),
    ('grapheme String.length and codepoint slicing (subs, split-slash)', 'V2e', lambda run, op, bl: any(f in ('leaf:Elixir.String/length/1', 'native-with-matches', 'native-string-slice', 'native-byte-slice', 'native-binary-string-split') or f.startswith('native-utf8') for f in run)),
    ('variadic / multi-arity dispatch through bl-invoke', 'N3', lambda run, op, bl: op in ('bl-invoke', 'native-resolve-call', '##apply', 'native-multi-callable?')),
    ('map and set operations: tree insert/find, keyword keys compared as strings', 'V2a+V2c', lambda run, op, bl: host_category(op) in ('map', 'key-compare')),
    ('keywords interned at run time (bl-key / string->symbol)', 'N1+V2a', lambda run, op, bl: host_category(op) == 'keyword-build'),
    ('generic arithmetic (native-num, decimal? probes)', 'E1+E2', lambda run, op, bl: host_category(op) == 'arith'),
    ('generic equality (kernel-exact-equal?)', 'E6', lambda run, op, bl: host_category(op) == 'equality'),
    ('h-tick', 'N4', lambda run, op, bl: op == 'h-tick'),
    ('text assembly and string operations', 'C2/V2e', lambda run, op, bl: host_category(op) == 'text'),
    ('Gambit runtime', '-', lambda run, op, bl: host_category(op) == 'gambit-runtime'),
    ('list BIFs and Enum leaves', '-', lambda run, op, bl: host_category(op) in ('list', 'leaf-other', 'runtime-state') or (op or '').startswith('leaf:')),
    ('other host procedures', '-', lambda run, op, bl: op is not None),
    ('compiled rt.bl kernel code (self)', 'N1+N2', lambda run, op, bl: bl and ns_of(bl) in ('rt', 'core')),
    ('compiled compiler / reader / emitter code (self)', 'E5', lambda run, op, bl: bl is not None),
]


def native_buckets(stacks, codes):
    out = collections.defaultdict(collections.Counter)
    for phase, n, fr in stacks:
        mapped = [frame(raw, codes) for raw in fr]
        mapped = [m for m in mapped if m[0] != 'driver'] or [('driver', 'driver')]
        i = 0
        while i < len(mapped) and mapped[i][0] == 'host':
            i += 1
        run = [m[1] for m in mapped[:i]]
        op = run[-1] if run else None
        bl = mapped[i][1] if i < len(mapped) and mapped[i][0] == 'bl' else None
        for name, item, rule in NATIVE_BUCKETS:
            if rule(run, op, bl):
                out[phase][(name, item)] += n
                out['all'][(name, item)] += n
                break
        else:
            out[phase][('unattributed', '-')] += n
            out['all'][('unattributed', '-')] += n
    return {p: [[k[0], k[1], v, round(100.0 * v / sum(c.values()), 1)] for k, v in c.most_common()]
            for p, c in out.items()}


def native(run):
    rows = parse_native(run / 'native.log')
    calib = parse_native(Path(sys.argv[3]) / 'native.log')['CALIB'] if len(sys.argv) > 3 else rows['CALIB']
    codes = CodeMap(rows['CODE'], calib)
    stacks = [(r[0], int(r[1]), r[2:]) for r in rows['STACK']]
    # Direction check: read-phase innermost BL frames should be reader/rt code.
    check = {}
    for direction in ('below', 'above'):
        hit = tot = 0
        for phase, n, fr in stacks:
            if phase != 'read':
                continue
            for raw in fr:
                kind, name = frame(raw, codes, direction)
                if kind == 'bl':
                    tot += n
                    hit += n if ns_of(name) in ('reader', 'reader-node', 'rt', 'core', 'host.compiler-data') else 0
                    break
        check[direction] = hit / tot if tot else 0
    codes.direction = max(check, key=check.get)
    phase_total = collections.Counter()
    self_name = collections.defaultdict(collections.Counter)
    entry_cat = collections.defaultdict(collections.Counter)
    entry_op = collections.defaultdict(collections.Counter)
    bl_self = collections.defaultdict(collections.Counter)
    bl_self_ns = collections.defaultdict(collections.Counter)
    inclusive = collections.defaultdict(collections.Counter)
    host_by_caller = collections.defaultdict(collections.Counter)
    for phase, n, fr in stacks:
        phase_total[phase] += n
        mapped = [frame(raw, codes) for raw in fr]
        mapped = [m for m in mapped if m[0] != 'driver'] or [('driver', 'driver')]
        kind, name = mapped[0]
        self_name[phase][kind + ':' + str(name)] += n
        # The contiguous run of host frames at the top of the stack is one host
        # operation; its outermost frame is the operation BL code invoked.
        i = 0
        while i < len(mapped) and mapped[i][0] == 'host':
            i += 1
        if i > 0:
            op = mapped[i - 1][1]
            cat = host_category(op)
            caller = mapped[i][1] if i < len(mapped) else 'top'
            entry_cat[phase][cat] += n
            entry_op[phase][op] += n
            host_by_caller[phase][(cat, str(caller))] += n
        else:
            entry_cat[phase]['bl-code' if kind == 'bl' else kind] += n
            if kind == 'bl':
                bl_self[phase][name] += n
                bl_self_ns[phase][ns_of(name)] += n
        seen = set()
        for k, nm in mapped:
            if k == 'bl' and nm not in seen:
                seen.add(nm)
                inclusive[phase][nm] += n
    counts = collections.defaultdict(collections.Counter)
    for phase, label, c in rows['COUNT']:
        counts[phase][label] += int(c)
    edges = collections.defaultdict(collections.Counter)
    for phase, caller, callee, c in rows['EDGE']:
        edges[phase][(caller, callee)] += int(c)

    def top(counter, n=25, total=None):
        total = total or sum(counter.values()) or 1
        return [[k if isinstance(k, str) else ' <- '.join(k), v, round(100.0 * v / total, 1)]
                for k, v in counter.most_common(n)]

    phases = ['read', 'compile', 'emit']
    all_samples = sum(phase_total.values())
    summary = {'direction': codes.direction, 'direction_check': check,
               'samples': dict(phase_total), 'samples_total': all_samples, 'phases': {}}
    for p in phases:
        c = counts[p]
        kinds = collections.Counter()
        for label, v in c.items():
            kinds[label.split(':', 1)[0]] += v
        fast = {}
        for (caller, callee), v in edges[p].items():
            if callee == 'slot:rt/kind-kind/1' and caller.startswith('slot:rt/'):
                fast[caller] = v
        fastpath = []
        for caller, falls in sorted(fast.items(), key=lambda kv: -kv[1])[:15]:
            calls = c.get(caller, 0)
            fastpath.append([caller, calls, falls, round(100.0 * (calls - falls) / calls, 1) if calls else None])
        leaf_fall = collections.Counter()
        for (caller, callee), v in edges[p].items():
            if callee.startswith('host:kernel-leaf-') and not caller.startswith('host:kernel-leaf-'):
                leaf_fall[(callee, caller)] += v
        summary['phases'][p] = {
            'samples': phase_total[p],
            'share_of_pipeline': round(100.0 * phase_total[p] / all_samples, 1) if all_samples else None,
            'entry_category': top(entry_cat[p], 20, phase_total[p]),
            'host_entry_op': top(entry_op[p], 30, phase_total[p]),
            'host_op_by_bl_caller': top(host_by_caller[p], 30, phase_total[p]),
            'bl_self_by_ns': top(bl_self_ns[p], 15, phase_total[p]),
            'bl_self': top(bl_self[p], 30, phase_total[p]),
            'bl_inclusive': top(inclusive[p], 30, phase_total[p]),
            'innermost_frame': top(self_name[p], 30, phase_total[p]),
            'counts_by_kind': dict(kinds),
            'h_tick': c.get('host:h-tick', 0),
            'top_slots': [[k, v] for k, v in collections.Counter({k: v for k, v in c.items() if k.startswith('slot:')}).most_common(30)],
            'top_leaves': [[k, v] for k, v in collections.Counter({k: v for k, v in c.items() if k.startswith('leaf:')}).most_common(20)],
            'top_host': [[k, v] for k, v in collections.Counter({k: v for k, v in c.items() if k.startswith('host:')}).most_common(40)],
            'host_counts_by_category': category_counts(c),
            'kernel_fast_path': fastpath,
            'kernel_template_fallthrough': [[f'{a} <- {b}', v] for (a, b), v in leaf_fall.most_common(15)],
            'generic_slot_calls': sum(v for k, v in c.items() if k.startswith('slot:') and k.endswith('/g')),
            'arity_slot_calls': sum(v for k, v in c.items() if k.startswith('slot:') and re.search(r'/\d+$', k)),
            'variadic_slot_calls': sum(v for k, v in c.items() if k.startswith('slot:') and k.endswith('/v')),
        }
    summary['buckets'] = native_buckets(stacks, codes)
    (run / 'native-summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    return summary


BEAM_GROUPS = [
    # (group, regex over "ns/fn"), first match wins
    ('var-invocation gate (N3)', r'^(rt/(source-invocation!|source-invocation1!|source-invocation2!|call-invoke|invoke|source-callable!)|Env/(ns_ready\?|own-module|fetch|fetch!|epoch_ref|current_epoch|chain|fetch_exact|peek|lookup)|Loader/ensure_ready|persistent_term/get|atomics/get)$'),
    ('file/source resolution (bare compiler API)', r'^(Path|File|file|filename|gen|gen_server|prim_file|erlang/(monitor|demonitor|whereis)|IO|Keyword|Loader/(find_file|source_relatives|search_dirs|resolvable\?|source_on_path\?|realm_facts|package_provider|doc-ext-list|source_decl|source_decls)|binary/last|code/.*|Code/.*)/?'),
    ('Env/Loader compile-time resolution', r'^(Env|Loader|ets|GenServer|os|erlang/(send|system_info|binary_to_atom)|Tuple)/'),
    ('nth/first/count chain (N2)', r'^rt/(nth|k-nth|nth-list|lists-at|nth-lazy|first|k-first|rest|k-rest|next|k-next|seq|k-seq|count|k-count|count-list|empty\?|k-empty\?|second)$|^core/(second|first|nth|count)$'),
    ('key paths: get/assoc/hash (Q3, V2c)', r'^rt/(coll-get|get|facade-get|hash-hash-key|coll-hash-key|hash_key|coll-assoc|assoc|coll-contains\?|contains\?|dissoc|find|map-join)$|^maps/|^Map/'),
    ('generic equality = / not= (E1, E6)', r'^rt/(eqv|k-eqv|not_|call-not-|identical\?|call-identical\?)$|^core/(not=|=|nil\?)$'),
    ('variadic constructors tuple/list (E5)', r'^core/(tuple__bl_v|list__bl_v|vector__bl_v|hash-map__bl_v)$|^erlang/list_to_tuple$'),
    ('classifier kind-kind (N2 fallthrough)', r'^rt/(kind-kind|struct-of\?|is-kind\?|kind-.*)$'),
    ('arith helpers inc/dec (E1, E2)', r'^core/(inc|dec|\+|-|<|>|<=|>=|zero\?|pos\?|neg\?)$|^rt/(num-.*|neg\?|pos\?|zero\?)$|^Num/'),
    ('reader own code', r'^reader/'),
    ('compiler / anf own code', r'^(compiler|anf|sugar|core-ext|syntax|binding|expand|lower|diag)/'),
    ('emitter own code', r'^native\.(scheme|eval|intrinsics)/'),
    ('reader-node / CompilerData', r'^(reader-node|CompilerData)/'),
    ('Enum / lists / text BIFs', r'^(Enum|lists|List|String|string|unicode|binary|erlang/(iolist_to_binary|binary_to_atom|atom_to_binary|integer_to_binary)|AtomGuard|Vector)/'),
]


def beam_group(name):
    for g, rx in BEAM_GROUPS:
        if re.match(rx, name):
            return g
    return 'other'


def beam(run):
    prof = collections.defaultdict(list)
    totals = {}
    for line in (run / 'beam.log').read_text(errors='replace').splitlines():
        parts = line.split('\t')
        if parts[0] == 'PROF':
            _, phase, ns, fn, calls, us, rt = parts
            prof[phase].append((ns, fn, int(calls), int(us), rt == 'true'))
        elif parts[0] == 'A3_TOTAL':
            totals[parts[1]] = int(parts[2])
    summary = {'totals_us': totals, 'phases': {}}
    for phase, rs in prof.items():
        us_total = sum(r[3] for r in rs) or 1
        by_ns = collections.Counter()
        for ns, fn, calls, us, rt in rs:
            by_ns[ns] += us
        rows = sorted(rs, key=lambda r: -r[3])
        groups = collections.Counter()
        gcalls = collections.Counter()
        for ns, fn, calls, us, rt in rs:
            g = beam_group(f'{ns}/{fn}')
            groups[g] += us
            gcalls[g] += calls
        summary['phases'][phase] = {
            'profiled_us': us_total,
            'calls': sum(r[2] for r in rs),
            'by_module': [[k, v, round(100.0 * v / us_total, 1)] for k, v in by_ns.most_common(20)],
            'groups': [[k, v, gcalls[k], round(100.0 * v / us_total, 1)] for k, v in groups.most_common()],
            'top': [[f'{r[0]}/{r[1]}', r[2], r[3], round(100.0 * r[3] / us_total, 1)] for r in rows[:40]],
        }
    (run / 'beam-summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    return summary


def main():
    mode, run = sys.argv[1], Path(sys.argv[2])
    summary = native(run) if mode == 'native' else beam(run)
    print(json.dumps(summary, indent=1)[:200000])


if __name__ == '__main__':
    main()

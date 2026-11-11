"""Compile fresh Core/term premises and link a checked composition theorem."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import core_term_check as core
import term_refutation as terms
from witness_kernel import theorem_audits

k, require = terms.k, terms.require


def check_linked(packet, text, output, *, module, premises, lean, libraries, axiom_policy, expected_audits, failure):
    """Import only objects produced by this invocation's premise checkers."""
    (output / (module + '.lean')).write_text(text)
    with tempfile.TemporaryDirectory(prefix='enchant-core-composition-') as temporary:
        work = Path(temporary)
        library = work / 'library'
        core.copy_library(library, libraries)
        imported = {}
        for side, premise_module in premises:
            leaf = packet[side]
            check_premise, object_hash = ((terms.run, 'proof_olean_sha256') if 'formal/term-refutation' in leaf
                                          else (core.run, 'olean_sha256'))
            input_path = work / (side + '.json')
            input_path.write_text(json.dumps(leaf))
            premise_output = output / side
            result = check_premise(input_path, premise_output, axiom_policy, module=premise_module)
            target = library / (premise_module + '.olean')
            shutil.copyfile(premise_output / 'Check.olean', target)
            require(k.sha(target) == result[object_hash], 'fresh composed premise object identity')
            imported[side] = result[object_hash]
        check = work / (module + '.lean')
        check.write_text(text)
        compiled = check.with_suffix('.olean')
        with (output / 'lean.txt').open('w') as log:
            completed = subprocess.run([str(lean), '--root=' + str(work), '-o', str(compiled), str(check)],
                                       cwd=work, env=dict(os.environ, LEAN_PATH=str(library)), stdout=log,
                                       stderr=subprocess.STDOUT, timeout=120)
        transcript = (output / 'lean.txt').read_text()
        require(completed.returncode == 0 and 'sorryAx' not in transcript and 'warning:' not in transcript,
                failure)
        audits = theorem_audits(transcript, expected_audits)
        require(all(set(deps) <= terms.AXIOM_POLICIES[axiom_policy] for deps in audits.values()), 'composed proof axioms exceed policy')
        shutil.copyfile(compiled, output / compiled.name)
    return imported, audits

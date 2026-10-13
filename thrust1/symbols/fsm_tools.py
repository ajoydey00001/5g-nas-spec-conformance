"""Tools for learned 5GBaseChecker FSMs (Mealy machines in .dot).

  python3 fsm_tools.py stats  FSM.dot            states / transitions (paper metric: non-self-loop edges)
  python3 fsm_tools.py nas    FSM.dot OUT.dot    NAS-only projection (drop RRC inputs/outputs), minimized
  python3 fsm_tools.py issues FSM.dot            probe the Table 8 NAS issues (I3 I4 I6 I7 I9 I10 I17 I19 I20)
  python3 fsm_tools.py ltl    FSM.dot PROPS.txt  check LTL properties with NuSMV (one per line, DevLyzer syntax)

Edge labels are "input / output", start state is s0, as written by the 5GBaseChecker learner.
"""
import os
import re
import subprocess
import sys
import tempfile

EDGE = re.compile(r'^\s*(\w+)\s*->\s*(\w+)\s*\[label="\s*([^/"]+?)\s*/\s*([^"]+?)\s*"\]')

# NAS projection keeps the 16 NAS inputs of symbols/alignment.md
RRC_INPUT = re.compile(r'^(rrc_|ue_cap_)')
NULL = 'null_action'
# DevLyzer all_outputs.txt: every output the learner can report, so properties may mention any of them
ALL_OUTPUTS = ('registration_request id_response auth_response nas_sm_complete nas_sm_reject registration_complete '
               'deregistration_accept rrc_sm_complete rrc_sm_failure rrc_ue_cap_info rrc_ueinfo_response '
               'rrc_countercheck_response rrc_reconf_complete null_action config_update_complete').split()


class Mealy:
    def __init__(self, start, delta):
        self.start = start
        self.delta = delta  # (state, input) -> (next_state, output)

    @classmethod
    def from_dot(cls, path):
        delta = {}
        for line in open(path):
            m = EDGE.match(line)
            if m:
                src, dst, inp, out = m.groups()
                delta[(src, inp)] = (dst, out)
        return cls('s0', delta)

    @property
    def states(self):
        return sorted({s for s, _ in self.delta} | {d for d, _ in self.delta.values()}, key=_skey)

    @property
    def inputs(self):
        return sorted({a for _, a in self.delta})

    def run(self, word):
        s, outs = self.start, []
        for a in word:
            s, o = self.delta[(s, a)]
            outs.append(o)
        return outs

    def restrict(self, keep_input):
        delta = {(s, a): v for (s, a), v in self.delta.items() if keep_input(a)}
        return Mealy(self.start, delta)

    def minimized(self):
        """Reachable part, then Moore-style partition refinement on output signatures."""
        inputs = self.inputs
        reach, todo = {self.start}, [self.start]
        while todo:
            s = todo.pop()
            for a in inputs:
                d = self.delta[(s, a)][0]
                if d not in reach:
                    reach.add(d)
                    todo.append(d)
        block = {s: tuple(self.delta[(s, a)][1] for a in inputs) for s in reach}
        while True:
            sig = {s: (block[s],) + tuple(block[self.delta[(s, a)][0]] for a in inputs) for s in reach}
            ids = {}
            new = {s: ids.setdefault(sig[s], len(ids)) for s in sorted(reach, key=_skey)}
            if len(set(new.values())) == len(set(block.values())):
                break
            block = new
        # renumber blocks in BFS order from the start state, s0 first
        order, seen, todo = {}, set(), [self.start]
        while todo:
            s = todo.pop(0)
            if block[s] in seen:
                continue
            seen.add(block[s])
            order[block[s]] = 's%d' % len(order)
            todo += [self.delta[(s, a)][0] for a in inputs]
        delta = {}
        for (s, a), (d, o) in self.delta.items():
            if s in reach:
                delta[(order[block[s]], a)] = (order[block[d]], o)
        return Mealy('s0', delta)

    def to_dot(self, path):
        with open(path, 'w') as f:
            f.write('digraph g {\n\n')
            for s in self.states:
                f.write('\t%s [shape="circle" label="%s"];\n' % (s, s))
            for s in self.states:
                for a in self.inputs:
                    d, o = self.delta[(s, a)]
                    f.write('\t%s -> %s [label="%s / %s"];\n' % (s, d, a, o))
            f.write('\n__start0 [label="" shape="none" width="0" height="0"];\n__start0 -> s0;\n\n}\n')

    def stats(self):
        moving = sum(1 for (s, _), (d, _) in self.delta.items() if s != d)
        return len(self.states), moving


def _skey(s):
    return int(s[1:]) if s[1:].isdigit() else s


# --- Table 8 NAS issues (PLAN.md §0.1) as concrete probes --------------------------------------------
# Each probe: (issue, prefix that reaches the situation, symbol under test, outputs that mean "issue present").
SEC = ['enable_s1', 'auth_request_plain_text', 'nas_sm_cmd']          # NAS security active
REG = SEC + ['registration_accept_protected']                          # ... and registered
ISSUES = [
    ('I3',  SEC, 'id_request_plain_text',         {'id_response'}),
    ('I4',  SEC, 'auth_request_plain_text',       {'auth_response'}),
    ('I6',  SEC, 'nas_sm_cmd_replay',             {'nas_sm_complete'}),
    ('I7',  REG, 'nas_sm_cmd_replay',             {'nas_sm_complete'}),
    ('I9a', SEC, 'registration_accept_plain_text', {'registration_complete'}),
    ('I9b', REG, 'config_update_cmd_plain_text',  {'config_update_complete'}),
    ('I10', ['enable_s1', 'auth_request_plain_text'], 'nas_sm_cmd_ns_plain_text', {'nas_sm_complete'}),
    ('I17', SEC, 'registration_accept_protected', {NULL}),
    ('I19', SEC, 'nas_sm_cmd_protected',          {'nas_sm_complete'}),
    ('I20', REG, 'config_update_cmd_protected',   {'config_update_complete'}),
]
# Table 8 ground truth (PLAN.md §0.1); I9 counts if either variant shows
EXPECTED = {'srsue': {'I3', 'I4', 'I7', 'I9', 'I10', 'I19', 'I20'},
            'oaiue': {'I3', 'I4', 'I6', 'I10', 'I17', 'I19'}}


def probe_issues(fsm):
    rows = []
    for name, prefix, sym, bad in ISSUES:
        outs = fsm.run(prefix + [sym])
        rows.append((name, ' '.join(prefix + [sym]), outs[-1], outs[-1] in bad))
    return rows


# --- LTL via NuSMV --------------------------------------------------------------------------------------
def to_smv(fsm, outputs_extra=('output_null_action',) + tuple(ALL_OUTPUTS)):
    """input is free each step; output is the response to the previous step's input (DevLyzer's X)."""
    ins = fsm.inputs
    outs = sorted({o for _, o in fsm.delta.values()} | set(outputs_extra))
    lines = ['MODULE main', 'VAR',
             '  state : {%s};' % ', '.join(fsm.states),
             '  input : {%s};' % ', '.join(ins),
             '  output : {%s};' % ', '.join(outs),
             'ASSIGN',
             '  init(state) := %s;' % fsm.start,
             '  init(output) := output_null_action;',
             '  next(state) := case']
    for (s, a), (d, _) in sorted(fsm.delta.items()):
        lines.append('    state = %s & input = %s : %s;' % (s, a, d))
    lines += ['    TRUE : state;', '  esac;', '  next(output) := case']
    for (s, a), (_, o) in sorted(fsm.delta.items()):
        lines.append('    state = %s & input = %s : %s;' % (s, a, o))
    lines += ['    TRUE : output_null_action;', '  esac;']
    if 'enable_s1' in ins:
        # one session per path, like DevLyzer's per-trace models: enable_s1 first, never again
        # (otherwise G/F range over the learner's power-cycles and every "after security" property fails)
        lines += ['VAR', '  started : boolean;', 'ASSIGN', '  init(started) := FALSE;', '  next(started) := TRUE;',
                  'INVAR started <-> input != enable_s1']
    return '\n'.join(lines) + '\n', set(ins), set(outs)


def check_ltl(fsm, props, nusmv='NuSMV'):
    model, ins, outs = to_smv(fsm)
    known = ins | outs | {'input', 'output', 'G', 'F', 'X', 'U'}
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, p in props:
            used = set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', p))
            if used - known:  # property mentions an input this FSM does not have (e.g. RRC after projection)
                results.append((i, 'skipped (%s)' % ' '.join(sorted(used - known)), p))
                continue
            smv = os.path.join(tmp, 'm.smv')
            open(smv, 'w').write(model + 'LTLSPEC %s\n' % p)
            r = subprocess.run([nusmv, smv], capture_output=True, text=True)
            verdict = 'holds' if 'is true' in r.stdout else 'VIOLATED' if 'is false' in r.stdout else 'error'
            results.append((i, verdict, p))
    return results


def main(argv):
    cmd, path = argv[1], argv[2]
    fsm = Mealy.from_dot(path)
    if cmd == 'stats':
        print('%s: %d states, %d transitions (non-self-loop)' % (path, *fsm.stats()))
    elif cmd == 'nas':
        nas = fsm.restrict(lambda a: not RRC_INPUT.match(a)).minimized()
        nas.to_dot(argv[3])
        print('NAS projection: %d states, %d transitions -> %s' % (*nas.stats(), argv[3]))
    elif cmd == 'issues':
        for name, word, out, present in probe_issues(fsm):
            print('%-4s %-8s %-24s %s' % (name, 'PRESENT' if present else '-', out, word))
    elif cmd == 'ltl':
        props = [(i + 1, l.strip()) for i, l in enumerate(open(argv[3])) if l.strip()]
        if len(argv) > 4:  # optional comma-separated 1-based indices
            keep = {int(x) for x in argv[4].split(',')}
            props = [p for p in props if p[0] in keep]
        for i, verdict, p in check_ltl(fsm, props):
            print('%2d %-9s %s' % (i, verdict, p if verdict != 'holds' else ''))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv)

"""PSMBench-format spec FSM (JSON) -> complete Mealy machine in 5GBaseChecker .dot (PLAN.md §3.2 steps 4, 6).

  python3 psm2dot.py spec_fsm.json spec_fsm.dot

Input (PSMBench schema, state_machine_format.json) with the closed NAS vocabulary of symbols/alignment.md:
  {"states": [...], "initial_state": "...", "final_states": [...],
   "transitions": [{"from": S, "event": "recv <input symbol>", "action": "send <output symbol>", "to": T,
                    "clause_id": "5.4.2.2", "quoted_text": "...", "support": 0, "contradiction": 0}]}
The four confidence fields are our extension; PSMBench's evaluator ignores unknown keys.

Output: states renamed s0..sN (s0 = initial_state, as the learner writes them), one edge per (state, input).
(state, input) pairs with no transition get output UNSPECIFIED and a self-loop, so DevScan can still compare
the machine and the four-case classifier can bucket them separately (PLAN.md §3.2 step 4).
Two transitions for the same (state, input) are an error: the spec model must be deterministic before
comparison (resolve them by the ensemble vote of step 5 first).
"""
import json
import re
import sys

INPUTS = ('enable_s1 id_request_plain_text auth_request_plain_text nas_sm_cmd nas_sm_cmd_protected '
          'nas_sm_cmd_replay nas_sm_cmd_ns nas_sm_cmd_ns_plain_text registration_accept_protected '
          'registration_accept_h4_plain_text registration_accept_plain_text config_update_cmd_protected '
          'config_update_cmd_plain_text config_update_cmd_replay deregistration_req_protected '
          'deregistration_req_plain_text').split()
OUTPUTS = ('registration_request id_response auth_response nas_sm_complete nas_sm_reject registration_complete '
           'deregistration_accept config_update_complete null_action').split()
UNSPECIFIED = 'UNSPECIFIED'


def symbol(field, prefix, allowed):
    m = re.match(r'^\s*(?:%s)\s+(\S+)\s*$' % prefix, field)
    if not m or m.group(1) not in allowed:
        raise ValueError('not in the closed vocabulary: %r' % field)
    return m.group(1)


def convert(psm):
    states = list(psm['states'])
    init = psm['initial_state']
    states.remove(init)
    names = {s: 's%d' % i for i, s in enumerate([init] + states)}
    delta = {}
    for t in psm['transitions']:
        a = symbol(t['event'], 'recv|receive', INPUTS)
        o = symbol(t['action'], 'send|reply', OUTPUTS)
        key = (names[t['from']], a)
        if key in delta:
            raise ValueError('nondeterministic: %s on %s has two transitions' % (t['from'], a))
        delta[key] = (names[t['to']], o, t)
    for s in names.values():
        for a in INPUTS:
            delta.setdefault((s, a), (s, UNSPECIFIED, None))
    return names, delta


def write_dot(names, delta, path):
    order = sorted(names.values(), key=lambda s: int(s[1:]))
    with open(path, 'w') as f:
        f.write('digraph g {\n\n')
        for s in order:
            f.write('\t%s [shape="circle" label="%s"];\n' % (s, s))
        for s in order:
            for a in INPUTS:
                d, o, _ = delta[(s, a)]
                f.write('\t%s -> %s [label="%s / %s"];\n' % (s, d, a, o))
        f.write('\n__start0 [label="" shape="none" width="0" height="0"];\n__start0 -> s0;\n\n}\n')


def main(src, dst):
    psm = json.load(open(src))
    names, delta = convert(psm)
    write_dot(names, delta, dst)
    json.dump({orig: s for orig, s in names.items()}, open(dst + '.states.json', 'w'), indent=1)
    unspec = sum(1 for (_, o, _) in delta.values() if o == UNSPECIFIED)
    print('%d states, %d (state, input) pairs, %d UNSPECIFIED -> %s' % (len(names), len(delta), unspec, dst))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

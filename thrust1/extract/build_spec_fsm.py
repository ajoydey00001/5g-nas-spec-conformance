"""Spec cells -> checked quotes, PSMBench JSON, and the spec FSM as the learner would observe it.

  python3 -I build_spec_fsm.py spec_cells_v1.json ts24501_v17.8.0_clauses.jsonl OUTDIR

Writes to OUTDIR:
  spec_v1.psm.json       PSMBench schema (+ clause_id, quoted_text, kind, also_allowed per transition)
  spec_v1_harness.dot    spec ⊗ harness, minimized, 5GBaseChecker .dot (primary outputs)
  spec_v1_harness.allowed.json  {state: {input: {"allowed": [...], "kind": ..., "clause": ...}}}

Why the harness product: the 5GBaseChecker core and learner answer null_action themselves when a
precondition fails (symbols/alignment.md), without the UE seeing anything. Every learned FSM contains
these edges, so the spec model must contain them too, or each one becomes a false Case 2 deviation.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'symbols'))
from fsm_tools import Mealy  # noqa: E402

NULL = 'null_action'


def norm(s):
    s = s.replace('“', '"').replace('”', '"').replace('’', "'").replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', s).strip()


def check_quotes(doc, clauses):
    bad = []
    for s, row in doc['cells'].items():
        for a, c in row.items():
            for ev in c['evidence']:
                text = clauses.get(ev['clause_id'])
                if text is None or norm(ev['quote']) not in norm(text):
                    bad.append((s, a, ev['clause_id'], ev['quote'][:60]))
    return bad


def write_psm(doc, path):
    trans = []
    for s, row in doc['cells'].items():
        for a, c in row.items():
            ev = c['evidence'][0] if c['evidence'] else {'clause_id': None, 'quote': ''}
            trans.append({'from': s, 'event': 'recv ' + a, 'action': 'send ' + c['output'], 'to': c['next'],
                          'clause_id': ev['clause_id'], 'quoted_text': ev['quote'], 'kind': c['kind'],
                          'also_allowed': c['also_allowed'], 'support': 0, 'contradiction': 0})
    json.dump({'states': list(doc['states']), 'initial_state': doc['initial_state'], 'final_states': [],
               'transitions': trans}, open(path, 'w'), indent=1)
    return len(trans)


# --- harness: core (testsocket.c) + learner (UESUL.context_check, srsueSUL.step) ----------------------
H0 = (False, False, False, False, False, 0, 0)  # auth_seen, kamf, smc_sent, kgnb, cu_prot, n_auth_resp, n_smc_compl


def blocked(a, h):
    auth_seen, kamf, smc_sent, kgnb, cu_prot, n_ar, n_sc = h
    if n_sc >= 1 and n_ar >= 2:                     # srsueSUL cut-off
        return True
    need = {
        'id_request_plain_text': kamf,                  # core: ogs_assert(amf_ue->kamf)
        'nas_sm_cmd': kamf,                             # check_kamf
        'nas_sm_cmd_ns': kamf,                          # check_kamf
        'nas_sm_cmd_protected': auth_seen and smc_sent,  # learner + check_int_and_enc
        'nas_sm_cmd_replay': smc_sent,                  # learner Inputmap + smd_replayed + check_int
        'registration_accept_protected': auth_seen and kgnb,
        'config_update_cmd_protected': auth_seen and smc_sent,
        'config_update_cmd_replay': cu_prot and smc_sent,
        'deregistration_req_protected': smc_sent,
    }
    return not need.get(a, True)


def advance(a, out, h):
    auth_seen, kamf, smc_sent, kgnb, cu_prot, n_ar, n_sc = h
    return (auth_seen or a == 'auth_request_plain_text',
            kamf or out == 'auth_response',
            smc_sent or a == 'nas_sm_cmd',
            kgnb or (a == 'nas_sm_cmd' and out == 'nas_sm_complete'),
            cu_prot or a == 'config_update_cmd_protected',
            min(n_ar + (out == 'auth_response'), 2),
            min(n_sc + (out == 'nas_sm_complete'), 1))


def product(doc):
    cells, inputs = doc['cells'], doc['inputs']
    start = (doc['initial_state'], H0)
    delta, todo, seen = {}, [start], {start}
    while todo:
        q = todo.pop()
        s, h = q
        for a in inputs:
            if a == 'enable_s1':
                c = cells[s][a]
                nq, label = (c['next'], H0), (c['output'], (), c['kind'], c['evidence'][0]['clause_id'], c['note'])
            elif s in ('S0', 'S5') or blocked(a, h):
                c = cells[s][a]
                kind = c['kind'] if s in ('S0', 'S5') else 'HARNESS'
                nq, label = q, (NULL, (), kind, None, 'harness precondition' if kind == 'HARNESS' else c['note'])
            else:
                c = cells[s][a]
                nq = (c['next'], advance(a, c['output'], h))
                label = (c['output'], tuple(c['also_allowed']), c['kind'],
                         c['evidence'][0]['clause_id'] if c['evidence'] else None, c['note'])
            delta[(q, a)] = (nq, label)
            if nq not in seen:
                seen.add(nq)
                todo.append(nq)
    return start, delta


def main(cells_path, clauses_path, outdir):
    doc = json.load(open(cells_path))
    clauses = {}
    for l in open(clauses_path):
        c = json.loads(l)
        clauses[c['id']] = c['title'] + '\n' + c['text']
    bad = check_quotes(doc, clauses)
    n_ev = sum(len(c['evidence']) for row in doc['cells'].values() for c in row.values())
    print('quotes: %d checked, %d not found verbatim' % (n_ev, len(bad)))
    for b in bad:
        print('  NOT FOUND', b)
    if bad:
        raise ValueError('spec evidence quote validation failed; no FSM artifacts written')
    os.makedirs(outdir, exist_ok=True)
    n = write_psm(doc, os.path.join(outdir, 'spec_v1.psm.json'))
    print('PSMBench JSON: %d states, %d transitions' % (len(doc['states']), n))

    start, delta = product(doc)
    names = {q: 'q%d' % i for i, q in enumerate(sorted({q for q, _ in delta}, key=lambda q: (q != start, str(q))))}
    enc = {}  # Mealy outputs carry the full label so minimization keeps allowed sets apart
    m_delta = {}
    for (q, a), (nq, label) in delta.items():
        key = json.dumps(label)
        enc.setdefault(key, label)
        m_delta[(names[q], a)] = (names[nq], key)
    raw = Mealy(names[start], m_delta)
    mini = raw.minimized()
    print('spec x harness: %d reachable product states -> %d after minimization' % (len(raw.states), len(mini.states)))

    plain = Mealy(mini.start, {k: (d, enc[o][0]) for k, (d, o) in mini.delta.items()})
    plain.to_dot(os.path.join(outdir, 'spec_v1_harness.dot'))
    allowed = {}
    for (s, a), (_, o) in mini.delta.items():
        out, also, kind, clause, note = enc[o]
        allowed.setdefault(s, {})[a] = {'allowed': [out] + list(also), 'kind': kind, 'clause': clause, 'note': note}
    json.dump(allowed, open(os.path.join(outdir, 'spec_v1_harness.allowed.json'), 'w'), indent=1)
    print('wrote %s/spec_v1_harness.dot: %d states, %d transitions (non-self-loop)' % (outdir, *plain.stats()))


if __name__ == '__main__':
    main(*sys.argv[1:4])

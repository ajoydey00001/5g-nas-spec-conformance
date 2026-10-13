"""Spec FSM vs learned device FSMs: first-point deviations and the four-case classification (T1.6, PLAN.md §3.3).

  python3 -I spec_vs_devices.py SPEC_CELLS.json OUT.json NAME=DEVICE.dot [NAME=DEVICE.dot ...]

The spec side is simulated from the extracted cells (extract/author_spec_cells.py) together with the test
harness, instead of from a fixed .dot, because the harness is only partly known:
  certain    no NAS connection in S0/S5 (radio down), enable_s1 = full restart
  uncertain  core/learner preconditions (keys present, auth seen, SMC sent, srsueSUL counter cut-off).
             Where the harness may have blocked the message, null_action is also allowed, and the device's
             answer tells which branch happened (null -> blocked, spec state unchanged).
Allowed outputs = spec output + also_allowed (+ null_action when the harness may block).

For each device, walk spec x device breadth-first over the 16 NAS inputs (a device's RRC edges are never
taken = its NAS projection). A deviation is the FIRST step whose device output is not allowed; the walk does
not continue past it (no cascades). Each violated spec cell becomes one deviation class, witnessed by the
shortest word over all devices, then replayed on every device (k = devices whose last output is allowed):
  Case 1  k = n                     all conform (not reported)
  Case 2  k = 0, all devices agree  invisible to device-vs-device differential testing
  Case 3  0 < k < n                 devices split
  Case 4  k = 0, devices disagree
"visible_to_diff": the devices' outputs differ somewhere along the witness, so pairwise device comparison
(DevScan) can surface this word; Case 2 classes with visible_to_diff = False are the blind spot (D2/D3).
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'symbols'))
from fsm_tools import Mealy  # noqa: E402

NULL = 'null_action'
H0 = (False, False, False, False, False, 0, 0)  # auth_seen, kamf, smc_sent, kgnb, cu_prot, n_auth_resp, n_smc_compl


def may_block(a, h):
    """True if the core or learner might answer null_action without delivering `a` (uncertain harness)."""
    auth_seen, kamf, smc_sent, kgnb, cu_prot, n_ar, n_sc = h
    if n_sc >= 1 and n_ar >= 2:  # srsueSUL cut-off
        return True
    return a in ('id_request_plain_text', 'nas_sm_cmd', 'nas_sm_cmd_ns', 'nas_sm_cmd_protected', 'nas_sm_cmd_replay',
                 'registration_accept_protected', 'config_update_cmd_protected', 'config_update_cmd_replay',
                 'deregistration_req_protected') and not (kamf and smc_sent and kgnb and auth_seen and (
                     cu_prot or a != 'config_update_cmd_replay'))


def advance(a, out, h):
    auth_seen, kamf, smc_sent, kgnb, cu_prot, n_ar, n_sc = h
    return (auth_seen or a == 'auth_request_plain_text', kamf or out == 'auth_response',
            smc_sent or a == 'nas_sm_cmd', kgnb or (a == 'nas_sm_cmd' and out == 'nas_sm_complete'),
            cu_prot or a == 'config_update_cmd_protected',
            min(n_ar + (out == 'auth_response'), 2), min(n_sc + (out == 'nas_sm_complete'), 1))


class Spec:
    def __init__(self, doc):
        self.cells, self.inputs, self.start = doc['cells'], doc['inputs'], (doc['initial_state'], H0)

    def step(self, q, a, observed):
        """-> (allowed outputs, next spec state given the observed device output, cell)."""
        s, h = q
        c = self.cells[s][a]
        if a == 'enable_s1':
            return [c['output']], (c['next'], H0), c
        if s in ('S0', 'S5'):
            return [NULL], q, c
        allowed = [c['output']] + c['also_allowed']
        blockable = may_block(a, h)
        if blockable and NULL not in allowed:
            allowed = allowed + [NULL]
        if observed == NULL and blockable and c['output'] != NULL:
            return allowed, (s, advance(a, NULL, h)), c     # treat as not delivered
        return allowed, (c['next'], advance(a, observed if observed in allowed else c['output'], h)), c


def first_deviations(spec, dev, silent=None):
    """silent: optional dict collecting device outputs in UNDERSPECIFIED cells -> (c) candidates."""
    start = (spec.start, dev.start)
    seen, todo, out = {start: []}, collections.deque([start]), []
    while todo:
        q = todo.popleft()
        sq, d = q
        for a in spec.inputs:
            nd, o = dev.delta[(d, a)]
            allowed, nsq, c = spec.step(sq, a, o)
            if silent is not None and c['kind'] == 'UNDERSPECIFIED' and sq[0] not in ('S0', 'S5'):
                key = (sq[0], a)
                if key not in silent or len(seen[q]) + 1 < len(silent[key]['word']):
                    silent[key] = {'word': seen[q] + [a], 'output': o, 'note': c['note']}
            if o not in allowed:
                out.append({'word': seen[q] + [a], 'spec_state': sq[0], 'input': a, 'device_output': o,
                            'allowed': allowed, 'cell': c})
                continue                                       # first point of disagreement only
            nq = (nsq, nd)
            if nq not in seen:
                seen[nq] = seen[q] + [a]
                todo.append(nq)
    return out


def last_allowed(spec, word, outputs):
    """Replay `word` on the spec with the device's outputs; return (allowed at last step, conformed before)."""
    q, ok = spec.start, True
    for i, (a, o) in enumerate(zip(word, outputs)):
        allowed, q, _ = spec.step(q, a, o)
        if i < len(word) - 1 and o not in allowed:
            ok = False
    return allowed, ok


def main(cells_json, out_json, *dev_args):
    spec = Spec(json.load(open(cells_json)))
    devices = {}
    for arg in dev_args:
        name, path = arg.split('=', 1)
        devices[name] = Mealy.from_dot(path)
    silent = {n: {} for n in devices}
    per_dev = {n: first_deviations(spec, m, silent[n]) for n, m in devices.items()}
    for n, ds in per_dev.items():
        print('%-8s %3d first-point deviations from spec' % (n, len(ds)))

    by_cell = {}
    for ds in per_dev.values():
        for d in ds:
            key = (d['spec_state'], d['input'])
            if key not in by_cell or len(d['word']) < len(by_cell[key]['word']):
                by_cell[key] = d
    classes = []
    for (s, a), d in sorted(by_cell.items(), key=lambda kv: (len(kv[1]['word']), kv[0])):
        w = d['word']
        outs = {n: m.run(w) for n, m in devices.items()}
        conform, reached = [], []
        for n in devices:
            allowed, ok = last_allowed(spec, w, outs[n])
            reached.append(n) if ok else None
            if outs[n][-1] in allowed:
                conform.append(n)
        # only devices that followed the spec up to the last step are judged on this cell; a device that
        # deviated earlier on the witness never reached this spec state
        conform = [n for n in conform if n in reached]
        last = {n: outs[n][-1] for n in reached}
        k, n_dev = len(conform), len(reached)
        case = 1 if k == n_dev else (2 if len(set(last.values())) == 1 else 4) if k == 0 else 3
        visible = any(len({tuple(o[:i + 1]) for o in outs.values()}) > 1 for i in range(len(w)))
        c = d['cell']
        classes.append({'case': case, 'visible_to_diff': visible, 'word': w, 'spec_state': s, 'input': a,
                        'spec_allowed': d['allowed'], 'kind': c['kind'], 'note': c['note'],
                        'evidence': c['evidence'], 'device_outputs': outs, 'conforming_devices': conform,
                        'devices_conforming_before_last_step': reached, 'k': k, 'n': n_dev})
    classes = [c for c in classes if c['case'] != 1]
    cands = {}
    for n, obs in silent.items():
        for (st, a), v in obs.items():
            cands.setdefault('%s@%s' % (a, st), {'note': v['note'], 'outputs': {}})['outputs'][n] = v['output']
    json.dump({'devices': list(devices), 'classes': classes, 'underspecified_observations': cands},
              open(out_json, 'w'), indent=1)

    print('\n%d deviation classes (one per violated spec cell):' % len(classes))
    for c in classes:
        print('  Case %d %s diff-visible:%-3s  %-14s %-32s@%s  spec %-28s devices %-24s %s' % (
            c['case'], '(%d/%d dev)' % (c['n'], len(devices)), 'yes' if c['visible_to_diff'] else 'NO', c['kind'], c['input'], c['spec_state'],
            '/'.join(c['spec_allowed'])[:28], ','.join('%s=%s' % (n, o[-1]) for n, o in c['device_outputs'].items())[:24],
            c['note'][:50]))
    print('\n(c) candidates - device behaviour where the spec is silent (UNDERSPECIFIED cells):')
    for k, v in sorted(cands.items()):
        print('  %-44s %-40s %s' % (k, ', '.join('%s=%s' % kv for kv in sorted(v['outputs'].items())), v['note'][:45]))
    cnt = collections.Counter((c['case'], c['visible_to_diff']) for c in classes)
    print('\nsummary:', ', '.join('Case %d %s: %d' % (k[0], 'visible' if k[1] else 'INVISIBLE to diff', v)
                                  for k, v in sorted(cnt.items())))


if __name__ == '__main__':
    main(*sys.argv[1:])

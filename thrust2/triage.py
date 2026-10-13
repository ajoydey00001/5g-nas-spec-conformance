"""Thrust 2 starter: label each Thrust 1 deviation class with an LLM that may call evidence tools.

Labels (PLAN.md §4): a = model-extraction error, b = benign learning artefact / nondeterminism,
c = spec ambiguity, d = exploitable noncompliance.

  python3 -I thrust2/triage.py RESULTS.json CLAUSES.jsonl OUT.jsonl [--model M] [--mode agent|alone]
                               [--swap device=NAME] [--swap release=Rel-16] [--fsm DEV=path.dot ...]

  RESULTS.json   thrust1/results/T1.6_spec_vs_ABsrs.json (or T1.6_spec_vs_AB.json)
  CLAUSES.jsonl  repro/clauses.jsonl (made by `bash reproduce.sh`)
  --model        ollama:qwen3:8b (default, local, free) | openai:<model> (any OpenAI-compatible server:
                 set LLM_BASE_URL and LLM_API_KEY, e.g. DeepSeek or Gemini) | dummy (no LLM, tests the pipeline)
  --mode agent   the model may call retrieve / confidence / replay (Thrust 2 design)
  --mode alone   the model sees only the record (Thrust 3 baseline)
  --swap         counterfactual probes for Thrust 3: rename the device, or change the release cue

Python 3 standard library only.
"""
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'thrust1', 'symbols'))
from fsm_tools import Mealy  # noqa: E402

SYSTEM = """You triage deviations between a 5G UE's learned NAS state machine and 3GPP TS 24.501 {release}.
Choose exactly one label:
 a = the spec model is wrong (extraction error: the clause does not say what the spec cell claims)
 b = benign: learning artefact, nondeterminism, or behaviour the spec allows ("may")
 c = the spec is ambiguous or silent, so neither side is clearly right
 d = real noncompliance that an attacker (fake base station) could exploit
{tools}
Finish with one JSON object on the last line:
{{"label": "a|b|c|d", "confidence": 0.0-1.0, "claim": "...", "clauses": ["4.4.4.2"]}}
For a or d the claim is an LTL property in DevLyzer syntax, e.g.
G((input = nas_sm_cmd & output = nas_sm_complete) -> G(input = id_request_plain_text -> output != id_response)).
For b the claim is the input sequence and how often to replay it; for c it is the clause pair that conflicts."""

TOOLS = """You may call tools. Write ONE line exactly like this and stop; the result comes back to you:
 TOOL retrieve <clause id or words>      -> text of a TS 24.501 clause
 TOOL confidence <spec_state> <input>    -> kind (SPEC / INFERRED / UNDERSPECIFIED) and quote of the spec cell
 TOOL replay <device> <input1 input2 ...> -> outputs of that device's learned FSM
At most 6 tool calls."""


def record(c, swap):
    dev_out = dict(c['device_outputs'])
    if 'device' in swap:
        dev_out = {swap['device']: v for v in list(dev_out.values())[:1]}  # one device, renamed
    return {'word': c['word'], 'spec_state': c['spec_state'], 'input': c['input'],
            'spec_allowed': c['spec_allowed'], 'kind': c['kind'], 'note': c.get('note', ''),
            'evidence': c.get('evidence', []), 'device_outputs': dev_out, 'k': c['k'], 'n': c['n']}


def cid(c):
    return '%s|%s|%s' % (c['spec_state'], c['input'], ' '.join(c['word']))


class Tools:
    def __init__(self, clauses, results, fsms):
        self.clauses = {}
        for line in open(clauses):
            d = json.loads(line)
            self.clauses[d['id']] = d
        self.cells = {(c['spec_state'], c['input']): c for c in results['classes']}
        self.fsms = {k: Mealy.from_dot(v) for k, v in fsms.items()}

    def retrieve(self, q):
        q = q.strip()
        if q in self.clauses:
            d = self.clauses[q]
            return '%s %s: %s' % (d['id'], d['title'], d['text'][:3000])
        words = [w.lower() for w in re.findall(r'\w+', q)]
        best = sorted(self.clauses.values(), key=lambda d: -sum((d['title'] + d['text']).lower().count(w) for w in words))
        return '\n\n'.join('%s %s: %s' % (d['id'], d['title'], d['text'][:800]) for d in best[:3])

    def confidence(self, args):
        p = args.split()
        c = self.cells.get(tuple(p[:2]))
        return json.dumps({k: c[k] for k in ('kind', 'evidence', 'note')}) if c else 'no spec cell for %s' % args

    def replay(self, args):
        p = args.split()
        if not p or p[0] not in self.fsms:
            return 'unknown device; known: %s' % ' '.join(self.fsms)
        try:
            return ' '.join(self.fsms[p[0]].run(p[1:]))
        except KeyError as e:
            return 'input not in the FSM alphabet: %s' % e

    def call(self, line):
        m = re.match(r'TOOL\s+(\w+)\s*(.*)', line.strip())
        if not m or m.group(1) not in ('retrieve', 'confidence', 'replay'):
            return None
        return getattr(self, m.group(1))(m.group(2))


def llm(model, messages):
    if model == 'dummy':
        last = messages[-1]['content']
        if 'TOOL retrieve' in messages[0]['content'] and len(messages) == 2:
            return 'TOOL retrieve 4.4.4.2'
        lab = 'd' if '"SPEC"' in last or 'SPEC' in last else 'c'
        return json.dumps({'label': lab, 'confidence': 0.6, 'claim': 'dummy', 'clauses': []})
    kind, name = model.split(':', 1)
    if kind == 'ollama':
        url = os.environ.get('OLLAMA_URL', 'http://localhost:11434') + '/api/chat'
        body = {'model': name, 'messages': messages, 'stream': False, 'options': {'temperature': 0}}
        hdr = {'Content-Type': 'application/json'}
    else:
        url = os.environ['LLM_BASE_URL'].rstrip('/') + '/chat/completions'
        body = {'model': name, 'messages': messages, 'temperature': 0}
        hdr = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + os.environ['LLM_API_KEY']}
    req = urllib.request.Request(url, json.dumps(body).encode(), hdr)
    out = json.load(urllib.request.urlopen(req, timeout=600))
    text = out['message']['content'] if kind == 'ollama' else out['choices'][0]['message']['content']
    return re.sub(r'<think>.*?</think>', '', text, flags=re.S).strip()   # qwen3 thinking blocks


def parse(text):
    for m in reversed(re.findall(r'\{[^{}]*"label"[^{}]*\}', text)):
        try:
            d = json.loads(m)
            if d.get('label') in ('a', 'b', 'c', 'd'):
                return d
        except ValueError:
            pass
    return {'label': None, 'confidence': None, 'claim': None, 'clauses': []}


def triage(c, tools, model, mode, swap):
    release = swap.get('release', 'v17.8.0 (Rel-17)')
    sys_msg = SYSTEM.format(release=release, tools=TOOLS if mode == 'agent' else '')
    msgs = [{'role': 'system', 'content': sys_msg},
            {'role': 'user', 'content': 'Deviation record:\n' + json.dumps(record(c, swap), indent=1)}]
    calls = []
    for _ in range(7):
        text = llm(model, msgs)
        msgs.append({'role': 'assistant', 'content': text})
        tool_line = next((l for l in text.splitlines() if l.strip().startswith('TOOL ')), None)
        if mode != 'agent' or tool_line is None or len(calls) >= 6:
            break
        res = tools.call(tool_line)
        calls.append(tool_line.strip())
        msgs.append({'role': 'user', 'content': 'RESULT:\n' + str(res)})
    out = parse(msgs[-1]['content'])
    out.update({'id': cid(c), 'case': c['case'], 'visible_to_diff': c['visible_to_diff'],
                'tool_calls': calls, 'model': model, 'mode': mode, 'swap': swap, 'raw': msgs[-1]['content'][-2000:]})
    return out


def main(argv):
    opt = {'model': 'ollama:qwen3:8b', 'mode': 'agent'}
    swap, fsms, pos = {}, {}, []
    i = 0
    while i < len(argv):
        if argv[i] in ('--swap', '--fsm'):
            k, v = argv[i + 1].split('=', 1)
            (swap if argv[i] == '--swap' else fsms)[k] = v
            i += 2
        elif argv[i].startswith('--'):
            opt[argv[i][2:]] = argv[i + 1]; i += 2
        else:
            pos.append(argv[i]); i += 1
    results_path, clauses_path, out_path = pos[:3]
    results = json.load(open(results_path))
    tools = Tools(clauses_path, results, fsms)
    done = set()
    if os.path.exists(out_path):          # resumable: skip classes already in OUT
        done = {json.loads(l)['id'] for l in open(out_path)}
    with open(out_path, 'a') as f:
        for c in results['classes']:
            if cid(c) in done:
                continue
            t = time.time()
            r = triage(c, tools, opt['model'], opt['mode'], swap)
            r['seconds'] = round(time.time() - t, 1)
            f.write(json.dumps(r) + '\n'); f.flush()
            print('%-60s label=%s conf=%s tools=%d %.0fs' % (r['id'][:60], r['label'], r['confidence'],
                                                            len(r['tool_calls']), r['seconds']))


if __name__ == '__main__':
    main(sys.argv[1:])

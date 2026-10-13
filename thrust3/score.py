"""Thrust 3 starter: score triage outputs against truth labels.

  python3 -I thrust3/score.py TRUTH.json RUN.jsonl [SWAPPED_RUN.jsonl ...]

  TRUTH.json  {"<class id>": "a|b|c|d", ...}  (class id = spec_state|input|word, as triage.py writes it;
              start from thrust3/truth_template.json and fill it in by hand, citing the confirming tool)
  RUN.jsonl   output of thrust2/triage.py
  more runs   the same classes with --swap: label-flip rate vs RUN, with a 95% bootstrap CI

Prints accuracy, per-label F1, macro-F1, ECE (10 bins) and Brier score. Standard library only.
"""
import json
import random
import sys

LABELS = 'abcd'


def load(p):
    return {d['id']: d for d in map(json.loads, open(p))}


def metrics(truth, run):
    ids = [i for i in truth if i in run]
    pred = {i: run[i]['label'] for i in ids}
    acc = sum(pred[i] == truth[i] for i in ids) / max(len(ids), 1)
    f1 = {}
    for l in LABELS:
        tp = sum(pred[i] == l and truth[i] == l for i in ids)
        fp = sum(pred[i] == l and truth[i] != l for i in ids)
        fn = sum(pred[i] != l and truth[i] == l for i in ids)
        if tp + fp + fn:
            f1[l] = 2 * tp / (2 * tp + fp + fn)
    conf = [(float(run[i]['confidence'] or 0), pred[i] == truth[i]) for i in ids]
    ece = 0.0
    for b in range(10):
        bin_ = [(c, ok) for c, ok in conf if b / 10 <= c < (b + 1) / 10 or (b == 9 and c == 1.0)]
        if bin_:
            ece += len(bin_) / len(conf) * abs(sum(c for c, _ in bin_) / len(bin_) - sum(ok for _, ok in bin_) / len(bin_))
    brier = sum((c - ok) ** 2 for c, ok in conf) / max(len(conf), 1)
    return len(ids), acc, f1, sum(f1.values()) / max(len(f1), 1), ece, brier


def flip_rate(base, other, n_boot=2000):
    ids = [i for i in base if i in other]
    flips = [base[i]['label'] != other[i]['label'] for i in ids]
    if not flips:
        return 0, 0, 0, 0
    rnd = random.Random(0)
    boots = sorted(sum(rnd.choice(flips) for _ in flips) / len(flips) for _ in range(n_boot))
    return len(ids), sum(flips) / len(flips), boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot)]


def main(truth_path, run_path, *swapped):
    truth = {k: v for k, v in json.load(open(truth_path)).items() if v in LABELS}
    run = load(run_path)
    n, acc, f1, mf1, ece, brier = metrics(truth, run)
    print('%s: n=%d  accuracy=%.3f  macro-F1=%.3f  ECE=%.3f  Brier=%.3f' % (run_path, n, acc, mf1, ece, brier))
    print('   per-label F1: ' + '  '.join('%s=%.2f' % kv for kv in sorted(f1.items())))
    for p in swapped:
        m, r, lo, hi = flip_rate(run, load(p))
        print('   flip rate vs %s: %.3f  95%% CI [%.3f, %.3f]  (n=%d)' % (p, r, lo, hi, m))


if __name__ == '__main__':
    main(*sys.argv[1:])

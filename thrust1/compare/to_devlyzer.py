"""Deviation classes (spec_vs_devices.py output) -> DevLyzer's deviant-queries.json input format.

  python3 -I to_devlyzer.py RESULTS.json OUT_DIR/deviant-queries.json

Then run the authors' DevLyzer on it (45 LTL properties, NuSMV), from a copy of 5GBaseChecker/DevLyzer:
  docker run --rm --cpus=2 -u $(id -u):$(id -g) -v OUT_DIR:/work -w /work t1-offline python3 main.py
It writes deviant-queries_attack.json / _benign.json / _unresolved.json next to the input.
"""
import json
import sys


def main(results, out):
    d = json.load(open(results))
    traces = []
    for c in d['classes']:
        groups = {}
        for dev, outs in c['device_outputs'].items():
            groups.setdefault(tuple(outs), []).append(dev)
        traces.append({'input_symbols': str(c['word']),
                       'outputs': [{'output_symbols': str(list(o)), 'devices': str(devs)} for o, devs in groups.items()]})
    json.dump({'traces': traces}, open(out, 'w'), indent=1)
    print(len(traces), 'traces written to', out)


if __name__ == '__main__':
    main(*sys.argv[1:3])

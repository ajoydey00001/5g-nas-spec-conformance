"""Print clauses (and their subclauses with --tree) from the clause index, for reading/retrieval.

  python3 -I dump_clauses.py ts24501_v17.8.0_clauses.jsonl 4.4.4.2 5.4.2.3 [--tree 5.4.3]
"""
import json
import sys

index, args = sys.argv[1], sys.argv[2:]
C = [json.loads(l) for l in open(index)]
tree = False
for a in args:
    if a == '--tree':
        tree = True
        continue
    for c in C:
        if c['id'] == a or (tree and c['id'].startswith(a + '.')):
            print('=== %s  %s\n%s\n' % (c['id'], c['title'], c['text']))
    tree = False

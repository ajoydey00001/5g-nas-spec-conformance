"""Map SPEC5G sentences of one spec back to clause IDs of our clause index.

  python3 -I spec5g_map.py spec5g_ts24501.txt ts24501_v17.8.0_clauses.jsonl spec5g_ts24501_map.jsonl

spec5g_ts24501.txt: the lines of one document cut out of SPEC5G's gold_5G_v4.txt (one sentence per line).
Output, one JSON object per SPEC5G line:
  {"line": 17, "text": "...", "clause": "5.4.2.2", "how": "exact" | "ngram", "score": 0.83}
"clause" is null when nothing matches well enough (boilerplate, tables, text not in this version).

Matching: SPEC5G cleaning removed brackets/semicolons and cut some sentences, so both sides are
normalized to lowercase words; first an exact substring search in the clause texts, then a vote over
word 5-grams (score = share of the line's 5-grams found in the winning clause).
"""
import collections
import json
import re
import sys

WORD = re.compile(r'[a-z0-9]+')
N = 5
MIN_WORDS = 6        # shorter lines (headings, table cells) are too ambiguous
MIN_SCORE = 0.5


def words(s):
    return WORD.findall(s.lower())


def main(spec5g_path, clauses_path, out_path):
    clauses = [json.loads(l) for l in open(clauses_path)]
    # one normalized string per clause, with clause boundaries for exact search
    joined, starts = [], []
    pos = 0
    grams = collections.defaultdict(set)
    for k, c in enumerate(clauses):
        w = words(c['title'] + ' ' + c['text'])
        s = ' ' + ' '.join(w) + ' '
        starts.append(pos)
        joined.append(s)
        pos += len(s)
        for i in range(len(w) - N + 1):
            grams[tuple(w[i:i + N])].add(k)
    big = ''.join(joined)

    def clause_at(offset):
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo

    stats = collections.Counter()
    with open(out_path, 'w') as out:
        for ln, line in enumerate(open(spec5g_path, errors='replace'), 1):
            text = line.strip()
            w = words(text)
            rec = {'line': ln, 'text': text, 'clause': None, 'how': None, 'score': 0.0}
            if len(w) >= MIN_WORDS:
                hit = big.find(' ' + ' '.join(w) + ' ')
                if hit >= 0:
                    rec.update(clause=clauses[clause_at(hit)]['id'], how='exact', score=1.0)
                else:
                    g = [tuple(w[i:i + N]) for i in range(len(w) - N + 1)]
                    votes = collections.Counter(k for t in g for k in grams.get(t, ()))
                    if votes:
                        k, v = votes.most_common(1)[0]
                        score = v / len(g)
                        if score >= MIN_SCORE:
                            rec.update(clause=clauses[k]['id'], how='ngram', score=round(score, 3))
                stats[rec['how'] or 'unmatched'] += 1
            else:
                stats['too short'] += 1
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
    total = sum(stats.values())
    print('%d lines: ' % total + ', '.join('%s %d (%.0f%%)' % (k, v, 100 * v / total) for k, v in stats.most_common()))


if __name__ == '__main__':
    main(*sys.argv[1:4])

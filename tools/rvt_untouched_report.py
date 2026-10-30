"""Untouched report for an rvt-ballet save: how much of the output is provably the same as the source.
usage: tools/rvt_untouched_report.py SRC.rvt OUT.rvt   (aggregate numbers only; no names, paths or ids are printed beyond short element ids of CHANGED elements, which --ids shows)
  elements: share of source elements whose verification dump is identical in the output (rvt_elements snapshot, disk-cached)
  streams:  share of compound-file streams (and of their bytes) identical
  sectors:  share of 512-byte blocks identical at the same file offset (raw bytes)"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/src/savegate'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import save
import cfb


def report(src, out):
    a, b = open(src, 'rb').read(), open(out, 'rb').read(); A = save._cached_adapter()
    sa, sb = A().snapshot(a), A().snapshot(b)
    el = [k for k in sa if k.startswith('el:')]; ch = [k for k in el if k not in sb or sa[k] != sb[k]]; new = [k for k in sb if k.startswith('el:') and k not in sa]
    ot = [k for k in set(sa) | set(sb) if not k.startswith('el:') and sa.get(k) != sb.get(k)]
    ca, cb = cfb.CFB(a).streams(), cfb.CFB(b).streams()
    same_b = tot_b = same_n = 0
    for n, e in ca.items():
        tot_b += e.size; d = n in cb and bytes(cb[n].data) == bytes(e.data)
        if d: same_b += e.size; same_n += 1
    B = 512; nb = (len(a) + B - 1) // B; eq = sum(1 for i in range(nb) if a[i * B:(i + 1) * B] == b[i * B:(i + 1) * B])
    pc = lambda x, y: round(100.0 * x / y, 3) if y else 100.0
    return {'size_src': len(a), 'size_out': len(b), 'elements': len(el), 'elements_changed': len(ch), 'elements_added': len(new), 'elements_untouched_pct': pc(len(el) - len(ch), len(el)),
            'streams': len(ca), 'streams_identical': same_n, 'stream_bytes_identical_pct': pc(same_b, tot_b), 'sectors_identical_pct': pc(eq, nb), 'other_keys_changed': len(ot),
            '_changed_ids': sorted(ch)[:50], '_other': sorted(ot)[:20]}


if __name__ == '__main__':
    r = report(sys.argv[1], sys.argv[2])
    if '--ids' not in sys.argv: r.pop('_changed_ids'); r.pop('_other')
    print(json.dumps(r))

"""classify the CSV written by rvt_save_timeline.ps1 (t_ms,name,length,lastwrite_ticks,fileindex) into the write pattern Revit used.
usage: rvt_save_timeline_classify.py timeline.csv TARGETNAME   -> prints one pattern line and the evidence. Pure stdlib, no Revit needed."""
import csv, sys


def classify(rows, target):
    rows = [r for r in rows if r.get('name')]; tgt = [r for r in rows if r['name'] == target]
    side = sorted({r['name'] for r in rows if r['name'] != target and r['name'].lower().startswith(target.lower()[:-4])})
    ev = {'side_files': side, 'target_rows': len(tgt)}
    if not tgt: return 'no-target-rows', ev
    ids = [r['fileindex'] for r in tgt if r['length'] != 'GONE']; lens = [int(r['length']) for r in tgt if r['length'] not in ('GONE', '')]
    gone = [r for r in tgt if r['length'] == 'GONE']
    ev.update(fileindex_changes=len(set(ids)) - 1, gone=len(gone), min_len=min(lens) if lens else None, max_len=max(lens) if lens else None)
    if gone or len(set(ids)) > 1: pat = 'replace-by-rename' if side or len(set(ids)) > 1 else 'delete-and-recreate'
    elif len(lens) > 1 and any(b < a for a, b in zip(lens, lens[1:])): pat = 'truncate-then-rewrite'
    elif len(tgt) > 2: pat = 'in-place-overwrite-in-steps'
    elif len(tgt) == 2: pat = 'in-place-single-step'
    else: pat = 'no-change-seen'
    return pat, ev


def main(argv):
    with open(argv[0], newline='') as f: rows = list(csv.DictReader(f))
    pat, ev = classify(rows, argv[1]); print(pat); print(ev); return 0


if __name__ == '__main__': sys.exit(main(sys.argv[1:]))

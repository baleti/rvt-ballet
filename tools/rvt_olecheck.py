"""rvt_olecheck.py SRC OUT...: cheap pre-VM oracle. Opens SRC and each OUT with olefile (not our reader), reads every stream fully, and requires the same stream names and the same total size as SRC. Exit 1 on any mismatch/unreadable file. Not a Revit verdict."""
import sys, olefile
def info(p):
    o = olefile.OleFileIO(p); d = {}
    try:
        for s in o.listdir(streams=True, storages=False):
            n = '/'.join(s); d[n] = len(o.openstream(s).read())
    finally: o.close()
    return d
def main(a):
    s = info(a[0]); bad = 0
    for p in a[1:]:
        try: d = info(p)
        except Exception as e: print('FAIL', p, repr(e)[:80]); bad += 1; continue
        ok = set(d) == set(s) and sum(d.values()) > 0
        print('OK  ' if ok else 'FAIL', p.rsplit('/', 1)[-1], len(d), 'streams', sum(d.values()), 'bytes', '' if ok else 'names differ'); bad += not ok
    return 1 if bad else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]) if len(sys.argv) > 2 else print(__doc__))

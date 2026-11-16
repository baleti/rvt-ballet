#!/usr/bin/env python3
"""Neighbour walls a wall move may auto-join (Revit joins a moved wall end that lands on/touches another wall: Facades 2024 wall 802680 +1 ft
also rewrote neighbour 802687, EndParam + join tweak). Conservative bbox test: other walls whose box overlaps this wall's box swept by the move delta.
usage: rvt_wall_touch.py FILE.rvt WALL_ID [dx dy dz] [tol_ft]"""
import json, subprocess, sys, os
def neighbours(rvt, wid, d=(0, 0, 0), tol=1.0):
    here = os.path.dirname(os.path.abspath(__file__))
    out = subprocess.run([os.path.join(here, '..', 'rvt-ballet'), 'query', 'elements', '--json', rvt], capture_output=True, text=True, check=True).stdout
    walls = {e['id']: e['bbox_ft'] for e in json.loads(out) if e.get('class') == 'SWall' and e.get('bbox_ft')}
    b = walls[wid]
    lo = [min(b[i], b[i] + d[i]) - tol for i in range(3)]; hi = [max(b[i + 3], b[i + 3] + d[i]) + tol for i in range(3)]
    return sorted(i for i, c in walls.items() if i != wid and all(c[k] <= hi[k] and c[k + 3] >= lo[k] for k in range(3)))
if __name__ == '__main__':
    a = sys.argv; d = tuple(float(x) for x in a[3:6]) if len(a) > 5 else (0, 0, 0)
    print(neighbours(a[1], int(a[2]), d, float(a[6]) if len(a) > 6 else 1.0))

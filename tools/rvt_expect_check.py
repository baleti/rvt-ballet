"""Replay the viewer's save-time EXPECTATIONS through the Revit API in the offline guest and compare original vs output: parameter values (exact), location shifts (feet), rotations (degrees), absent elements.
usage: tools/rvt_expect_check.py YEAR ORIG.rvt OUT.rvt EXPECT.json   (EXPECT.json = the 'expectations' list of a SAVE AS result). Prints PASS/FAIL per expectation and a summary; aggregate use only (ids are local).
Needs the shared Revit VM (waits for its lock). Strings are compared by their UTF-16 code units (ASCII-safe guest output). Units: feet and degrees as stored; parameters compared as the API's storage value."""
import sys, os, json, re, subprocess, math
year, orig, out, expf = sys.argv[1], os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3]), sys.argv[4]
exp = json.load(open(expf)); HERE = os.path.dirname(os.path.abspath(__file__))
WL = os.path.expanduser('~/rvt-research/write-lab')
def run(tool, ids, f):
    r = subprocess.run(['python3', os.path.join(HERE, tool), year, ids, f], cwd=WL, capture_output=True, text=True, timeout=3600)
    return r.stdout
def parse_loc(txt):
    d = {}
    tf = {}
    for l in txt.splitlines():
        t = re.match(r'TF (\d+) X=(\S+) Y=(\S+) Z=(\S+)', l)      # FamilyInstance.GetTransform() basis vectors
        if t: tf[int(t.group(1))] = [[float(x) for x in t.group(i).split(',')] for i in (2, 3, 4)]
        m = re.match(r'RB (\d+) loc=(\S+) (\S+) (\S+) rotdeg=(\S+)', l)
        if m: d[int(m.group(1))] = {'loc': [float(m.group(i)) for i in (2, 3, 4)], 'rot': (float(m.group(5)) if m.group(5) != '-' else None), 'tf': tf.get(int(m.group(1)))}
        elif re.match(r'RB (\d+) loc=noloc', l): d[int(l.split()[1])] = {'loc': None, 'rot': None}  # exists, no Location
        elif re.match(r'RB (\d+) missing', l): d[int(l.split()[1])] = None
    return d
def parse_par(txt):
    d = {}
    for l in txt.splitlines():
        m = re.match(r'RB (\d+)\|(.*?) storage=(\w+) value=(.*?)( shown=.*?)?( len=(\d+) utf16=(\S*))?$', l)
        if m: d[(int(m.group(1)), m.group(2))] = (m.group(3), m.group(4), m.group(8))
    return d
loc_ids = ','.join(sorted({str(e['eid']) for e in exp if e['kind'] in ('move', 'rotate', 'absent')})); par = sorted({'%d|%s' % (e['eid'], e['name']) for e in exp if e['kind'] == 'param'})
res = {}
for label, f in (('orig', orig), ('out', out)):
    res[label] = {'loc': parse_loc(run(os.environ.get('RVT_LOC_TOOL','rvt_rotation_readback.py'), loc_ids, f)) if loc_ids else {}, 'par': parse_par(run('rvt_param_readback.py', ','.join(par), f)) if par else {}}
npass = nfail = 0
for e in exp:
    k = e['kind']; ok = False; why = ''
    if k == 'absent': ok = res['orig']['loc'].get(e['eid']) is not None and res['out']['loc'].get(e['eid'], 1) is None; why = 'present before, missing after'
    elif k == 'move':
        a, b = res['orig']['loc'].get(e['eid']), res['out']['loc'].get(e['eid'])
        ok = bool(a and b and a['loc'] and b['loc']) and all(abs((b['loc'][i] - a['loc'][i]) - e['d'][i]) < 1e-6 for i in range(3)); why = 'shift %s' % ([round(b['loc'][i] - a['loc'][i], 6) for i in range(3)] if a and b and a['loc'] and b['loc'] else '?')
    elif k == 'rotate':
        a, b = res['orig']['loc'].get(e['eid']), res['out']['loc'].get(e['eid'])
        if a and b and a.get('tf') and b.get('tf'):      # FamilyInstance: Location.Rotation is not the world-Z angle of a tilted instance, so compare the whole frame: every basis vector must equal Rz(deg) of the source's
            c, sn = math.cos(math.radians(e['deg'])), math.sin(math.radians(e['deg']))
            err = max(abs(r - w) for u, v in zip(a['tf'], b['tf']) for r, w in zip((c * u[0] - sn * u[1], sn * u[0] + c * u[1], u[2]), v))
            ok = err < 1e-3; why = 'frame rotated %s deg about Z (max basis error %.5f; Location.Rotation change %s)' % (e['deg'], err, round(b['rot'] - a['rot'], 4) if a['rot'] is not None and b['rot'] is not None else '?')
        else:
            ok = bool(a and b and a['rot'] is not None and b['rot'] is not None) and abs(math.remainder((b['rot'] - a['rot']) - e['deg'], 360.0)) < 1e-3; why = 'rotation change %s' % (round(b['rot'] - a['rot'], 4) if a and b and a['rot'] is not None and b['rot'] is not None else '?')
    elif k == 'param':
        a, b = res['orig']['par'].get((e['eid'], e['name'])), res['out']['par'].get((e['eid'], e['name']))
        if b is None: why = 'not read'
        elif e['type'] == 'String': want = ','.join('%X' % ord(c) if ord(c) < 0x10000 else '%X,%X' % (0xD800 + ((ord(c) - 0x10000) >> 10), 0xDC00 + ((ord(c) - 0x10000) & 0x3FF)) for c in e['value']); ok = b[2] == want; why = 'utf16 %s' % b[2]
        else: ok = abs(float(b[1]) - float(e['value'])) < 1e-6; why = 'value %s' % b[1]
    print(('PASS ' if ok else 'FAIL ') + k + ' (' + why + ')'); npass += ok; nfail += not ok
print('EXPECT-CHECK', {'expectations': len(exp), 'pass': npass, 'fail': nfail})
sys.exit(1 if nfail else 0)

"""Aggregate fuzz failures by element class: for every non-200 chain, the classes of the EDITED elements and of the elements that changed undeclared.
usage: tools/fuzz_classes.py MODELDIR FUZZ.json [FUZZ.json...]  (counts only)"""
import sys, os, json, sqlite3, collections
db = sqlite3.connect(os.path.join(sys.argv[1], 'model.sqlite')); cls = lambda i: (db.execute('select cls from el where id=?', (i,)).fetchone() or ['?'])[0]
edited = collections.Counter(); changed = collections.Counter(); pair = collections.Counter(); n = 0; chains = 0
for f in sys.argv[2:]:
    j = json.load(open(f)); chains += j['chains']
    for x in j['failures']:
        if not x.get('ops'): continue
        n += 1; ec = sorted({cls(o['eid']) for o in x['ops']}); edited.update(ec)
        cc = sorted({cls(int(k.split(':')[1])) for k in x.get('changed', []) if k.startswith('el:')}); changed.update(cc)
        pair[(' + '.join(ec), ' + '.join(cc) or x['code'])] += 1
print('chains', chains, 'failures with ops', n); print('edited classes in failing chains', dict(edited)); print('undeclared-changed classes', dict(changed))
for (e, c), k in pair.most_common(): print(k, 'x edited[%s] -> changed[%s]' % (e, c))

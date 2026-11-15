"""Temp-orphan sweep of one target never removes another document's temp: names sharing the first 40 chars, one name being a prefix of the other, unicode names, and a temp of the same name in another directory."""
import os, sys, tempfile, shutil
sys.path.insert(0, os.path.expanduser('~/src/savegate'))
from savegate import atomic
T = tempfile.mkdtemp(); os.makedirs(T + '/o')
try:
    base = 'a' * 40
    names = [base + '_one.rvt', base + '_two.rvt', base + '_one.rvt.rvt', base[:20] + '.rvt', 'projekt äö.rvt', 'projekt äö 2.rvt']
    mine = names[0]; temps = {}
    for n in names:
        p = atomic.write_temp(os.path.join(T, n), b'x'); temps[n] = p
    other = atomic.write_temp(os.path.join(T, 'o', mine), b'x')
    extra = os.path.join(T, os.path.basename(temps[mine]).replace('.sgtmp', '.x.sgtmp')); open(extra, 'w').write('y')
    k = atomic.sweep_own_temps(os.path.join(T, mine))
    assert k == 1, k
    assert not os.path.exists(temps[mine])
    for n in names[1:]: assert os.path.exists(temps[n]), 'sibling temp of %r removed' % n
    assert os.path.exists(other) and os.path.exists(extra)
    print('OK')
finally: shutil.rmtree(T, ignore_errors=True)

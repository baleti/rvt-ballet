#!/usr/bin/env python3
"""rvt_vm_probe.py YEAR FILE EIDS : open a saved output in the offline Revit VM and print the PROBE readback lines (TYPEID etc.) for the comma separated element ids."""
import os, sys
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab/campaign')); os.environ['STAGEB'] = '1'; os.environ['PROBE_EIDS'] = sys.argv[3]
import stages
r = stages.api_stage(int(sys.argv[1]), sys.argv[2], True, 'pr' + str(os.getpid()))
print('OPEN', r['ok'], 'cmp', r.get('cmp'), 'dialogs', r.get('dialogs'))
for k in ('err','phase','lane','attempts','sec'):
    if r.get(k) is not None: print(k, r[k])
print('OUT', (r.get('out') or '')[-600:])
for p in r.get('probe', []): print('PROBE', p)
for p in r.get('pbind', []): print('PBIND', p)

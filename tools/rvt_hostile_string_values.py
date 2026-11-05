#!/usr/bin/env python3
"""c6x-rvtwrite: hostile set_string VALUES through the real gated save_as on a template (NUL, lone surrogate, CR/LF, 100k chars, BOM, empty, RTL, combining). Invariant: refused with source untouched, or saved and the value reads back exactly (or the gate verify refused). Prints one line per value. usage: rvt_hostile_string_values.py [RTE]"""
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
os.environ.setdefault('RVT_BALLET_CACHE', _T + '/bc'); os.environ.setdefault('RVT_CORE_CACHE', _T + '/cc')
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
RTE = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
VALS = {'nul': 'a\x00b', 'surrogate': 'a\ud800b', 'crlf': 'a\r\nb', 'long100k': 'x' * 100000, 'bom': '﻿name', 'empty': '', 'rtl': '‮abc', 'combining': 'é' * 50, 'tab': 'a\tb', 'quote': '"\'<>&'}
def main():
    from rvtballet import save
    sg = save._import(); import savegate as sg
    bad = 0
    for k, v in VALS.items():
        d = tempfile.mkdtemp(dir=_T); src = d + '/s.rte'; shutil.copy(RTE, src); h0 = sha(src); out = d + '/o.rte'
        ss = save.SaveSessions(sg.Config(allow_overwrite=False, require_gate=False)); ss.doc('m', src)
        try:
            save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': 24, 'value': v, 'match': ''}); save.save_as(ss, 'm', src, out); res = 'saved'
        except Exception as e: res = 'refused %s' % type(e).__name__
        ok = sha(src) == h0 and (res.startswith('refused') or os.path.exists(out))
        print(k, res, 'src_untouched=%s' % (sha(src) == h0), 'OK' if ok else 'FAIL', flush=True); bad += not ok
    sys.exit(1 if bad else 0)
main()

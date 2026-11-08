"""regression: a Revit string field stores its length in UTF-16 CODE UNITS. len(str) is wrong for non-BMP characters (emoji: 1 char = 2 units),
which wrote a length prefix one short and corrupted the record. No writer may pack len(<str>) next to .encode('utf-16le')."""
import os, re, sys
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
bad = []
for d in ('rvtballet', 'tools'):
    for f in sorted(os.listdir(os.path.join(root, d))):
        if not f.endswith('.py'): continue
        for n, l in enumerate(open(os.path.join(root, d, f), errors='replace'), 1):
            if re.search(r"pack\('<I',\s*len\([^()]*\)\)\s*\+\s*[^#\n]*\.encode\('utf-16le'\)", l): bad.append('%s/%s:%d' % (d, f, n))
assert not bad, 'length prefix uses len(str) instead of UTF-16 code units: %s' % bad
s = 'A\U0001F600B'; assert len(s.encode('utf-16le')) // 2 == 4 != len(s)
print('ok: no len(str)-prefixed utf-16 writers')

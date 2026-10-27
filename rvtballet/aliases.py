"""Command aliases for the command line, ~/.config/rvt-ballet/aliases.pgp (acad.pgp style, user editable): `ALIAS, *COMMAND [arguments]` per line, `;` starts a comment.
Created with the defaults on first use; never overwritten."""
import os

FILE = os.environ.get('RVT_BALLET_ALIASES') or os.path.expanduser('~/.config/rvt-ballet/aliases.pgp')
DEFAULT = """; rvt-ballet command aliases: ALIAS, *COMMAND [arguments]   (edit freely; reload the page to apply)
Z,   *FIT
ZE,  *FIT
F,   *FIND
SEL, *SELECT
I,   *ISOLATE
H,   *HIDE
SA,  *SHOWALL
O,   *OPEN
?,   *HELP
"""


def load():
    try:
        if not os.path.exists(FILE):
            os.makedirs(os.path.dirname(FILE), exist_ok=True); open(FILE, 'w').write(DEFAULT)
        text = open(FILE, encoding='utf-8', errors='replace').read()
    except OSError:
        text = DEFAULT
    out = {}
    for ln in text.splitlines():
        ln = ln.split(';', 1)[0].strip()
        if ',' not in ln: continue
        a, c = ln.split(',', 1); a, c = a.strip().lower(), c.strip()
        if a and c.startswith('*') and len(c) > 1: out[a] = c[1:].strip().lower()
    return out

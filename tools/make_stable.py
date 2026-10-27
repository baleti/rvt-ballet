"""tools/make_stable.py [DEST]: snapshot the viewer, its reader and the sheets renderer into a stable install (default ~/.local/share/rvt-ballet) so that
daily use does not follow edits in the working trees. Layout: DEST/{rvt-ballet,rvt-sheets,rvt-research,rvt-core/python}; python environments are symlinked
(DEST/rvt-ballet/.venv, DEST/rvt-sheets/.venv -> the working trees' venvs; they hold packages only). Hardcoded ~/src/... and ~/rvt-research paths in the
copied .py files are rewritten to DEST (env RVT_READER_DIR / RVT_CORE_PY / RVTSHEETS still override). Source files come from the working trees as they are
(tracked files only for the two git repos). No Autodesk samples or caches are copied."""
import os, re, shutil, subprocess, sys

H = os.path.expanduser('~')
DEST = os.path.abspath(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else '~/.local/share/rvt-ballet'))
SRC = {'rvt-ballet': H + '/src/rvt-ballet', 'rvt-sheets': H + '/src/rvt-sheets', 'rvt-research': H + '/rvt-research', 'rvt-core': H + '/src/rvt-core'}
SRC = {k: os.environ.get('SNAP_' + k.upper().replace('-', '_'), v) for k, v in SRC.items()}
SKIP_DIRS = {'screenshots', 'docs', 'qa'}


def git_export(repo, dst, skip=()):
    os.makedirs(dst, exist_ok=True)
    tar = subprocess.run(['git', '-C', repo, 'ls-files', '-z'], capture_output=True, check=True).stdout.split(b'\0')
    n = 0
    for f in tar:
        f = f.decode()
        if not f or f.split('/')[0] in skip or f.endswith(('.md', '.txt')) and '/' not in f and f.startswith(('HANDOFF', 'PROGRESS', 'NEEDS')): continue
        s = os.path.join(repo, f)
        if not os.path.isfile(s): continue
        d = os.path.join(dst, f); os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(s, d); n += 1
    return n


def rewrite(root):
    subs = [("os.path.expanduser('~/src/rvt-core/python')", "os.environ.get('RVT_CORE_PY') or %r" % (DEST + '/rvt-core/python')),
            ("os.path.expanduser('~/rvt-research')", "os.environ.get('RVT_READER_DIR') or %r" % (DEST + '/rvt-research')),
            ("os.path.expanduser('~/src/rvt-sheets')", "(os.environ.get('RVT_SHEETS_DIR') or %r)" % (DEST + '/rvt-sheets')),
            ("os.path.expanduser(os.environ.get('RVTSHEETS', '~/src/rvt-sheets'))", "os.environ.get('RVTSHEETS') or %r" % (DEST + '/rvt-sheets')),
            ("os.path.expanduser('~/src/rvt-sheets/rvtsheets')", "os.path.join(%r, 'rvtsheets')" % (DEST + '/rvt-sheets')),
            ("os.path.expanduser('~/src/rvt-sheets/rvt-sheets')", "%r" % (DEST + '/rvt-sheets/rvt-sheets')),
            ("os.path.expanduser('~/src/rvt-sheets/.venv/bin/python')", "%r" % (DEST + '/rvt-sheets/.venv/bin/python')),
            ("'path': '~/src/rvt-sheets'", "'path': %r" % (DEST + '/rvt-sheets')),
            ("os.path.expanduser('~/src/rvt-core/python')", "%r" % (DEST + '/rvt-core/python'))]
    # only the first four are env-aware; the exact-string subs below also apply to the leftover literal forms
    changed = 0
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ('.venv', '__pycache__', 'node_modules')]
        for f in fn:
            if not f.endswith('.py'): continue
            p = os.path.join(dp, f); s = open(p, encoding='utf-8').read(); o = s
            for a, b in subs: s = s.replace(a, b)
            s = s.replace("'~/src/rvt-sheets/.venv/bin/python'", repr(DEST + '/rvt-sheets/.venv/bin/python'))
            if s != o: open(p, 'w', encoding='utf-8').write(s); changed += 1
    return changed


def reader(src, dst):
    os.makedirs(dst, exist_ok=True); n = 0
    for f in sorted(os.listdir(src)):
        p = os.path.join(src, f)
        if not os.path.isfile(p): continue
        if f.endswith(('.md', '.log', '.rvt', '.sh', '.tsv', '.pkl', '.png')) or f.startswith(('HANDOFF', 'PROGRESS', 'agg_', 'pout_', 'PARAM_', 'cmp', 'ab_')): continue
        if os.path.getsize(p) > 8e6 and not f.endswith('.so'): continue
        if f.endswith(('.py', '.so', '.json', '.xml', '.txt', '.csv')): shutil.copy2(p, os.path.join(dst, f)); n += 1
    for d in ('rvtreader', 'data', 'schemas'):
        if os.path.isdir(os.path.join(src, d)): shutil.copytree(os.path.join(src, d), os.path.join(dst, d), dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
    return n


def main():
    if os.path.exists(DEST): shutil.move(DEST, DEST + '.prev')       # one previous snapshot is kept for rollback
    prev = DEST + '.prev'
    os.makedirs(DEST)
    print('rvt-ballet', git_export(SRC['rvt-ballet'], DEST + '/rvt-ballet', SKIP_DIRS))
    print('rvt-sheets', git_export(SRC['rvt-sheets'], DEST + '/rvt-sheets', SKIP_DIRS | {'out'}))
    print('rvt-research', reader(SRC['rvt-research'], DEST + '/rvt-research'))
    os.makedirs(DEST + '/rvt-core/python')
    for f in os.listdir(SRC['rvt-core'] + '/python'):
        p = SRC['rvt-core'] + '/python/' + f
        if os.path.isfile(p): shutil.copy2(p, DEST + '/rvt-core/python/' + f)
    for name in ('rvt-ballet', 'rvt-sheets'):
        v = SRC[name] + '/.venv'
        if os.path.isdir(v): os.symlink(v, DEST + '/' + name + '/.venv')
    print('rewritten files', rewrite(DEST + '/rvt-ballet') + rewrite(DEST + '/rvt-sheets') + rewrite(DEST + '/rvt-research') + rewrite(DEST + '/rvt-core'))
    open(DEST + '/SNAPSHOT.txt', 'w').write('snapshot %s\n' % subprocess.run(['date', '-Is'], capture_output=True, text=True).stdout.strip() + ''.join(
        '%s %s\n' % (k, subprocess.run(['git', '-C', v, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip() or '-') for k, v in SRC.items()))
    print(open(DEST + '/SNAPSHOT.txt').read())


if __name__ == '__main__':
    main()

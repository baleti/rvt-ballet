"""rvt-ballet CLI: direct open parsing, rvt-view shim, edit refusal paths, -o never overwrites the input, real edit on the Autodesk HVAC 2024 sample (skipped when absent)."""
import os, sys, subprocess, tempfile, hashlib, shutil
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
from rvtballet import cli, editcli
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
# 1. open parsing: files and flags open; subcommands and -h stay
assert cli.normalize_argv(['A.rvt', 'B.rvt']) == ['open', 'A.rvt', 'B.rvt']
assert cli.normalize_argv(['--no-browser', 'A.rvt']) == ['open', '--no-browser', 'A.rvt']
assert cli.normalize_argv(['open', 'A.rvt']) == ['open', 'A.rvt'] and cli.normalize_argv(['edit', 'A.rvt']) == ['edit', 'A.rvt']
assert cli.normalize_argv(['info', 'A.rvt']) == ['info', 'A.rvt'] and cli.normalize_argv(['serve']) == ['serve'] and cli.normalize_argv(['-h']) == ['-h'] and cli.normalize_argv([]) == []
# 2. shim: rvt-view prints one line to stderr and runs rvt-ballet
r = subprocess.run([os.path.join(HERE, 'bin', 'rvt-view'), 'edit', '--list-ops'], capture_output=True, text=True, timeout=120)
assert r.returncode == 0 and r.stderr.strip() == 'rvt-view is now rvt-ballet' and 'supported' in r.stdout, (r.returncode, r.stderr[-200:])
r = subprocess.run([os.path.join(HERE, 'bin', 'rvt-ballet'), 'edit', '--list-ops'], capture_output=True, text=True, timeout=120)
assert r.returncode == 0 and r.stderr == '' and 'rotate EID DEG' in r.stdout
# 3. op words -> ops, bad numbers rejected
assert editcli.build_op('move', ['5', '1', '0', '-2.5']) == {'op': 'move', 'eid': 5, 'dx': 1.0, 'dy': 0.0, 'dz': -2.5}
for k, v in (('move', ['x', '1', '0', '0']), ('rotate', ['5', 'abc']), ('delete', ['1.5'])):
    try: editcli.build_op(k, v); raise SystemExit('FAIL accepted bad ' + k)
    except ValueError: pass
# 4. path rules: input is never an -o target, existing OUT needs a flag, in-place needs the policy
d = tempfile.mkdtemp(); a = os.path.join(d, 'a.rvt'); open(a, 'wb').write(b'x'); os.symlink(a, os.path.join(d, 'link.rvt')); b = os.path.join(d, 'b.rvt'); open(b, 'wb').write(b'y')
os.environ.pop('RVTBALLET_ALLOW_OVERWRITE', None)
assert 'original' in editcli.check_paths(a, a, False, False) and 'original' in editcli.check_paths(a, os.path.join(d, 'link.rvt'), False, True) and 'original' in editcli.check_paths(a, a, False, True)
assert 'exists' in editcli.check_paths(a, b, False, False) and editcli.check_paths(a, b, False, True) is None and editcli.check_paths(a, os.path.join(d, 'new.rvt'), False, False) is None
assert 'SAVE!' in editcli.check_paths(a, None, True, False) and 'mutually' in editcli.check_paths(a, b, True, False) and 'give -o' in editcli.check_paths(a, None, False, False)
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; assert editcli.check_paths(a, None, True, False) is None; os.environ.pop('RVTBALLET_ALLOW_OVERWRITE')
# 5. edit command refusals leave every file untouched (exit 2, no traceback)
out = []; ha = sha(a)
assert editcli.edit_main([a, '--move', '1', '1', '0', '0', '-o', a], out.append) == 2 and sha(a) == ha
assert editcli.edit_main([a, '-o', os.path.join(d, 'z.rvt')], out.append) == 2      # no operation
assert editcli.edit_main([a, '--rotate', '1', '30', '-o', os.path.join(d, 'z.rvt')], out.append) == 2 and not os.path.exists(os.path.join(d, 'z.rvt'))      # not a Revit file
assert editcli.edit_main([os.path.join(d, 'missing.rvt'), '--delete', '1', '-o', os.path.join(d, 'z.rvt')], out.append) == 2
assert editcli.edit_main([a, '--move', 'q', '1', '0', '0', '-o', os.path.join(d, 'z.rvt')], out.append) == 2
assert editcli.edit_main([a, '--rotate', '1', '30', '--in-place'], out.append) == 2 and sha(a) == ha
print('cli parsing, shim and refusal paths OK')
# 6. real edit on a sample: -o writes a new file, input unchanged, second run refuses to replace it, a bad element is refused with a reason
F = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(F): print('skip real edit'); sys.exit(0)
src = os.path.join(d, 'h.rvt'); shutil.copy(F, src); h0 = sha(src); o = os.path.join(d, 'h_out.rvt'); out = []
rc = editcli.edit_main([src, '--move', '1490644', '2', '0', '0', '--set-string', '1365188', 'Mark', 'CLI1', '-o', o], out.append)
assert rc == 0 and os.path.exists(o) and sha(src) == h0 and sha(o) != h0 and 'accepted [supported]: move' in '\n'.join(out), out
assert editcli.edit_main([src, '--move', '1365188', '2', '0', '0', '-o', o], out.append) == 2
out = []; rc = editcli.edit_main([src, '--rotate', '999999999', '30', '-o', os.path.join(d, 'bad.rvt')], out.append)
assert rc == 3 and not os.path.exists(os.path.join(d, 'bad.rvt')) and sha(src) == h0 and 'refused' in out[-1], out
out = []; rc = editcli.edit_main([src, '--move', '1365188', '2', '0', '0', '--in-place'], out.append); assert rc == 2 and sha(src) == h0
shutil.rmtree(d, ignore_errors=True)
print('cli real edit OK: new file written, input unchanged, refusals clean')

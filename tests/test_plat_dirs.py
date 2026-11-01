"""no hardcoded ~/.cache or ~/.config left in the shipped modules: with RVTPLAT_CACHE/CONFIG set every location moves under them
(so Windows/macOS defaults from rvtplat.dirs apply); Linux default is unchanged."""
import os, sys, subprocess, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = "from rvtballet import vcache,aliases,viewctl,materials,save; print('\\n'.join([vcache.CACHE,aliases.FILE,viewctl.PRESETS,materials.TEX_LIB,save._disk_dir()]))"

def paths(env):
    e = {k: v for k, v in os.environ.items() if not k.startswith(('XDG_', 'RVTPLAT', 'RVT_', 'RVTBALLET'))}; e.update(env); e['PYTHONPATH'] = ROOT
    return subprocess.run([sys.executable, '-c', CODE], capture_output=True, text=True, env=e, cwd=ROOT).stdout.split('\n')[:5]

class T(unittest.TestCase):
    def test_overridden(self):
        v = paths({'RVTPLAT_CACHE': '/C', 'RVTPLAT_CONFIG': '/G'})
        self.assertEqual([p.split('/')[1] for p in v], ['C', 'G', 'G', 'C', 'C'], v)
    def test_linux_unchanged(self):
        h = os.path.expanduser('~'); v = paths({})
        self.assertEqual(v[0], h + '/.cache/rvt-ballet/vscene'); self.assertEqual(v[1], h + '/.config/rvt-ballet/aliases.pgp'); self.assertEqual(v[4], h + '/.cache/rvtballet/snapshots')
if __name__ == '__main__': unittest.main()

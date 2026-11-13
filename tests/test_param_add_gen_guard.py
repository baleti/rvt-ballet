"""c5x-rvttype 2026-11-13: the member-boundary insert path of rvt_param_add_gen (RVTGEN_INPLACE empty) is refused unless RVTGEN_EXPERIMENT=1
(Revit 2024 rejects its output on vendor-original files with CArchiveException 105). Synthetic: no input file is read before the refusal."""
import os, subprocess, sys
TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_param_add_gen.py')

def run(env_extra):
    env = dict(os.environ); env.pop('RVTGEN_EXPERIMENT', None); env.update(env_extra)
    return subprocess.run([sys.executable, TOOL, '/nonexistent/in.rvt', '/nonexistent/out.rvt'], env=env, capture_output=True, text=True)

def test_boundary_path_refused_by_default():
    r = run({'RVTGEN_INPLACE': ''})
    assert r.returncode != 0 and 'REFUSED' in (r.stdout + r.stderr) and 'RVTGEN_EXPERIMENT' in (r.stdout + r.stderr)

def test_experiment_flag_lifts_that_refusal():
    r = run({'RVTGEN_INPLACE': '', 'RVTGEN_EXPERIMENT': '1'})
    assert 'member-boundary insert path' not in (r.stdout + r.stderr)

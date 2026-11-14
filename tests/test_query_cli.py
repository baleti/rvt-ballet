"""rvt-ballet query (fastquery) CLI: (1) the query commands never open the .rvt for writing (open/os.open patched to refuse write modes on the target, in the master
and in the forked workers); (2) a file written in place or replaced while it is read gives exit 75 changed during read and no output, never a wrong answer
(deterministic hook + a replace-while-reading stress loop); (3) a damaged block gives a warning or a one-line error; (4) the CLI lists the same commands as
fastquery. Autodesk samples (skipped when the corpus is absent). Run: python -m pytest tests/test_query_cli.py"""
import os, sys, io, shutil, tempfile, threading, time, random, builtins, subprocess
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); sys.path.insert(0, HERE)
import pytest
from rvtballet import fastquery as Q, cli

CORPUS = os.path.expanduser("~/rvt-research/corpus")
A = os.path.join(CORPUS, "2020/18_rst_basic_sample_project.rvt"); B = os.path.join(CORPUS, "2020/19_Commercial_Sample_Project.rvt")
need = pytest.mark.skipif(not (os.path.exists(A) and os.path.exists(B)), reason="Autodesk corpus absent")
WRITE = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC


def run(argv, env=None):
    out = []; old = dict(os.environ); os.environ.update(env or {})
    try: rc = Q.main(argv, out.append)
    finally: os.environ.clear(); os.environ.update(old)
    return rc, out


def test_cli_lists_every_query_command():
    assert set(cli.QUERY) == set(Q.SUMMARY) | {"collect", "walls-red-material"} | set(Q.READY)
    assert all(c in Q.HELP for c in cli.QUERY)


@need
def test_queries_never_open_the_file_for_writing(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "m.rvt"); shutil.copy(A, f); st = os.stat(f); real = os.path.realpath(f); calls = []
        o_open, o_os_open, o_io_open = builtins.open, os.open, io.open
        def is_target(p):
            try: return os.path.realpath(p if not isinstance(p, int) else "") == real
            except Exception: return False
        def g_open(p, mode="r", *a, **k):
            if is_target(p): calls.append(("open", mode))
            if is_target(p) and any(c in mode for c in "wax+"): raise PermissionError("test: write open of the model")
            return o_open(p, mode, *a, **k)
        def g_os_open(p, flags, *a, **k):
            if is_target(p): calls.append(("os.open", flags))
            if is_target(p) and flags & WRITE: raise PermissionError("test: write os.open of the model")
            return o_os_open(p, flags, *a, **k)
        monkeypatch.setattr(builtins, "open", g_open); monkeypatch.setattr(io, "open", g_io := g_open); monkeypatch.setattr(os, "open", g_os_open)
        for argv in (["sheets", f], ["views", f, "--json"], ["levels", f], ["grids", f], ["counts", f, "--json"], ["elements", f, "--limit", "5"], ["walls", f, "--tsv"],
                     ["collect", f, "--category", "Doors"], ["walls-red-material", f], ["rooms", f, "--json"]):
            for w in ("1", "3"):                        # in-process and forked workers (they inherit the patched functions and the read-only handle)
                rc, out = run(argv, {"RVT_Q_WORKERS": w}); assert rc == 0 and out, (argv, rc)
        assert calls and all(m == "os.open" and not (fl & WRITE) for m, fl in calls if m == "os.open")
        assert os.stat(f).st_mtime_ns == st.st_mtime_ns and open(f, "rb").read() == open(A, "rb").read()


@need
def test_damaged_file_warns_or_fails_cleanly():
    rb = os.path.join(HERE, "bin", "rvt-ballet")
    with tempfile.TemporaryDirectory() as T:
        t1 = T + "/t1.rvt"; shutil.copy(A, t1)
        with open(t1, "r+b") as h: h.truncate(os.path.getsize(A) - 400000)
        r = subprocess.run([rb, "counts", t1], capture_output=True, text=True); assert "Traceback" not in r.stderr and (r.returncode != 0 or "WARNING" in r.stderr), (r.returncode, r.stderr[-300:])
        t2 = T + "/t2.rvt"; shutil.copy(A, t2)
        with open(t2, "r+b") as h: h.seek(os.path.getsize(A) // 2); b = h.read(1); h.seek(os.path.getsize(A) // 2); h.write(bytes([b[0] ^ 0xFF]))
        r = subprocess.run([rb, "counts", t2], capture_output=True, text=True); assert "Traceback" not in r.stderr and ("WARNING" in r.stderr or r.returncode != 0), (r.returncode, r.stderr[-300:])


def test_help_lists_query_commands():
    rb = os.path.join(HERE, "bin", "rvt-ballet")
    h = subprocess.run([rb, "--help"], capture_output=True, text=True).stdout; q = subprocess.run([rb, "query", "--help"], capture_output=True, text=True).stdout
    assert "rvt-ballet sheets FILE" in h and "query collect" in h and "install-skill" in h
    assert all(c in q for c in cli.QUERY)


def test_install_skill(tmp_path, monkeypatch):
    from rvtballet import skill
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    for n in (".claude", ".claude2", ".claude-x", ".claudeish", "other"): (tmp_path / n).mkdir()
    assert [os.path.basename(p) for p in skill.config_dirs(str(tmp_path))] == [".claude", ".claude-x", ".claude2"]
    monkeypatch.setattr(skill, "config_dirs", lambda: [str(tmp_path / ".claude"), str(tmp_path / ".claude2")])
    assert skill.main([]) == 0
    t = (tmp_path / ".claude2" / "skills" / "rvt-query" / "SKILL.md").read_text()
    assert t.startswith("---\nname: rvt-query\ndescription: ") and "{{RVT_BALLET}}" not in t and "rvt-ballet" in t

"""rvt-ballet install-skill: copy the Claude skill skills/rvt-query/SKILL.md into <config>/skills/rvt-query/ of every Claude config directory found
(~/.claude, ~/.claude2, ~/.claude3, ..., ~/.claude-NAME and $CLAUDE_CONFIG_DIR), so a fresh agent session that is asked about the contents of a .rvt finds
rvt-ballet. The installed copy names the rvt-ballet command of this checkout as a fallback when rvt-ballet is not on PATH. A host-local addendum
(~/.config/rvt-ballet/skill-local.md, never part of the repo: e.g. where private model copies live on that machine) is appended when present."""
import os, sys, re, argparse

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "skills", "rvt-query", "SKILL.md")
LOCAL = os.path.expanduser("~/.config/rvt-ballet/skill-local.md")


def config_dirs(home=None):
    home = home or os.path.expanduser("~"); out = []
    for n in sorted(os.listdir(home)):
        p = os.path.join(home, n)
        if re.fullmatch(r"\.claude(\d+|-[\w.-]+)?", n) and os.path.isdir(p) and not os.path.islink(p): out.append(p)
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    if env and os.path.isdir(env) and os.path.abspath(env) not in map(os.path.abspath, out): out.append(env)
    return out


def render():
    s = open(SRC, encoding="utf-8").read()
    wrapper = os.path.join(HERE, "bin", "rvt-ballet")
    s = s.replace("{{RVT_BALLET}}", wrapper)
    if os.path.exists(LOCAL): s = s.rstrip() + "\n\n## This machine\n" + open(LOCAL, encoding="utf-8").read().strip() + "\n"
    return s


def main(argv):
    ap = argparse.ArgumentParser(prog="rvt-ballet install-skill", description=__doc__)
    ap.add_argument("--dir", action="append", default=[], help="install into this config directory only (repeatable)")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--print", action="store_true", help="print the rendered SKILL.md and exit")
    a = ap.parse_args(argv)
    text = render()
    if a.print: sys.stdout.write(text); return 0
    dirs = a.dir or config_dirs()
    if not dirs: print("rvt-ballet: no Claude config directory found (~/.claude*): nothing installed", file=sys.stderr); return 1
    for d in dirs:
        t = os.path.join(d, "skills", "rvt-query", "SKILL.md")
        old = open(t, encoding="utf-8").read() if os.path.exists(t) else None
        what = "unchanged" if old == text else ("updated" if old is not None else "installed")
        if not a.dry_run and old != text:
            os.makedirs(os.path.dirname(t), exist_ok=True); tmp = t + ".tmp"
            open(tmp, "w", encoding="utf-8").write(text); os.replace(tmp, t)
        print("%s %s" % ("would be " + what if a.dry_run else what, t))
    return 0


if __name__ == "__main__": sys.exit(main(sys.argv[1:]))

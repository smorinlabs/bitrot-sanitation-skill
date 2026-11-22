"""Hook declaration tests (design §7).

1. Text: every command has the guarded form and names the right harness.
2. Missing brot: every command exits 0 and prints nothing without brot on PATH.
3. Stability (HC-06a): hook files equal the latest release tag's, unless
   HOOK_CHANGE_FLAGGED=1 (the release notes flag a hook change, DS-05).
4. Replay: with BROT_FIXTURES set to a directory of captured payloads
   (<harness>/<NativeEvent>[.<case>].json), each declared command records a
   non-error hook event in a throwaway database. Skipped, and said so, without it.

Run: python3 -I tests/hooks.py
"""
import json, os, re, shutil, sqlite3, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "brot"
FILES = {"claude-code": PLUGIN / "hooks" / "hooks.json",
         "codex": PLUGIN / "hooks" / "codex-hooks.json"}
GUARD = re.compile(r"^if command -v brot >/dev/null 2>&1; then brot hook (\S+) (\S+); fi$")
EXPECTED = {
    "claude-code": {"SessionStart": "session-start", "SessionEnd": "session-end",
                    "PreToolUse": "pre-tool", "PostToolUse": "post-tool-use",
                    "PostToolUseFailure": "post-tool-use-failure",
                    "SubagentStart": "subagent-start", "SubagentStop": "subagent-stop",
                    "PostCompact": "post-compact"},
    "codex": {"SessionStart": "session-start", "SessionEnd": "session-end",
              "PreToolUse": "pre-tool", "PostToolUse": "post-tool-use",
              "SubagentStart": "subagent-start", "SubagentStop": "subagent-stop",
              "PostCompact": "post-compact"},
    "muse": {"SessionStart": "session-start", "SessionEnd": "session-end",
             "PreToolUse": "pre-tool", "PostToolUse": "post-tool-use",
             "PostToolUseFailure": "post-tool-use-failure",
             "SubagentStart": "subagent-start", "SubagentStop": "subagent-stop",
             "PostCompact": "post-compact"},
}
MUSE = PLUGIN / ".muse-plugin" / "plugin.json"
failures = []

def fail(msg):
    failures.append(msg)
    print("FAIL", msg)

def commands(harness):
    """Native event -> argv to run. Shell commands run through /bin/sh."""
    if harness == "muse":
        hooks = json.loads(MUSE.read_text())["capabilities"]["hooks"]
        return {h["event"]: h["command"] for h in hooks}
    data = json.loads(FILES[harness].read_text())
    out = {}
    for event, groups in data["hooks"].items():
        for g in groups:
            for h in g["hooks"]:
                out[event] = ["/bin/sh", "-c", h["command"]]
    return out

def test_text():
    for harness, want in EXPECTED.items():
        got = commands(harness)
        if set(got) != set(want):
            fail(f"{harness}: events {sorted(got)} != {sorted(want)}")
        for event, argv in got.items():
            if harness == "muse":
                want_argv = ["brot", "hook", "muse", want.get(event)]
                if argv != want_argv:
                    fail(f"muse {event}: argv {argv}, want {want_argv}")
                continue
            cmd = argv[2]
            m = GUARD.match(cmd)
            if not m:
                fail(f"{harness} {event}: command not in the guarded form: {cmd!r}")
            elif m.groups() != (harness, want.get(event)):
                fail(f"{harness} {event}: names {m.groups()}, want {(harness, want.get(event))}")
    print("ok   text" if not failures else "done text")

def test_missing_brot():
    env = {"PATH": "/usr/bin:/bin", "HOME": tempfile.mkdtemp()}
    for harness in ("claude-code", "codex"):  # Muse runs argv: no shell guard (design §3.2)
        for event, argv in commands(harness).items():
            p = subprocess.run(argv, input=b"{}", env=env, capture_output=True)
            if p.returncode != 0 or p.stdout or p.stderr:
                fail(f"{harness} {event}: without brot exit={p.returncode} out={p.stdout!r} err={p.stderr!r}")
    print("ok   missing brot" if not failures else "done missing brot")

def test_stability():
    tags = subprocess.run(["git", "-C", str(ROOT), "tag", "--list", "v*", "--sort=-v:refname"],
                          capture_output=True, text=True).stdout.split()
    if not tags:
        print("skip stability: no release tag yet")
        return
    if os.environ.get("HOOK_CHANGE_FLAGGED") == "1":
        print("skip stability: HOOK_CHANGE_FLAGGED=1")
        return
    for f in list(FILES.values()) + [PLUGIN / ".muse-plugin" / "plugin.json"]:
        rel = f.relative_to(ROOT).as_posix()
        old = subprocess.run(["git", "-C", str(ROOT), "show", f"{tags[0]}:{rel}"], capture_output=True)
        if old.returncode != 0:
            continue  # file is new since the tag: adding a harness is allowed
        cur = f.read_bytes()
        if rel.endswith(".muse-plugin/plugin.json"):
            old_hooks = json.loads(old.stdout).get("capabilities", {}).get("hooks")
            if json.loads(cur).get("capabilities", {}).get("hooks") != old_hooks:
                fail(f"{rel}: hooks changed since {tags[0]}")
        elif cur != old.stdout:
            fail(f"{rel}: changed since {tags[0]}")
    print("ok   stability" if not failures else "done stability")

def test_replay():
    fixtures = os.environ.get("BROT_FIXTURES")
    if not fixtures:
        print("skip replay: BROT_FIXTURES is not set")
        return
    if not shutil.which("brot"):
        fail("replay: BROT_FIXTURES is set but brot is not on PATH")
        return
    tmp = Path(tempfile.mkdtemp())
    db = tmp / "brot.db"
    env = dict(os.environ, BROT_DB=str(db), XDG_STATE_HOME=str(tmp / "state"),
               XDG_CONFIG_HOME=str(tmp / "config"))
    env.pop("BROT_SESSION", None)
    subprocess.run(["brot", "object", "list"], env=env, capture_output=True, check=True)
    n = 0
    for harness in EXPECTED:
        cmds = commands(harness)
        for fx in sorted((Path(fixtures) / harness).glob("*.json")):
            if fx.name.endswith(".env.json"):
                continue
            event = fx.name.split(".")[0]
            if event not in cmds:
                continue  # an event the plugin does not declare
            p = subprocess.run(cmds[event], input=fx.read_bytes(),
                               env=env, capture_output=True)
            con = sqlite3.connect(db)
            row = con.execute("SELECT harness, event, outcome FROM hook_events ORDER BY id DESC LIMIT 1").fetchone()
            con.close()
            want = (harness, EXPECTED[harness][event])
            if p.returncode != 0:
                fail(f"replay {harness}/{fx.name}: exit {p.returncode}")
            elif not row or row[:2] != want:
                fail(f"replay {harness}/{fx.name}: last hook event {row}, want {want}")
            elif row[2] == "error":
                fail(f"replay {harness}/{fx.name}: outcome error")
            n += 1
    print(f"ok   replay ({n} payloads)")

def test_versions():
    meta = re.search(r'^version = "([^"]+)"', (PLUGIN / "plugin.meta.toml").read_text(), re.M).group(1)
    for f in (MUSE, PLUGIN / ".claude-plugin" / "plugin.json", PLUGIN / ".codex-plugin" / "plugin.json"):
        v = json.loads(f.read_text()).get("version")
        if v != meta:
            fail(f"{f.relative_to(ROOT)}: version {v}, plugin.meta.toml has {meta}")
    print("ok   versions" if not failures else "done versions")

for t in (test_text, test_versions, test_missing_brot, test_stability, test_replay):
    t()
sys.exit(1 if failures else 0)

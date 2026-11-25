"""Hook declaration tests (design §7).

1. Text: every command has the guarded form and names the right harness.
2. Antigravity structure & sync: named hook group, flat SessionStart/Stop,
   grouped PostToolUse matcher, byte-identical source and generated hooks.json,
   and generated .antigravity-plugin/plugin.json + .agents/plugins.json.
3. Missing brot: every shell-guarded command exits 0 without brot on PATH
   (empty output on Claude Code/Codex; valid JSON `{}` on Antigravity).
4. Stability (HC-06a): hook files equal the latest release tag's, unless
   HOOK_CHANGE_FLAGGED=1 (the release notes flag a hook change, DS-05).
5. Replay: with BROT_FIXTURES set to a directory of captured payloads
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
AGY_SRC = PLUGIN / "hooks" / "antigravity-hooks.json"
AGY_GEN = PLUGIN / "hooks.json"
AGY_MANIFEST = PLUGIN / ".antigravity-plugin" / "plugin.json"
AGY_PLUGINS_CFG = ROOT / ".agents" / "plugins.json"
AGY_POST_TOOL_MATCHER = "run_command|write_file|write_to_file"
AGY_FLAT_EVENTS = ("SessionStart", "PreInvocation", "PostInvocation", "Stop")
AGY_GROUPED_EVENTS = ("PreToolUse", "PostToolUse")

GUARD = re.compile(r"^if command -v brot >/dev/null 2>&1; then brot hook (\S+) (\S+); fi$")
AGY_GUARD = re.compile(
    r"^if command -v brot >/dev/null 2>&1; then brot hook (antigravity) (\S+); else printf '\{\}\\n'; fi$"
)
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
    "antigravity": {"SessionStart": "session-start",
                    "PostToolUse": "post-tool-use",
                    "Stop": "stop"},
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
    if harness == "antigravity":
        data = json.loads(AGY_GEN.read_text())
        out = {}
        for group in data.values():
            if not isinstance(group, dict):
                continue
            for event in AGY_FLAT_EVENTS:
                for h in group.get(event, []):
                    out[event] = ["/bin/sh", "-c", h["command"]]
            for event in AGY_GROUPED_EVENTS:
                for g in group.get(event, []):
                    for h in g["hooks"]:
                        out[event] = ["/bin/sh", "-c", h["command"]]
        return out
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
            pattern = AGY_GUARD if harness == "antigravity" else GUARD
            m = pattern.match(cmd)
            if not m:
                fail(f"{harness} {event}: command not in the guarded form: {cmd!r}")
            elif m.groups() != (harness, want.get(event)):
                fail(f"{harness} {event}: names {m.groups()}, want {(harness, want.get(event))}")
    print("ok   text" if not failures else "done text")

def test_antigravity_structure():
    before = len(failures)
    if not AGY_SRC.is_file():
        fail(f"antigravity: missing {AGY_SRC.relative_to(ROOT)}")
        return
    if not AGY_GEN.is_file():
        fail(f"antigravity: missing {AGY_GEN.relative_to(ROOT)}")
        return
    if AGY_GEN.read_bytes() != AGY_SRC.read_bytes():
        fail("antigravity: plugins/brot/hooks.json is out of sync with hooks/antigravity-hooks.json")

    data = json.loads(AGY_GEN.read_text())
    if not isinstance(data, dict) or set(data) != {"brot"}:
        fail(f"antigravity: top-level keys {sorted(data) if isinstance(data, dict) else type(data)}, want ['brot']")
    else:
        group = data["brot"]
        if not isinstance(group, dict):
            fail("antigravity: 'brot' hook group is not an object")
        else:
            want_keys = set(EXPECTED["antigravity"])
            got_keys = set(group) - {"enabled"}
            if got_keys != want_keys:
                fail(f"antigravity: hook group events {sorted(got_keys)}, want {sorted(want_keys)}")
            if "enabled" in group and not isinstance(group["enabled"], bool):
                fail("antigravity: 'enabled' must be a boolean")
            for event in ("SessionStart", "Stop"):
                handlers = group.get(event)
                if not isinstance(handlers, list) or len(handlers) != 1:
                    fail(f"antigravity {event}: expected flat list of 1 handler, got {handlers!r}")
                else:
                    h = handlers[0]
                    if not isinstance(h, dict) or h.get("type") != "command" or not isinstance(h.get("command"), str):
                        fail(f"antigravity {event}: invalid flat handler {h!r}")
                    if "hooks" in h or "matcher" in h:
                        fail(f"antigravity {event}: flat event must not wrap in matcher/hooks: {h!r}")
            post = group.get("PostToolUse")
            if not isinstance(post, list) or len(post) != 1:
                fail(f"antigravity PostToolUse: expected grouped list of 1 entry, got {post!r}")
            else:
                entry = post[0]
                if not isinstance(entry, dict) or entry.get("matcher") != AGY_POST_TOOL_MATCHER:
                    fail(f"antigravity PostToolUse: matcher {entry.get('matcher') if isinstance(entry, dict) else None!r}, want {AGY_POST_TOOL_MATCHER!r}")
                handlers = entry.get("hooks") if isinstance(entry, dict) else None
                if not isinstance(handlers, list) or len(handlers) != 1:
                    fail(f"antigravity PostToolUse: expected 1 handler, got {handlers!r}")
                elif handlers[0].get("type") != "command" or not isinstance(handlers[0].get("command"), str):
                    fail(f"antigravity PostToolUse: invalid handler {handlers[0]!r}")

    if not AGY_MANIFEST.is_file():
        fail(f"antigravity: missing {AGY_MANIFEST.relative_to(ROOT)}")
    else:
        manifest = json.loads(AGY_MANIFEST.read_text())
        hooks_src = manifest.get("extensions", {}).get("harness-kit", {}).get("hooksSource")
        if hooks_src != "./hooks/antigravity-hooks.json":
            fail(f"antigravity: manifest hooksSource {hooks_src!r}, want './hooks/antigravity-hooks.json'")

    if not AGY_PLUGINS_CFG.is_file():
        fail(f"antigravity: missing {AGY_PLUGINS_CFG.relative_to(ROOT)}")
    else:
        cfg = json.loads(AGY_PLUGINS_CFG.read_text())
        entries = cfg.get("entries")
        if not isinstance(entries, list) or not any(isinstance(e, dict) and e.get("path") == "plugins" for e in entries):
            fail(f"antigravity: .agents/plugins.json missing plugins entry: {cfg!r}")

    print("ok   antigravity" if len(failures) == before else "done antigravity")

def test_missing_brot():
    before = len(failures)
    env = {"PATH": "/usr/bin:/bin", "HOME": tempfile.mkdtemp()}
    for harness in ("claude-code", "codex", "antigravity"):  # Muse runs argv: no shell guard (design §3.2)
        for event, argv in commands(harness).items():
            p = subprocess.run(argv, input=b"{}", env=env, capture_output=True)
            if harness == "antigravity":
                if p.returncode != 0 or p.stdout != b"{}\n" or p.stderr:
                    fail(f"{harness} {event}: without brot exit={p.returncode} out={p.stdout!r} err={p.stderr!r}")
            elif p.returncode != 0 or p.stdout or p.stderr:
                fail(f"{harness} {event}: without brot exit={p.returncode} out={p.stdout!r} err={p.stderr!r}")
    print("ok   missing brot" if len(failures) == before else "done missing brot")

def test_stability():
    before = len(failures)
    tags = subprocess.run(["git", "-C", str(ROOT), "tag", "--list", "v*", "--sort=-v:refname"],
                          capture_output=True, text=True).stdout.split()
    if not tags:
        print("skip stability: no release tag yet")
        return
    if os.environ.get("HOOK_CHANGE_FLAGGED") == "1":
        print("skip stability: HOOK_CHANGE_FLAGGED=1")
        return
    for f in list(FILES.values()) + [AGY_SRC, AGY_GEN, MUSE]:
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
    print("ok   stability" if len(failures) == before else "done stability")

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
            elif harness == "antigravity":
                if p.stderr:
                    fail(f"replay {harness}/{fx.name}: non-empty stderr {p.stderr!r}")
                try:
                    parsed_out = json.loads(p.stdout)
                except json.JSONDecodeError as e:
                    fail(f"replay {harness}/{fx.name}: stdout not valid JSON ({e}): {p.stdout!r}")
                else:
                    if not isinstance(parsed_out, dict):
                        fail(f"replay {harness}/{fx.name}: stdout JSON not an object: {parsed_out!r}")
            n += 1
    print(f"ok   replay ({n} payloads)")

def test_versions():
    before = len(failures)
    meta = re.search(r'^version = "([^"]+)"', (PLUGIN / "plugin.meta.toml").read_text(), re.M).group(1)
    for f in (MUSE, PLUGIN / ".claude-plugin" / "plugin.json",
              PLUGIN / ".codex-plugin" / "plugin.json", AGY_MANIFEST):
        v = json.loads(f.read_text()).get("version")
        if v != meta:
            fail(f"{f.relative_to(ROOT)}: version {v}, plugin.meta.toml has {meta}")
    print("ok   versions" if len(failures) == before else "done versions")

for t in (test_text, test_antigravity_structure, test_versions, test_missing_brot, test_stability, test_replay):
    t()
sys.exit(1 if failures else 0)

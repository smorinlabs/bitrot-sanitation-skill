# T4 — `bitrot-sanitation-skill`: design

**Status:** design phase, draft 1, written 2026-11-22 against `brot` v0.8.2. It implements `docs/requirements.md` (draft 3). The three decisions in §9 were settled on 2026-11-22.
**Harness versions checked:** Claude Code 2.1.330, Codex `codex-cli 0.171.0`, Muse Code 1.4.25, OpenCode v2.3.0, harness-kit 0.4.0.
**Evidence labels** are as in requirements §0.4: **[O]** observed on 2026-11-22, **[D]** from the harness's official documentation, **[U]** unverified.

## 1. What v1 ships

One plugin named `brot`. It contains:

- one skill, also named `brot` (requirements OQ-07);
- hook declarations for Claude Code, Codex and Muse;
- an OpenCode plugin module.

Every hook calls `brot hook <harness> <event>` with the payload on stdin (HC-06). The hooks contain no logic beyond the missing-binary guard (DG-01).

### 1.1 Deferred from v1

These requirements depend on `brot` features that v0.8.2 does not have. v1 states each gap in the skill text. None is stubbed.

| Requirement | Needs from `brot` | v1 behaviour |
|---|---|---|
| SK-17, SK-18, DEP-14 (stored cleanup policy) | T3 reopens D-3 (conflict C-2) | The skill follows SK-10 and SK-11 and asks before every destructive step. The skill tells the user that policies are not yet stored |
| SK-21 selectable soft modes for worktrees, branches and PRs | T3 reopens D-4 (conflict C-4) | The skill reports the backup ref `brot` keeps for each removed branch and worktree HEAD |
| DS-03 runtime range check inside hooks, DG-02 hook no-op | DEP-08: `brot` would have to know the plugin's range | Only the skill checks the range (§6). Hooks always call `brot` |
| SL-04 re-inject after compaction | `brot` prints context only on `session-start` | The `post-compact` hook is declared, and `brot` records it. If `brot` later prints context on it, the hook text stays the same (HC-06a) |
| SL-02 fork links for Claude Code and Codex | No harness sends a fork parent in hook payloads ([D] both harnesses' hook docs) | The skill links sessions manually (SL-03) |

## 2. Repo layout (home 5, CV-06)

```
harness.toml                        marketplace identity (harness-kit)
plugins/brot/
  plugin.meta.toml                  plugin metadata (harness-kit)
  .claude-plugin/plugin.json        generated
  .codex-plugin/plugin.json         see §9 D-1
  .muse-plugin/plugin.json          hand-maintained; native Muse manifest and hooks
  hooks/hooks.json                  hand-maintained; Claude Code hooks
  hooks/codex-hooks.json            hand-maintained; Codex hooks
  opencode/brot.js                  hand-maintained; OpenCode module
  skills/brot/SKILL.md
  skills/brot/references/*.md       CV-02 split
  compat.toml                       supported brot range (DS-03)
.claude-plugin/marketplace.json     generated
.agents/plugins/marketplace.json    generated
tests/                              see §7
```

**Why the hooks are split into separate files:**

- Claude Code and Codex both load `hooks/hooks.json` by default ([D]). Each command names its harness, so the two harnesses cannot share that file. The Codex manifest therefore points at `hooks/codex-hooks.json` through its `hooks` key.
- When `.muse-plugin/` is missing, Muse falls back to the Claude manifest and imports `hooks/hooks.json`. It would then run `brot hook claude-code …` ([O] `muse plugins validate`). The native Muse manifest is therefore required.
- With `.muse-plugin/` present, Muse ignores `hooks/hooks.json` and the other manifests. It warns only `multiple-manifests` ([O]).

## 3. Hook declarations

### 3.1 Events

| `brot` event | Claude Code | Codex | Muse | OpenCode module source |
|---|---|---|---|---|
| `session-start` | `SessionStart` | `SessionStart` | `SessionStart` | the first event seen for a root session (`session-created`), and `session.created` for a child session |
| `session-end` | `SessionEnd` | `SessionEnd` | `SessionEnd` | `session.deleted` (`session-deleted`); `session.execution.*` other than started (`execution-ended`) |
| `post-tool-use` | `PostToolUse`, matcher `Bash\|Write` | `PostToolUse` | `PostToolUse` | `tool.execute.after` (`tool-after`) |
| `post-tool-use-failure` | `PostToolUseFailure`, matcher `Bash\|Write` | **not declared**: Codex 0.171.0 has no such event ([O] binary, [D] event list) | `PostToolUseFailure` | — (part of `tool-after`) |
| `subagent-start` | `SubagentStart` | `SubagentStart` | `SubagentStart` | `session.created` carrying `parentID` |
| `subagent-stop` | `SubagentStop` | `SubagentStop` | `SubagentStop` | — |
| `post-compact` | `PostCompact` | `PostCompact` | `PostCompact` | — |
| `pre-tool` (HC-07a) | `PreToolUse`, matcher `Bash` | `PreToolUse`, matcher `Bash` | see §9 D-2 | `tool.execute.before`, filtered in code to the shell tool |
| (OpenCode) `session-forked` | — | — | — | `ctx.session.hook("fork")` |

No `Stop` and no `UserPromptSubmit` hook on any harness (T3 `FR-HOOK-19`). `brot` records every event name it does not handle as `ignored`. That includes `pre-tool` today, so declaring it is safe (C-1).

### 3.2 Command text

- **Claude Code and Codex:** `if command -v brot >/dev/null 2>&1; then brot hook <harness> <event>; fi`. When `brot` is missing, the hook exits 0 and prints nothing (DG-01). `brot doctor` recognises this form; a form such as `sh -c '…'` would show as `unknown` (T3 `FR-HOOK-9`).
- **Muse:** the argument vector `["brot", "hook", "muse", "<event>"]`, with `timeoutMs` set. Observed on Muse 1.4.25 with `muse plugins hook test` in a throwaway Muse home ([O]):
  - Muse finds `brot` on `PATH`, and the hook completes with exit 0.
  - With `brot` missing, the hook ends `failed` with "No such file or directory", and Muse does not block the tool call (`should_block: false`). Muse has no shell guard, so this is the v1 behaviour for DG-01. Whether Muse shows the failure to the user in a live session is [U].
  - Muse treats any argv element that contains `/` as a file inside the plugin, so `sh -c '… >/dev/null …'` fails validation. It does not expand variables in argv either.
  - Muse passes hooks a fixed set of environment variables (`HOME`, `PATH`, `USER`, `SHELL`, `TERM`, `TMPDIR`, `LANG`, `LOGNAME` and the plugin variables). `BROT_DB`, `BROT_CONFIG` and every `XDG_*` variable are dropped, so `brot` under Muse always uses its default paths under `HOME`. That was `hook test`; whether a live session passes more, including `MUSE_SESSION_ID`, is [U] (§10).
- **No hook names a plugin path or a bundled script.** Codex asks for a new review when a bundled script changes, even if the hook definition stays the same ([D]).

### 3.3 Keeping the hook text unchanged (HC-06a)

Codex and Muse approve hooks one at a time, by hash ([D], [O]):

- **Codex** keys trust by plugin, hook file path, event, group index and hook index ([O]). The key contains no version.
- **Muse** keys approval as `plugin:<id>:hook:<hook-id>` ([O]).

Rules that keep approvals valid across releases:

1. Never change a command, even to reformat it.
2. Never rename a hook file.
3. Codex groups and hooks are append-only, in a fixed order.
4. Muse hook `id`s never change. They are named `brot-<event>`.
5. CI compares every hook file, and the `hooks` part of the Muse manifest, against the previous release tag. CI fails when they differ, unless the release notes flag a hook change (DS-05).

Unverified: whether a version bump with unchanged hook text really keeps the approval on Codex and Muse ([U]). §8 tests this before v0.1.0 ships.

## 4. OpenCode module (HC-05, HC-12)

- **API:** targets the V2 API only: `export default Plugin.define({ id: "brot", setup(ctx) { … } })` ([D]).
- **Session ID in shells (`FR-HOOK-4`):** the module injects nothing. OpenCode 2.3.0 sets `OPENCODE_SESSION_ID` in the agent shell, and `brot` resolves it (T3 contract). v1 therefore requires OpenCode 2.3.0 or later. This departs from HC-12, which asks for the `BROT_SESSION=opencode:<id> ` prefix; see §9 D-3.
- **Mappings (HC-12):**
  - a root session's first event becomes `session-created`;
  - `session.deleted` and an interrupted execution become a session end;
  - `session.idle` is not an end;
  - child sessions start through `session.created` carrying `parentID`.
- **Calls:** `Bun.spawn(["brot", "hook", "opencode", event])`, written as that literal array because `brot doctor` recognises only literal forms. Without Bun it uses `node:child_process`. The JSON payload goes on stdin. The module awaits the call only for a root `session-created` and for `session-forked`, the two events where `brot` prints context. Every other call runs without waiting, so the agent is never blocked.
- **Context:** the printed `{"context": …}` text is added once, to that session's next model request, through `ctx.session.hook("context")`. The module reads the session from the hook's `sessionID` field. The docs do not list that field, so context injection is [U] until a live run (§8).
- **Guard (DG-01):** a failed spawn is caught and dropped. It is never thrown into OpenCode.
- **Install:** copy or symlink the module into `~/.config/opencode/plugins/` (OQ-06). The skill is found through `~/.claude/skills` or `~/.agents/skills` ([D]). Whether OpenCode 2.3.0 honours `.agents/skills` is [U].

## 5. Skill

`SKILL.md` holds:

- the description (CV-03, 300–500 characters, carved against `session-loose-ends`, CV-04);
- the iron law, "never delete a tracked object except through `brot`";
- a Red Flags table (CV-07);
- the workflow: register, record a blocker, check status, clean up, end report, link sessions.

References (CV-02):

| File | Holds |
|---|---|
| `registration.md` | What hooks register automatically, and the manual commands |
| `blockers.md` | How to add, evaluate and resolve blockers |
| `cleanup.md` | Plan, soft risks, hard stops, force rules (SK-11), and how to report a delete |
| `degraded-modes.md` | `brot` missing, version out of range, the DG-06 checks and their fix commands |
| `harness-claude-code.md`, `harness-codex.md`, `harness-muse.md`, `harness-opencode.md` | Install, trust step, verification command (HC-02, HC-10) |

The skill never uses `--force-agent` unless the user asks for it, and then passes the user's request as `--reason` (OQ-15 (f)).

## 6. Version compatibility (DS-03)

`plugins/brot/compat.toml` holds `brot = ">=0.8.2, <0.9.0"`. It is the only place the supported range is written down. The skill reads it, runs `brot --version`, and reports any mismatch with the install command (DG-02). Hooks do not check the range (§1.1).

## 7. Tests

| Layer | What | How |
|---|---|---|
| Manifests | Each harness accepts the plugin | `claude plugin validate`, `muse plugins validate --json` (zero errors), `uv run harness-kit gen --check` |
| Hook text | Every command matches the §3.1 table, and the stability check from §3.3 | a script under `tests/` |
| Shim replay | Each declared command, run with a payload on stdin and a throwaway `BROT_DB`, records the expected outcome in `brot`'s hook-event record (DEP-13) | Fixtures come from `BROT_FIXTURES`, a path to brot's checkout. None are copied into this public repo (CV-09). Without `BROT_FIXTURES`, the test is skipped and says so |
| OpenCode module | The mappings in §4, against a fake `ctx` | `node --test`, no dependencies (NF-05) |
| Missing `brot` | Every shim exits 0 with no output when `PATH` has no `brot` | the same script |
| Skill | Fleet skill checks | `skill-quality` layers 1, 2, 3, 4 against the worktree (CV-01) |

## 8. Verification before v0.1.0

Each check runs in a throwaway harness home (`CODEX_HOME`, the Muse `XDG_*` variables, a temporary Claude config). None touches the user's live configuration.

1. Install the plugin from a local marketplace on each harness, and confirm the hooks fire, using `brot doctor` with a throwaway `BROT_DB`. Done so far (2026-11-22, [O]):
   - Muse: installed and approved in a throwaway Muse home. Its `post-tool-use` hook ran `brot` through `muse plugins hook test`.
   - OpenCode: the module ran against the real `brot` with a captured payload. `brot doctor` reported it `declared` and `firing` from a throwaway OpenCode config directory.
   - Claude Code 2.1.330: one headless session with `--plugin-dir` and a throwaway `BROT_DB` ran `git worktree add`. `brot` recorded `session-start` (ok), `pre-tool` (ignored), `post-tool-use` (ok) and `session-end` (ok), with plugin version `0.0.0`, and registered the worktree and its branch as hook registrations needing validation.
   - Codex 0.171.0: `codex plugin add` into a throwaway `CODEX_HOME` installed a manifest whose `hooks` entry is `./hooks/codex-hooks.json`. No session was run: a throwaway `CODEX_HOME` has no login.
2. On Codex and Muse, approve the hooks. Bump only the plugin version, reinstall, and confirm the hooks still run without a new approval. This tests the HC-06a premise.
3. ~~Run Muse with `brot` missing~~ Done: the hook fails and does not block (§3.2).
4. ~~Measure Muse `pre-tool` latency~~ Done 2026-11-22: 8.9 ms p95 (D-2).

## 9. Open design decisions

| ID | Question | Options | Recommendation |
|---|---|---|---|
| D-1 | How does the Codex manifest get its `hooks` key? harness-kit 0.4.0 cannot write it, and `plugin.meta.toml` rejects unknown keys | A: add an optional `codex_hooks` path to harness-kit (a separate PR in that repo), then generate. B: set `codex = false` and hand-maintain `.codex-plugin/plugin.json` | **Decided 2026-11-22 (owner): A.** Shipped in harness-kit v0.5.0 (`codex_hooks`); `plugin.meta.toml` sets `codex_hooks = "./hooks/codex-hooks.json"` |
| D-2 | Muse rejects `matcher`, so a Muse `pre-tool` hook runs `brot` on every tool call | A: declare it. B: leave it out until Muse supports matchers | **Decided on evidence: A.** `brot hook muse pre-tool` measured 7.7 ms p50 and 8.9 ms p95 over 60 runs (2026-11-22, brot 0.8.2), far inside the 100 ms p95 budget of T3 `FR-HOOK-7` |
| D-3 | OpenCode session ID for `brot` commands the agent runs (HC-12, T3 `FR-HOOK-4`) | A: inject `BROT_SESSION` as env. B: prefix the command, as HC-12 says. C: inject nothing and require OpenCode 2.3.0 or later, which sets `OPENCODE_SESSION_ID` itself | **Decided 2026-11-22 (owner): C.** v1 requires OpenCode 2.3.0 or later. The prefix can be added later without changing any other hook |

## 10. Notes for T3 (`brot`)

- Codex 0.171.0 has no `PostToolUseFailure`. T3's hook contract lists it for Codex.
- An OpenCode module can set shell env through `shell.hook("create.before")` (D-3).
- Muse plugin hooks receive a fixed environment in `muse plugins hook test` (§3.2), without `MUSE_SESSION_ID`. T3's contract reads `MUSE_SESSION_ID` in the hook to link a Muse subagent to its parent. If live plugin hooks drop it too, Muse subagent links fail. T3's capture used settings-style hooks, which did receive it.
- Under Muse, `BROT_DB` and `XDG_*` never reach `brot hook` (§3.2), so a throwaway database cannot be used in a live Muse test.
- Claude Code's `WorktreeCreate` hook fires for harness-native worktrees. It is a possible source for registering those worktrees (T3's call).

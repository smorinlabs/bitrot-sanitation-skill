# Release notes

## v0.1.0 — first release (2026-11-22)

**Hooks: all new.** This is the first release, so every hook is new. After you install it:
- **Codex:** trust each brot hook in `/hooks`.
- **Muse:** run `muse plugins approve brot`.
- **Claude Code:** enable the plugin.
- **OpenCode:** nothing to approve.

From now on, a release that changes any hook definition says so here, because Codex and Muse then need a new approval.

### Added
- The `brot` skill. It registers what the hooks miss, records blockers, cleans up only through `brot object clean` with a dry run and the user's consent, writes an end-of-session report, adopts orphaned objects, and hands the user the session-link command.
- Claude Code hooks in `hooks/hooks.json`, 8 events.
- Codex hooks in `hooks/codex-hooks.json`, 7 events. Codex has no `PostToolUseFailure`. The Codex manifest points at this file through harness-kit `codex_hooks`.
- Muse native manifest with hooks for 8 events. `pre-tool` runs on every tool call, measured at 8.9 ms p95.
- OpenCode V2 server module `opencode/brot.js`. Requires OpenCode 2.3.0 or later.
- Supported `brot` range: `>=0.8.2, <0.9.0` (`plugins/brot/compat.toml`).

### Known limits
- Codex and OpenCode have not yet been exercised in a live, logged-in session.
- Muse plugin hooks receive a fixed environment in `muse plugins hook test`. Whether a live session passes `MUSE_SESSION_ID`, which `brot` needs to link Muse subagents, is unverified.
- Deferred until `brot` supports them: a stored cleanup policy, and selectable soft-delete modes for worktrees and branches.

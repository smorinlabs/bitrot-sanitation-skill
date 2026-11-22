---
name: brot
description: "Track what this session creates (worktrees, branches, PRs, files, cloud resources) in the brot registry and clean it up safely through brot's checks. Use when registering an object, recording what blocks its cleanup, checking status, cleaning up, writing the end-of-session report of outstanding objects, adopting orphaned objects, or linking sessions. Not for general session loose ends such as unpushed commits or zombie jobs (session-loose-ends)."
---

# brot

`brot` is a per-machine registry of the objects coding agents create, with a
cleanup command that checks before it deletes. Hooks register most objects
automatically. This skill covers what the hooks cannot do: blockers, cleanup,
the end report, and recovery when hooks are not running.

> **NEVER DELETE A TRACKED OBJECT EXCEPT THROUGH `brot object clean`.** No raw
> `rm`, `git worktree remove`, `git branch -D`, `gh pr close` or cloud delete
> for anything `brot` tracks. An object `brot` does not track yet is registered
> first, then cleaned through `brot`.
>
> No exceptions: not "it's only a temp dir", not "brot is slow", not "the user
> said clean up". A raw delete skips the checks that protect unpushed work.

## First use in a session

1. Run `brot --version`. Missing → tell the user `brot` is not installed, give
   the install command from `references/degraded-modes.md`, and stop
   registering. Do not keep a registry in notes or files.
2. Compare the version with the range in `../../compat.toml`. Out of range →
   report the installed version and the range, then continue.
3. Check that hooks are running (`references/degraded-modes.md`, "Are hooks
   running?"). Report a problem once per session per cause.

## Workflow

| The user or the work needs to… | Do | Details |
|---|---|---|
| Track something the hooks missed | `brot object register --type <type> <locator>` | `references/registration.md` |
| Say what must happen before it can go | `brot blocker add <obj> --condition … --ref …` or `--text …` | `references/blockers.md` |
| See what is outstanding | `brot object list`, `brot object view <obj>` | `references/registration.md` |
| Clean up | `brot object clean <obj> --dry-run` first, then the real run | `references/cleanup.md` |
| Take over a dead session's objects | `brot object adopt <obj>` or `brot session adopt <session>` | `references/cleanup.md` |
| Link to an earlier session | Give the user the `brot session link` command; it is human-only | `references/registration.md` |
| Wrap up ("tie this off", "done for today") | Write the end report | below |

## Cleanup rules

- Always run `--dry-run` first and read the whole plan, including every soft
  risk and hard stop.
- **Ask the user before each destructive step.** v1 of `brot` stores no cleanup
  policy, so there is no setting that allows unattended deletes.
- **Soft risk:** weigh it, ask, and state every accepted soft risk in your report.
- **Hard stop:** report the reason verbatim and stop. Show the user the exact
  force command for a refusal a force can clear. A deny-list refusal is final:
  show no force command for it.
- **Never use `--force-agent` on your own.** Use it only when the user asks for
  it, and pass the user's request as `--reason`.
- **Never run `brot quarantine purge`** unless the user asks.

## End report

List every object this session created that is still outstanding. For each one:

- its ID, type and locator;
- its status;
- its open blockers;
- the exact `brot object clean <id>` command that would clean it once unblocked.

Then list orphaned objects in the current directory and offer to adopt them.
Never clean an orphaned object that this session has not adopted. Mention how
many quarantined items are waiting to be purged (`brot quarantine list`).

## Red Flags

| Thought | Reality |
|---|---|
| "It's a scratch file, `rm` is fine" | If `brot` tracks it, `rm` leaves a stale record and skips the checks. Clean it through `brot`. |
| "The hook will have registered it" | Hooks fail silently. Check (`references/degraded-modes.md`) and register by hand when they missed it. |
| "The dry run looks fine, skip asking" | v1 stores no cleanup policy. Every destructive step needs the user's yes. |
| "A hard stop, but I know it's safe — `--force-agent`" | Only on the user's explicit request, with their words as `--reason`. |
| "This orphaned worktree is obviously dead, clean it" | Adopt it first, with the user's agreement. Never clean what this session has not adopted. |
| "`brot` is missing, I'll track things in a notes file" | No. Tell the user how to install it and stop registering. |

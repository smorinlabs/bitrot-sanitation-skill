# Degraded modes

## `brot` is not installed

`command -v brot` finds nothing. The hooks then do nothing, by design.

Tell the user, give the install command, and stop registering. Do not keep a
substitute registry in notes or files.

```sh
# from a checkout of the brot repository
cargo install --path <brot-checkout> --locked
```

## `brot` is outside the supported range

Read the range from `../../../compat.toml` and the installed version from
`brot --version`. Report both and continue. The commands this skill uses may
behave differently outside the range.

## Are hooks running?

Hooks fail silently: the plugin is disabled, a Codex hook is not trusted, a
Muse hook is not approved, or a harness update renamed an event. Check once per
session, and again after a command the hooks should have registered.

1. **Start check.** `brot session view <harness>:<session-id>`. A session that
   `brot` first saw through an explicit command, not a session-start hook, is
   a sign the start hook is not running.
2. **Tool check.** After `git worktree add <path>`, `brot object list --json`
   should list `<path>` registered by a hook. Missing means the tool hook is
   not running.
3. **Diagnose.** `brot doctor`. Its `hooks` section shows, per harness, whether
   a brot hook is declared, its consent state (trusted or approved), the last
   event seen, and errors in the last 24 hours. Its `attribution` section shows
   whether this agent's own `brot` commands resolve to a session.
4. **Report the cause** once per session, in this order: `brot` missing,
   version out of range, plugin not installed or disabled, Codex hook not
   trusted, Muse hook not approved. Give the fix from the harness's install
   page.
5. **Keep working.** Register the missed object by hand
   (`references/registration.md`), so the record is still complete.

## A `brot` command fails while registering

Registration fails open. Continue the user's work, and report the failure with
the command and its error.

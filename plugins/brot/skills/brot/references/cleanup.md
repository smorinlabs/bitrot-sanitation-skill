# Cleanup

## The sequence

1. **Plan.** `brot object clean <obj> --dry-run`. It prints every step, the
   files that would be deleted, the backup ref, an `undo:` command, and every
   refusal with its key (for example `BROT504:dirty-tree`). It changes nothing.
   A refusal line ends with a hint naming `--force-agent`: that hint is not
   permission to use it.
2. **Ask.** Show the user the plan and every risk. v1 stores no cleanup
   policy, so every destructive step needs the user's yes.
3. **Clean.** `brot object clean <obj>` with the mode the user chose, adding
   `--yes` only after the user agreed.
4. **Report.** Name each object cleaned, the mode, every soft risk accepted,
   and the restore command for anything quarantined.

## Modes (file and directory objects)

| Mode | Effect | Undo |
|---|---|---|
| `quarantine` (default) | Moved into brot's quarantine area | `brot object restore <obj>` |
| `trash` | Moved to the macOS Trash | Restore from the Trash |
| `hard` | Deleted outright, after a verified capture | None |

A project config can change the default mode per object type, limited to
`quarantine` or `trash`. Read the plan for the mode that will be used, rather
than assuming one.

Worktrees and local branches have no selectable mode. Before removing one,
`brot` pins its HEAD under a backup ref and reports it: tell the user the ref
name. A cloud object is never deleted by `brot`: the plan prints its delete
command, and the user runs it.

## Refusals

| Kind | What it means | What you do |
|---|---|---|
| Overridable refusal | A type check or sanity check failed: for example uncommitted files, unpushed commits, an unmerged branch, an escaping symlink, or a stale blocker answer | Show it to the user with the exact command that clears it: `brot object clean <obj> --force --override <key>` for the user to run at a terminal |
| Hard stop | A locked worktree, hidden changes, an operation in progress, a checked-out branch, an unborn HEAD, a partial clone | Report the reason verbatim and the step that clears it (for example "finish or abort the rebase"). Stop |
| Deny list (`BROT505`) | A protected path: a mount point, a brot-owned path, a worktree below the root | Final. Report it. Show no force command |
| Not cleanable (`BROT503`) | Open blockers, needs validation, pinned `keep`, already cleaned | Resolve the cause first (validate, resolve the blocker, or ask the user) |

**`--force-agent`** clears overridable refusals without a terminal. Use it only
when the user explicitly asks you to, and pass their request as `--reason`:

```sh
brot object clean <obj> --force-agent --override BROT504:dirty-tree \
  --reason "user: 'yes, delete the worktree, the changes are scratch'"
```

## Orphaned objects

Objects whose session died show as orphaned. Never clean one before adopting it.
Ask the user first, then adopt one object or a whole session's objects:

```sh
brot object adopt <obj>
brot session adopt <ses>
```

## Cleaned outside brot

If something was already removed by other means, record it with
`brot object mark-cleaned <obj> --note "…"`. `brot` checks that it is really
gone and refuses when it still exists.

## Purging

Quarantined items are kept until a human purges them. Never run
`brot quarantine purge` unless the user asks. `brot quarantine list` shows what
is held.

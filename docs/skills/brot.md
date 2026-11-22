# `brot` skill

**Plugin:** `brot` · **Source:** `plugins/brot/skills/brot/` · **Needs:** the `brot` CLI in the range in `plugins/brot/compat.toml`

## What it does

Teaches a coding agent to keep the `brot` registry complete and to clean up
only through `brot`:

- register objects the hooks missed;
- record blockers;
- check status;
- clean up through `brot object clean`, with a dry run, the user's consent and
  a report;
- write an end-of-session report of outstanding objects;
- adopt orphaned objects;
- hand the user the command that links two sessions.

## When it fires

Registering an object, recording what blocks its cleanup, checking status,
cleaning up, wrapping up a session, adopting orphaned objects, or linking
sessions. General loose ends, such as unpushed commits or zombie jobs, belong to
`session-loose-ends`.

## Rules it enforces

- Never delete a tracked object except through `brot object clean`.
- Ask before every destructive step. `brot` 0.8 stores no cleanup policy.
- Never use `--force-agent` unless the user asks, and pass their words as
  `--reason`.
- Never purge quarantined items unless the user asks.

## Files

| File | Holds |
|---|---|
| `SKILL.md` | The iron law, first-use checks, the workflow, cleanup rules, the end report, Red Flags |
| `references/registration.md` | Automatic and manual registration, status, linking sessions |
| `references/blockers.md` | Checked and agent blockers |
| `references/cleanup.md` | Plan, modes, refusals, force, orphans, purge |
| `references/degraded-modes.md` | `brot` missing or out of range, checking that hooks run |

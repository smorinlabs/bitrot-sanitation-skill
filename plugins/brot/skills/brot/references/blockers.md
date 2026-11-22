# Blockers

A blocker records what must happen before an object can be cleaned. An object
with an open blocker has status `blocked`, and `brot object clean` refuses it.

## Checked blockers (brot evaluates them)

```sh
brot blocker add <obj> --condition pr-merged-or-closed --ref <pr-url>
brot blocker add <obj> --condition path-absent --ref <path>
brot blocker add <obj> --condition branch-merged --ref <branch> [--base <branch>]
brot blocker add <obj> --condition object-cleaned --ref <obj>
brot blocker add <obj> --condition cloud-gone
```

`brot blocker evaluate` re-checks them. Pull-request conditions make network
calls. When a session starts, the hook can re-evaluate them in the background.

## Agent blockers (free text, never evaluated)

```sh
brot blocker add <obj> --text "keep until the user has reviewed the benchmark output"
```

Use one when the condition is a judgement no command can check. Resolve it
when the condition holds:

```sh
brot blocker resolve <blk> --note "user reviewed the output on <date>"
```

## Listing

`brot blocker list` lists unresolved blockers in scope, agent blockers first.
At session start the hook shows blockers that cleared since the session last
looked, and the session's open agent blockers.

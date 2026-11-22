# Registration and status

## What the hooks register on their own

When the plugin's hooks run, `brot` registers, from each shell command or file
write:

- worktrees (`git worktree add`);
- branches (`git checkout -b`, `git switch -c`, `git branch <name>`);
- pull requests (`gh pr create`);
- new files the agent writes.

Each one is marked "needs validation" until someone confirms it
(`brot object validate <obj>`). A hook cannot tell whether a command
succeeded on every harness, so a failed command may still register an object.

## Registering by hand

Register anything the hooks missed, and anything that is not a shell command or
file write: a cloud resource, a directory made by a tool, a custom object.

```sh
brot object register --type worktree ../repo-topic
brot object register --type branch feat/topic --repo .
brot object register --type pr https://github.com/<owner>/<repo>/pull/<n>
brot object register --type file ./scratch/out.json --note "probe output"
brot object register --type cloud --provider gcp --account <project> \
  --region us-central1 --resource-type run.service --resource-id <name> \
  --delete-command '["gcloud","run","services","delete","<name>","--region","us-central1","--project","<project>"]'
```

Registration is idempotent: registering an object twice adds a second
registration to the same record. A cloud delete command is stored and shown in
full, so it must not contain a credential. `brot` prints it and never runs it.

Blockers can be set at registration time:
`--blocked-by-pr <url>`, `--blocked-by-path <path>`, `--blocked-by-object <obj>`.

## Status

- `brot object list` — outstanding objects of this session. `--all` covers the
  whole machine. `--status` and `--type` filter.
- `brot object view <obj>` — registrations, blockers, links, notes, history.
- `brot session list`, `brot session view <ses>` — sessions and their state.

Add `--json` when you need to read fields programmatically.

## Linking sessions

A link between two sessions is recorded by a human only, from a terminal. When
the user says "continue from yesterday's session" or a handoff names a prior
session, give the user the command to run, prefixed with `!` where the harness
supports it:

```sh
brot session link --help    # shows the exact arguments for this brot version
```

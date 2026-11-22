# bitrot-sanitation-skill

Plugin and skill that teach coding agents to track and safely clean up what
they create, using the `brot` CLI.

`brot` is a per-machine registry of the objects agents create: worktrees,
branches, pull requests, files, and cloud resources. Its cleanup command checks
before it deletes. This plugin connects `brot` to four coding agents:

- **Hooks** call `brot hook <harness> <event>` on session start and end, after
  shell commands and file writes, and on subagent and compaction events.
  `brot` registers what it recognises.
- **The `brot` skill** teaches the agent to register what the hooks miss, record
  blockers, clean up only through `brot`, and write an end-of-session report.

| Harness | What ships | Consent step |
|---|---|---|
| Claude Code | `plugins/brot/hooks/hooks.json` and the skill | Enable the plugin |
| Codex | `plugins/brot/hooks/codex-hooks.json` and the skill | Trust each hook in `/hooks` |
| Muse | `plugins/brot/.muse-plugin/plugin.json` (native hooks and the skill) | `muse plugins approve brot` |
| OpenCode | `plugins/brot/opencode/brot.js` | None: plugin files load as code |

The hooks contain no logic. When `brot` is not installed they do nothing.

## Prerequisite: install `brot`

Installing this plugin does not install `brot`. Install it first, then check:

```sh
brot --version     # the plugin supports the range in plugins/brot/compat.toml
```

## Claude Code

```sh
claude plugin marketplace add smorinlabs/bitrot-sanitation-skill
claude plugin install brot@bitrot-sanitation-skill
```

- **Verify:** start a new session, then run `brot doctor`. The `hooks` section
  shows `claude-code` as declared and firing.
- **Uninstall:** `claude plugin uninstall brot@bitrot-sanitation-skill`.

## Codex

> **Not yet tested in a live Codex session.** The Codex manifest points Codex
> at `hooks/codex-hooks.json` (harness-kit `codex_hooks`), and an install into a
> throwaway Codex home carried that entry. Please report what `brot doctor`
> shows after your first session.

```sh
codex plugin marketplace add smorinlabs/bitrot-sanitation-skill
codex plugin add brot@bitrot-sanitation-skill
```

- **Trust:** open `/hooks` in Codex and trust each brot hook. Codex skips an
  untrusted hook. Hooks are on by default; `features.hooks = false` or a
  managed `requirements.toml` turns them off.
- **Verify:** start a new session, then run `brot doctor`. The `hooks` section
  shows `codex` as declared, trusted and firing.
- **Uninstall:** `codex plugin remove brot@bitrot-sanitation-skill`.

## Muse

```sh
muse plugins marketplace add bitrot-sanitation-skill https://github.com/smorinlabs/bitrot-sanitation-skill.git
muse plugins install brot@bitrot-sanitation-skill
muse plugins approve brot
```

- **Approve:** Muse runs a plugin hook only after it is approved. Approval is
  per hook. A release that changes a hook needs a new approval, and its
  release notes say so.
- **Verify:** start a new session, then run `brot doctor`. The `hooks` section
  shows `muse` as declared, approved and firing.
- **Uninstall:** `muse plugins remove brot`.

## OpenCode

OpenCode loads plugin files from its config directory. Copy or symlink the
module there, and the skill into a skills directory OpenCode reads:

```sh
git clone https://github.com/smorinlabs/bitrot-sanitation-skill.git
mkdir -p ~/.config/opencode/plugins ~/.config/opencode/skills
ln -s "$PWD/bitrot-sanitation-skill/plugins/brot/opencode/brot.js" ~/.config/opencode/plugins/brot.js
ln -s "$PWD/bitrot-sanitation-skill/plugins/brot/skills/brot" ~/.config/opencode/skills/brot
```

- **Verify:** start a new session, then run `brot doctor`. The `hooks` section
  shows `opencode` as declared and firing.
- **Uninstall:** remove the two symlinks.

## Development

```sh
just gen        # regenerate the Claude Code and Codex manifests (harness-kit)
just test       # hook text, missing-brot guard, versions, OpenCode module
BROT_FIXTURES=<brot-checkout>/tests/fixtures/hooks just test   # also replay captured payloads
```

Hook text must not change between releases unless the release notes flag it:
Codex and Muse approve each hook by its definition. See `docs/design.md` §3.3.

- Requirements: `docs/requirements.md`
- Design: `docs/design.md`
- Skill page: `docs/skills/brot.md`

## License

MIT. See `LICENSE`.

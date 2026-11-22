# T4 — `bitrot-sanitation-skill`: requirements

**Status:** requirements phase, draft 3. Written 2026-11-12. All owner decisions OQ-01 to OQ-12 recorded 2026-11-12; OQ-13 is research for the design phase. Reconciled with T3's final requirements (2026-11-12 15:27) in §7.4; the four conflicts with T3 (C-1 to C-4) and OQ-15 (f) were decided 2026-11-16.
**Location:** `docs/requirements.md` in `smorinlabs/bitrot-sanitation-skill`. Local paths, private tool names, and machine-specific details were removed before publishing (CV-09).
**Brief:** task brief T4, kept outside this repo.

## 0. How to read this document

### 0.1 Purpose
This repo holds the **agent-facing side** of `brot`. It contains a plugin and a skill that teach coding agents to use `brot` and that wire `brot` into each harness's hooks. `brot` itself is the per-machine Rust + SQLite CLI specified by T3 (`smorinlabs/bitrot-sanitation`).

### 0.2 Boundary with T3
- **T3 owns** everything about the CLI: object and session schema, command names and flags, safe-delete checks, storage, and the hooks gap table.
- **T4 owns** packaging, hook declarations per harness, skill behaviour, session-lifecycle choreography, conventions, and distribution.
- T3's output did not exist when this draft was written (checked 2026-11-12). Every place that depends on T3 cites a placeholder ID of the form **`T3:<area>`**. Section 4 lists what T4 needs from `brot` as dependencies for T3 to own, not as CLI requirements.
- Command spellings such as `brot session start` are **illustrative only** until T3 fixes the CLI surface.

### 0.3 Requirement IDs
| Prefix | Area |
|---|---|
| `HC-nn` | Harness coverage: packaging, install, hooks |
| `SK-nn` | Skill behaviour: registration, blockers, status, cleanup |
| `SL-nn` | Session lifecycle |
| `CV-nn` | Fleet conventions |
| `DS-nn` | Distribution and versioning |
| `DG-nn` | Degraded modes |
| `NF-nn` | Non-functional requirements |
| `DEP-nn` | Dependencies on `brot` (T3 to own). Named `DEP` to avoid clashing with T3's decision IDs `D-n`. |
| `OQ-nn` | Open questions (decision requests) |

Keywords: **MUST** = required for v1. **SHOULD** = required unless a design decision records why not. **MAY** = optional.

### 0.4 Evidence labels for harness facts
Each harness fact carries one label:
- **[O]** observed on the author's machine on 2026-11-12 at the stated version.
- **[F]** taken from a fleet document. The document named is `skill-create/references/in-repo-marketplace.md`, verified on Claude Code 2.1.x and Codex 0.145.0 in 2026-07.
- **[U]** unverified. It must be confirmed during design, and it is tracked as an open question or a design task.

Local versions observed: Claude Code `2.1.322`, Codex `codex-cli 0.167.2`, Muse `Muse Code 1.4.15`, OpenCode `v2.2.7`.

## 1. Terms

| Term | Meaning here |
|---|---|
| **object** | Something an agent created that may need cleanup: file, directory, worktree, branch, PR, cloud resource, or a custom type. Defined by `T3:registry`. |
| **blocker** | A condition that must be true before an object may be cleaned up, such as "PR `https://github.com/o/r/pull/12` is merged". Defined by `T3:registry`. |
| **exact reference** | A machine-checkable identifier: full PR URL, absolute path, `<repo-path>@<branch>`, cloud resource ID (for example an ARN or a GCP resource name), or a harness session ID. Prose such as "after the PR lands" is not an exact reference. |
| **harness** | One of the four agent runtimes in scope: Claude Code, Codex, OpenCode, Muse. |
| **hook declaration** | The harness-specific file or module in this plugin that runs a `brot` command when a harness event fires. |
| **thin shim** | A hook declaration that contains no logic beyond calling `brot` with the event payload. |
| **safe-delete** | `brot`'s cleanup commands, which run a sanity pass before deleting anything (`T3:safe-delete`). |
| **home 4b** | Fleet placement term (`_routing.md`): a repo that is its own marketplace with hand-written Claude and Codex catalogs (`.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`), normally shipping inside the product repo. |
| **home 5** | Fleet placement term: a standalone harness repo using the harness-kit layout. `harness.toml` and `plugins/<name>/plugin.meta.toml` are the sources; `harness-kit gen` generates the catalogs and manifests. The naming convention is `<purpose>-harness`. |

## 2. Harness facts gathered (evidence)

These facts shape the requirements in section 3. They are **not** the hooks gap table; T3 owns that table.

| # | Harness | Fact | Label |
|---|---|---|---|
| E1 | Claude Code | Installs plugins from a marketplace catalog: `/plugin marketplace add`, then `/plugin install <name>@<market>`. | [F] |
| E2 | Claude Code | Plugins ship hook declarations as `hooks/hooks.json` inside the plugin. Several installed third-party plugins do this. A `SessionStart` hook can add text to the model's context; the authoring session showed it. | [O] 2.1.322 |
| E3 | Codex | Has `codex plugin add / list / marketplace / remove`. | [O] 0.167.2 |
| E4 | Codex | Plugins can carry hooks. An installed third-party plugin ships `hooks/hooks.json` with `session_start`, `user_prompt_submit`, `post_tool_use`, and `permission_request` hooks. | [O] 0.167.2 |
| E5 | Codex | Every hook needs trust. `~/.codex/config.toml` stores a `trusted_hash` per hook under `[hooks.state."<plugin>:hooks/hooks.json:<event>:<i>:<j>"]`. `codex --dangerously-bypass-hook-trust` skips the check. Consequence: **any change to a hook definition requires the user to re-trust it.** | [O] 0.167.2 |
| E6 | Codex | Hooks are behind `features.hooks = true` in `config.toml` (set on the author's machine). Whether that flag is still required by default is unknown. | [O] set / [U] default |
| E7 | Muse | Has `muse plugins install / marketplace add / approve / reject / hook test --fixture / validate`. | [O] 1.4.15 |
| E8 | Muse | Installed a third-party plugin from a git marketplace source. The cached source sits under a directory named `.muse-codex-sources/`, with `manifest_family: "agent-plugins"`. That name suggests Muse reads Codex-format plugins, but the format itself was not checked. | [O] source / [U] format |
| E9 | Muse | Plugins carry hooks: `muse plugins hook test <plugin-id>:<hook-id> --fixture <path>` exists, and `approve` / `reject` act on `<plugin-id>:<kind>:<capability-id>`. T3's Muse research (gap-table capability C13) reports hooks are declared in `.muse-plugin/plugin.json` under `capabilities.hooks[]` and need `muse plugins approve`. | [O] hooks exist / [T3] format |
| E10 | Muse | Hook JSON uses the Claude-style shape with events `SessionStart`, `SubagentStart`, `SessionEnd` (seen in a third-party managed hooks file). | [O] 1.4.15 |
| E11 | Muse | Runtime capabilities are trusted by definition hash (`trusted_definition_hash` in `settings.json`) and approved per capability (E9). The install warning reads: "MCP servers require review before activation; skills are active without review." Whether hooks need approval before they run is unknown. | [O] hash / [U] hook approval |
| E12 | Muse | `muse skills import --from claude\|codex` exists. | [O] 1.4.15 |
| E13 | OpenCode | Has `opencode plugin list / add / check / update / remove`. `opencode plugin add <package>` takes an "npm registry or Git package specifier". | [O] 2.2.7 |
| E14 | OpenCode | Local plugins are **JavaScript/TypeScript modules** in `~/.config/opencode/plugins/` that subscribe to events such as `permission.asked` and session status. OpenCode hooks are therefore code, not JSON. | [O] 2.2.7 |
| E15 | OpenCode | Whether OpenCode discovers skills from `~/.agents/skills` or `.claude/skills`, in addition to `~/.config/opencode/skills`, is unknown. | [U] |
| E16 | All | Session stores and fork lineage fields for all four harnesses are already documented by `session-inventory-cli` (`smorinlabs-skills/plugins/session/docs/session-inventory-cli.md`): Codex `forked_from_id`, Muse `msp_fork_source_session_id`, OpenCode `parent_id` / `fork_session_id`. | [O] doc |

## 3. Requirements

### 3.1 Harness coverage (HC)

- **HC-01** — The plugin MUST support Claude Code, Codex, OpenCode, and Muse.
- **HC-02** — For each harness, the repo MUST document one install path, one uninstall path, and one verification command that proves the skill and hooks loaded.
- **HC-03** — Claude Code and Codex MUST install the plugin from a marketplace catalog (E1, E3). The layout is home 5 (OQ-02, CV-06).
- **HC-04** — Muse SHOULD install from the same git marketplace source (E8). If Muse cannot read the hook declarations in that plugin (E9 format unknown), the repo MUST ship a Muse-specific hook declaration and document how to install it.
- **HC-05** — OpenCode MUST receive its hooks as a JS/TS plugin module (E14). The module ships as a file in this repo, installed by a documented copy or symlink into `~/.config/opencode/plugins/` (OQ-06). An npm package is deferred.
- **HC-06** — **Small hooks, logic in `brot`.** Every hook declaration MUST be a thin shim: it calls `brot hook <harness> <event>` with the event payload on stdin and does nothing else. The only logic a shim may contain is the missing-binary guard in DG-01. **Exception:** OpenCode hooks are a code module, not a declaration (E14). That module MAY also perform the harness-specific mappings HC-12 lists, and nothing beyond them. Everything else runs inside `brot` (`DEP-03`): the version-compatibility check (DS-03), the once-per-session warning (DG-02), command detection (SK-01, `DEP-04`), and the hook-event record used by DG-06 (`DEP-13`).
- **HC-06a** — **Stable hook definitions.** The text of each hook declaration MUST stay byte-identical across plugin and `brot` releases. It changes only when an event is added or removed. Therefore a declaration MUST NOT contain a version number, a versioned path, or any other value that changes per release. Where the hook needs the plugin's location, it uses the harness's plugin-root variable (for example `${CLAUDE_PLUGIN_ROOT}` on Claude Code; the equivalents on Codex and Muse are research item OQ-13).
  - **Why:** Codex and Muse approve hooks by a hash of their definition (E5, E11). A changed definition is skipped until the user re-approves it. Stable definitions mean upgrading `brot` or the plugin never silently turns hooks off.
  - **Check:** CI MUST compare every hook declaration file against the previous release tag and fail if it changed, unless the release notes flag a hook change (DS-05).
- **HC-07** — The set of hook events wired per harness MUST come from T3's hooks gap table (`T3:hooks`). For each harness the repo MUST record which `brot` needs it covers: session start, session end, tool use that creates an object, tool use that deletes something, and subagent or fork start. The gap table MUST also record two capabilities per harness, because SL-04 and OQ-03 depend on them:
  - whether a hook's output reaches the model's context (needed for the session-start summary);
  - whether a pre-tool-use hook can add a warning, deny the call, or neither (required: the v1 pre-tool hook in HC-07a must be able to enforce later without a definition change).
- **HC-07a** — **Pre-tool hook ships in v1 with the guard off** (X2 decided B, 2026-11-12). Each harness MUST get a pre-tool-use hook limited to shell commands (matcher `Bash` or the harness equivalent) that calls `brot hook <harness> pre-tool`. In v1 `brot` passes every command through unchanged: no warning, no block. A later `brot` release can turn on the guard (T3 `FR-HOOK-16`) without changing the hook text (HC-06a), so no user re-approves anything. The hook MUST stay within T3's tool-path budget (`FR-HOOK-7`, 100 ms p95). *C-1 decided B and resolved (§7.4.3): T3's design accepts `brot hook <harness> pre-tool` as an ignored event.*
- **HC-08** — Where T3's gap table marks an event as **missing** for a harness, the plugin MUST name the fallback, in this order of preference:
  1. **Build the hook.** T3's brief says missing hooks "will be created from scratch". For OpenCode a built hook is code in the plugin module (E14). A built hook ships in this plugin, not in `brot` (OQ-11).
  2. A skill-driven manual step (SK, SL).
  3. A `brot` liveness check (`DEP-06`).
  4. "Unsupported", stated in the docs.
- **HC-09** — The plugin ships the hook declarations for every harness, and the harness loads them on plugin install (OQ-01, decided 2026-11-12). `brot` MUST NOT be required to write harness hook config.
- **HC-10** — Install docs MUST tell the user about the trust step for each harness: Codex hook trust (E5), Muse `muse plugins approve` (E7, E11), and the Claude Code plugin enable step.
- **HC-11** — The plugin MUST NOT require `--dangerously-bypass-hook-trust` or any equivalent bypass flag.
- **HC-12** — The OpenCode module MUST perform the harness-specific work T3 assigns to it: inject `BROT_SESSION` into each shell (T3 `FR-HOOK-4`; *owner decision 2026-11-22, design D-3: not injected; v1 requires OpenCode 2.3.0 or later, which sets `OPENCODE_SESSION_ID` itself*), synthesize session start from `session.created` (`FR-HOOK-11`), map `session.execution.interrupted` and `session.deleted` to session end and not treat `session.idle` as an end (`FR-HOOK-12`), and derive subagent stop from child-session events (`FR-HOOK-13`). Each mapping MUST then call `brot hook opencode <event>`.
- **HC-13** — The Muse hook declaration MUST use `.muse-plugin/plugin.json` `capabilities.hooks[]` (T3 gap table C13), validated with `muse plugins validate` and tested with `muse plugins hook test --fixture` (T3 `FR-HOOK-10`).

### 3.2 Skill behaviour (SK)

**Registration**

- **SK-01** — Hooks SHOULD register objects automatically whenever the creating action can be detected deterministically from the tool event. Examples: a shell command `git worktree add <path>`, `git checkout -b <branch>`, `gh pr create`. Which commands are detectable is decided with T3 (`DEP-04`).
- **SK-02** — The skill MUST instruct the agent to register, immediately after creating it, any object the hooks cannot detect: files written outside the repo, scratch directories, cloud resources, background services, and custom types.
- **SK-03** — Registration MUST be idempotent. Registering the same exact reference twice (once by a hook, once by the agent) MUST NOT create a duplicate (`DEP-05`).
- **SK-04** — Each registration MUST record the owning session (SL-01), the object type, the exact reference, and a one-line purpose note written for a future reader.
- **SK-05** — The skill MUST tell the agent what not to register: objects the user created by hand, and objects inside the repo's tracked tree that are ordinary committed work.
- **SK-05a** — **Trust level.** The agent MUST pass `--on-behalf-of user` (T3 D-10, trust level `agent-requested`) only when the user explicitly asked for that action in this session. Otherwise it registers at the default `agent` level.
- **SK-05b** — **Validate hook-added objects.** An object registered by a hook has the lowest trust (T3 D-9) and is something to watch, not something to clean. Before proposing its cleanup, the agent MUST confirm it is real and unwanted, and record that validation through `brot`.

**Blockers and dependencies**

- **SK-06** — When an object must outlive a condition, the agent MUST record a blocker that uses an exact reference. Example: the worktree `/path/repo-topic` is blocked on `https://github.com/o/r/pull/12` reaching *merged*.
- **SK-07** — The agent MUST prefer **checked** blockers: an exact reference that `brot` evaluates itself (T3 `FR-OBJ-7`). It MAY record an **agent-checked** blocker, which `brot` only stores and lists, when no machine check exists (T3 D-6). An agent-checked blocker MUST still name every exact reference it can (path, URL, ID), and the agent MUST mark it resolved only after checking it. When the reference appears later (for example, the PR is opened), the agent SHOULD replace the agent-checked blocker with a checked one (`DEP-07`).
- **SK-08** — The skill MUST teach the agent to record dependencies between objects, for example "branch depends on worktree", so that cleanup order is computed by `brot` and not guessed by the agent (`T3:registry`).

**Status before cleanup**

- **SK-09** — Before proposing any cleanup, the agent MUST ask `brot` for the object's status and blockers, and MUST NOT re-derive blocker state itself (`DEP-02`).
- **SK-10** — Before any destructive step, the agent MUST read `brot`'s plan for it, including the risk information for every step (DEP-15). What happens next depends on the cleanup policy in force (SK-17). The agent MUST NOT skip a confirmation the policy requires.
- **SK-11** — `brot` classifies each failed check as either a **soft risk** or a **hard stop** (DEP-15).
  - **Soft risk:** the agent weighs it and proceeds or not, as the policy allows (SK-17). The agent MUST state each soft risk it accepted in its report.
  - **Hard stop:** the agent MUST report the reason verbatim and stop. A hard stop can be passed only with `brot`'s explicit force override. `brot` offers two overrides (T3 `FR-DEL-9`): `--force`, which needs a human at an interactive terminal, and `--force-agent --reason <text>`, which an agent can use. The skill does not let an agent use `--force-agent` on its own (OQ-15 (f), decided 2026-11-16). The agent MUST NOT use it unless the user explicitly asks, and MUST pass the user's request as the `--reason`.

**Cleanup**

- **SK-12** — Cleanup of a **registered** object MUST go through `brot`. For local and git objects, `brot` performs the delete (T3 D-2); the agent MUST NOT use raw `rm`, `rm -rf`, `git worktree remove`, `git branch -D`, `git push --delete`, or `gh pr close` on them. For cloud resources, `brot` only prints the exact delete command and never runs it (T3 D-13). The agent MUST use that printed command unchanged, never compose its own, and afterwards confirm with `brot mark-cleaned` or the registered check command. Whether the agent may run the printed cloud command itself is OQ-15 (g).
- **SK-13** — To clean up an **unregistered** object, the agent MUST first register it, then delete it through `brot`'s safe-delete (OQ-04).
- **SK-14** — SK-12 is advisory in v1: it is enforced by the skill's iron law and Red Flags table (OQ-03, decided 2026-11-12). The pre-tool hook ships in v1 but `brot` lets every command through (HC-07a, X2 decided B); no command is warned about or blocked in v1.
- **SK-15** — The skill MUST resolve the conflict with existing fleet instructions. The global `CLAUDE.md` and `skill-create` both prescribe `git worktree remove` and `git branch -d` when closing the loop after a merge. Resolution (OQ-05): add a carve-out to all three copies (global `CLAUDE.md`, the `git-main-branch-discipline` memory, `skill-create`) saying "when `brot` is installed, delete the worktree or branch through `brot`'s safe-delete, registering it first if it is not registered (SK-13); when `brot` is not installed, use the git commands". Land it only after `brot` ships safe-delete for worktrees and branches.
- **SK-16** — After cleanup, the agent MUST confirm the object's final state with `brot` and not by inspecting the filesystem directly.

**Cleanup policy (OQ-14, decided 2026-11-12)**

- **SK-17** — **Configurable cleanup policy.** A human chooses how much autonomy agents have for cleanup. The policy is stored in `brot` (DEP-14), and the skill MUST read and follow it, never assume it. The policy MUST cover at least this spectrum: *C-2 decided B (§7.4.3): kept, but `brot` stores no policy until T3 reopens D-3 in a later phase.*

  | Mode | Behaviour |
  |---|---|
  | `confirm-each` | The agent shows the plan; the human approves or rejects each step. |
  | `confirm-batch` | The agent shows the plan; one human approval covers the whole batch. |
  | `auto-low-risk` | The agent proceeds alone on steps `brot` classifies as low risk; the other steps need confirmation (each or batch). |
  | `auto` | The agent decides for every step, using the full risk information, and reports what it did and which soft risks it accepted. |
  | `direct` | The agent still reads the plan and its risk information (SK-10), then deletes without waiting for any confirmation. It still states every soft risk it accepted (SK-11, SK-20). Hard stops still apply and need a force override (SK-11). |

  Mode names are illustrative; the design phase fixes them.
- **SK-18** — **Default policy.** The owner's default is `auto`: agents make the full decision with all risk information. The shipped default for other users is open, design question OQ-15 (a). *C-2 decided B (§7.4.3): kept, but `brot` stores no policy until T3 reopens D-3 in a later phase.*
- **SK-19** — **Review risks, then force-delete one object.** A human MUST be able to see the warnings and risks `brot` reports for deleting one object (the soft risks and hard stops from DEP-15), and then run a single command that force-deletes that object anyway, choosing the deletion mode: hard, or one of the soft-delete modes in SK-21. The skill MUST show the exact force command alongside the risks, so the human can copy and run it. This applies only to refusals a force flag can override: type-check and sanity-pass refusals (T3 `FR-DEL-9`). A deny-list refusal (T3 `FR-DEL-3`) is absolute; the skill MUST report it as final and MUST NOT show a force command for it. Forcing is an explicit human choice; SK-11 still governs whether an agent may apply force on its own (OQ-15 (f)). (Owner's clarification, 2026-11-12: "I can see warnings and risks of deleting an object, then go ahead with a command that will force delete it.")
- **SK-20** — **Report every autonomous cleanup.** In `auto`, `auto-low-risk`, and `direct` modes, the agent MUST report each cleanup it performed, with the exact objects and any soft risks it accepted. Reports go into the session and into `brot`'s history (T3 `FR-OBJ-11`).
- **SK-21** — **Soft-delete modes** (owner request, 2026-11-12). A delete, forced or not, MUST let the human choose a deletion mode, including several kinds of soft (reversible) delete. The skill MUST show the modes available for the object next to its risks, each with its exact command. Proposed modes by object type (the design phase fixes the set): *C-4 decided B (§7.4.3): kept. T3's design already pins every removed local branch and worktree HEAD under `refs/brot/backup/`; the selectable modes wait until T3 reopens D-4 in a later phase.*

  | Object | Soft modes | Hard mode |
  |---|---|---|
  | file, directory | `trash` (move to the OS Trash); `quarantine` (move to a `brot` holding area until purged); `archive` (compress into a `brot` archive, then remove) | remove permanently |
  | worktree | `archive` (save a patch of tracked changes plus a tarball of untracked files, then remove the worktree) | remove the worktree |
  | branch | `backup-ref` (keep the tip as `refs/brot/backup/<branch>`, then delete the branch) | delete the branch |
  | PR | `close` (close the PR, keep its head branch) | close the PR and delete its head branch |
  | cloud resource | none in v1: `brot` tracks cloud resources and prints their delete command but never runs it (T3 D-13) | the printed delete command (SK-12) |

- **SK-22** — **Restore.** Every soft delete MUST print the command that restores the object, and the skill MUST include it in its report (SK-20).
- **SK-23** — **Default mode is configurable.** When no mode is given, a forced delete uses the object type's soft mode, so it stays reversible unless `--mode hard` is given (OQ-15 (i), decided 2026-11-12). An object type with no soft mode (cloud resources in v1, SK-21) has no reversible default: the skill MUST state that the delete cannot be undone and MUST NOT describe it as reversible. The default mode MUST be configurable per object type in a user-level config and a project-level config, with the project level winning (DEP-16). The skill MUST read the effective default from `brot`, never assume it. *C-3 decided B and resolved (§7.4.3): T3's project config layer sets the default mode per object type, limited to `quarantine` or `trash`.*
- **SK-24** — **Manual purge.** Quarantined and archived items MUST be kept until a human purges them; nothing expires automatically (OQ-15 (j), decided 2026-11-12). The skill MUST NOT purge unless the user asks, and the end report (SL-07) SHOULD mention how many soft-deleted items are waiting to be purged.

### 3.3 Session lifecycle (SL)

**Start**

- **SL-01** — At session start, the plugin MUST register the session with `brot`: harness, session ID, working directory, transcript path or export command, start time, and parent session if known (`T3:sessions`, `DEP-01`). A hook does this where the harness has a start event; otherwise the skill does it on first use (HC-08).
- **SL-02** — Session linking MUST use the harness's own lineage fields when present (E16): Codex `forked_from_id`, Muse `msp_fork_source_session_id`, OpenCode `parent_id` / `fork_session_id`, and Claude Code resume or fork IDs [U]. Subagent sessions MUST link to their parent.
- **SL-03** — The skill MUST let the agent link sessions manually when lineage is not machine-visible, for example when the user says "continue from yesterday's session" or a handoff document names a prior session ID.
- **SL-04** — At session start, the plugin SHOULD inject `brot`'s session-start context (T3 `FR-STAT-7`): blockers that cleared since the session last looked, and the session's still-open agent-checked blockers. Per T3 D-6 this covers **only objects owned by this session**. The size cap is `NF-03`. Known gap: after `/clear`, compaction, or a fork, the new session ID owns nothing, so the summary is empty until T3 resolves `Q-CHAIN` (§7.3, A6).
- **SL-05** — Objects of dead sessions show in `brot` as `orphaned` (T3 D-8) and are not in the session-start context (SL-04). The skill MUST surface them on demand and in the end report (SL-07): it lists orphaned objects in the current working directory and offers to **adopt** them (T3 `FR-SES-7`) before any cleanup. The agent MUST NOT clean an orphaned object it has not adopted.

**End**

- **SL-06** — At session end, the plugin MUST mark the session ended in `brot` where the harness has an end event (E10 for Muse; others per `T3:hooks`).
- **SL-07** — When the user wraps up ("tie this off", "done for today"), the skill MUST produce an end report. The report lists objects this session created and still outstanding, each with status, blockers, and the exact `brot` command that would clean it once unblocked.
- **SL-08** — Sessions that end without an end event (crash, killed terminal) MUST be detectable by `brot` liveness checks (`DEP-06`). The plugin MUST NOT depend on the end hook for correctness.
- **SL-09** — The end report's trigger is decided by OQ-08: the end report is skill-driven only, and the end hook only marks the session ended. Many harnesses do not show end-hook output to the model or the user.

### 3.4 Conventions (CV)

- **CV-01** — The skill MUST pass `skill-quality` layers 1, 2, and 4 against the worktree path. Further checks follow from OQ-02 (home 5 chosen; the home-4b line is kept for reference):
  - **home 5:** layer 3 (`plugin.meta.toml` well-formed, plugin listed in the catalog, `uv run harness-kit gen --check` green);
  - **home 4b:** both catalogs parse, the manifest is a symlinked superset, and the fleet's deep, strict skill verifier passes on both Claude Code and Codex.
- **CV-02** — **Progressive disclosure.** `SKILL.md` stays scannable and holds the workflow and the iron law. Long procedures go in `references/`, loaded on demand. Proposed split: `references/registration.md`, `references/blockers.md`, `references/cleanup.md`, `references/harness-<name>.md` (one per harness), `references/degraded-modes.md`.
- **CV-03** — **Action-scoped description**, following the fleet shape: `<what it does>. Use when <actions>. Not for <sibling> (<name>).` Target 300–500 characters, hard ceiling about 900. It MUST keep every distinct action verb: register, record a blocker, check status, clean up safely, report outstanding objects, link sessions.
- **CV-04** — The description MUST carve against `session-loose-ends`, which already fires on "anything to clean up?" and "tie this off". The `session-loose-ends` description MUST gain a reciprocal "Not for registered-object cleanup (`brot`)" pointer, and nothing more in v1 (OQ-09). That edit is a change in `smorinlabs-skills` and needs its own worktree and PR.
- **CV-05** — The skill name MUST be globally unique across installed skills. No current skill matches `brot`, `bitrot`, `cleanup`, or `sanit` (checked 2026-11-12). The skill is named `brot`, and v1 ships one skill with per-area references (OQ-07).
- **CV-06** — Repo layout MUST follow home 5 (OQ-02). The home-4b line is kept for reference only:
  - **home 5:** the harness-kit layout, the same as `smorinlabs-skills` (`harness.toml`, `plugins/<name>/plugin.meta.toml`, catalogs and manifests generated by `harness-kit gen`);
  - **home 4b:** the self-hosted marketplace pattern [F] (`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, `plugins/<name>/` holding a real `.claude-plugin/plugin.json` with a symlinked `.codex-plugin/plugin.json`, `skills` present, `interface` omitted). That pattern was verified on Codex 0.145.0; the machine now runs 0.167.2, so it MUST be re-verified (design task).
- **CV-07** — The skill is discipline-enforcing (never delete raw). It therefore MUST carry an iron law near the top and a Red Flags table of 4–6 rows, per `_conventions.md`.
- **CV-08** — Interaction with the user follows the fleet interaction contract: one question per message, a recommendation first, confirm before mutating. For cleanup, the cleanup policy (SK-17) decides which confirmations are needed; every other mutation is still confirmed.
- **CV-09** — No secrets, PII, or absolute personal paths in any shipped file. Public-docs gate: public files do not reference private fleet tools. The repo is public (OQ-12), so this requirements file was scrubbed of private tool names, local paths, and machine-specific observations before it moved into the repo.
- **CV-10** — The repo MUST carry a `.claude/settings.json` welcome announcement that describes the project and its commands. The text is confirmed with the owner first.

### 3.5 Distribution and versioning (DS)

- **DS-01** — The plugin lives in the standalone repo `smorinlabs/bitrot-sanitation-skill` using the home-5 harness-kit layout, and is cross-listed in `smorinlabs-skills` by `github:` reference (OQ-02). The repo is public (OQ-12).
- **DS-02** — The plugin MUST use semantic versioning independent of `brot`'s version.
- **DS-03** — The plugin MUST declare a compatible `brot` version range in one machine-readable place. Hooks and the skill MUST check it at runtime against `brot`'s reported version and capabilities (`DEP-08`).
- **DS-04** — A release MUST bump the version in every manifest and catalog that carries one, in one change. Under home 5 that is `harness.toml` and `plugin.meta.toml`, followed by `harness-kit gen`. Under home 4b it is the Claude catalog, the Codex catalog, and the plugin manifest. In both cases the OpenCode package is included if one exists.
- **DS-05** — Release notes MUST flag any release that changes a hook definition, because users must re-trust it on Codex and Muse (E5, E11).
- **DS-06** — Releases follow the fleet path: a release branch, a PR, a merge commit, and the tag placed on the merge commit. The `skill-harness-release` skill drives this path; release-please is not used (OQ-10).
- **DS-07** — Installing the plugin MUST NOT install `brot`. The docs MUST give the `brot` install command as a prerequisite. The plugin MUST detect a missing `brot` (DG-01).

### 3.6 Degraded modes (DG)

- **DG-01** — **`brot` missing.** This guard is the one piece of logic a shim may contain (HC-06). Hooks MUST exit 0 quickly and print nothing that blocks the session. The skill MUST tell the user `brot` is not installed, give the install command, and stop registering. It MUST NOT emulate the registry in notes or files.
- **DG-02** — **`brot` older or newer than the declared range.** Hooks MUST no-op with a single warning per session. The skill MUST report the installed version and the required range.
- **DG-03** — **Harness without a usable event.** The skill performs that step manually. Examples: session registration on first use (SL-01), and the end report on wrap-up (SL-07).
- **DG-04** — **Hook not trusted or not approved** (Codex E5, Muse E11). Covered by DG-06, which names the trust or approve command.
- **DG-05** — **`brot` error during registration.** Registration failures MUST fail open: the agent's work continues and the failure is reported.
- **DG-06** — **The skill MUST detect when hooks are not running.** Hooks can fail silently: the plugin is disabled, Codex has not trusted the hook, Muse has not approved it, the Codex hooks feature is off, or a harness update changed event names. Without detection, nothing gets registered and nobody notices.
  1. **When it checks:** the first time the skill is used in a session, and again whenever the agent runs a command that hooks should have registered automatically (SK-01).
  2. **Start check:** the skill resolves the current session ID (T3 `FR-HOOK-5`) and asks `brot` whether it received a session-start hook event for that session (`DEP-13`). No session ID resolvable, or no start event recorded, means the start hook is not running.
  3. **Tool check:** after a detectable command such as `git worktree add <path>`, the skill asks `brot` whether `<path>` is registered as `source=hook` (T3 `FR-OBJ-5`). Not registered means the post-tool hook is not running.
  4. **Diagnosis:** the skill runs `brot`'s read-only doctor (T3 `FR-HOOK-9`) and reports the cause in this order: `brot` missing (DG-01), version out of range (DG-02), plugin not installed or disabled, hook not trusted (Codex), hook not approved (Muse), hooks feature disabled (Codex `features.hooks`). It gives the exact command that fixes the cause.
  5. **Keep working:** after reporting, the skill registers the session and the missed object manually (DG-03), so the session's record is still complete.
  6. **Noise limit:** the report appears once per session per cause, not on every check.

### 3.7 Non-functional (NF)

- **NF-01** — Hook latency follows T3: tool-path hooks under 100 ms p95 (T3 `FR-HOOK-7`) and session-end work under 1 s (T3 `FR-HOOK-6`). A shim MUST add no measurable time beyond the `brot` call.
- **NF-02** — Hooks MUST be safe under concurrent sessions. Concurrency inside `brot` is `T3:storage`.
- **NF-03** — The session-start context injection (SL-04) MUST be capped. Proposed cap: 15 objects or about 1,500 characters, with a pointer to the full `brot` status command.
- **NF-04** — Testing MUST include: the fleet's deep, strict skill verifier; the fleet install-test recipe on Claude Code and Codex; `muse plugins hook test --fixture` for Muse hooks; a fixture-driven test of the OpenCode module; and one headless end-to-end run per harness with a throwaway `brot` database.
- **NF-05** — Command-type hook shims (Claude Code, Codex, Muse) MUST be POSIX `sh`-compatible on macOS and Linux. The OpenCode shim is a JS/TS module (E14) and MUST NOT need dependencies beyond what OpenCode provides. Windows support is out of scope for v1 (section 5).

## 4. Dependencies on `brot` (T3 to own)

These are what the plugin needs from `brot`. They are listed so T3 can confirm or reject them; they are not CLI requirements written by T4.

| ID | Need | Used by |
|---|---|---|
| DEP-01 | A session-register command that accepts harness, session ID, cwd, transcript path, and parent ID. | SL-01, SL-02 |
| DEP-02 | Status and blocker queries with JSON output and stable exit codes. | SK-09, SL-04, SL-07 |
| DEP-03 | One hook entrypoint, `brot hook <harness> <event>`, that reads the harness's event payload on stdin. Behind it: the plugin/`brot` compatibility check, the once-per-session warning, and command detection. `brot` finds the plugin version by reading the plugin manifest (located through the plugin-root variable or the payload), **never** from an argument in the hook text, so the hook text stays stable (HC-06a). | HC-06, HC-06a, DS-03, DG-02 |
| DEP-04 | Command-pattern detection for automatic registration (which shell commands create which object types). Could live in `brot` or in the shim; decided jointly. | SK-01 |
| DEP-05 | Idempotent registration keyed on the exact reference. | SK-03 |
| DEP-06 | Session liveness checks that detect crashed sessions without an end event. | SL-05, SL-08 |
| DEP-07 | Pending blockers that can be filled in later with an exact reference. | SK-07 |
| DEP-08 | A machine-readable version and capabilities report (for example `brot --version --json`). | DS-03, DG-02 |
| DEP-09 | A dry-run mode for every safe-delete command that lists the full target set. | SK-10 |
| DEP-10 | ~~A "would this delete touch a registered or protected object?" check for a pre-tool-use hook.~~ **Not needed in v1** (OQ-03 decided advisory). | — |
| DEP-11 | In the hooks gap table, per harness: does hook output reach the model's context? | SL-04 |
| DEP-12 | In the hooks gap table, per harness: can a pre-tool-use hook warn, deny, or neither? Required (HC-07a). T3 gap table C3: ✅ on all four harnesses. | HC-07a |
| DEP-13 | A record of hook events received per session (event name and time), and a query for it, for example "did session `<id>` receive a start event?" and "was `<locator>` registered as inferred?". | DG-06 |
| DEP-14 | *C-2 decided B: waits until T3 reopens D-3 (§7.4.3).* A stored cleanup policy (SK-17) that the skill can query, and that `brot` itself enforces on its delete commands. T3's `Q-AUTH` is answered by this: configurable, not fixed. | SK-17, SK-18 |
| DEP-15 | Plans with per-step risk information: each check is classed as soft risk or hard stop, and steps are classed low risk or not. A per-object risk view (`brot` shows every warning and risk for deleting one object) and a force-delete command for that one object, which passes hard stops only when force is given explicitly. | SK-10, SK-11, SK-19 |
| DEP-16 | *C-3 resolved; C-4 waits until T3 reopens D-4 (§7.4.3).* Deletion modes per object type (SK-21), selectable on every delete including forced ones; `brot restore <id>`; a manual purge command with no automatic expiry (SK-24); a default mode per object type, configurable at user and project level, with the project level winning (SK-23). | SK-19, SK-21 to SK-24 |

## 5. Out of scope

- The `brot` CLI itself: schema, commands, safe-delete rules, storage (T3).
- Object-type extensibility through plugins (deferred in T3; informed by T7).
- Session discovery across harnesses beyond what `brot` registers. `session-inventory-cli` (session plugin) and T6 `lost-sessions` own that.
- Harnesses other than the four named. Windows hosts.
- Cleaning up objects created before `brot` was installed, except through OQ-04.

## 6. Open questions (decision requests)

Each question gives the reason it is needed, the options with their effects, and a recommendation. The owner decides. **Some decisions below conflicted with T3's final requirements.** Conflicts C-1 to C-4 in §7.4.3 list them. They and OQ-15 (f) were decided 2026-11-16.

### OQ-01 — Who installs the hooks? — **DECIDED 2026-11-12: A** (the plugin ships thin-shim hooks; `brot` does not write harness config)
**Why:** T3's brief says "the CLI and skill orchestrate registration via harness hooks", which leaves the owner of hook installation undecided. The answer reshapes HC-03 to HC-06 and DS-07.
| Option | Effect |
|---|---|
| **A. The plugin ships thin-shim hook declarations; the harness loads them on install.** | One install step per harness. Hook trust is handled by each harness's normal plugin flow. All four harnesses load hooks from plugins: Claude Code [O] E2, Codex [O] E4, Muse [O] E9 (declaration format [U]), OpenCode as a code module [O] E14. |
| B. `brot hooks install --harness <h>` writes hook config into user settings; the plugin carries only the skill. | Works even where plugins cannot carry hooks. `brot` then edits user config files on four harnesses, which is more surface for T3 and harder to uninstall cleanly. |
| C. A mix: A where the harness supports plugin hooks, B as fallback. | Covers every harness, but two install paths need documenting and testing. |
**Recommendation: A**, falling back to C only for a harness proven unable to load plugin hooks. It keeps `brot` free of harness config writing and gives one uninstall path.

### OQ-02 — Repo layout and marketplace placement — **DECIDED 2026-11-12 (recommendation accepted): A** (home 5 harness-kit layout, cross-listed in `smorinlabs-skills`)
**Why:** `_routing.md` places a standalone repo in home 5, which uses the harness-kit layout and the naming pattern `<purpose>-harness`. The repo name `bitrot-sanitation-skill` was already decided in T5 and is not re-opened here; it deviates from `<purpose>-harness`, and the docs should note that deviation. The open parts are the layout and whether the plugin also appears in the public fleet catalog `smorinlabs-skills`.
| Option | Effect |
|---|---|
| **A. Home 5: harness-kit layout, cross-listed in `smorinlabs-skills` by `github:` reference.** | Same tooling as the rest of the fleet (`harness-kit gen`, `skill-harness-release`, `skill-quality` layer 3). Generated catalogs avoid hand-editing versions. Needs harness-kit to emit everything Muse and OpenCode need, or hand-maintained extras for those two. |
| B. Home 4b-style hand-written catalogs in the standalone repo, cross-listed. | Full control over both catalogs. Versions are bumped by hand in several files (DS-04). The fleet's 4b guide assumes the plugin ships inside the product repo, which this one does not. |
| C. Move the plugin into `bitrot-sanitation` (true 4b: ships inside the CLI repo). | Plugin and CLI version together, which removes the compatibility-range problem (DS-03). Contradicts the T5 decision to use a separate repo. |
**Recommendation: A.** It follows `_routing.md` for a standalone repo and reuses the fleet's generation and release tooling. Choose B only if harness-kit cannot represent the hooks.

### OQ-03 — Is "never raw `rm`" enforced or advisory? — **DECIDED 2026-11-12: A, advisory only** (skill text and iron law; no pre-tool-use delete hook in v1)
**Why:** SK-12 forbids raw deletes of registered objects. Skill text alone cannot stop a model from running `rm -rf`.
| Option | Effect |
|---|---|
| A. Advisory: skill text and the iron law only. | No hook latency on every tool call. Relies on the model complying. |
| **B. Warn: a pre-tool-use hook asks `brot` (DEP-10) and adds a warning to the agent's context when a raw delete targets a registered object.** | Catches mistakes without blocking unregistered work. Needs DEP-10 and a pre-tool-use event per harness (`T3:hooks`). |
| C. Deny: the same hook blocks the command. | Strongest guarantee. A false positive blocks legitimate work, and a broken `brot` blocks deletes until fixed. |
**Recommendation: B for v1**, with deny enabled only for targets under `brot`'s protected prefixes. Revisit C after measuring false positives.

### OQ-04 — Cleanup of unregistered objects — **DECIDED 2026-11-12 (recommendation accepted): A** (register first, then delete through `brot`)
**Why:** Agents will meet objects created before `brot` existed, or missed by registration.
| Option | Effect |
|---|---|
| **A. Register first, then delete through `brot`.** | Every delete goes through the sanity pass. Adds one step. |
| B. Out of scope: the skill says nothing; normal practice applies. | Leaves a gap exactly where agents delete the wrong thing. |
**Recommendation: A.**

### OQ-05 — Conflict with the fleet's "closing the loop" instructions — **DECIDED 2026-11-12 (recommendation accepted): A** (carve-out in all three copies, after `brot` ships worktree/branch safe-delete)
**Why:** The global `CLAUDE.md`, the `git-main-branch-discipline` memory, and `skill-create` all prescribe `git worktree remove`, `git worktree prune`, and `git branch -d` after a merge. SK-12 forbids those commands on registered objects. The `CLAUDE.md` rule "correct all three or none" applies.
| Option | Effect |
|---|---|
| **A. Carve-out: those three instructions say "use `brot`'s safe-delete when the worktree or branch is registered; otherwise the git commands".** | Consistent with SK-12. Requires coordinated edits to all three copies. |
| B. Exempt git worktree and branch cleanup from SK-12. | No edits elsewhere. Worktrees, the most common object, lose the sanity pass. |
**Recommendation: A**, landed after `brot` ships safe-delete for worktrees and branches.

### OQ-06 — OpenCode distribution form — **DECIDED 2026-11-12 (recommendation accepted): B** (a file in this repo, installed by copy or symlink)
**Why:** OpenCode hooks are JS/TS modules (E14). They can ship as an npm "package plugin" (E13) or as a file copied into `~/.config/opencode/plugins/`.
| Option | Effect |
|---|---|
| A. npm package (for example `opencode-brot`). | `opencode plugin add/update` works. Needs an npm name and a publish pipeline. |
| **B. A file in this repo, installed by a documented copy or symlink.** | No npm publishing. Updates are manual. |
**Recommendation: B for v1**, moving to A if OpenCode becomes a primary harness.

### OQ-07 — Skill name and skill count — **DECIDED 2026-11-12 (recommendation accepted): A** (one skill named `brot`)
**Why:** The name is the trigger namespace, and it must be globally unique (CV-05).
| Option | Effect |
|---|---|
| **A. One skill named `brot`, with per-area references.** | Matches the binary, so it is easy to invoke by name. One description must cover six actions. |
| B. One skill named `bitrot-sanitation`. | Matches the repo; less natural to type. |
| C. Two skills: `brot` (registration and cleanup) and `brot-status` (read-only report). | Sharper triggers. Two descriptions must stay mutually exclusive. |
**Recommendation: A.**

### OQ-08 — Automatic end report — **DECIDED 2026-11-12 (recommendation accepted): A** (skill-driven only)
**Why:** SL-07 makes the end report skill-driven. An end hook could also print it, but end-hook output is often invisible.
| Option | Effect |
|---|---|
| **A. Skill-driven only; the end hook just marks the session ended.** | Simple. The report appears only when the user wraps up through the agent. |
| B. Also write the report to a file and surface it at the next session start (SL-04). | Survives sessions that end abruptly. Duplicates the start summary. |
**Recommendation: A**, because SL-04 and SL-05 already resurface outstanding objects at the next start.

### OQ-09 — How far `session-loose-ends` changes — **DECIDED 2026-11-12 (recommendation accepted): A** (description pointer only)
**Why:** CV-04 needs `session-loose-ends` to point to the new skill for registered-object cleanup. That is a change in `smorinlabs-skills`, made in its own worktree and PR.
| Option | Effect |
|---|---|
| **A. Description pointer only.** `session-loose-ends` gains "Not for registered-object cleanup (`brot`)". | Smallest change. Triggers stay exclusive. The loose-ends sweep still ignores `brot` data. |
| B. Pointer plus integration. When `brot` is installed, `session-loose-ends` also lists `brot`'s outstanding objects in its sweep. | One sweep shows everything. Couples a public fleet skill to `brot`. |
**Recommendation: A for v1.** **Reply needed:** A or B.

### OQ-10 — Release automation — **DECIDED 2026-11-12 (recommendation accepted): A** (`skill-harness-release`, because OQ-02 chose home 5)
**Why:** DS-06 requires the fleet release path. Several files carry versions (DS-04).
| Option | Effect |
|---|---|
| **A. `skill-harness-release` only** (fits home 5). | Same release flow as `smorinlabs-skills`. Manual trigger. |
| B. release-please via `repo-please-setup`. | Automatic version bumps and changelog from conventional commits. Must be configured to bump every versioned file. |
**Recommendation: A if OQ-02 picks home 5; otherwise B.** **Reply needed:** A or B.

### OQ-11 — Where a from-scratch hook ships — **DECIDED 2026-11-12 (recommendation accepted): A** (in this plugin)
**Why:** HC-08 makes "build the hook" the first fallback for a missing event. A built hook could be harness integration code (for example, an OpenCode module listening to an event T3 needs) or a watcher process.
| Option | Effect |
|---|---|
| **A. In this plugin.** | All harness integration lives in one repo. `brot` stays harness-agnostic. |
| B. In `brot`. | One binary to install. `brot` gains harness-specific code and must track harness releases. |
**Recommendation: A.** **Reply needed:** A or B.

### OQ-12 — Repo visibility — **DECIDED 2026-11-12 (recommendation accepted): A** (public)
**Why:** CV-09's scrub rules apply only to a public repo, and `smorinlabs` repos are usually public. `brot` itself may hold machine-specific paths, but this repo ships only the plugin.
| Option | Effect |
|---|---|
| **A. Public.** | Can be cross-listed in the public `smorinlabs-skills` (OQ-02 A). This requirements file must be scrubbed before it moves in. |
| B. Private. | No scrub needed. It cannot be cross-listed in a public catalog. |
**Recommendation: A**, matching `bitrot-sanitation`'s visibility. **Reply needed:** A or B.

### OQ-13 — Verification still owed (research, not owner decisions)
These are facts to establish during design, not choices:
- E8: whether one plugin directory can carry both the Codex manifest and `.muse-plugin/plugin.json`, so Muse installs from the same git marketplace.
- E11: whether Muse hooks need approval before they run.
- HC-06a: the plugin-root variable each harness exposes to hook commands (Claude Code `${CLAUDE_PLUGIN_ROOT}`; Codex and Muse unknown), and whether the trust hash covers only the hook text or the whole hooks file.
- E6: whether Codex still needs `features.hooks = true`.
- E15: OpenCode skill discovery paths.
- CV-06 / HC-04 / HC-05: confirm harness-kit can generate or carry the hook declarations (Claude Code, Codex), the Muse hook declaration, and the OpenCode module file. Hand-maintain any it cannot.
- SL-02: Claude Code's fork and resume lineage fields.
- Fold in T3's hooks gap table when T3's output exists, and replace every `T3:<area>` placeholder with real T3 IDs.

### OQ-14 — Can the agent clean up without asking? — **DECIDED 2026-11-12: configurable policy** (none of the three original options)
The owner chose a configurable spectrum instead of one fixed rule. Agents should be able to clean up; a human sets the policy. Confirmation can be per step or per batch, or required only above low risk. The owner's own default is full agent autonomy with full risk information. A direct mode skips the plan, with hard stops that need a force override. Recorded as SK-17 to SK-20, DEP-14, and DEP-15. Detail is deferred to OQ-15.

### OQ-15 — Cleanup policy design questions (for the design phase)
The owner asked for this part to be planned in more detail. These questions are for the design phase, not answered here:
- **(a)** The shipped default for users other than the owner (the owner's default is `auto`).
- **(b)** Where the policy is set, and which setting wins: machine-wide, per repo, per object type, per session.
- **(c)** What makes a step "low risk", and who defines it: `brot` defaults, user configuration, or both.
- **(d)** Which failed checks are hard stops and which are soft risks.
- **(e)** ~~Confirm SK-19's reading.~~ **Resolved 2026-11-12:** the owner views one object's warnings and risks, then runs a force-delete command for it (SK-19). Plan editing (striking steps) is not a requirement.
- **(f)** ~~Whether an agent may apply force on its own.~~ **Decided 2026-11-16: never without a user request** (SK-11). Reopened 2026-11-12 by T3 D-15: T3 added `--force-agent --reason <text>`, which overrides type-check and sanity refusals without a terminal; neither flag overrides the deny list. `brot` therefore allows agent force, and the question was whether the skill does. The options not chosen were allowing it in `auto` and `direct` policies with the reason reported (SK-20), or in every policy. Research item kept: whether a command run through the harness (for example Claude Code's `!` prefix) counts as an interactive terminal for `--force`.
- **(g)** Whether PRs and cloud resources follow the same policy as local objects, or always need confirmation.
- **(h)** ~~Risk level and acknowledgement code on force.~~ **Decided 2026-11-12: no.** Force takes no risk level and no acknowledgement code; the human reviews the risks (SK-19) and chooses the mode (SK-21).
- **(i)** ~~Default mode.~~ **Decided 2026-11-12: yes, configurable** (SK-23). Owner confirmed: the project level wins over the user level.
- **(j)** ~~Retention.~~ **Decided 2026-11-12: manual.** Soft-deleted items are kept until a human purges them; there is no automatic expiry (SK-24). Owner confirmed this reading. Storage location stays with T3.

## 7. Cross-reference with T3

§7.1 and §7.2 were written against T3's draft of 10:53, and §7.3 against T3's file of 13:30. **§7.4 is current**: it was checked against T3's final file of 15:27 (status "Final — requirements complete"). §7.1 to §7.3 are kept as history.

T3's requirements file was marked "Draft — interview in progress". This mapping was re-checked against T3's final file in §7.4.

### 7.1 Placeholder and dependency mapping

| T4 reference | T3 ID(s) | Match |
|---|---|---|
| `T3:registry` | `FR-OBJ-1`–`FR-OBJ-11` | — |
| `T3:sessions` | `FR-SES-1`–`FR-SES-7` | — |
| `T3:hooks` | §5.1 caps C1–C13, §5.2 gap table, `FR-HOOK-1`–`FR-HOOK-18` | — |
| `T3:safe-delete` | `FR-DEL-1`–`FR-DEL-6` | — |
| `T3:storage` | `NFR-STO-1`–`NFR-STO-5` | — |
| DEP-01 session register | `FR-SES-1`, `FR-SES-2` | covered |
| DEP-02 status queries, JSON, exit codes | §6 `FR-STAT`, `NFR-3` | covered |
| DEP-03 one hook entrypoint | `FR-HOOK-1` | covered; reading the plugin version from the manifest (not the hook text) and the compatibility check are **not yet in T3** |
| DEP-04 command detection | `FR-OBJ-9` | covered (lives in `brot`) |
| DEP-05 idempotent registration | `FR-OBJ-8` | covered |
| DEP-06 liveness | `FR-HOOK-2`, `FR-SES-4` | covered |
| DEP-07 pending blockers | `FR-OBJ-7` | **not yet in T3** (blockers need an exact reference at creation) |
| DEP-08 version and capabilities report | — | **not yet in T3** |
| DEP-09 dry-run | `FR-DEL-5` | covered |
| DEP-11 hook output reaches model | gap table C9 | covered: ✅ on all four harnesses |
| DEP-12 pre-tool warn/deny | gap table C3 | covered: ✅ on all four harnesses |
| DEP-13 hook-event record and query | `FR-HOOK-9` (doctor) is related | **not yet in T3**: the doctor reports trust state, but nothing records which events actually arrived |
| DEP-14 stored cleanup policy | `Q-AUTH` (open) | **not yet in T3**: answer `Q-AUTH` "configurable" (OQ-14) |
| DEP-16 deletion modes, restore, manual purge, configurable default | `Q-AUTH` mentions "hard delete or trash" | **not yet in T3** as requirements |
| DEP-15 plan risk classes, per-object risk view, force delete | `FR-DEL-1`, `FR-DEL-5` partly | **not yet in T3**: soft risk versus hard stop, low-risk class, per-object risk view, single-object force delete |
| SK-13 / OQ-04 register before delete | `FR-DEL-6` | consistent |

### 7.2 Conflicts for the owner to resolve in T3

These are decision requests. T4's side is already decided; each one asks what T3's draft should say. Answer them in the T3 session.

#### X1 — Who installs the hooks: the plugin or `brot`? — **DECIDED 2026-11-12: A** (`brot` installs nothing; read-only `brot doctor`)
**Conflict.** T4 `OQ-01` decided the plugin ships the hooks and `brot` writes no harness config (HC-09). T3's draft has `brot` install hooks by merging them into existing config files (`FR-HOOK-17`), alongside "install and doctor commands" (`FR-HOOK-9`).
**Why it matters.** If both happen, every hook is installed twice. Each `brot` event would then be recorded twice, and uninstalling the plugin would leave `brot`'s copies behind.
**Key fact.** Plugin hooks live in the plugin's own files (Claude Code and Codex `hooks/hooks.json`, Muse `.muse-plugin/plugin.json`, the OpenCode module file). Installing the plugin never edits the shared `~/.codex/hooks.json` or a Muse hooks file managed by another tool. The merge problem `FR-HOOK-17` guards against therefore does not arise under OQ-01.

| Option | What T3 changes | Effect |
|---|---|---|
| **A. `brot` installs nothing.** | Drop installation from `FR-HOOK-17`, or turn it into a rule for the plugin: "never edit another tool's hook files". Narrow `FR-HOOK-9` to a read-only `brot doctor` that reports hooks that are missing, untrusted, or unapproved. | One owner and one uninstall path. `brot doctor` also powers T4's hook-health check (DG-06). |
| B. `brot` keeps an installer as a fallback. | Keep `FR-HOOK-17` for harnesses where the plugin cannot load hooks. | Two install paths to build, document, and test. This is the "plugin, `brot` as fallback" option you turned down in OQ-01. All four harnesses load plugin hooks (gap table C13), so the fallback has no current use. |
| C. Reopen OQ-01: `brot` owns installation. | Keep `FR-HOOK-17` as written. | The plugin becomes skill-only, and T4 HC-03 to HC-13 are rewritten. `brot` must track four harnesses' config formats. |

**Recommendation: A.** It matches your OQ-01 decision, and the gap table shows no harness needs a fallback. **Reply needed in T3:** A, B, or C.

#### X2 — Does v1 include a delete guard? — **DECIDED 2026-11-12: B** (ship the shell-only pre-tool hook; guard off in v1)
**Conflict.** T4 `OQ-03` decided raw-delete prevention is advisory only in v1: skill text, no blocking hook (SK-14). T3's draft plans a `brot` guard that runs in each harness's pre-tool hook and stops raw destructive commands (`FR-HOOK-16`, open question `Q-GUARD`).
**Why it matters.** Under HC-06a, adding a new hook event later changes the hook definitions, and every Codex and Muse user must re-approve once. Shipping the hook now but having `brot` do nothing with it avoids that later re-approval.

| Option | What ships in v1 | Effect |
|---|---|---|
| A. Defer entirely. | No pre-tool hook. T3 answers `Q-GUARD` "deferred past v1" and marks `FR-HOOK-16` deferred. | Smallest v1, with no extra cost per command. Adding the guard later is a hook change, so every Codex and Muse user must re-approve once. |
| **B. Ship the hook, guard off.** | A pre-tool hook limited to shell commands (matcher `Bash` or the harness equivalent). In v1 `brot` lets every command through unchanged; it does not warn or block. T3 answers `Q-GUARD` "hook present in v1, guard logic deferred". | Behaviour matches your advisory decision. Turning the guard on later needs only a `brot` upgrade, with no re-approval. Cost: one extra `brot` call per shell command, which must stay well under T3's 100 ms budget (`FR-HOOK-7`). |
| C. Guard on in v1 (warn or block). | As B, with `brot` warning about or blocking raw deletes of registered objects. | Reopens OQ-03. Needs the fast "is this registered or protected?" check (DEP-10) in v1. |

**Recommendation: B.** It keeps your advisory decision for v1 and follows your new stability rule: when the guard arrives, only `brot` changes and nobody re-approves hooks. Choose A if an extra process per shell command is unacceptable. **Reply needed in T3:** A, B, or C. If B, T4 adds the shell-only pre-tool hook to HC-07 and re-labels DEP-12 from informational to required.

#### X3 — Who confirms deletes?
Resolved through **OQ-14** (decided: configurable policy). T3's `Q-AUTH` should be answered "configurable", with the policy stored and enforced by `brot` (DEP-14) and plans carrying risk classes (DEP-15). Owner default: `auto`.

### 7.3 Reconciliation with T3 (file of 2026-11-12 13:30)

#### 7.3.1 T4 changes made to follow T3 decisions
These T3 rows are marked Decided, so T4 adapts to them.

| T3 decision | T4 change |
|---|---|
| D-6: blockers may be agent-checked, not only machine-checked | SK-07 rewritten: prefer checked blockers; agent-checked allowed, with exact references where possible |
| D-6 / `FR-STAT-7`: session-start context covers only the session's own objects | SL-04 rewritten to inject only that; SL-05 moves orphaned objects to on-demand and the end report |
| D-8: dead sessions' objects become `orphaned`; adoption | SL-05: the skill offers adoption before cleanup, and never cleans an unadopted orphan |
| D-9: hook-added objects are lowest trust and must be validated | New SK-05b |
| D-10: trust levels, `--on-behalf-of user` | New SK-05a |
| D-2 / D-13: `brot` deletes local and git objects; for cloud it only prints the delete command | SK-12 rewritten; SK-21 cloud row changed to "none in v1" |
| D-3 / `FR-DEL-9`: `--force` only at an interactive terminal | OQ-15 (f) settled: only a human can force, matching SK-19 |

#### 7.3.2 Asks for T3's final confirm pass
The owner should raise these in the T3 session. A1, A4 and A6 touch rows still Proposed or Open. A2, A3 and A5 amend Decided rows, which needs the owner.

| # | T3 row (status) | Ask | Source in T4 |
|---|---|---|---|
| A1 | `FR-HOOK-17`, `FR-HOOK-9` (Proposed) | Drop hook installation from `brot`. Keep a read-only `brot doctor` that reports hooks that are missing, untrusted, or unapproved. | X1 = A |
| A2 | D-5 / `FR-HOOK-16` (Decided) | Keep "no guard logic at v1", but allow the plugin to ship a shell-only pre-tool hook that calls `brot hook <harness> pre-tool`, which passes every command through. The text "`brot` installs no `PreToolUse` hooks" stays true, because the plugin installs it. `FR-HOOK-1` must accept the `pre-tool` event. | X2 = B, HC-07a |
| A3 | D-3 (Decided) | Make agent-autonomous cleanup the **default** of a configurable policy, not the only rule. Modes: `confirm-each`, `confirm-batch`, `auto-low-risk`, `auto`, `direct`. The owner's default stays `auto`, which is D-3. | OQ-14, SK-17, DEP-14 |
| A4 | `FR-DEL-14` (Proposed), `FR-DEL-10` (Decided) | Purge runs only on command, with no automatic expiry; a retention window may only filter what the purge command removes. Add project-level config for the default delete mode, with the project level winning over the user level. | SK-23, SK-24 |
| A5 | D-4 (Decided; covers local files only) | Add soft-delete modes for other types: worktree `archive` (patch plus untracked files), branch `backup-ref` (`refs/brot/backup/<branch>`), and PR `close` that keeps the head branch. `brot restore <id>` for each. | SK-21, SK-22, DEP-16 |
| A6 | `Q-CHAIN` (Open) | Widen the default "related objects" scope through `continues` and `forked_from` links. Without this, the session-start context is empty after `/clear`, compaction, or a fork, which is when it matters most. | SL-04 |
| A7 | not in T3 | Add three needs: read the plugin version from the plugin's manifest, never from hook text (DEP-03); a machine-readable version and capabilities report (DEP-08); a query showing whether a session was registered by its start hook (DEP-13). `FR-OBJ-5`'s `source=hook` already covers the tool-hook half of DEP-13. | HC-06a, DS-03, DG-06 |

#### 7.3.3 Dependencies now covered by T3
DEP-01 (`FR-SES-1`, `FR-SES-2`), DEP-02 (`FR-STAT-1`, `FR-STAT-2`, `FR-STAT-4`), DEP-04 (`FR-OBJ-9`, `FR-OBJ-9a`), DEP-05 (`FR-OBJ-8`), DEP-06 (`FR-HOOK-2`), DEP-07 partly (D-6 agent-checked blockers), DEP-09 (`FR-DEL-5`), DEP-15 partly (`FR-DEL-9` refusals and force). Not covered: DEP-03, DEP-08, DEP-13 (A7), DEP-14 (A3), DEP-16 (A5).


### 7.4 Reconciliation with T3 final (file of 2026-11-12 15:27)
T3's status is now "Final — requirements complete". D-17 confirmed every row that had been Proposed. This section records how each ask in §7.3.2 landed and what T4 must still settle. §7.3 is kept as history.

#### 7.4.1 Outcome of each ask
| # | Outcome | T3 evidence | Effect on T4 |
|---|---|---|---|
| A1 | **Accepted** | D-16, `FR-HOOK-17`: `brot` never edits harness config; the T4 plugins ship the hooks. `FR-HOOK-9`: `brot doctor` reports installed, trusted or approved, and last event seen | HC-09 and X1 = A hold. No change |
| A2 | **Not reflected in T3 final** | `FR-HOOK-19`: the v1 hook matrix lists no pre-tool hook | **Conflict C-1** below |
| A3 | **Not reflected in T3 final** | D-3 unchanged: cleanup is agent-autonomous when every check passes. No stored policy | **Conflict C-2** below |
| A4 | **Partly accepted** | `FR-DEL-11`: `brot purge` is a command and removes only items older than the retention window, so nothing expires on its own; SK-24 holds. `FR-DEL-10` sets the mode globally, per type, and per command, with **no project level** | **Conflict C-3** below (project level only) |
| A5 | **Partly accepted** | D-4 names local files only; T3 does not say whether quarantine applies to worktrees or local branches. `FR-DEL-7` records a remote branch's head SHA before deleting it, so that branch can be restored | **Conflict C-4** below |
| A6 | **Deferred** | `Q-CHAIN` left for the design phase; `--session <id>` is the workaround | SL-04 gap stays open, owned by design |
| A7 | **Partly accepted** | `FR-HOOK-9` "last event seen" covers part of DEP-13 | DEP-03, DEP-08 and the session-start half of DEP-13 stay as T4 needs for design |

#### 7.4.2 New T3 decisions T4 follows
| T3 decision | T4 change, or note for design |
|---|---|
| D-15 / `FR-DEL-9`: `--force-agent --reason <text>` lets an agent override type-check and sanity refusals without a terminal; the deny list is absolute | SK-11 rewritten; OQ-15 (f) reopened |
| D-14 / `FR-HOOK-5`: no session variable and no terminal means `unattributed`, the lowest trust | Note for design: DG-06 should treat an `unattributed` registration from an agent shell as a sign that session attribution is broken. Design detail |
| `FR-HOOK-19`: v1 hooks are `SessionStart`, `SessionEnd`, `PostToolUse` (+ `PostToolUseFailure`), `SubagentStart`/`SubagentStop`, `PostCompact`; no `Stop` hook | No edit needed: HC-07 takes its event list from T3's table. Note for design: `PostCompact` is the hook that should re-inject session-start context (SL-04) |

#### 7.4.3 Conflicts (decided 2026-11-16: B for all four)
T3 is final, so each conflict resolves one of two ways. The owner finalised T3 after asks A1 to A7 were raised, so Option A may be the intended outcome. Either T4 adopts T3's row, or the owner reopens that T3 row in the design phase.

| ID | Conflict | Option A: adopt T3 | Option B: keep T4 and reopen T3 | Recommendation |
|---|---|---|---|---|
| C-1 | Pre-tool hook in v1 (HC-07a, X2 = B) | Drop HC-07a. Adding a guard later changes the hook text, so Codex and Muse users must re-trust once | Keep HC-07a; reopen `FR-HOOK-19` to add a pass-through `pre-tool` event | **B**, because the one-time re-trust is the cost HC-06a exists to avoid, and the pass-through costs one process start per shell call within the 100 ms budget of `FR-HOOK-7` |
| C-2 | Configurable cleanup policy (OQ-14, SK-17, DEP-14) | v1 is `auto` only, D-3; the skill offers only skill-level confirmation | Reopen D-3: `brot` stores and enforces the policy | **B**, because the owner chose a configurable policy and a skill-only rule cannot stop a second agent that skips the skill |
| C-3 | Project-level default delete mode (SK-23) | User-level and per-command only | Reopen `FR-DEL-10` to add a project level that wins | **B**, because it was an explicit owner decision (OQ-15 (i)) |
| C-4 | Soft modes beyond files (SK-21) | T3 defines no archive mode for worktrees and no backup-ref mode for local branches; remote branches are restorable through the recorded SHA | Reopen D-4 to add worktree `archive`, branch `backup-ref`, and PR `close` | **B** for worktrees and local branches, which hold the unpushed work at most risk. PR `close` is already non-destructive |

**Decision (owner, 2026-11-16): B for C-1 to C-4.** T4 keeps its requirements. Checked the same day against T3's `docs/design.md` §15, which had already answered two of the four:

| ID | State in T3 | What remains |
|---|---|---|
| C-1 | **Resolved.** `brot hook <harness> pre-tool` is accepted as an `ignored` event (design §10.1), so the pass-through hook needs no T3 requirement change. `FR-HOOK-16` still holds, because `brot` acts on nothing pre-tool | Nothing. HC-07a ships as written |
| C-2 | **Not adopted.** T3's design defers reopening D-3 to a later phase | T3 reopens D-3 so that `brot` stores and enforces the policy (DEP-14). Until then SK-17, SK-18, and DEP-14 cannot be met |
| C-3 | **Resolved.** A project config may set `delete.mode` per object type to `quarantine` or `trash` (design §13, R5.1) | Nothing |
| C-4 | **Partly met.** Every local branch and worktree HEAD that a clean removes is first pinned under `refs/brot/backup/` (design §6.2). The selectable modes are not adopted | T3 reopens D-4 to add worktree `archive`, branch `backup-ref`, and PR `close` as modes (SK-21) |

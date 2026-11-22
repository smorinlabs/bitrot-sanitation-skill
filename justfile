# regenerate the Claude Code and Codex manifests and marketplaces
gen:
    uv run harness-kit gen

# fail (exit 1) if any generated manifest is stale
gen-check:
    uv run harness-kit gen --check

# hook text, missing-brot guard, and (with BROT_FIXTURES) shim replay
test:
    python3 -I tests/hooks.py
    node --test tests/opencode.test.mjs

all: gen-check test

# KEYRING

```
 █  █  ▄▀▀▀▀▀▄  █  █  █▀▀▀▀▀▄  █▀▀▀▀▀▄  █  █  █▄  █  ▄▀▀▀▀▀▄
 █▄▄▀   █▄▄▄▄▄  ▀▄▄▀  █▄▄▄▄▄▀  █  ▄▄▄█  █  █  █ ▀▄█  █     ▀
 █  █   █          █  █    ▀▄  █  ▀█    █  █  █   █  █  ▀▀█
 █  █   ▀▄▄▄▄▄     █  █     █  █   ▀█▄  █  █  █   █  ▀▄▄▄▄▀
```

**Find every credential on this machine, without ever showing one.**
KEYRING sweeps harness dot-directories, shell profiles, and project env
files, then reports *where* each secret lives, *which* ones have been
copied to more than one place, and *which* are exposed by file
permissions.

## The safety guarantee

This is the whole design constraint, and it is not negotiable:

- A secret's **value is never printed**, never logged, never written to
  the clipboard, and **never sent to the model**.
- Duplicate detection uses an **HMAC-SHA256 fingerprint** with a
  per-machine salt stored `0600` at `~/.keyring-salt`. Stable across runs
  so copies can be matched; not reversible into the secret.
- The only value-derived thing shown is the first 3 characters, which for
  real keys is the public provider prefix (`sk-`, `ghp`, `AKIA`).
- **Read-only.** Never edits, moves, or deletes a file.

Verified: no secret value from a known credentials file appears in any
output mode (default, `--json`, `--dupes`, `--exposed`).

## Why the ranking is what it is

Ranked by **blast radius**, not provider prestige:

| condition | weight | reasoning |
|---|---|---|
| world-readable | 60 | any process on the box can read it — the only true emergency |
| each additional copy | 15 | more places to leak from, harder to rotate |
| private key material | 25 | usually grants more than an API key |
| group-readable | 15 | narrower than world, still wrong |

## Usage

```
keyring                     sweep and report
keyring --dupes             only secrets living in 2+ places
keyring --exposed           only world/group-readable
keyring --provider z.ai     filter to one provider
keyring explain             GLM advises rotation order (no values sent)
keyring --json              machine-readable (still no values)
```

## Detection

Provider-specific signatures for OpenAI, Anthropic, GitHub, Slack,
Google, AWS, Stripe, GitLab, HuggingFace, Groq, z.ai, OpenRouter,
Replicate, Tavily, and PEM private keys, plus a generic
`api_key = ...` assignment matcher. Placeholders (`xxxx`, `<your-key>`,
`${ENV_VAR}`, `changeme`) are filtered out, and commented lines are
skipped so documented examples don't inflate the count.

## Config

Only `explain` needs an API key. Shared with qglm:
`QGLM_API_KEY` → `~/.qglm.yaml` → `/usr/local/share/qglm/.qglm.yaml`.
Override the model with `KEYRING_MODEL`.

## MCP App

KEYRING also ships as an MCP Apps server (`keyring-app`) implementing
SEP-1865. In a compliant host it renders an interactive inventory where
**you** can reveal a secret value on click, while the model still only
ever receives fingerprints — enforced by `visibility: ["app"]` rather
than by string masking.

See [../MCP-APPS.md](../MCP-APPS.md). Install with `../register-mcp --apply`.

# CLI-TOOLS

A suite of zero-dependency command-line tools, installed machine-wide, plus
three MCP Apps servers that expose the same engines to AI hosts.

Every tool follows the same shape: **a vague ask in, an exact artifact out**,
delivered to your clipboard, framed in the terminal.

## The tools

| tool | one line | language |
|---|---|---|
| **skiller** | vague ask in, exact SKILL.md out | Python |
| **prompter** | describe a prompt, get an engineered one | Python |
| **qglm** | streaming CLI client for GLM models | Go |
| **lgcy** | TUI client for OpenAI/Anthropic/OpenCode providers | TypeScript |
| **salvager** | find git work that exists nowhere else | Python |
| **keyring** | find every credential without showing one | Python |
| **recaller** | recover a command you already got working once | Python |

Each has its own README with design rationale.

## Install

```bash
sudo bash install-global.sh     # /usr/local/bin + /usr/local/share
sudo bash finalize-global.sh    # make shared indexes admin-writable
sudo bash install-go.sh         # Go toolchain (only needed to build qglm)
./register-mcp --apply          # register MCP Apps servers with hosts
```

`/usr/local/bin` is on the default macOS PATH, so every account on the
machine gets the tools with no shell configuration.

Per-user state (history, sessions, personal config) stays in each user's
home. Shared indexes and credentials live in `/usr/local/share`, with
credentials at `0640 root:admin` — never world-readable.

## Layout

```
lib/            shared, written once
  clikit.py       frames, color, GLM streaming, config resolution
  mcpkit.py       dual-era MCP server (2026-07-28 + legacy handshake)
  uikit.py        MCP Apps view runtime: handshake, theming, resize
SKILLER/        skiller
PROMPTER/       prompter
SALVAGER/       salvager  + salvager-app  (MCP)
KEYRING/        keyring   + keyring-app   (MCP)
RECALLER/       recaller  + recaller-app  (MCP)
test-mcp-apps   83-check verification suite
mcp-probe       drive an MCP server over real stdio JSON-RPC
view-harness.mjs run a view's JS against a fake DOM + fake host
```

`lib/` exists because SKILLER and PROMPTER had each grown their own copy of
the same ~250 lines of terminal chrome. Three more tools would have meant
five copies. One fix now lands everywhere.

## MCP Apps

Three tools also ship as MCP Apps servers implementing SEP-1865, with
interactive HTML views that render inline in a compliant host. See
[MCP-APPS.md](MCP-APPS.md).

The headline case is KEYRING: the sandboxed view can reveal a secret **to
you** while the model still only ever receives fingerprints, enforced by
`visibility: ["app"]` at the protocol level rather than by string masking.

## Testing

```bash
./test-mcp-apps     # 83 checks across both MCP protocol eras
```

Covers protocol conformance, graceful degradation, the security rules, and
live view rendering. Two harnesses because they catch different failures:
`mcp-probe` speaks real JSON-RPC; `view-harness.mjs` executes the view's
JavaScript. Both found real bugs during development.

## Not in this repo

Three directories are deliberately excluded (see `.gitignore`):

- **QGLM/**, **LGCY/**, **MITsh/** — each is already its own git repo with
  its own history. Tracking them here would either swallow that history or
  create broken gitlinks. If they should become part of this repo, convert
  them properly with `git submodule add`.

Also excluded: compiled binaries (rebuildable, 14MB each), build caches,
`.env` files, and hand-rolled timestamped backups. That last category is
what this repo replaces.

## Design constraints

**Zero dependencies.** Stdlib Python only; no SDK, no `node_modules`, no
build step. `qglm` is Go and `lgcy` is TypeScript, but both ship as single
binaries.

**Read-only by default.** SKILLER, PROMPTER, KEYRING and RECALLER never
modify your system. SALVAGER's CLI is read-only; only its MCP app can
write, through two narrow tools that commit or push one named repo and
never force-push, reset, or discard.

**Secrets are never printed.** KEYRING matches duplicates via salted
HMAC-SHA256 fingerprints, so it can tell you a key lives in four places
without ever showing you or a model what it is.

## Storage note

This repo lives on an external USB SSD (`/Volumes/Storage`), and the boot
volume is *also* an external USB SSD. The installed tools are symlinks into
this directory, so unmounting the drive breaks all seven for every user.
Moving the suite under `/usr/local/libexec` would collapse that to a single
drive dependency.

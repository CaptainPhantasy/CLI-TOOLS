# RECALLER

```
 █▀▀▀▀▀▄  █▀▀▀▀▀  ▄▀▀▀▀▀▄  ▄▀▀▀▀▀▄  █      █      █▀▀▀▀▀  █▀▀▀▀▀▄
 █▄▄▄▄▄▀  █▄▄▄▄   █        █▄▄▄▄▄█  █      █      █▄▄▄▄   █▄▄▄▄▄▀
 █    ▀▄  █       █        █     █  █      █      █       █    ▀▄
 █     █  █▄▄▄▄▄  ▀▄▄▄▄▄▄  █     █  █▄▄▄▄  █▄▄▄▄  █▄▄▄▄▄  █     █
```

**You solved this before. Find it, run it again.** RECALLER searches every
agent session transcript on the machine for the command you know you got
working once but can't remember.

Where SKILLER and PROMPTER *generate* an artifact, RECALLER *recovers* one
you already earned. It's the only tool in the suite that gets better purely
because you kept working.

## Why the ranking is what it is

**Commands that exited 0 rank above ones that errored** (1.8× vs 0.45×).
The entire point is recovering something that *worked*, not something you
tried.

Scoring also uses **IDF weighting**: a query term appearing in 3 of 2,337
commands counts far more than one appearing in 500. Without this, a search
for `ffmpeg video frame` is hijacked by the common word "frame" while the
discriminating term contributes nothing. Query coverage is rewarded too, so
matching three terms beats matching one common one.

Identical commands are collapsed across sessions, keeping the best
instance, so the list shows variety rather than the same line ten times.

## Usage

```
recaller "the ffmpeg flag that fixed audio drift"
recaller --cmd "docker run"      literal command substring
recaller --file report.tsx       sessions that touched a file
recaller --local                 skip GLM, local search only
recaller index                   rebuild the transcript index
recaller info                    index stats and sources
recaller --json                  machine-readable
```

Without an API key RECALLER still works as a fast local search and puts
the top match on your clipboard. With one, GLM deduces what you meant from
a vague description and returns the single best command with context.

## Sources

Parses three distinct transcript schemas natively:

| harness | shape |
|---|---|
| **codex** | `{timestamp, type, payload}` — records exit codes, so success is known exactly |
| **jcode** | `{meta, append_messages[]}` with content blocks |
| **claude** | one message object per line, `type=user\|assistant` |

Also sweeps opencode, cursor, grok, and pi, falling back to whichever
parser recovers the most from an unknown format. Every user home on the
machine is indexed, not just the current one.

Success for jcode/claude is inferred from tool-result text (error markers,
tracebacks, non-zero exit lines) since those formats don't record exit
codes directly.

## Safety

Read-only. Never modifies a transcript.

## Config

Shared with qglm: `QGLM_API_KEY` → `~/.qglm.yaml` →
`/usr/local/share/qglm/.qglm.yaml`. Override the model with
`RECALLER_MODEL`. Index goes to `/usr/local/share/recaller/` when
writable, else `~/.recaller/`.

## MCP App

RECALLER also ships as an MCP Apps server (`recaller-app`) implementing
SEP-1865: a command palette with live filtering, exit-status marks, and
one-click send-to-chat. It never executes a recovered command.

See [../MCP-APPS.md](../MCP-APPS.md). Install with `../register-mcp --apply`.

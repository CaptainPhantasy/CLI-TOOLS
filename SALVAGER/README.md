# SALVAGER

```
 ▄▀▀▀▀▀▀▀█   ▄▀▀▀▀▀▄   █      █   █  █  ▄▀▀▀▀▀▄   ▄▀▀▀▀▀▄   █▀▀▀▀▀▄   █▀▀▀▀▀▄
█   ▄▄▄▄▄█  █       █  █      █   █  █  █     █  █       █  █      █  █      █
█  ▀▄▄▄▄    █▄▄▄▄▄▄▄█  █      ▀▄ ▄▀  █  █▄▄▄▄▄█  █▄▄▄▄▄▄▄█  █▄▄▄▄▄▀   █▄▄▄▄▄▀
 ▀▄▄▄▄▄ ▀▄  █       █  █        █    █  █     █  █       █  █     ▀▄  █   ▀▄
 ▄▄▄▄▄▄▄▄▀  █       █  █▄▄▄▄▄▄  █    █  █     █  █       █  █      █  █     █
```

**Find the work you haven't saved yet.** SALVAGER walks every git repo on
the machine and reports what would vanish if the disk died right now,
ranked by how much you'd actually lose.

## Why the ranking is what it is

Most "git status everywhere" scripts rank by volume of change. That's the
wrong signal. SALVAGER ranks by **what exists in exactly one place**:

| finding | weight | reasoning |
|---|---|---|
| stash | 12 | invisible in every UI; people forget these for years |
| commit on a branch with no upstream | 10 | committed, but on no remote — git will never warn you |
| unpushed commit | 6 | a remote exists; you're merely behind |
| uncommitted / staged edit | 3 | real work, trivially lost |
| untracked file | 2 | easiest of all to delete by accident |

A repo with **no remote at all** gets a 1.6× multiplier: you couldn't
rescue it by pushing even if you tried.

## Usage

```
salvager                    scan and rank everything at risk
salvager --all              include clean repos in the listing
salvager --brief            one line per repo
salvager explain            GLM triages: what to rescue first, and how
salvager --roots A:B        scan specific roots
salvager --json             machine-readable
```

## Safety

**Read-only by construction.** SALVAGER runs no git command that writes.
It will never commit, push, stash, or checkout on your behalf. Telling
you what to save is the job; deciding how is yours.

## Performance

Roughly 1,100 repos on this machine. Git calls are IO-bound and
independent, so inspection runs across 16 threads. A full sweep is
seconds, not minutes.

## Config

Only `explain` needs an API key. Shared with qglm:
`QGLM_API_KEY` → `~/.qglm.yaml` → `/usr/local/share/qglm/.qglm.yaml`.
Override the model with `SALVAGER_MODEL`.

## MCP App

SALVAGER also ships as an MCP Apps server (`salvager-app`) implementing
SEP-1865: a triage board where you check the repos you want and commit or
push them in one action, with the result reported back into model context.

The CLI stays strictly read-only; the app adds exactly two narrow writes
(`commit_repo`, `push_repo`). Nothing force-pushes, resets, or discards.

See [../MCP-APPS.md](../MCP-APPS.md). Install with `../register-mcp --apply`.

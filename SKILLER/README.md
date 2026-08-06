# SKILLER

```
 ▄▀▀▀▀▀▀▀▀█  █▀▀█   █▀▀█  █▀▀█  █▀▀█         █▀▀█          ▄▀▀▀▀▀▀▀▀█  █▀▀▀▀▀▀▀▀▄
█   ▄▄▄▄▄▄█  █  █   █  █  █  █  █  █         █  █         █  █▄▄▄▄▄▄█  █  ▄▄▄▄   █
█  ▀▄▄▄▄     █  █▄▄▄▀  █  █  █  █  █         █  █         █  █▄▄▄▄▄    █  █▄▄▄▀  █
 ▀▄     ▀▄   ▀        ▄   ▀  ▄  ▀  ▀         ▀  ▀         ▀       █    ▀        ▄
   ▀▀▀▀▄  █  █  █▀▀▀▄  █  █  █  █  █         █  █         █  █▀▀▀▀▀    █  █▀▀▀▄  █
█▀▀▀▀▀▀   █  █  ▀   █  █  █  █  █  █▀▀▀▀▀▀█  █  █▀▀▀▀▀▀█  █  █▀▀▀▀▀▀█  █  █   █  █
█▄▄▄▄▄▄▄▄▀   █▄▄█   ▄▄▄█  █▄▄█   ▀▄▄▄▄▄▄▄▄█   ▀▄▄▄▄▄▄▄▄█   ▀▄▄▄▄▄▄▄▄█  █▄▄█   █▄▄█
```

**Vague ask in, exact skill out.** Describe what you're trying to do —
however roughly — and SKILLER returns one complete, ready-to-use SKILL.md
on your clipboard.

Two GLM-4.5 personas do the work:

- **SKILL-SCOUT** reads your rough request, deduces the latent goal behind
  it (typos, shorthand, and missing words resolved charitably), and picks
  the best matches from the local skill library.
- **SKILL-SMITH** then delivers: uses the best match as-is, merges and
  adapts several, or writes a new skill from scratch when nothing fits.

## Usage

```
skiller "make my agent stop forgetting stuff between sessions"
skiller index                 rebuild the local skill index
skiller search <term>         quick local keyword search (no LLM, free)
skiller info                  engine, index stats, catalog source
skiller --no-copy "…"         show the skill without copying
skiller --preview N "…"       preview N lines on screen (default 32)
skiller --help                framed help
```

Every result is copied to the clipboard and saved to `~/.skiller/skills/`.

## The library

`skiller index` sweeps **~190 dot-folders** in `$HOME` (every agent,
IDE, and AI-tool config dir — `.agents`, `.claude`, `.codex`, `.cursor`,
`.floyd*`, `.gemini*`, `.opencode`, … the full list is embedded in the
script) plus the codex marketplace staging cache at
`/Volumes/applebottom/live-caches/codex-marketplace-staging`.

Found `SKILL.md` files are deduplicated two ways: identical content
collapses to one entry (the staging cache holds ~80 copies of the same
marketplace), and same-name variants keep the newest as primary. The
index lives at `~/.skiller/index.json`; rebuild whenever you add skills.

Extra roots: `SKILLER_ROOTS=/path/one:/path/two skiller index`.

## Curated catalog (optional, recommended)

Drop a categorized skills index at **`~/.skiller/catalog.md`** (or
`skills-catalog.md` beside the script, or point `SKILLER_CATALOG` at it)
and SKILL-SCOUT browses it first, alongside the generated index. This is
the hook for the hand-curated categorized index of all skills.

## Engine

| setting  | source (first match wins)                             |
|----------|-------------------------------------------------------|
| model    | `SKILLER_MODEL` env → `glm-4.7-flash` (z.ai free tier) |
| api key  | `QGLM_API_KEY` env → `api_key` in `~/.qglm.yaml`      |
| endpoint | `QGLM_ENDPOINT` env → `endpoint` in `~/.qglm.yaml`    |
| thinking | `--think` flag / `SKILLER_THINKING=enabled` → `disabled` |

Deduction runs at temp 0.1; composition at temp 0.2 / 8k max tokens.

**Prompt caching + telemetry.** z.ai caches repeated prompt content
implicitly. The catalog is built as a stable
byte-identical prefix with a small query-relevant tail, so *different*
asks still hit the cache — measured 72-83% cached across distinct
queries. Every run ends with a telemetry line.
The telemetry prices runs with z.ai's real rate card — on the free
`glm-4.7-flash` default it reads `→ free tier ✦`; on paid models it
shows actual dollars and the cache discount (cached input is ~82% off,
e.g. $0.11 vs $0.60 per 1M on glm-4.5/4.6/4.7).
GLM-4.5's thinking phase is **disabled by default** — measured 55.6s →
2.3s per call on this endpoint with no quality loss on catalog matching
(a full skiller run dropped 166s → 33s). Use `--think` for genuinely
hard asks where deep reasoning is worth the wait.

## Install

Already installed globally via symlink:

```
/usr/local/bin/skiller -> /Volumes/Storage/CLITOOLS/SKILLER/skiller
```

Zero dependencies — Python 3 stdlib, `pbcopy`, and `fd` if present
(falls back to `find`). Colors respect `NO_COLOR` and disable when piped.

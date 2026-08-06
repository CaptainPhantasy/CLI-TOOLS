# Findings — CLITOOLS suite

## z.ai coding endpoint (api.z.ai/api/coding/paas/v4/chat/completions)
- Auth/key from ~/.qglm.yaml (`api_key`) or QGLM_API_KEY. Never print it.
- Model routing measured 2026-07-20: glm-4.5→itself, glm-4.5-air→glm-4.7
  (silent alias), glm-4.7-air→400 unknown model, glm-4.6/4.7/4.7-flash
  exist directly.
- `thinking: {"type":"enabled"|"disabled"}` — 55.6s vs 2.3s on a small
  glm-4.5 call; param silently ignored by non-thinking models (glm-4-32b).
- Streaming SSE returns `usage` (with prompt_tokens_details.cached_tokens)
  in final chunks even without stream_options.include_usage.
- Implicit prompt cache: prefix-based, model-scoped. glm-4-32b returns no
  prompt_tokens_details at all (no cache support). Flash caches (99.5% on
  identical prefix). Cached input ≈82-85% cheaper on paid models; pricing
  table 2026-07 embedded in both scripts as PRICING.

## Model bench (same typo'd ask, SKILLER pipeline)
| model | total | sources found | skill style |
|---|---|---|---|
| glm-4.5 | 33s | 4 (best retrieval) | 74-line tight agent-style |
| glm-4-32b | 34s | 2 | 209-line human tutorial |
| glm-4.5-air→4.7 | 44s | 2 | 101-line polished |
| glm-4.7-flash | 14s | 2 (1 marginal) | 119-line valid |
PROMPTER on flash: 20-23s, 10-11/11 layers, needs 16k output budget.

## Skill library layout
- SKILL.md files: YAML frontmatter name/description (desc sometimes `|`
  multi-line) or bare markdown; CP437 quirks none.
- Staging cache holds ~80 near-identical copies of the marketplace repo →
  content-hash dedup collapses 46,129 files to 4,996 variants / 3,401
  unique names.
- Curated categorized index (553 skills, 12 category docs + 00-HANDOFF)
  at /Volumes/applebottom/live-caches/codex-marketplace-staging/
  agent-skills-index; skill names as `## headings`; compressed to
  category→names (~11KB) for the scout catalog.

## TheDraw font rendering (hero art)
- TAAG fonts live at patorjk.com/software/taag/tdf-font-sets/tdf-chunk-NN.tdf.
- "Boner Purple" is in chunk 04; parser + renderer at scratchpad
  tdf_render.py (marker 55AA00FF, namelen+12B name, 4B reserved, type,
  spacing, blocksize, 94×uint16 charlist, CP437 glyphs, 0x0D newline,
  color fonts = char+attr pairs).
- Rendered heroes embedded in both scripts; PROMPTER wide hero is 102
  cols (compact fallback below that), SKILLER hero is 83 cols.

## Misc
- awk `length()` counts bytes not columns for box-drawing chars — use
  python for width checks.
- /usr/local/bin is writable and on PATH; his tools (qglm) live there.
- qglm is a Go binary; config surface: QGLM_API_KEY/ENDPOINT/MODEL,
  ~/.qglm.yaml.

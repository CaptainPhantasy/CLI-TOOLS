# Task Plan — CLITOOLS suite (PROMPTER + SKILLER)

## Goal
Build and maintain Douglas's framed, clipboard-first CLI tools in
/Volumes/Storage/CLITOOLS, each wrapping a GLM-backed LLM persona:
- PROMPTER (`prompter`): PROMPT-ENGINEER-PRIME engineers production prompts.
- SKILLER (`skiller`): SKILL-SCOUT/SKILL-SMITH turn vague asks into one
  complete SKILL.md from the local skill library.
Both: zero-dependency Python stdlib, pbcopy, framed TUI output, telemetry.

## Phases

### Phase 1: PROMPTER build — Status: complete
- Tool at PROMPTER/prompter, global symlink /usr/local/bin/prompter.
- Boner Purple TDF hero (wide 102-col + compact fallback), framed views,
  wizard for the 5 hard-gate inputs, history at ~/.prompter/bundles/.

### Phase 2: SKILLER build — Status: complete
- Tool at SKILLER/skiller, global symlink /usr/local/bin/skiller.
- Index: 199 roots (~190 home dot-dirs + marketplace staging), 46,129
  SKILL.md files → 3,401 unique skills at ~/.skiller/index.json.
- Curated categorized index read live from
  /Volumes/applebottom/live-caches/codex-marketplace-staging/agent-skills-index.
- History at ~/.skiller/skills/.

### Phase 3: Model tuning — Status: complete
- thinking:{type:disabled} default on both (55.6s → 2.3s per call).
- Model comparisons run: glm-4.5 / glm-4-32b / glm-4.5-air(→4.7) /
  glm-4.7-flash. Both tools default to glm-4.7-flash (free tier).
- Overrides: PROMPTER_MODEL / SKILLER_MODEL, *_THINKING=enabled, --think.

### Phase 4: Caching + telemetry — Status: complete
- z.ai implicit cache; SKILLER catalog restructured to stable prefix +
  query tail (66-83% cross-query hits; PROMPTER 95%+).
- Telemetry line on every run priced from real z.ai rate card (PRICING
  dict in both scripts); free models show "free tier ✦".
- Served-model alias display (glm-4.5-air → glm-4.7) in SKILLER footer.

### Phase 5: Planning adoption — Status: complete
- This file + findings.md + progress.md created 2026-07-20.

## Key decisions
- Provider config shared with qglm (~/.qglm.yaml) for key/endpoint only;
  each tool owns its model default (glm-4.7-flash).
- PROMPTER engineering-call output budget 16k (Flash verbosity truncated
  JSON at 8k).
- SKILLER catalog must stay byte-stable in its prefix — do not reintroduce
  per-query filtering ahead of the stable block (breaks caching).

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| GLM-4-32b narrates then stops before JSON | 1 | Auto-continuation nudges (up to 2) in prompter |
| Frame overflow at 74-col floor | 1 | clip_ansi + wrapped help descriptions |
| Chrome ext blocked patorjk.com | 1 | Rendered TheDraw TDF font directly (scratchpad tdf_render.py) |
| Per-query catalog broke cross-run caching | 1 | Stable catalog prefix + small relevance tail |
| Flash truncated prompter JSON at 8k out | 1 | max_tokens raised to 16k for engineering call |
| glm-4.5-air aliased to glm-4.7 by endpoint | 1 | Served-model shown in footer; documented |

## Next / open items
- None pending. Optional future: `skiller index` refresh after new skill
  installs; consider GLM-5 family bench when pricing settles.

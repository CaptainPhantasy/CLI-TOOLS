# Progress — CLITOOLS suite

## Session 2026-07-20 (initial build session; plan files created at end)

- Built PROMPTER (viewer → corrected to LLM-in-tool per Douglas), global
  `prompter`. Verified: live GLM runs, pbpaste byte-match, wizard via PTY,
  error paths, history saves.
- Built SKILLER, global `skiller`. Index: 199 roots, 46,129 files, 3,401
  unique, 25s build. Verified: vague typo'd asks → correct interpreted
  need, composed skills on clipboard byte-matched to history.
- Curated agent-skills-index wired in as scout catalog (live read).
- thinking disabled by default both tools (166s → 33s SKILLER full run).
- Model bench 4-way; defaults switched glm-4.5 → glm-4.5-air(→4.7) →
  final: glm-4.7-flash (free) on both after Flash benched well.
- Fixed Flash JSON truncation (16k output budget in prompter).
- Cache telemetry added both tools; SKILLER catalog made cache-stable
  (66-83% cross-query hits); telemetry priced from real rate card.
- Final verify: SKILLER 26s / 66% cached / free tier ✦; PROMPTER 20s /
  96% cached / free tier ✦. Both py_compile clean.

### Test evidence (latest good runs)
- SKILLER: "help me wrangle csv files fast" → 26s, engine glm-4.7-flash,
  32,426 in / 21,352 cached / 2,449 out.
- PROMPTER: "triages bug reports by severity" → 20s, 10/11 layers,
  3,114 in / 2,998 cached (96%) / 1,821 out.

### Artifacts
- /Volumes/Storage/CLITOOLS/{PROMPTER,SKILLER}/{tool,README.md}
- /usr/local/bin/{prompter,skiller} symlinks
- ~/.prompter/bundles/, ~/.skiller/{index.json,skills/}
- Scratchpad (session-scoped, not durable): tdf_render.py, chunk04.tdf

# PROMPTER

```
█▀▀▀▀▀▀▀▀▄   █▀▀▀▀▀▀▀▀▄    ▄▀▀▀▀▀▀▀▄   █▀▀▀▄ ▄▀▀▀█  █▀▀▀▀▀▀▀▀▄   █▀▀▀▀▀▀▀▀▀█   ▄▀▀▀▀▀▀▀▀█  █▀▀▀▀▀▀▀▀▄
█  ▄▄▄▄   █  █  ▄▄▄▄   █  █   ▄▄▄   █  █    ▀    █  █  ▄▄▄▄   █  █▄▄▄██▄▄▄▄█  █  █▄▄▄▄▄▄█  █  ▄▄▄▄   █
█  █▄▄▄▀  █  █  █▄▄▄▀  █  █  █   █  █  █  █▄ ▄█  █  █  █▄▄▄▀  █     █  █      █  █▄▄▄▄▄    █  █▄▄▄▀  █
▀        ▄   ▀        ▄   ▀  ▀   ▄  ▄  ▀  █ ▀ █  ▄  ▀        ▄      ▀  █      ▀       █    ▀        ▄
█  █▀▀▀▀▀    █  █▀▀▀▄  █  █  █   █  █  █  █   █  █  █  █▀▀▀▀▀       █  █      █  █▀▀▀▀▀    █  █▀▀▀▄  █
█  █         █  █   █  █  █   ▀▀▀   █  █  █   █  █  █  █            █  █      █  █▀▀▀▀▀▀█  █  █   █  █
█▄▄█         █▄▄█   █▄▄█   ▀▄▄▄▄▄▄▄▀   █▄▄█   █▄▄█  █▄▄█            █▄▄█       ▀▄▄▄▄▄▄▄▄█  █▄▄█   █▄▄█
```

**Your resident prompt engineer.** Describe the prompt you need;
PROMPT-ENGINEER-PRIME (the meta-agent from the Prompt Engineering Research
bundle, running on GLM-4) engineers a production-grade prompt and the
finished system prompt lands on your clipboard, ready to paste with ⌘V.

Hero art: "prompter" in TheDraw font **Boner Purple**
(patorjk.com/software/taag), with a compact fallback for terminals
narrower than 102 columns.

## Usage

```
prompter "a prompt that summarizes legal contracts"   commission a prompt
prompter                                              fully interactive wizard
prompter --quick "…"                                  no wizard; defaults for unset fields
prompter -a AUDIENCE -s SOURCES -c CONSTRAINTS -o SHAPE "…"
prompter --copy json|prompt|none                      what lands on the clipboard
prompter info                                         engine, config, 11-layer stack
prompter show|copy|raw <system|template|params|bundle>  inspect the meta bundle
prompter --help                                       framed help
```

The wizard collects the five inputs PROMPT-ENGINEER-PRIME hard-gates on
(task, audience, sources, constraints, output shape); Enter accepts an
explicit sensible default for anything but the task.

## What you get back

A versioned **prompt bundle**: system prompt, user-message template, JSON
output schema, few-shot examples (incl. adversarial), grounding plan,
abstention rules, self-critique criteria, and an eval plan.

- The engineered **system prompt** is framed on screen and copied to the
  clipboard (default).
- The **full bundle JSON** is auto-saved to `~/.prompter/bundles/` and can
  be copied instead with `--copy json`.
- If the engineer decides your request is under-specified, its input-gate
  response is shown framed so you can re-run with the missing details.

## Engine

Shares its API key and endpoint with `qglm`; the model is prompter's own:

| setting  | source (first match wins)                            |
|----------|------------------------------------------------------|
| api key  | `QGLM_API_KEY` env → `api_key` in `~/.qglm.yaml`     |
| endpoint | `QGLM_ENDPOINT` env → `endpoint` in `~/.qglm.yaml`   |
| model    | `PROMPTER_MODEL` env → `glm-4.7-flash` (z.ai free tier) |
| thinking | `PROMPTER_THINKING=enabled` → `disabled`             |

Sampling for the engineering call follows the research bundle's own
recommendation (temp 0.1 · top_p 0.9), with a 16k output budget for
verbose models. Small-model
narration stalls are handled by automatic continuation (up to 2 nudges)
until the JSON bundle arrives.

Every run ends with a token/cache telemetry line priced from z.ai's
real rate card. On the free `glm-4.7-flash` default it reads
`→ free tier ✦`; the 13.6k-char meta-prompt still caches (measured
96%+ hits across different tasks), which keeps runs fast. On paid
models the line shows actual dollars plus the cache discount; models
without cache support (e.g. `glm-4-32b`) read `cache n/a`.

## Meta-prompt source resolution

1. `$PROMPTER_SOURCE` (env override)
2. iCloud research copy:
   `~/Library/Mobile Documents/com~apple~CloudDocs/Floyd Docs/Research/Prompt Engineering Research/prompt-engineering-agent-prompt.json`
3. Vendored snapshot beside the script: `prompt-source.json`

## Install

Already installed globally via symlink:

```
/usr/local/bin/prompter -> /Volumes/Storage/CLITOOLS/PROMPTER/prompter
```

Zero dependencies — Python 3 stdlib plus `pbcopy`. Colors respect
`NO_COLOR` and are disabled automatically when output is piped.

# CLITOOLS verification receipt

Verified at: 2026-08-01T23:50:00-04:00

## Outcome

The verification is accepted, but the requested tools are not all working end to end. All four launch locally. PROMPTER, SKILLER, and QGLM fail their core Z.AI call with the same authentication rejection. LGCY's terminal UI, tests, typecheck, and build pass, but its default OpenCode route lacks broker/proxy credentials and its alternate OpenAI route is rejected by the provider.

## A) Requested items checklist

- PROMPTER: startup and local info verified; normal model operation blocked by invalid shared Z.AI credential.
- SKILLER: startup, local index, and local info verified; normal model operation blocked by invalid shared Z.AI credential.
- QGLM: installed command and version verified; normal model operation blocked by invalid shared Z.AI credential.
- LGCY: source, compiled binary, automated suite, and real terminal lifecycle verified; model operation blocked by missing OpenCode credentials and rejected OpenAI credentials; global `lgcy` command is absent.

## B) Per-item evidence ledger

| Tool | Exact action | Direct evidence | Verification result | Readiness state |
|---|---|---|---|---|
| PROMPTER | Ran `prompter info`; ran a live quick commission with `--copy none` | `info` exit 0 reported configured key and endpoint; live call exited 1 with HTTP 401 and provider code `1000`, `Authentication Failed` | Local command path passes; core model path fails | `BLOCKED_BY_INVALID_ZAI_CREDENTIAL` |
| SKILLER | Ran `skiller info`; ran a live no-copy, three-line-preview skill request | `info` exit 0 reported 3,401 indexed skills and configured key; live call exited 1 with HTTP 401 and provider code `1000`, `Authentication Failed` | Local catalog path passes; core model path fails | `BLOCKED_BY_INVALID_ZAI_CREDENTIAL` |
| QGLM | Resolved command; ran `qglm --version`; ran a live no-search, non-stream completion | Command resolves to `/Users/douglas/.local/bin/qglm`; version exits 0; live call exits 1 with HTTP 401 and provider code `1000`, `Authentication Failed` | Startup passes; core model path fails | `BLOCKED_BY_INVALID_ZAI_CREDENTIAL` |
| LGCY | Ran source/existing/fresh-binary help, non-TTY startup, 289 tests, strict typecheck, temp compile, true-TTY `/help` and `/exit`, default OpenCode relay, alternate OpenAI relay | Help/startup/TTY/tests/typecheck/build exit 0; OpenCode relay exits 1 because broker token cannot be read; OpenAI relay reaches provider and exits 1 with HTTP 401; `command -v lgcy` reports missing | Runtime and local quality gates pass; all tested model paths fail; global launcher absent | `BLOCKED_BY_MISSING_AND_INVALID_CREDENTIALS` |

## C) Verification receipts

- `bun test` in `/Volumes/Storage/CLITOOLS/LGCY`: exit 0; 289 pass, 0 fail, 695 expectations, 21 files.
- `bunx tsc --noEmit` in `/Volumes/Storage/CLITOOLS/LGCY`: exit 0; no diagnostics.
- `bun build --compile --outfile /private/tmp/lgcy-verification-20260801 src/app/main.ts`: exit 0; fresh binary created and then executed with `--help`, exit 0.
- LGCY true-TTY smoke: banner rendered; `/help` listed commands; `/exit` restored cursor and alternate-screen state; process exit 0.
- Sanitized config comparison: QGLM repository `.env` and user `~/.qglm.yaml` both contain a key and endpoint; the two keys match and the two endpoints match. No secret value was emitted.
- Live network boundary: restricted-lane DNS/connect failures were rerun with approved live access. Provider results above are live provider responses, not sandbox artifacts.
- LGCY auth readiness: default local broker unavailable, broker token file missing, `OPENCODE_PROXY_AUTH` missing, `OPENAI_API_KEY` present, `ANTHROPIC_API_KEY` missing. No values were emitted.
- Environment Ecosystem drift: its QGLM record still points to missing `/usr/local/bin/qglm`, while the live shell resolves the working launcher at `/Users/douglas/.local/bin/qglm`.
- No tool source code was edited during this verification. LGCY's pre-existing dirty tree was preserved.
- Independent full-scope critic reproduced command resolution, local startup, all 289 LGCY tests, strict typecheck, a fresh temporary build, and the three live Z.AI 401 results; final verdict: `PASS`.

## D) Completeness matrix

| Task | Owner | Branch | State | Evidence | Next action |
|---|---|---|---|---|---|
| Verify PROMPTER | root | current workspace | BLOCKED_BY_INVALID_ZAI_CREDENTIAL | Local info exit 0; live commission HTTP 401 | Replace or refresh the shared Z.AI credential, then rerun the commission |
| Verify SKILLER | root | current workspace | BLOCKED_BY_INVALID_ZAI_CREDENTIAL | Local info/index exit 0; live generation HTTP 401 | Replace or refresh the shared Z.AI credential, then rerun generation |
| Verify QGLM | root | current workspace | BLOCKED_BY_INVALID_ZAI_CREDENTIAL | Launcher/version exit 0; live completion HTTP 401 | Replace or refresh the shared Z.AI credential; update the stale Environment Ecosystem path |
| Verify LGCY | root | current workspace | BLOCKED_BY_MISSING_AND_INVALID_CREDENTIALS | 289 tests, typecheck, build, and TTY pass; both provider paths fail | Identify/provision the approved OpenCode proxy or broker source; repair OpenAI credential; install global launcher only if explicitly requested |
| Verification report | root | current workspace | ACCEPTED | Every requested tool has a direct evidence row; full-scope critic `VERDICT: PASS` | Use this receipt as the current source of truth |

## Technical footguns

**Footgun:** The same rejected credential exists in two QGLM config locations and is consumed by three tools. | **Consequence:** updating only one copy may appear fixed in one working directory and remain broken elsewhere. | **Mitigation:** choose one authoritative secret source, remove the duplicate after explicit approval, then rerun PROMPTER, SKILLER, and QGLM from their normal launch locations.

**Footgun:** LGCY's default provider requires two credential layers, but neither current source is available. | **Consequence:** adding only a model or only one credential still leaves the default route unusable. | **Mitigation:** confirm the approved proxy/broker architecture, provision both required request-time credentials, set a tested default model, and run one true-TTY completion.

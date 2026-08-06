# CLITOOLS MCP Apps

Three of the CLI tools also ship as **MCP Apps** servers. Each serves an
interactive HTML view that renders inline in a compliant host.

**Protocol versions implemented (dual-era):**

| layer | version | notes |
|---|---|---|
| core protocol | **2026-07-28** | current spec: stateless, no `initialize`, `server/discover` required |
| core protocol | 2026-01-26 / 2025-11-25 / 2025-06-18 | legacy handshake, still what installed hosts negotiate |
| extension | **SEP-1865** MCP Apps (`io.modelcontextprotocol/ui`) | Stable 2026-01-26; draft additions included |

The era is detected **per request**, so one server satisfies both without
configuration. This matters concretely: the MCP hosts installed on this
machine still negotiate `2025-11-25`, while `2026-07-28` is the current
core spec. A modern-only server would be unusable today; a legacy-only
server is already obsolete.

| server | view | what it adds over the CLI |
|---|---|---|
| `keyring-app` | `ui://keyring/inventory` | Reveals secret values **to you** while the model still only sees fingerprints |
| `salvager-app` | `ui://salvager/triage` | Multi-select repos, bulk commit/push, reports back to model context |
| `recaller-app` | `ui://recaller/palette` | Live-filtering command palette over 2,300+ recovered commands |

## Install

```
./register-mcp            # dry run: show what would change
./register-mcp --apply    # write config (backs up each file first)
./register-mcp --remove   # unregister
```

Registers with jcode, Claude Desktop, and Claude Code — whichever are
present. Idempotent. Restart the host afterwards.

## The KEYRING case, in detail

This is the one where the extension removes a real constraint rather than
adding polish.

The CLI's guarantee is that secret values never reach the model. The cost
is that they never reach *you* either: you get `bc9…` and a fingerprint,
and then you go open the file yourself.

MCP Apps splits those two audiences, because the sandboxed iframe is not
the model's context window:

```
scan_credentials   visibility: [model, app]   → fingerprints only
reveal_secret      visibility: [app]          → real value, app-only
```

Per SEP-1865 the host **MUST NOT** list an app-only tool to the model and
**MUST** reject model-originated calls to it. So the boundary is enforced
by the protocol, not by string masking. The result is strictly stronger
than the CLI: previously the model received redacted text, now it cannot
invoke the code path at all.

`reveal_secret` also re-reads the value from disk on each call rather than
caching it from the scan, so no plaintext lingers in memory where it could
later be serialized into a log or transcript.

**Verified:** with 33 real secret strings from a known credentials file,
zero appear anywhere in the model-visible surface (`tools/list`,
`scan_credentials` output, and the view HTML).

## Safety posture per server

**keyring** — read-only except `tighten_permissions`, which only ever
*narrows* access (chmod 600) and refuses any path where no credential was
detected.

**salvager** — the CLI is strictly read-only; the app adds exactly two
writes, `commit_repo` and `push_repo`, each acting on one named repo.
There is no "rescue everything" tool: the view loops over what you
checked, so every write is explicit. Nothing force-pushes, resets,
rebases, or discards. The worst case is an unwanted commit, which is
itself recoverable.

**recaller** — never executes a recovered command. `Send to chat` hands
the text to the model; running it stays a separate decision under your
host's existing approval flow. Recovering and running are different acts,
and conflating them is how you rerun an `rm -rf` from six months ago.

## What 2026-07-28 changed

The July 2026 core revision is a larger break than a normal version bump:

- **MCP is now stateless.** The `initialize` / `notifications/initialized`
  handshake is gone. Every request carries its own protocol version and
  client capabilities in `_meta` (SEP-2575).
- **`server/discover` is mandatory.** Servers MUST implement it; it is
  also the stdio probe a dual-era client uses to detect which era a server
  speaks.
- **Every result carries `resultType`** (`"complete"` or
  `"input_required"` for multi round-trip requests, SEP-2322).
- **List and read results MUST carry caching hints** — `ttlMs` and
  `cacheScope` (SEP-2549). These servers use a 5-minute TTL with
  `cacheScope: "private"`, since the data is user-specific.
- **Error codes were renumbered.** Resource-not-found moved from `-32002`
  to `-32602`; `UnsupportedProtocolVersion` is `-32022`;
  `MissingRequiredClientCapability` is `-32021`.
- **`tools/list` SHOULD be deterministically ordered** so clients can
  cache and LLM prompt caches hit.
- **Sampling, Roots, and Logging are deprecated.** These servers use none
  of them.

All of the above are implemented and covered by the test suite.

## Design notes

**Zero dependencies, still.** `lib/mcpkit.py` is a ~200-line stdio MCP
server and `lib/uikit.py` is the shared view runtime. No SDK, no
`node_modules`, no build step — consistent with the rest of the suite.

**No CDN in the views.** The default CSP for a UI resource is
`default-src 'none'` with `script-src 'self' 'unsafe-inline'`. Loading
React from a CDN would require widening CSP, which is a bad trade for
rendering a table. So: vanilla JS, inline, CSP left at its restrictive
default. All three views declare `csp: {}` — no external origins at all.

**Graceful degradation.** Servers check the host's
`io.modelcontextprotocol/ui` capability during `initialize` and omit
`_meta.ui.resourceUri` when it is absent. Every tool returns a meaningful
text block regardless, so text-only hosts get a real answer.

## Testing

Two harnesses, because they catch different failures:

```
./mcp-probe KEYRING/keyring-app                    # speak real JSON-RPC
./mcp-probe --no-ui SALVAGER/salvager-app          # simulate text-only host
node view-harness.mjs view.html fixture.json "expected text"
```

`mcp-probe` drives the server over actual stdio: framing, capability
negotiation, `ui://` scheme, mimeType, and HTML5 validity. `view-harness`
runs the view's JavaScript against a fake DOM and a host that performs the
real `ui/initialize` handshake **and a `ui/resource-teardown` round trip**,
then asserts content actually rendered — a syntax check alone would miss a
mistyped field silently rendering an empty box.

`./test-mcp-apps` runs 83 checks across both protocol eras: modern
stateless requests with no handshake, legacy handshake requests, version
negotiation errors, the SEP-1865 security rules, and live view rendering.

Both harnesses caught real bugs during development, including one where a
view stopped rendering entirely because the fake DOM kept only the last
`message` listener while the runtime registers several.

## Known limits

- HTML only; external URLs and remote DOM are deferred by the spec.
- Host support is uneven and the `domain` field is explicitly
  host-specific, so portability across Claude Desktop and ChatGPT is
  thinner than it looks.
- `ui/update-model-context` is a prompt-injection surface **by design**:
  a view can write into model context, and hosts only *MAY* show those
  updates to the user. Only run app servers you trust. These are yours.

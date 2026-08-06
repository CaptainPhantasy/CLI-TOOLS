"""mcpkit — a tiny, zero-dependency, DUAL-ERA MCP server over stdio.

Supports both protocol eras, because the ecosystem is mid-migration:

  * MODERN  (2026-07-28): stateless. No initialize handshake. Every request
            carries its protocol version and client capabilities in `_meta`.
            Servers MUST implement `server/discover`. List/read results MUST
            carry caching hints (`ttlMs`, `cacheScope`) and every result
            carries `resultType`.
  * LEGACY  (2026-01-26 and earlier): the `initialize` handshake establishes
            session state, which is then reused for later requests.

Why both: as of this writing the locally installed hosts still negotiate
`2025-11-25`, while `2026-07-28` is the current core spec. A modern-only
server would be unusable today; a legacy-only server is already obsolete.
The era is detected per request, so one server satisfies both without any
configuration.

Also implements the MCP Apps extension (SEP-1865):
  * ui:// resources with mimeType text/html;profile=mcp-app
  * tool linkage via _meta.ui.resourceUri
  * visibility ["app"] to hide plumbing tools from the model
  * CSP declaration on BOTH resources/list and resources/read (the draft
    requires hosts to check both, content-item taking precedence)

Deliberately NOT implemented: sampling (deprecated in 2026-07-28), prompts,
subscriptions, tasks. None of these apps need them, and a smaller surface
is a smaller attack surface.

Protocol notes that bit during implementation:
  * stdout is the transport. Diagnostics go to stderr or they corrupt it.
  * Notifications (no id) MUST NOT be answered.
  * A modern request missing protocolVersion/clientCapabilities is
    malformed and MUST be rejected with -32602.
"""

import json
import sys
import traceback

# Versions this server speaks, newest first. Advertised by server/discover
# and used to validate the per-request version in modern mode.
SUPPORTED_VERSIONS = ["2026-07-28", "2026-01-26", "2025-11-25", "2025-06-18"]
MODERN_VERSIONS = {"2026-07-28"}
LATEST_VERSION = SUPPORTED_VERSIONS[0]

UI_EXTENSION = "io.modelcontextprotocol/ui"
UI_MIME = "text/html;profile=mcp-app"

META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CLIENT_INFO = "io.modelcontextprotocol/clientInfo"
META_CLIENT_CAPS = "io.modelcontextprotocol/clientCapabilities"
META_SERVER_INFO = "io.modelcontextprotocol/serverInfo"

# Error codes. -32020..-32099 is reserved for the MCP spec; the codes below
# are the ones allocated in 2026-07-28.
ERR_INVALID_PARAMS = -32602
ERR_METHOD_NOT_FOUND = -32601
ERR_INTERNAL = -32603
ERR_MISSING_CAPABILITY = -32021
ERR_UNSUPPORTED_VERSION = -32022

# Caching hints. These are cheap local scans, but they are not free: a
# short TTL keeps a host from re-running a filesystem sweep on every
# keystroke, while staying short enough that the data is never stale in a
# way a human would notice.
TTL_LIST_MS = 300_000      # tool/resource lists change only when code does
TTL_READ_MS = 300_000      # view HTML is static for the life of the process


def log(*args):
    """Never write diagnostics to stdout: it is the JSON-RPC transport."""
    print(*args, file=sys.stderr, flush=True)


class JsonRpcError(Exception):
    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class Server:
    def __init__(self, name, version="1.0.0", instructions=""):
        self.name = name
        self.version = version
        self.instructions = instructions
        self._tools = {}
        self._resources = {}
        # Legacy sessions set this once at initialize; modern requests
        # carry capabilities per-request, so it is recomputed each time.
        self._legacy_ui_enabled = False
        self.ui_enabled = False

    # ------------------------------------------------------------ register

    def resource(self, uri, name, html, description="", csp=None,
                 prefers_border=True):
        """Register a ui:// view. Content is served via resources/read."""
        meta = {"csp": csp or {}, "prefersBorder": prefers_border}
        self._resources[uri] = {
            "uri": uri,
            "name": name,
            "description": description,
            "mimeType": UI_MIME,
            "_meta": {"ui": meta},
            "_html": html,
        }

    def tool(self, name, description, schema=None, resource_uri=None,
             visibility=None):
        """Decorator registering a tool. `visibility` per SEP-1865:
        ["app"] hides it from the model entirely."""
        def deco(fn):
            self._tools[name] = {
                "name": name,
                "description": description,
                "inputSchema": schema or {"type": "object", "properties": {}},
                "_fn": fn,
                "_resource_uri": resource_uri,
                "_visibility": visibility or ["model", "app"],
            }
            return fn
        return deco

    # ------------------------------------------------------------ helpers

    def _server_info_meta(self):
        return {META_SERVER_INFO: {"name": self.name, "version": self.version}}

    def _cacheable(self, result, ttl_ms):
        """Attach the caching hints 2026-07-28 requires on list/read results.

        Harmless to legacy clients, which simply ignore unknown fields."""
        result["ttlMs"] = ttl_ms
        result["cacheScope"] = "private"   # this data is user-specific
        return result

    def _tool_descriptor(self, entry, ui_enabled):
        d = {
            "name": entry["name"],
            "description": entry["description"],
            "inputSchema": entry["inputSchema"],
        }
        ui = {}
        # Only advertise a view when the host actually supports MCP Apps.
        if entry["_resource_uri"] and ui_enabled:
            ui["resourceUri"] = entry["_resource_uri"]
        if entry["_visibility"] != ["model", "app"]:
            ui["visibility"] = entry["_visibility"]
        if ui:
            d["_meta"] = {"ui": ui}
        return d

    @staticmethod
    def _ui_from_caps(caps):
        ext = ((caps or {}).get("extensions") or {}).get(UI_EXTENSION)
        return bool(ext and UI_MIME in (ext.get("mimeTypes") or []))

    def _negotiate(self, params):
        """Determine era + UI support for THIS request.

        Modern requests carry version and capabilities in _meta. Legacy
        requests rely on state established by initialize."""
        meta = (params or {}).get("_meta") or {}
        version = meta.get(META_VERSION)
        if version is None:
            # No per-request version: legacy era, use session state.
            return False, self._legacy_ui_enabled
        if version not in SUPPORTED_VERSIONS:
            raise JsonRpcError(
                ERR_UNSUPPORTED_VERSION, "Unsupported protocol version",
                {"supported": SUPPORTED_VERSIONS, "requested": version})
        if version in MODERN_VERSIONS:
            # clientCapabilities is REQUIRED on modern requests.
            if META_CLIENT_CAPS not in meta:
                raise JsonRpcError(
                    ERR_INVALID_PARAMS,
                    f"missing required _meta field: {META_CLIENT_CAPS}")
            return True, self._ui_from_caps(meta.get(META_CLIENT_CAPS))
        # A legacy version named explicitly in _meta: honour it, but the
        # capabilities still come from the handshake.
        return False, self._legacy_ui_enabled

    # ------------------------------------------------------------ dispatch

    def _handle(self, method, params):
        modern, ui_enabled = self._negotiate(params)
        self.ui_enabled = ui_enabled

        if method == "server/discover":
            # REQUIRED in 2026-07-28. Also the stdio probe legacy-capable
            # clients use to detect a modern server.
            return self._cacheable({
                "supportedVersions": SUPPORTED_VERSIONS,
                "capabilities": {
                    "tools": {}, "resources": {},
                    "extensions": {UI_EXTENSION: {"mimeTypes": [UI_MIME]}},
                },
                "instructions": self.instructions,
            }, TTL_LIST_MS)

        if method == "initialize":
            # Legacy handshake. Retained because installed hosts still use
            # it; a modern-only server would be unusable on this machine.
            caps = (params.get("capabilities") or {})
            self._legacy_ui_enabled = self._ui_from_caps(caps)
            self.ui_enabled = self._legacy_ui_enabled
            requested = params.get("protocolVersion") or LATEST_VERSION
            # Echo the client's version when we speak it, else our newest
            # legacy version, so old hosts do not see a modern version they
            # cannot parse.
            agreed = requested if requested in SUPPORTED_VERSIONS else "2025-11-25"
            log(f"[{self.name}] initialize (legacy) v={agreed} "
                f"ui={'yes' if self.ui_enabled else 'no'}")
            return {
                "protocolVersion": agreed,
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": self.name, "version": self.version},
                "instructions": self.instructions,
            }

        if method == "tools/list":
            # Deterministic order: 2026-07-28 asks for this so clients can
            # cache and so LLM prompt caches hit.
            tools = [self._tool_descriptor(e, ui_enabled)
                     for e in sorted(self._tools.values(), key=lambda x: x["name"])
                     if "model" in e["_visibility"]]
            return self._cacheable({"tools": tools}, TTL_LIST_MS)

        if method == "resources/list":
            out = []
            for r in sorted(self._resources.values(), key=lambda x: x["uri"]):
                out.append({
                    "uri": r["uri"], "name": r["name"],
                    "description": r["description"], "mimeType": r["mimeType"],
                    # Listing-level _meta.ui lets hosts review the security
                    # configuration at connection time without a read.
                    "_meta": r["_meta"],
                })
            return self._cacheable({"resources": out}, TTL_LIST_MS)

        if method == "resources/read":
            uri = params.get("uri")
            r = self._resources.get(uri)
            if not r:
                # 2026-07-28 changed this from -32002 to -32602.
                raise JsonRpcError(ERR_INVALID_PARAMS, f"unknown resource: {uri}")
            return self._cacheable({"contents": [{
                "uri": uri,
                "mimeType": UI_MIME,
                "text": r["_html"],
                # Content-item _meta.ui takes precedence over the listing.
                "_meta": r["_meta"],
            }]}, TTL_READ_MS)

        if method == "tools/call":
            name = params.get("name")
            entry = self._tools.get(name)
            if not entry:
                raise JsonRpcError(ERR_INVALID_PARAMS, f"unknown tool: {name}")
            args = params.get("arguments") or {}
            result = entry["_fn"](**args) if args else entry["_fn"]()
            return normalize_tool_result(result)

        if method == "ping":
            # Removed in 2026-07-28 but harmless to keep for legacy hosts.
            return {}

        raise JsonRpcError(ERR_METHOD_NOT_FOUND, f"method not found: {method}")

    def serve(self):
        """Read framed JSON-RPC from stdin until EOF."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            req_id = msg.get("id")
            method = msg.get("method", "")
            params = msg.get("params") or {}
            # Notifications carry no id and MUST NOT be answered.
            if req_id is None:
                continue
            try:
                result = self._handle(method, params)
                # Every 2026-07-28 result carries resultType; legacy
                # clients ignore the extra field.
                result.setdefault("resultType", "complete")
                meta = result.setdefault("_meta", {})
                meta.update(self._server_info_meta())
                out = {"jsonrpc": "2.0", "id": req_id, "result": result}
            except JsonRpcError as e:
                err = {"code": e.code, "message": e.message}
                if e.data is not None:
                    err["data"] = e.data
                out = {"jsonrpc": "2.0", "id": req_id, "error": err}
            except Exception as e:  # noqa: BLE001 - report, never die
                log(f"[{self.name}] error in {method}: {e}")
                log(traceback.format_exc())
                out = {"jsonrpc": "2.0", "id": req_id,
                       "error": {"code": ERR_INTERNAL, "message": str(e)}}
            sys.stdout.write(json.dumps(out) + "\n")
            sys.stdout.flush()


def normalize_tool_result(result):
    """Accept (text, structured) or plain text and produce CallToolResult.

    Every tool MUST return a meaningful content array even when a UI is
    present, so text-only hosts still get a real answer (SEP-1865
    graceful degradation)."""
    if isinstance(result, tuple):
        text, structured = result
    else:
        text, structured = result, None
    out = {"content": [{"type": "text", "text": text}]}
    if structured is not None:
        out["structuredContent"] = structured
    return out

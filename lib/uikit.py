"""uikit — shared HTML/JS runtime for the CLITOOLS MCP Apps views.

Three views need identical plumbing: the ui/initialize handshake, host
theming, auto-resize, and calling back into the server. Written once here
so a protocol fix lands in all three.

The JS deliberately uses no framework and no CDN. The default CSP for a
UI resource is `default-src 'none'` with `script-src 'self' 'unsafe-inline'`,
so an external React bundle simply would not load without widening CSP.
Widening CSP to render a table is a bad trade, so: vanilla, inline, and
the CSP stays at its restrictive default.
"""

# The handshake, per SEP-1865 lifecycle:
#   View -> Host : ui/initialize          (declares appCapabilities)
#   Host -> View : McpUiInitializeResult  (hostContext: theme, styles, size)
#   View -> Host : ui/notifications/initialized
#   Host -> View : ui/notifications/tool-input     (complete arguments)
#   Host -> View : ui/notifications/tool-result    (CallToolResult)
RUNTIME_JS = r"""
const MCP = (() => {
  let nextId = 1;
  let HOST_CAPS = {};
  const pending = new Map();
  const notifyHandlers = new Map();

  // MCP Apps stable (2026-08) display-mode contract state.
  // DISPLAY_MODE is the host-applied mode (source of truth), never the last
  // requested one. HOST_MODES is the host-advertised availableDisplayModes;
  // empty array means "not confirmed yet" — controls stay hidden.
  let DISPLAY_MODE = 'inline';
  let HOST_MODES = [];

  window.addEventListener('message', (event) => {
    const msg = event.data;
    if (!msg || msg.jsonrpc !== '2.0') return;
    if (msg.id !== undefined && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(msg.error.message || 'rpc error'));
      else resolve(msg.result);
      return;
    }
    if (msg.method) {
      const hs = notifyHandlers.get(msg.method) || [];
      hs.forEach((h) => { try { h(msg.params); } catch (e) { console.error(e); } });
    }
  });

  function request(method, params) {
    const id = nextId++;
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
      window.parent.postMessage({ jsonrpc: '2.0', id, method, params }, '*');
      setTimeout(() => {
        if (pending.has(id)) { pending.delete(id); reject(new Error('timeout: ' + method)); }
      }, 30000);
    });
  }
  function notify(method, params) {
    window.parent.postMessage({ jsonrpc: '2.0', method, params }, '*');
  }
  function on(method, handler) {
    if (!notifyHandlers.has(method)) notifyHandlers.set(method, []);
    notifyHandlers.get(method).push(handler);
  }

  // Host-provided CSS variables. Views declare their own fallbacks, so a
  // host that sends no styles still renders correctly.
  function applyTheme(hostContext) {
    const vars = (hostContext && hostContext.styles && hostContext.styles.variables) || {};
    const root = document.documentElement;
    for (const [k, v] of Object.entries(vars)) {
      if (v !== undefined && v !== null) root.style.setProperty(k, v);
    }
    if (hostContext && hostContext.theme) {
      root.setAttribute('data-theme', hostContext.theme);
      root.style.colorScheme = hostContext.theme;
    }
    const fonts = hostContext && hostContext.styles && hostContext.styles.css
      && hostContext.styles.css.fonts;
    if (fonts) {
      const s = document.createElement('style');
      s.textContent = fonts;
      document.head.appendChild(s);
    }
  }

  // Hosts using flexible sizing need size-changed to lay us out at all.
  function autoResize() {
    let lastH = 0, lastW = 0;
    const send = () => {
      const h = Math.ceil(document.documentElement.scrollHeight);
      const w = Math.ceil(document.documentElement.scrollWidth);
      if (h !== lastH || w !== lastW) {
        lastH = h; lastW = w;
        notify('ui/notifications/size-changed', { width: w, height: h });
      }
    };
    new ResizeObserver(send).observe(document.documentElement);
    setTimeout(send, 50);
  }

  async function init(opts) {
    const res = await request('ui/initialize', {
      protocolVersion: '2026-01-26',
      appCapabilities: {
        availableDisplayModes: (opts && opts.displayModes) || ['inline', 'fullscreen'],
      },
      clientInfo: { name: (opts && opts.name) || 'clitools-view', version: '1.0.0' },
    });
    const hostContext = (res && res.hostContext) || {};
    HOST_CAPS = (res && res.hostCapabilities) || {};
    // Stable contract: read the host's applied mode + advertised modes.
    if (hostContext.displayMode) DISPLAY_MODE = hostContext.displayMode;
    if (Array.isArray(hostContext.availableDisplayModes)) {
      HOST_MODES = hostContext.availableDisplayModes;
    }
    applyTheme(hostContext);
    notify('ui/notifications/initialized', {});
    autoResize();
    on('ui/notifications/host-context-changed', (p) => {
      applyTheme(p || {});
      // Host may move us (or change what it offers) at any time.
      if (p && p.displayMode) DISPLAY_MODE = p.displayMode;
      if (p && Array.isArray(p.availableDisplayModes)) {
        HOST_MODES = p.availableDisplayModes;
      }
    });

    // The host sends this before tearing us down and SHOULD wait for the
    // reply, which is the only chance a view gets to flush state. Always
    // answer, or a host that waits will stall.
    respondTo('ui/resource-teardown', () => {
      try { (opts && opts.onTeardown || (() => {}))(); } catch (e) { console.error(e); }
      return {};
    });

    return { hostContext, hostCapabilities: HOST_CAPS };
  }

  // Requests flow Host -> View too; without a reply the host hangs.
  function respondTo(method, handler) {
    on(method, () => {});
    window.addEventListener('message', (event) => {
      const msg = event.data;
      if (!msg || msg.jsonrpc !== '2.0' || msg.method !== method) return;
      if (msg.id === undefined) return;
      let result = {};
      try { result = handler(msg.params) || {}; } catch (e) { console.error(e); }
      window.parent.postMessage({ jsonrpc: '2.0', id: msg.id, result }, '*');
    });
  }

  const callTool = (name, args) =>
    request('tools/call', { name, arguments: args || {} });
  const openLink = (url) => request('ui/open-link', { url });
  const sendMessage = (text) =>
    request('ui/message', { role: 'user', content: { type: 'text', text } });
  const updateContext = (text, structured) =>
    request('ui/update-model-context', {
      content: [{ type: 'text', text }],
      structuredContent: structured,
    });
  // Views MAY ask to be torn down (e.g. a "Done" button).
  const requestTeardown = () => notify('ui/notifications/request-teardown', {});
  // Host capability probe: apps SHOULD check before using an optional feature.
  const hostSupports = (name) => Boolean(HOST_CAPS && HOST_CAPS[name]);

  // --- Display modes (MCP Apps stable, August 2026) ---------------------
  // Current host-applied mode. Read THIS, not the last requested mode.
  const getDisplayMode = () => DISPLAY_MODE;
  // Modes the host advertised. [] = not confirmed; hide mode controls then.
  const getAvailableDisplayModes = () => HOST_MODES.slice();
  // Ask the host to move us. Awaits the host's decision and records the
  // APPLIED mode as truth (the host may keep or substitute a mode).
  // Returns the applied mode string.
  async function requestDisplayMode(mode) {
    if (!HOST_MODES.includes(mode)) {
      throw new Error('host does not advertise display mode: ' + mode);
    }
    const result = await request('ui/request-display-mode', { mode });
    const applied = (result && result.mode) || DISPLAY_MODE;
    DISPLAY_MODE = applied;
    return applied;
  }

  return { init, on, respondTo, request, notify, callTool, openLink,
           sendMessage, updateContext, requestTeardown, hostSupports,
           getDisplayMode, getAvailableDisplayModes, requestDisplayMode };
})();

// Tool payloads arrive as notifications after the handshake.
function onToolData(handler) {
  let input = null, result = null;
  const fire = () => handler({ input, result });
  MCP.on('ui/notifications/tool-input', (p) => { input = (p && p.arguments) || {}; fire(); });
  MCP.on('ui/notifications/tool-result', (p) => { result = p; fire(); });
  MCP.on('ui/notifications/tool-cancelled', (p) =>
    handler({ input, result: null, cancelled: (p && p.reason) || 'cancelled' }));
}

// Tool results carry the real payload in structuredContent; fall back to
// parsing the text block for hosts or paths that omit it.
function structuredOf(result) {
  if (!result) return null;
  if (result.structuredContent) return result.structuredContent;
  const block = (result.content || []).find((c) => c.type === 'text');
  if (!block) return null;
  try { return JSON.parse(block.text); } catch (e) { return null; }
}
"""

# Fallback values for every host variable the views use. Without these a
# host that sends no styles renders unreadable text.
BASE_CSS = r"""
:root {
  color-scheme: light dark;
  --color-background-primary: light-dark(#ffffff, #171717);
  --color-background-secondary: light-dark(#f6f6f7, #202020);
  --color-background-tertiary: light-dark(#ededee, #262626);
  --color-background-danger: light-dark(#fdeceb, #3a1c1a);
  --color-background-warning: light-dark(#fdf4e3, #362a12);
  --color-background-success: light-dark(#e9f7ef, #14301f);
  --color-text-primary: light-dark(#171717, #fafafa);
  --color-text-secondary: light-dark(#5c5c5c, #a8a8a8);
  --color-text-tertiary: light-dark(#8a8a8a, #7c7c7c);
  --color-text-danger: light-dark(#b3261e, #f2938c);
  --color-text-warning: light-dark(#8a5a00, #f0c274);
  --color-text-success: light-dark(#1c7c4a, #7fd6a4);
  --color-border-primary: light-dark(#e3e3e5, #303030);
  --color-border-secondary: light-dark(#efeff1, #292929);
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  --font-text-sm-size: 13px;
  --font-text-md-size: 14px;
  --border-radius-sm: 6px;
  --border-radius-md: 8px;
  --border-radius-lg: 12px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,.06);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 14px;
  font-family: var(--font-sans);
  font-size: var(--font-text-md-size);
  background: var(--color-background-primary);
  color: var(--color-text-primary);
}
.muted { color: var(--color-text-secondary); }
.tiny { font-size: var(--font-text-sm-size); }
.mono { font-family: var(--font-mono); }
.row { display: flex; align-items: center; gap: 8px; }
.spread { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.card {
  border: 1px solid var(--color-border-primary);
  border-radius: var(--border-radius-md);
  background: var(--color-background-secondary);
  padding: 10px 12px;
  margin-bottom: 8px;
}
.hdr { display: flex; align-items: baseline; justify-content: space-between;
       margin-bottom: 12px; gap: 12px; flex-wrap: wrap; }
h1 { font-size: 16px; margin: 0; font-weight: 600; }
button {
  font: inherit; font-size: var(--font-text-sm-size);
  padding: 5px 11px; cursor: pointer;
  border-radius: var(--border-radius-sm);
  border: 1px solid var(--color-border-primary);
  background: var(--color-background-primary);
  color: var(--color-text-primary);
}
button:hover:not(:disabled) { background: var(--color-background-tertiary); }
button:disabled { opacity: .5; cursor: default; }
button.primary { background: var(--color-text-primary);
                 color: var(--color-background-primary); border-color: transparent; }
.pill { display: inline-block; padding: 1px 7px; border-radius: 999px;
        font-size: 11px; font-weight: 600; letter-spacing: .02em; }
.pill.danger  { background: var(--color-background-danger);  color: var(--color-text-danger); }
.pill.warn    { background: var(--color-background-warning); color: var(--color-text-warning); }
.pill.ok      { background: var(--color-background-success); color: var(--color-text-success); }
.pill.neutral { background: var(--color-background-tertiary); color: var(--color-text-secondary); }
input[type=search], input[type=text] {
  font: inherit; width: 100%; padding: 6px 9px;
  border-radius: var(--border-radius-sm);
  border: 1px solid var(--color-border-primary);
  background: var(--color-background-primary);
  color: var(--color-text-primary);
}
.empty { padding: 22px; text-align: center; color: var(--color-text-secondary); }
.loading { padding: 22px; text-align: center; color: var(--color-text-tertiary); }
"""


def page(title, body_html, extra_css="", extra_js=""):
    """Assemble a complete HTML5 document for a ui:// resource."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{BASE_CSS}{extra_css}</style>
</head>
<body>
{body_html}
<script>{RUNTIME_JS}
{extra_js}
</script>
</body>
</html>"""

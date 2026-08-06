/**
 * view-harness.mjs — run a CLITOOLS view's JS in a fake host and assert it
 * renders real data.
 *
 * Syntax-checking the view proves nothing about behaviour: a typo'd field
 * name or a bad structuredContent path renders an empty box in total
 * silence. This harness stands up a minimal DOM plus a host that speaks
 * the SEP-1865 handshake, feeds the view a real tool result, and checks
 * that content actually appeared.
 *
 * Usage: node view-harness.mjs <html-file> <fixture.json> <expect-substring>
 */
import { readFileSync } from 'node:fs';

const [htmlFile, fixtureFile, expect] = process.argv.slice(2);
const html = readFileSync(htmlFile, 'utf8');
const fixture = JSON.parse(readFileSync(fixtureFile, 'utf8'));

// ---- minimal DOM ---------------------------------------------------------
class El {
  constructor(tag) {
    this.tagName = (tag || 'div').toUpperCase();
    this.children = []; this.attrs = {}; this.dataset = {};
    // style must behave like CSSStyleDeclaration: views call setProperty
    // for host theme variables.
    this.style = {
      _props: {},
      setProperty(k, v) { this._props[k] = v; },
      getPropertyValue(k) { return this._props[k] || ''; },
      removeProperty(k) { delete this._props[k]; },
    };
    this._text = ''; this._html = ''; this.classList = makeClassList(this);
    this.className = ''; this.disabled = false; this.value = '';
  }
  set innerHTML(v) { this._html = String(v); }
  get innerHTML() { return this._html; }
  set textContent(v) { this._text = String(v); this._html = ''; }
  get textContent() { return this._text; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  appendChild(c) { this.children.push(c); return c; }
  addEventListener() {}
  removeEventListener() {}
  querySelectorAll() { return []; }
  closest() { return null; }
  observe() {}
  get scrollHeight() { return 400; }
  get scrollWidth() { return 600; }
  // What a human would actually see in this element.
  visible() { return (this._html || '') + (this._text || ''); }
}
function makeClassList(el) {
  const s = new Set();
  return {
    add: (c) => s.add(c), remove: (c) => s.delete(c),
    toggle: (c, on) => (on ? s.add(c) : s.delete(c)),
    contains: (c) => s.has(c), _set: s,
  };
}

const nodes = new Map();
const doc = {
  documentElement: new El('html'),
  head: new El('head'),
  body: new El('body'),
  createElement: (t) => new El(t),
  getElementById: (id) => {
    if (!nodes.has(id)) { const e = new El('div'); e.id = id; nodes.set(id, e); }
    return nodes.get(id);
  },
  querySelectorAll: () => [],
  addEventListener: () => {},
};

// ---- fake host implementing the SEP-1865 handshake -----------------------
const sent = [];
// A real window supports MANY message listeners; the view registers one
// for RPC replies and another per respondTo(). Storing only the last one
// silently breaks the handshake, so fan out to all of them.
const viewListeners = [];
let teardownAnswered = false;
const parent = {
  postMessage: (msg) => {
    sent.push(msg);
    if (msg.method === 'ui/initialize') {
      reply({
        jsonrpc: '2.0', id: msg.id,
        result: {
          protocolVersion: '2026-01-26',
          hostCapabilities: { serverTools: {}, openLinks: {}, logging: {} },
          hostInfo: { name: 'harness', version: '1.0.0' },
          hostContext: {
            theme: 'dark',
            styles: { variables: { '--color-text-primary': '#fff' } },
            displayMode: 'inline',
            containerDimensions: { maxHeight: 600 },
          },
        },
      });
      // Then deliver the tool payload, as a real host does.
      setTimeout(() => {
        notify('ui/notifications/tool-input', { arguments: fixture.input || {} });
        notify('ui/notifications/tool-result', fixture.result);
      }, 0);
    } else if (msg.method === 'tools/call') {
      reply({ jsonrpc: '2.0', id: msg.id, result: fixture.result });
    } else if (msg.id !== undefined && msg.result !== undefined) {
      // A response FROM the view (e.g. to ui/resource-teardown).
      if (msg.id === 9999) teardownAnswered = true;
    } else if (msg.id !== undefined) {
      reply({ jsonrpc: '2.0', id: msg.id, result: {} });
    }
  },
};
function reply(m) {
  setTimeout(() => {
    for (const fn of [...viewListeners]) {
      try { fn({ data: m }); } catch (e) { console.error(e); }
    }
  }, 0);
}
function notify(method, params) { reply({ jsonrpc: '2.0', method, params }); }

globalThis.window = {
  parent,
  addEventListener: (type, fn) => { if (type === 'message') viewListeners.push(fn); },
  removeEventListener: (type, fn) => {
    const i = viewListeners.indexOf(fn);
    if (i >= 0) viewListeners.splice(i, 1);
  },
};
globalThis.document = doc;
globalThis.ResizeObserver = class { observe() {} };
// navigator is a getter-only global in modern Node; define instead of assign.
Object.defineProperty(globalThis, 'navigator', {
  value: { clipboard: { writeText: async () => {} } },
  configurable: true, writable: true,
});
globalThis.console = console;
globalThis.setTimeout = setTimeout;
globalThis.clearTimeout = clearTimeout;

// ---- run the view --------------------------------------------------------
const js = html.match(/<script>([\s\S]*)<\/script>/)[1];
try {
  new Function(js)();
} catch (e) {
  console.log('FAIL: view threw on load: ' + e.message);
  process.exit(1);
}

setTimeout(() => {
  // A host SHOULD wait for the view's teardown reply before destroying
  // the iframe. A view that never answers stalls that host, so assert it.
  reply({ jsonrpc: '2.0', id: 9999, method: 'ui/resource-teardown',
          params: { reason: 'harness check' } });

  setTimeout(() => {
    const rendered = [...nodes.values()].map((n) => n.visible()).join('\n');
    const initialized = sent.some((m) => m.method === 'ui/notifications/initialized');
    const sizeSent = sent.some((m) => m.method === 'ui/notifications/size-changed');

    const problems = [];
    if (!sent.some((m) => m.method === 'ui/initialize')) problems.push('no ui/initialize');
    if (!initialized) problems.push('no ui/notifications/initialized');
    if (!sizeSent) problems.push('no size-changed notification');
    if (!teardownAnswered) problems.push('did not answer ui/resource-teardown');
    if (expect && !rendered.includes(expect)) {
      problems.push(`rendered output missing expected text: ${JSON.stringify(expect)}`);
    }
    if (/loading…/.test(rendered) && !rendered.includes(expect || '\u0000')) {
      problems.push('view still shows loading state');
    }

    if (problems.length) {
      console.log('FAIL: ' + problems.join('; '));
      console.log('--- rendered (first 700 chars) ---');
      console.log(rendered.slice(0, 700));
      process.exit(1);
    }
    console.log(`PASS: handshake + teardown ok, rendered ${rendered.length} chars, `
      + `found ${JSON.stringify(expect)}`);
  }, 60);
}, 120);

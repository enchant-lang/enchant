// live/client.js — the browser half: apply patch ops to the DOM.
//
// This is a direct port of the reference semantics in priv/live/diff.bl
// (`apply-ops`). The server computes the ops by diffing hiccup TREES; the
// client applies the SAME ops to the real DOM. Because the op set is small
// and keyed, this is ~120 lines with no virtual DOM and no heuristics.
//
// Wire protocol (JSON over a WebSocket):
//   server → client:  ["mount", html, features]  first paint (full HTML)
//                     features["text-layout"] restores parsed text boundaries
//                     ["style", css]              rules for classes the next
//                                                 mount/patch introduces
//                     ["patch", ops]              a list of patch ops
//                     ["denied", why]             an intent was refused
//   client → server:  ["event", term, data]      a fired event + its data
//                     ["ping"]                    heartbeat — inbound traffic
//                                                 that keeps an idle socket
//                                                 under the server's idle
//                                                 timeout (no reply expected)
//                     ["remount"]                 a patch op did not apply:
//                                                 send a fresh ["mount"]
//
// Op set (mirrors diff.bl):
//   ["set-attr",    path, k, v]
//   ["remove-attr", path, k]
//   ["text",        path, s]
//   ["replace",     path, subtree]       subtree is hiccup-as-array
//   ["insert",      path, key, idx, subtree]
//   ["remove",      path, key]
//   ["move",        path, key, idx]
//
// `path` is a vector of child indices from the mount root. A keyed op names
// its child by the element's `key` attribute (the server strips `:key` from
// HTML but re-emits it as `data-key` on rendered elements — see render()).
//
// What a page can listen to (CustomEvents on `document`) and wait on
// (attributes on <html>):
//   live:state    {up}           the socket opened/closed  · html[data-live="1"|"0"]
//   live:pending  {count}        un-acked durable gestures · html[data-live-pending]
//   live:mount    {root}         a ["mount"] repainted root · html[data-mounted="1"]
//   live:patch    {root, ops}    a ["patch"] was applied
//   live:patch-error {failed}    ops of that patch did not apply ({op, error}
//                                each; the rest did); a ["remount"] is asked
//   live:denied   {why}          the server refused an intent (["denied", why]);
//                                also opts.onDenied(why) when the shell passed one
//   live:tap      {t, basis}     a tapped socket's frame id (dev tools)

(function () {
  "use strict";

  // ── durable offline outbox (opt-in via connect({outbox:true})) ────────
  //
  // The floor tablet drops wifi mid-gesture. A durable gesture (an element
  // marked data-live-durable) is minted a client idempotency id, injected into
  // the event data as "ev/id", PERSISTED to localStorage, then sent. It clears
  // only when the server sends ["ack", id]; on reconnect every un-acked frame
  // is replayed. The server dedups by the unique :ev/id, so replay is
  // exactly-once. The outbox itself stays opt-in; RECONNECT does not (see
  // connect()): every socket auto-reconnects unless {reconnect:false}.
  function makeOutbox(key) {
    function load() {
      try { return JSON.parse(window.localStorage.getItem(key) || "[]"); }
      catch (_e) { return []; }
    }
    function save(q) {
      try { window.localStorage.setItem(key, JSON.stringify(q)); } catch (_e) {}
    }
    return {
      add: function (id, frame) {
        var q = load(), i;
        for (i = 0; i < q.length; i++) if (q[i].id === id) return;
        q.push({ id: id, frame: frame });
        save(q);
      },
      ack: function (id) {
        var q = load(), out = [], i;
        for (i = 0; i < q.length; i++) if (q[i].id !== id) out.push(q[i]);
        save(out);
      },
      replay: function (sendFrame) {
        var q = load(), i;
        for (i = 0; i < q.length; i++) sendFrame(q[i].frame);
      },
      count: function () { return load().length; },
    };
  }

  // a monotonic-ish client id for a device: a stable per-tab prefix + counter,
  // so two tablets on the same PIN never collide and a crash-restart continues.
  var __seq = 0;
  function mintId(op) {
    var pfx;
    try {
      pfx = window.localStorage.getItem("live:client-id");
      if (!pfx) { pfx = "c" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
                  window.localStorage.setItem("live:client-id", pfx); }
    } catch (_e) { pfx = "c" + Date.now().toString(36); }
    __seq++;
    return "ev-" + op + "-" + pfx + "-" + Date.now().toString(36) + "-" + __seq;
  }

  // ── resolve a path (array of child indices) to a DOM element ──────────
  //
  // The diff paths are relative to the VIEW's root element (the single
  // element the view returns, e.g. the `<ul>`), which the mount renders as
  // the first element child of the mount container. So a path of [] is that
  // element, [0] its first child, etc. `rootEl` normalises the container to
  // its mounted view element.
  function rootEl(container) {
    // if the container IS the view root already (has a tag other than the
    // mount wrapper), use it; otherwise descend to its first element child.
    const kids = elementChildren(container);
    return kids.length === 1 && container.id === "live-root" ? kids[0] : container;
  }

  function at(container, path) {
    let el = rootEl(container);
    // Walk ALL child nodes (text + element), NOT element-only: the server
    // differ (diff.bl `children-of`) indexes a node's children as the flat
    // text+element list. Mount hydration restores adjacent/empty text nodes
    // that HTML parsing otherwise merges or drops. Walking
    // elementChildren here skips text siblings, so a path segment under a node
    // that interleaves text and elements (e.g. `[:button (icon) "Label"]`)
    // resolves to the WRONG node — or past the end — and the op is silently
    // dropped. That is the live-nav "URL changes but the page doesn't" bug.
    for (const i of path) el = domChildren(el)[i];
    return el;
  }

  // the child nodes a diff PATH indexes: text + element, in document order,
  // mirroring the server differ's `children-of` (which keeps strings and
  // elements, drops nils, splices seqs). Comment/other node types are
  // excluded (hiccup never emits them). This is the indexing the whole op
  // set is computed against; `elementChildren` below is only for the two
  // element-only concerns (root normalization + keyed lookup).
  function domChildren(el) {
    return Array.prototype.filter.call(el.childNodes, function (n) {
      return n.nodeType === 1 || n.nodeType === 3;
    });
  }

  function hydrateText(root, layouts) {
    const next = function (node) {
      for (let n = node.nextSibling; n; n = n.nextSibling) {
        if (n.nodeType === 1 || n.nodeType === 3) return n;
      }
      return null;
    };
    // Parents precede descendants: splitting a parent's text first restores
    // the child indices by which its descendants are subsequently addressed.
    for (const [path, fragments] of layouts || []) {
      const parent = at(root, path);
      let cursor = domChildren(parent)[0] || null;
      let leading = /^(PRE|TEXTAREA|LISTING)$/.test(parent.tagName);
      let previousCR = false;
      for (let fragment of fragments) {
        if (fragment === null) {
          leading = false;
          previousCR = false;
          if (!cursor || cursor.nodeType !== 1) throw Error("Live text hydration: missing element at " + path);
          cursor = next(cursor);
        } else {
          // The HTML parser normalizes CR/CRLF and strips one initial LF in
          // preformatted/RCDATA containers. Split the parsed text, preserving
          // its visible content, elements, input state and event listeners.
          const original = fragment;
          if (previousCR && fragment[0] === "\n") fragment = fragment.slice(1);
          if (original.length) previousCR = original.endsWith("\r");
          fragment = fragment.replace(/\r\n?/g, "\n");
          if (leading && fragment.length) {
            leading = false;
            if (fragment[0] === "\n") fragment = fragment.slice(1);
          }
          if (!fragment.length) {
            parent.insertBefore(document.createTextNode(""), cursor);
          } else {
            if (!cursor || cursor.nodeType !== 3 || cursor.data.length < fragment.length)
              throw Error("Live text hydration: missing text at " + path);
            if (cursor.data.length > fragment.length) cursor.splitText(fragment.length);
            cursor = next(cursor);
          }
        }
      }
      if (cursor) throw Error("Live text hydration: surplus children at " + path);
    }
  }

  // element children only (skip text nodes) — used for the #live-root → view
  // root normalization and for keyed lookups (a `:key` is always on an
  // element, and a keyed child list is all-element by construction).
  function elementChildren(el) {
    return Array.prototype.filter.call(el.childNodes, function (n) {
      return n.nodeType === 1;
    });
  }

  function childByKey(parent, key) {
    return elementChildren(parent).find(function (c) {
      return c.getAttribute("data-key") === String(key);
    });
  }

  // ── render a hiccup-as-array subtree to a DOM node ────────────────────
  // ["tag", {attrs}, ...children]  |  "text"  |  number
  //
  // SVG AWARENESS: an element inside an <svg> must be created with
  // createElementNS — a plain createElement builds an HTML-namespace element
  // the browser renders as an unknown inline tag ("blank" posters, text
  // spilled as loose strings). The context enters at <svg> and inherits to
  // every descendant; `svg` is false at the roots applyOp renders.
  const SVG_NS = "http://www.w3.org/2000/svg";
  const HTML_NS = "http://www.w3.org/1999/xhtml";
  const SVG_TAGS = {
    svg: 1, defs: 1, g: 1, rect: 1, circle: 1, ellipse: 1, line: 1,
    path: 1, polygon: 1, polyline: 1, text: 1, tspan: 1, stop: 1,
    linearGradient: 1, radialGradient: 1, pattern: 1, clipPath: 1, mask: 1,
    use: 1, symbol: 1, marker: 1, filter: 1, image: 1
  };
  function render(node, svg) {
    // live.diff/splice-children drops nil: an empty fragment preserves those
    // child indices, whereas an empty text node shifts every later patch.
    if (node === null || node === undefined) return document.createDocumentFragment();
    if (typeof node === "string" || typeof node === "number") {
      return document.createTextNode(String(node));
    }
    // element: [tag, attrs?, ...children]
    const tag = node[0];
    let attrs = {};
    let rest = node.slice(1);
    if (rest.length && isPlainObject(rest[0])) {
      attrs = rest[0];
      rest = rest.slice(1);
    }
    const bare = String(tag).replace(/[#.].*$/, "") || "div";
    const inSvg = svg || SVG_TAGS[bare] === 1;
    const el = document.createElementNS(inSvg ? SVG_NS : HTML_NS, bare);
    // shorthand id/classes on the tag (e.g. "li.task")
    applyShorthand(el, String(tag));
    // then the attrs map, merged with the shorthand the way the server
    // renderer (live/hiccup render-attrs) merges it: classes CONCATENATE
    // (shorthand first, then :class) and an explicit :id wins. A plain
    // setAttr here REPLACED the shorthand: `["span.x", {"class": "y"}]`
    // painted class="y" in an inserted subtree where the first paint had "x y".
    for (const k in attrs) {
      const v = attrs[k];
      const absent = v === null || v === undefined || v === false;
      if (k === "class" && el.hasAttribute("class")) {
        if (!absent) el.setAttribute("class", el.getAttribute("class") + " " + String(v));
      } else if (k === "id" && absent && el.hasAttribute("id")) {
        // a nil :id falls back to the shorthand's, as on the server
      } else {
        setAttr(el, k, v);
      }
    }
    // a nested array of children (a spliced seq) flattens — at ANY depth, as
    // hiccup->html and diff's splice-children do: a seq of seqs (a `& body`
    // rest-arg handed on as one child) used to reach render() as a "tag" that
    // was an array, createElementNS threw, and the whole patch was dropped
    const appendKids = (kids) => {
      for (const child of kids) {
        if (Array.isArray(child) && typeof child[0] !== "string") appendKids(child);
        else el.appendChild(render(child, inSvg));
      }
    };
    appendKids(rest);
    return el;
  }

  function applyShorthand(el, tag) {
    const hashI = tag.indexOf("#");
    const dotI = tag.indexOf(".");
    let cut = tag.length;
    if (hashI >= 0 && dotI >= 0) cut = Math.min(hashI, dotI);
    else if (hashI >= 0) cut = hashI;
    else if (dotI >= 0) cut = dotI;
    const rest = tag.slice(cut).replace(/#/g, ".#").split(".").filter(Boolean);
    for (const seg of rest) {
      if (seg[0] === "#") el.id = seg.slice(1);
      else el.classList.add(seg);
    }
  }

  function isPlainObject(x) {
    return x && typeof x === "object" && !Array.isArray(x);
  }

  // Set one attribute, translating the reserved keys the same way the server
  // renderer (live/hiccup render-attr) does — this is what keeps a rendered
  // subtree and a patched attribute in the SAME namespace:
  //   :key       -> data-key
  //   :on-EVENT  -> data-ev-EVENT, VALUE is the JSON event term (so the fire
  //                handler relays exactly what the view now declares; this is
  //                what makes a changed intent — e.g. a new room — take effect)
  // For `render` the value `v` is the raw hiccup value (an array term); for a
  // patch (`set-attr`) it arrives already JSON-encoded as a string. `evJson`
  // normalizes both to the JSON string the attribute must hold.
  function inputOwner(el) {
    for (var p = el; p; p = p.parentElement)
      if (p.__liveInputAck !== undefined) return p;
    return null;
  }
  function syncInput(el) {
    var owner = inputOwner(el);
    // An older server cannot acknowledge newer typing; keep its old contract.
    if (!owner || !owner.__liveInputAck) return;
    if (el.__liveInputPending || el.__liveComposing) return;
    if (el.tagName === "INPUT" && el.type === "file") return;
    if (el.hasAttribute("value")) el.__liveValueControlled = true;
    if (el.__liveValueControlled) {
      var value = el.getAttribute("value") || "";
      if (el.value !== value) el.value = value;
    } else if (el.tagName === "TEXTAREA" && el.hasAttribute("data-ev-input")) {
      if (el.value !== el.textContent) el.value = el.textContent;
    }
    if (el.tagName === "INPUT" && (el.type === "checkbox" || el.type === "radio") &&
        el.hasAttribute("data-ev-change")) el.checked = el.hasAttribute("checked");
    if (el.tagName === "SELECT" && !el.__liveValueControlled && el.hasAttribute("data-ev-change")) {
      for (var i = 0; i < el.options.length; i++)
        el.options[i].selected = el.options[i].hasAttribute("selected");
    }
  }
  function syncInputs(root) {
    for (var el of root.querySelectorAll("input,textarea,select")) syncInput(el);
  }
  function setAttr(el, k, v) {
    if (k === "live/region") {
      el.setAttribute("data-live-region", evJson(v));
      return;
    }
    if (k === "key") {
      el.setAttribute("data-key", String(v));
      return;
    }
    if (k.indexOf("on-") === 0) {
      el.setAttribute("data-ev-" + k.slice(3), evJson(v));
      return;
    }
    if (v === true) el.setAttribute(k, "");
    else if (v === false || v === null || v === undefined) el.removeAttribute(k);
    else el.setAttribute(k, String(v));
  }

  // the JSON string an event attribute holds: a string is already encoded
  // (a patch value), anything else is a live term to stringify (a render value)
  function evJson(v) {
    return typeof v === "string" ? v : JSON.stringify(v);
  }

  // Region drivers own browser interaction under a declared projection root.
  // The differ emits one semantic update; descendants have one renderer.
  const regionFactories = new Map(), regionInstances = new Map();
  function regionSpec(el) {
    try { return JSON.parse(el.getAttribute("data-live-region")); }
    catch (_) { return null; }
  }
  function regionNodes(root) {
    return [...(root.matches?.("[data-live-region]") ? [root] : []),
            ...root.querySelectorAll("[data-live-region]")];
  }
  function disposeRegion(el) {
    const instance = regionInstances.get(el);
    if (instance) { regionInstances.delete(el); instance.driver?.dispose?.(); }
  }
  function syncRegions(root) {
    for (const [el, instance] of regionInstances)
      if (!el.isConnected || !regionFactories.has(instance.kind)) disposeRegion(el);
    for (const el of regionNodes(root)) {
      const spec = regionSpec(el), factory = spec && regionFactories.get(spec.kind);
      if (!factory || regionInstances.has(el)) continue;
      const owner = root.closest?.("#live-root") || root;
      const instance = {kind: spec.kind, id: spec.id, factory};
      regionInstances.set(el, instance);
      try {
        instance.driver = factory(el, spec.model, {
          dispatch(term, data) { owner.__liveRegionSend?.(term, data || {}); },
          settle(options) {
            return owner.__liveSettle ? owner.__liveSettle(options) : Promise.reject(Error('Current Live tools are required before sharing.'));
          },
          render,
        });
      } catch (error) { regionInstances.delete(el); throw error; }
    }
  }
  function registerRegion(kind, factory) {
    if (typeof kind !== "string" || typeof factory !== "function") throw Error("Invalid Live region driver");
    if (regionFactories.has(kind)) throw Error("Live region driver already registered: " + kind);
    regionFactories.set(kind, factory);
    if (Live.root) syncRegions(Live.root);
    let active = true;
    return function () {
      if (!active) return; active = false;
      regionFactories.delete(kind);
      for (const [el, instance] of regionInstances) if (instance.factory === factory) disposeRegion(el);
    };
  }
  function restoreRegions(root, kept) {
    for (const fresh of regionNodes(root)) {
      const spec = regionSpec(fresh);
      const previous = kept.find(([el, instance]) => instance.kind === spec?.kind && instance.id === spec?.id && el.tagName === fresh.tagName);
      if (!previous) continue;
      const [el, instance] = previous;
      el.setAttribute("data-live-region", fresh.getAttribute("data-live-region"));
      fresh.replaceWith(el);
      instance.driver?.update?.(spec.model);
    }
    syncRegions(root);
  }

  // ── apply one op ──────────────────────────────────────────────────────
  // ── apply one patch (a list of ops) ───────────────────────────────────
  // The server's reference (diff.bl apply-ops) applies ALL structural ops
  // first — grouped by parent path, SHALLOWEST parents first — and only then
  // the deep ops, whose paths index the REBUILT tree. Every path under a list
  // indexes that list's NEW children, so an inner parent is addressable only
  // after its outer list is rebuilt (deepest-first patched the row one late).
  // Within a parent, wire order already is removes → placements (anchor-fill).
  //
  // Every op is GUARDED. One op that throws (a path into a DOM the model does
  // not describe — e.g. a parser-inserted element) used to abort the loop, and
  // every later op of the patch was lost in silence. The rest of the patch now
  // still lands; the failures are returned so the socket can report them and
  // ask for a fresh mount (see connect()).
  const STRUCTURAL = { remove: 1, "remove-at": 1, insert: 1, move: 1 };
  function applyPatch(root, ops) {
    const structural = [];
    const deep = [];
    const failed = [];
    const run = (op) => {
      try { applyOp(root, op); }
      catch (e) { failed.push({ op: op, error: String(e && e.message || e) }); }
    };
    for (const op of ops) (STRUCTURAL[op[0]] ? structural : deep).push(op);
    const byPath = new Map();
    for (const op of structural) {
      const k = JSON.stringify(op[1]);
      if (!byPath.has(k)) byPath.set(k, []);
      byPath.get(k).push(op);
    }
    const paths = Array.from(byPath.keys()).sort(
      (a, b) => JSON.parse(a).length - JSON.parse(b).length);
    for (const p of paths) for (const op of byPath.get(p)) run(op);
    for (const op of deep) run(op);
    syncInputs(root);
    syncRegions(root);
    return failed;
  }

  function applyOp(root, op) {
    const kind = op[0];
    const path = op[1];
    if (kind === "set-attr") {
      // route through setAttr so on-EVENT/key are translated to data-ev-*/
      // data-key exactly as render does — a raw setAttribute here would write
      // a dead `on-keydown.enter` attr the fire handler never reads.
      setAttr(at(root, path), op[2], op[3]);
    } else if (kind === "remove-attr") {
      var el = at(root, path);
      var k = op[2];
      if (k === "key") el.removeAttribute("data-key");
      else if (k.indexOf("on-") === 0) el.removeAttribute("data-ev-" + k.slice(3));
      else el.removeAttribute(k);
    } else if (kind === "text") {
      // a text op's path ends at a child slot that is a TEXT node. Walk the
      // parent's ALL child nodes (text + element) to the slot and set its
      // data, so a text change beside sibling elements does not clobber them.
      const parent = at(root, path.slice(0, -1));
      const slot = path[path.length - 1];
      const node = domChildren(parent)[slot];
      if (node && node.nodeType === 3) {
        node.data = String(op[2]);
      } else if (node) {
        parent.replaceChild(document.createTextNode(String(op[2])), node);
      } else {
        parent.appendChild(document.createTextNode(String(op[2])));
      }
    } else if (kind === "region") {
      const el = at(root, path), tree = op[2], attrs = isPlainObject(tree[1]) ? tree[1] : {};
      const spec = attrs["live/region"], instance = regionInstances.get(el);
      if (instance && spec && instance.kind === spec.kind && instance.id === spec.id) {
        for (const [key, value] of Object.entries(attrs)) setAttr(el, key, value);
        instance.driver?.update?.(spec.model);
      } else {
        const next = render(tree); el.replaceWith(next); syncRegions(root);
      }
    } else if (kind === "replace") {
      const parent = at(root, path.slice(0, -1));
      const idx = path[path.length - 1];
      // children-of index (text+element), matching the server differ
      const el = domChildren(parent)[idx];
      parent.replaceChild(render(op[2]), el);
    } else if (kind === "remove") {
      const parent = at(root, path);
      const el = childByKey(parent, op[2]);
      if (el) parent.removeChild(el);
    } else if (kind === "remove-at") {
      // positional remove (unkeyed list): drop the child at a children-of
      // index (text+element), matching the server differ. The differ emits
      // these high-index-first, so sequential application keeps the remaining
      // indices valid.
      const parent = at(root, path);
      const el = domChildren(parent)[op[2]];
      if (el) parent.removeChild(el);
    } else if (kind === "insert") {
      const parent = at(root, path);
      const idx = op[3];
      const node = render(op[4]);
      // insert before the child now at the children-of index (text+element),
      // matching the server differ; null → append
      const ref = domChildren(parent)[idx] || null;
      parent.insertBefore(node, ref);
    } else if (kind === "move") {
      const parent = at(root, path);
      const el = childByKey(parent, op[2]);
      const idx = op[3];
      if (el) {
        // absolute-index placement, matching diff.bl's apply-ops: remove the
        // node, then insert it before the element now at `idx` among the
        // REMAINING children (null → append). This is the anchor-fill
        // reconciliation the differ assumes.
        parent.removeChild(el);
        const remaining = domChildren(parent);
        const ref = remaining[idx] || null;
        parent.insertBefore(el, ref);
      }
    }
  }

  // ── the socket ────────────────────────────────────────────────────────
  function connect(opts) {
    const root = opts.root || document.getElementById("live-root");

    // The outbox is opt-in: {outbox:true} turns on a durable localStorage queue
    // + replay. RECONNECT is the default: every socket re-opens on close with
    // backoff ({reconnect:false} restores the old volatile behaviour for hosts
    // that manage the lifecycle themselves). Without the outbox a dropped
    // volatile frame is still lost — only durable frames replay.
    var outbox = opts.outbox ? makeOutbox("live:outbox") : null;
    var reconnect = opts.reconnect !== false;

    // heartbeat: a ["ping"] frame every heartbeatMs keeps a quiet page's
    // socket under the server's idle timeout (web/upgrade carries 120s) and
    // holds proxies open. Default 30s; {heartbeatMs:0} disables.
    var heartbeatMs = opts.heartbeatMs === undefined ? 30000 : opts.heartbeatMs;

    // the SESSION id: minted once PER PAGE LOAD and carried by every
    // reconnect, so the server re-attaches the SAME session — locals (a
    // wizard's step, a query, a flash), subscriptions and the tree the client
    // last saw — instead of mounting a fresh one. In memory only, on purpose:
    // a reload is a new page load and wants a fresh session, so there is
    // nothing to persist, expire or clear.
    // A reconnect before initial delivery cannot resume from SSR as though
    // it were hydrated. Only a successfully applied mount changes this receipt.
    var mounted = false;
    var sid = (function () {
      var a = new Uint8Array(16), i, s = "";
      if (window.crypto && window.crypto.getRandomValues) window.crypto.getRandomValues(a);
      else for (i = 0; i < a.length; i++) a[i] = Math.floor(Math.random() * 256);
      for (i = 0; i < a.length; i++) s += ("0" + a[i].toString(16)).slice(-2);
      return s;
    })();
    function sessionUrl(url) {
      return url + (url.indexOf("?") === -1 ? "?" : "&") + "live-sid=" + sid + "&live-mounted=" + (mounted ? "1" : "0");
    }

    // `ws` is now MUTABLE — a reconnect swaps in a fresh socket while the event
    // delegation (bound to `root` once, below) keeps firing. `pending` buffers
    // sends made while the CURRENT socket is still CONNECTING.
    var ws = null;
    var pending = [];
    var inputFrames = new Map();
    const settlements = new Map();
    function settleConnection({signal,timeout=30000}={}) {
      if (!root.__liveSettlement || !ws || ws.readyState !== WebSocket.OPEN)
        return Promise.reject(Error('Reconnect with current Live tools before sharing.'));
      if (signal?.aborted) return Promise.reject(Error('The writing surface closed before confirmation.'));
      const id=mintId('settle'),socket=ws;
      return new Promise((resolve,reject)=>{
        const finish=error=>{
          const entry=settlements.get(id);if(!entry)return;
          settlements.delete(id);clearTimeout(entry.timer);signal?.removeEventListener('abort',aborted);
          if(error)reject(error);else resolve();
        };
        const aborted=()=>finish(Error('The writing surface closed before confirmation.'));
        settlements.set(id,{socket,finish,timer:setTimeout(()=>finish(Error('Confirmation is still pending. Keep this page open and try again.')),timeout)});
        signal?.addEventListener('abort',aborted,{once:true});
        try{socket.send(JSON.stringify(['settle',id]));}catch(error){finish(error);}
      });
    }
    function rejectSettlements(message) {
      for(const entry of [...settlements.values()])entry.finish(Error(message));
    }
    function trackInput(el, data) {
      if (!root.__liveInputAck || !ws ||
          (ws.readyState !== WebSocket.OPEN && ws.readyState !== WebSocket.CONNECTING)) return data;
      var id = mintId("input");
      inputFrames.set(id, el);
      el.__liveInputPending = (el.__liveInputPending || 0) + 1;
      return Object.assign({}, data, { "live/input-id": id });
    }
    function acknowledgeInput(id) {
      var el = inputFrames.get(id);
      if (!el) return;
      inputFrames.delete(id);
      el.__liveInputPending = Math.max(0, (el.__liveInputPending || 0) - 1);
      if (el.isConnected) syncInput(el);
    }
    function discardInputs() {
      for (var el of inputFrames.values()) el.__liveInputPending = 0;
      inputFrames.clear();
    }
    var reconnectMs = 500;
    var reconnectTimer = null;
    var beat = null;
    var suspended = false;
    // the latest route the page wants but has not yet put on the wire. A
    // navigation moves the URL bar SYNCHRONOUSLY (pushState) but the page only
    // changes when the server receives the navigate event and re-projects
    // ([:patch] content + [:style] the new route's rules). If the socket is not
    // OPEN at click/popstate time the frame is dropped, so the URL and the page
    // diverge — and because a reconnect RESUMES the same server session at its
    // (now stale) route, the divergence survives the reconnect and only a full
    // reload recovers. So navigation CONVERGES instead of dropping: the desired
    // route is remembered here and flushed on (re)open. Last-wins — only the
    // final route matters, so a newer navigate replaces an older pending one.
    var pendingNav = null;
    // a ["remount"] is in flight (a patch op failed); cleared by the mount
    var remountAsked = false;

    // send a raw JSON frame string: straight through when OPEN, buffered while
    // CONNECTING, dropped when there is no socket (the outbox holds the durable
    // ones and replays them on reconnect). relay() calls ws.__send; that is a
    // thin shim over this so existing call sites are unchanged.
    function sendFrame(payload) {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(payload);
      else if (ws && ws.readyState === WebSocket.CONNECTING) pending.push(payload);
      // no socket / CLOSED: drop — a durable frame is in the outbox already
    }

    // send a navigate to `path` now when the socket is OPEN, else remember it as
    // the latest route to flush on (re)open. Unlike sendFrame's CLOSED-drop, a
    // navigate is idempotent and last-wins, so it is never dropped: the page
    // always catches up to the address bar. Used by __navigate (link clicks) and
    // the popstate handler (Back/Forward).
    function sendNav(path) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        pendingNav = null;
        ws.send(JSON.stringify(["event", ["navigate", path], {}]));
      } else {
        pendingNav = path;
      }
    }

    function dispatchLive(up) {
      try {
        document.documentElement.setAttribute("data-live", up ? "1" : "0");
        document.dispatchEvent(new CustomEvent("live:state", { detail: { up: up } }));
      } catch (_e) { /* non-DOM host (tests) — ignore */ }
      if (opts.onLive) opts.onLive(up);
    }
    function setLive(up) {
      dispatchLive(up);
      // publish the pending-count so a view/pill can show « N en attente ».
      if (outbox) {
        try {
          document.documentElement.setAttribute("data-live-pending", String(outbox.count()));
          document.dispatchEvent(new CustomEvent("live:pending",
            { detail: { count: outbox.count() } }));
        } catch (_e) {}
      }
    }

    function announce(name, detail) {
      try { document.dispatchEvent(new CustomEvent(name, { detail: detail })); }
      catch (_e) { /* non-DOM host */ }
    }

    // open (or re-open) the socket and wire its handlers.
    function openSocket() {
      if (suspended || (ws && (ws.readyState === WebSocket.OPEN ||
                              ws.readyState === WebSocket.CONNECTING))) return;
      ws = new WebSocket(sessionUrl(opts.url));
      ws.__send = sendFrame;   // relay() and __navigate use this
      ws.__sendNav = sendNav;  // relay() uses this for a view-declared :navigate
      // The NAVIGATOR is per-socket too, for the same reason: the click handler
      // below reads `ws.__navigate` off whatever socket is current. Attach it
      // once, outside openSocket, and only the FIRST socket ever gets one — the
      // socket a reconnect brings back has none, so every in-app <a href="/…">
      // is preventDefault'd and then dropped: the URL never moves, the page
      // never repaints, and nothing on the wire records that a click happened.
      ws.__navigate = function (path) {
        try { history.pushState({ live: path }, "", path); } catch (_e) {}
        // sendNav, NOT sendFrame: a navigate is buffered (last-wins) when the
        // socket is not OPEN and flushed on (re)open, so the page always
        // catches up to the URL the pushState just set — never the dropped
        // frame that left the address bar ahead of a stale page.
        sendNav(path);
      };
      var sock = ws;           // callbacks belong only to this transport

      ws.onopen = function () {
        if (sock !== ws || suspended) return;
        reconnectMs = 500;                         // reset backoff
        // flush the route the page wants before anything else: a click or a
        // Back/Forward that happened while the socket was down left the URL bar
        // ahead of the page, and a reconnect RESUMES the server session at its
        // stale route — so drive it to the current URL first, and the resume's
        // own render/diff then ships the page the address bar promises.
        if (pendingNav !== null) {
          ws.send(JSON.stringify(["event", ["navigate", pendingNav], {}]));
          pendingNav = null;
        }
        for (var i = 0; i < pending.length; i++) ws.send(pending[i]);
        pending = [];
        if (outbox) outbox.replay(sendFrame);      // resend every un-acked frame
        if (heartbeatMs > 0) {
          beat = setInterval(function () {
            if (sock.readyState === WebSocket.OPEN) sock.send(JSON.stringify(["ping"]));
          }, heartbeatMs);
        }
        setLive(true);
      };
      ws.onclose = function () {
        if (sock !== ws) return;
        discardInputs();
        rejectSettlements('Connection lost before confirmation. Your writing is retained.');
        if (beat) { clearInterval(beat); beat = null; }
        setLive(false);
        if (reconnect && !suspended && reconnectTimer === null) {
          reconnectTimer = setTimeout(function () {
            reconnectTimer = null;
            openSocket();
          }, reconnectMs);
          reconnectMs = Math.min(reconnectMs * 2, 10000);
        }
      };
      ws.onerror = function () { if (sock === ws && !suspended) setLive(false); };
      ws.onmessage = function (msg) {
        if (sock !== ws || suspended) return;
        const [kind, a, b] = JSON.parse(msg.data);
        if (kind === "mount") {
          // The mount REPLACES the server-rendered page. Whatever the reader
          // did to that page before the socket came up — text typed into a
          // field, a box ticked, the caret in a textarea — lived only in the
          // DOM the innerHTML below throws away. Carry it across (see
          // keepFields): typed values, focus and selection survive, and a
          // field bound to the server re-sends its value so the session's
          // state agrees with what the reader sees.
          const kept = keepFields(root);
          const keptRegions = [...regionInstances].filter(([el]) => root.contains(el));
          remountAsked = false;
          discardInputs();
          root.__liveInputAck = !!(b && b["input-ack"]);
          root.__liveSettlement = !!(b && b.settlement);
          root.innerHTML = a;
          hydrateText(root, b && b["text-layout"]);
          restoreRegions(root, keptRegions);
          syncInputs(root);
          restoreFields(root, kept);
          // a waitable mark (an event can fire before a test starts waiting)
          try { document.documentElement.setAttribute("data-mounted", "1"); } catch (_e) {}
          mounted = true;
          announce("live:mount", { root: root });
        } else if (kind === "style") {
          // the head sheet holds what the warm reached; a socket that renders
          // a class the warm never did ships its rule first (see socket.bl
          // ship-css!). Append, never replace: the warm rules stay.
          //
          // WHERE the rules go is the page's call, not ours. The SSR shell's
          // sheet is <style id="live-style"> (live.app render-page), placed
          // wherever the app's :shell put its `style` argument — so appending
          // INTO it keeps live's rules at that point of the cascade. A page
          // with no such sheet gets one inserted BEFORE its first stylesheet,
          // never after: appended at the end of <head>, live's base reset
          // (body background and ink) overrode the app's own sheet, whose
          // equal-specificity rules then lost on source order. An app that
          // wants live's rules elsewhere declares an empty
          // <style id="live-style"> there.
          let tag = document.getElementById("live-style");
          if (!tag) {
            tag = document.createElement("style"); tag.id = "live-style";
            document.head.insertBefore(tag,
              document.head.querySelector('link[rel~="stylesheet"], style'));
          }
          tag.appendChild(document.createTextNode(a + "\n"));
        } else if (kind === "patch") {
          const failed = applyPatch(root, a);
          announce("live:patch", { root: root, ops: a });
          if (failed.length) {
            // the page no longer matches the tree the server diffs against, so
            // every later patch would be computed for a page we do not have:
            // say so, and ask for a fresh mount — once, until it arrives
            try { console.error("live: " + failed.length + " patch op(s) did not apply", failed); }
            catch (_e) {}
            announce("live:patch-error", { failed: failed });
            if (!remountAsked) { remountAsked = true; sendFrame(JSON.stringify(["remount"])); }
          }
        } else if (kind === "tap") {
          announce("live:tap", { t: a, basis: b });
        } else if (kind === "denied") {
          // a refusal must reach the page even when the shell passed no
          // onDenied (live.app's default shell gives an app no way to): the
          // DOM event is what any page can listen to
          if (opts.onDenied) opts.onDenied(a);
          announce("live:denied", { why: a });
        } else if (kind === "ack") {
          if (outbox) { outbox.ack(a); setLive(true); }   // the gesture landed — drop it
        } else if (kind === "settled") {
          const entry=settlements.get(a);if(entry?.socket===sock)entry.finish();
        } else if (kind === "input-ack") {
          acknowledgeInput(a);
        }
      };
      Live.ws = ws;
    }
    // Cached pages keep their DOM and JavaScript heap, but cannot consume
    // patches while frozen. Release the transport so its server session
    // detaches and stops projecting. A patch may already be in flight when
    // the page freezes, so a return requests a fresh mount of the SAME
    // session; keepFields preserves its private inputs and focus. Retain sid
    // and the outbox. Tab visibility alone does not suspend a live viewer.
    window.addEventListener("pagehide", function () {
      suspended = true;
      mounted = false;
      if (reconnectTimer !== null) { clearTimeout(reconnectTimer); reconnectTimer = null; }
      if (beat) { clearInterval(beat); beat = null; }
      discardInputs();
      rejectSettlements('The page closed before confirmation. Your writing is retained.');
      setLive(false);
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close(1000, "pagehide");
      }
    });
    window.addEventListener("pageshow", function () {
      if (!suspended) return;
      suspended = false;
      if (reconnect) openSocket();
    });
    openSocket();
    Live.root = root;
    root.__liveRegionSend = function (term, data) {
      sendFrame(JSON.stringify(["event", term, data]));
    };
    root.__liveSettle = settleConnection;
    syncRegions(root);

    // relay() delegates to this to mark+persist a durable gesture before send.
    // A node marked data-live-durable mints an idempotency id, injects it into
    // the event data as "ev/id", and stores the full frame so a reconnect can
    // replay it. Returns the (possibly augmented) data object.
    Live.__durable = function (el, term, data) {
      if (!outbox || !el || !el.closest || !el.closest("[data-live-durable]")) return data;
      var op = (Array.isArray(term) && term[0] === "intent") ? String(term[1]) : "ev";
      var d = Object.assign({}, data || {});
      d["ev/id"] = mintId(op);
      outbox.add(d["ev/id"], JSON.stringify(["event", term, d]));
      setLive(!!(ws && ws.readyState === WebSocket.OPEN));
      return d;
    };

    // event delegation. A [data-ev-EVENT] node carries its intent as a JSON
    // attribute; on fire we relay that term plus the value of the nearest
    // input (so a Send button and an Enter key both carry the field text).
    root.addEventListener("click", function (e) {
      // A plain in-app <a href="/…"> becomes LIVE navigation automatically:
      // intercept the click, push the URL, and fire a navigate event so the
      // dispatcher re-projects with a keyed patch (no reload). Falls back to a
      // real page load when JS is off, when it's a modified click (new tab),
      // when the link is external/hash, or when the socket has no navigator
      // (see openSocket) — so links stay honest and bookmarkable, and a link is
      // never preventDefault'd into silence. This is what makes EVERY
      // screen-to-screen move live without wiring a single link by hand.
      var a = e.target.closest && e.target.closest("a[href]");
      if (a && !a.closest('[data-live-await-region],[data-live-await-regions]') && !e.defaultPrevented && !e.metaKey && !e.ctrlKey &&
          !e.shiftKey && !e.altKey && (a.getAttribute("target") || "") === "") {
        var href = a.getAttribute("href") || "";
        if (href.indexOf("/") === 0 && href.indexOf("//") !== 0 &&
            href.indexOf("#") < 0 && ws && ws.__navigate) {
          e.preventDefault();
          ws.__navigate(href);
          return;
        }
      }
      fireFrom(e.target, "click", ws, formData(e.target));
    });
    root.addEventListener("input", function (e) {
      var data = { value: e.target.value };
      if (closestAttrPrefix(e.target, "data-ev-input")) data = trackInput(e.target, data);
      fireFrom(e.target, "input", ws, data);
    });
    // a <select> / checkbox / radio commits on `change`, not `input`: a
    // form-for select carries `on-change` and must reach the server too
    root.addEventListener("change", function (e) {
      var t = e.target;
      var data = (t.type === "checkbox" || t.type === "radio")
        ? { value: t.value, checked: t.checked }
        : { value: t.value };
      if (closestAttrPrefix(t, "data-ev-change")) data = trackInput(t, data);
      fireFrom(t, "change", ws, data);
    });
    root.addEventListener("compositionstart", function (e) { e.target.__liveComposing = true; });
    root.addEventListener("compositionend", function (e) { e.target.__liveComposing = false; syncInput(e.target); });
    // Enter in an input fires its `on-keydown.enter` intent (if any), and
    // clears the field — the chat-composer gesture. The `.enter` modifier is
    // part of the attribute name (data-ev-keydown.enter), so match by prefix.
    root.addEventListener("keydown", function (e) {
      if (e.key !== "Enter" || e.shiftKey) return;
      var el = closestAttrPrefix(e.target, "data-ev-keydown");
      if (!el) return;
      e.preventDefault();
      var attr = el.__evAttr;
      // honour a `.enter` modifier if present; a bare keydown fires on any key
      if (attr.indexOf(".enter") >= 0 || attr === "data-ev-keydown") {
        relay(el, attr, ws, { value: e.target.value });
        if (el.tagName === "INPUT") el.value = "";
      }
    });

    // Escape is a DOCUMENT-level gesture, unlike Enter: when it is pressed
    // nothing in particular has focus, so an element that declares
    // `data-ev-keydown.escape` is found from the document. This is what lets a
    // dialog close without a pointer (loom.parts/drawer puts the attribute on
    // its ✕ and on the layer). Without it an escape was only ever a click.
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      var el = closestAttrPrefix(e.target, "data-ev-keydown.escape") ||
               document.querySelector("[data-ev-keydown\\.escape]");
      if (!el) return;
      e.preventDefault();
      relay(el, "data-ev-keydown.escape", ws, {});
    });

    // Back/Forward: the browser restored a previous URL, so tell the server to
    // re-route to it (a plain navigate event → the dispatcher re-projects).
    // No pushState here — the history entry already moved; we only sync state.
    // sendNav (not a bare send): when the socket is down the browser has
    // ALREADY moved the history entry, so a dropped frame would strand the page
    // on the screen the user left — buffering the route and flushing it on
    // reopen is what makes Back/Forward converge instead.
    window.addEventListener("popstate", function () {
      sendNav(location.pathname + location.search);
    });

    return ws;
  }

  // ── what the reader did to the page survives the mount ────────────────
  //
  // The first paint is server HTML; the socket's ["mount"] replaces it. A
  // reader who typed before the socket opened lost the text and the focus.
  // keepFields snapshots, before the swap, every field the reader CHANGED
  // (its value differs from what the HTML said: value ≠ defaultValue,
  // checked ≠ defaultChecked, a select off its default option) plus the
  // focused element and its selection; restoreFields finds each one again in
  // the new DOM — by id, else by name (radios by name + value, nth among the
  // same name), else by its child-index path — and puts it back. A restored
  // field the view binds (data-ev-input / data-ev-change) fires its event, so
  // the server's state learns the value instead of overwriting it later.
  function isTextLike(el) {
    return el.tagName === "TEXTAREA" ||
      (el.tagName === "INPUT" && !/^(checkbox|radio|file|button|submit|reset|image|hidden)$/.test(el.type));
  }
  function isDirty(el) {
    if (el.tagName === "SELECT") {
      var opts = el.options, i;
      if (el.multiple) {
        for (i = 0; i < opts.length; i++) if (opts[i].selected !== opts[i].defaultSelected) return true;
        return false;
      }
      var def = -1;
      for (i = 0; i < opts.length; i++) if (opts[i].defaultSelected) def = i;
      if (def < 0) for (i = 0; i < opts.length; i++) if (!opts[i].disabled) { def = i; break; }
      return opts.length > 0 && el.selectedIndex !== def;
    }
    if (el.type === "checkbox" || el.type === "radio") return el.checked !== el.defaultChecked;
    return isTextLike(el) && el.value !== el.defaultValue;
  }
  function childPath(root, el) {
    var path = [];
    for (var n = el; n && n !== root; n = n.parentNode) {
      var p = n.parentNode;
      if (!p) return null;
      path.unshift(domChildren(p).indexOf(n));
    }
    return path;
  }
  function sameName(root, tag, name, radioValue) {
    return Array.prototype.filter.call(root.getElementsByTagName(tag), function (o) {
      return o.getAttribute("name") === name &&
        (radioValue === null || (o.type === "radio" && o.value === radioValue));
    });
  }
  function keyOf(root, el) {
    if (el.id) return { id: el.id };
    var name = el.getAttribute("name");
    if (name) {
      var radio = el.type === "radio" ? el.value : null;
      return { name: name, tag: el.tagName, radio: radio,
               n: sameName(root, el.tagName, name, radio).indexOf(el) };
    }
    return { path: childPath(root, el) };
  }
  function findKey(root, key) {
    if (key.id) {
      var byId = document.getElementById(key.id);
      return byId && root.contains(byId) ? byId : null;
    }
    if (key.name) return sameName(root, key.tag, key.name, key.radio)[key.n] || null;
    if (!key.path) return null;
    var el = root;
    for (var i = 0; i < key.path.length && el; i++) el = domChildren(el)[key.path[i]];
    return el && el.nodeType === 1 ? el : null;
  }
  function keepFields(root) {
    var kept = { fields: [], focus: null };
    for (var el of root.querySelectorAll("input,textarea,select")) {
      if (!isDirty(el)) continue;
      var rec = { key: keyOf(root, el), tag: el.tagName, type: el.type };
      if (el.tagName === "SELECT")
        rec.selected = Array.prototype.map.call(el.selectedOptions, function (o) { return o.value; });
      else if (el.type === "checkbox" || el.type === "radio") rec.checked = el.checked;
      else rec.value = el.value;
      kept.fields.push(rec);
    }
    var active = document.activeElement;
    if (active && active !== root && root.contains(active)) {
      kept.focus = { key: keyOf(root, active), tag: active.tagName };
      try {
        if (typeof active.selectionStart === "number")
          kept.focus.sel = [active.selectionStart, active.selectionEnd, active.selectionDirection];
      } catch (_e) { /* a type with no selection API */ }
    }
    return kept;
  }
  function restoreFields(root, kept) {
    var bound = [];
    for (var rec of kept.fields) {
      var el = findKey(root, rec.key);
      if (!el || el.tagName !== rec.tag || el.type !== rec.type) continue;
      if (rec.selected) {
        for (var o of el.options) o.selected = rec.selected.indexOf(o.value) >= 0;
      } else if (rec.checked !== undefined) {
        el.checked = rec.checked;
      } else {
        el.value = rec.value;
      }
      var ev = isTextLike(el) ? "input" : "change";
      if (closestAttrPrefix(el, "data-ev-" + ev)) bound.push([el, ev]);
    }
    if (kept.focus) {
      var f = findKey(root, kept.focus.key);
      if (f && f.tagName === kept.focus.tag && typeof f.focus === "function") {
        try { f.focus({ preventScroll: true }); } catch (_e) { f.focus(); }
        if (kept.focus.sel) {
          try { f.setSelectionRange(kept.focus.sel[0], kept.focus.sel[1], kept.focus.sel[2] || "none"); }
          catch (_e) { /* not a text control after all */ }
        }
      }
    }
    for (var b of bound) b[0].dispatchEvent(new Event(b[1], { bubbles: true }));
  }

  // the value of the input nearest `el` (itself, or one in its container),
  // so a button click carries the message the user typed
  function formData(el) {
    if (el.tagName === "INPUT") return { value: el.value };
    var box = el.closest("div,footer,form,section") || el.parentElement;
    var input = box && box.querySelector("input");
    var data = input ? { value: input.value } : {};
    if (input) input.__clear = true;
    return data;
  }

  // walk up from `node` to the first element carrying an attribute whose name
  // starts with `prefix` (so `data-ev-keydown` matches `data-ev-keydown.enter`).
  // Stashes the matched attribute name on the element as `__evAttr`.
  function closestAttrPrefix(node, prefix) {
    var el = node;
    while (el && el.nodeType === 1) {
      if (el.attributes) {
        for (var i = 0; i < el.attributes.length; i++) {
          var name = el.attributes[i].name;
          if (name.indexOf(prefix) === 0) { el.__evAttr = name; return el; }
        }
      }
      el = el.parentElement;
    }
    return null;
  }

  // A `:navigate` event term carries the app-route to move to. live.app turns
  // it into a keyed PATCH (no reload), but the URL bar must follow so links
  // stay real and shareable, and Back/Forward work. `navTarget` finds the
  // navigate path in a term — a single ["navigate", "/x"] or the second slot
  // of a [["assign",…],["navigate","/x"]] batch — or null when there is none.
  function navTarget(term) {
    if (!Array.isArray(term) || term.length === 0) return null;
    if (term[0] === "navigate") return term[1];
    // a vector of terms: scan for a navigate among them
    if (Array.isArray(term[0])) {
      for (var i = 0; i < term.length; i++) {
        if (Array.isArray(term[i]) && term[i][0] === "navigate") return term[i][1];
      }
    }
    return null;
  }

  // relay the JSON term stored in attribute `attr` of `el` to the server
  const settlingActions = new WeakSet(), actionWarnings = new WeakMap();
  const awaitSelector = '[data-live-await-region],[data-live-await-regions]';
  function clearActionWarning(el) {
    const warning=actionWarnings.get(el);if(!warning)return;
    for(const [name,value] of [['title',warning.title],['aria-description',warning.description]])
      if(el.getAttribute(name)===warning.message){if(value===null)el.removeAttribute(name);else el.setAttribute(name,value);}
    actionWarnings.delete(el);
  }
  function relay(el, attr, ws, data, settled, onRelayed) {
    const scope = el.closest?.(awaitSelector);
    if (!settled && scope && ['data-ev-click','data-ev-submit','data-ev-keydown.enter'].includes(attr)) {
      if (settlingActions.has(scope) || el.matches?.(':disabled') || el.getAttribute('aria-disabled') === 'true') return false;
      const raw=scope.getAttribute('data-live-await-regions'),single=scope.getAttribute('data-live-await-region');
      let ids,regions=[];
      const blocked = error => {
        const message=error?.message||String(error);regions[0]?.[1]?.driver?.report?.(Error(message));
        if(el.isConnected){
          if(!actionWarnings.has(el))actionWarnings.set(el,{title:el.getAttribute('title'),description:el.getAttribute('aria-description')});
          actionWarnings.get(el).message=message;el.setAttribute('aria-description',message);el.title=message;
        }
        el.dispatchEvent(new CustomEvent('live:action-blocked',{bubbles:true,detail:{reason:message}}));
      };
      try {
        ids=raw===null?[single]:JSON.parse(raw);
        if(!Array.isArray(ids)||!ids.length||ids.length>16||ids.some(id=>typeof id!=='string'||!id.length||id.length>1024))throw Error('Invalid writing surface declaration.');
        regions=[...new Set(ids)].map(id=>{
          const matches=[...regionInstances].filter(([node,instance])=>node.isConnected&&instance.id===id);
          if(matches.length!==1||!matches[0][1].driver?.settle)throw Error('The writing surface changed. Reopen the current page before sharing.');
          return matches[0];
        });
      }catch(error){blocked(error);return false;}
      if (!ws || ws.readyState !== WebSocket.OPEN) { blocked(Error('You are offline. Reconnect before sharing your writing.')); return false; }
      const owner=regions[0][0].closest('#live-root')||Live.root,controller=new AbortController();
      const valid=()=>{
        if(!el.isConnected||!scope.isConnected||el.closest(awaitSelector)!==scope||
           scope.getAttribute('data-live-await-regions')!==raw||scope.getAttribute('data-live-await-region')!==single||
           regions.some(([node,instance])=>regionInstances.get(node)!==instance))
          throw Error('The writing surface changed. Reopen the current page before sharing.');
        if(el.matches?.(':disabled')||el.getAttribute('aria-disabled')==='true')throw Error('This action is no longer available. Your writing is retained.');
        if(ws.readyState!==WebSocket.OPEN)throw Error('You are offline. Reconnect before sharing your writing.');
      };
      settlingActions.add(scope);scope.setAttribute('aria-busy','true');
      const timer=setTimeout(()=>controller.abort(Error('Confirmation is still pending. Keep this page open and try again.')),30000);
      Promise.resolve().then(async()=>{
        for(;;){
          valid();
          await Promise.all(regions.map(([,instance])=>instance.driver.settle({signal:controller.signal})));
          // Ordinary native fields share the same ordered actor mailbox. Their
          // assignments and resulting guard patches must also precede dispatch.
          if(!owner?.__liveSettle)throw Error('Current Live tools are required before sharing.');
          await owner.__liveSettle({signal:controller.signal});valid();
          if(regions.every(([,instance])=>!instance.driver.ready||instance.driver.ready()))break;
        }
        clearActionWarning(el);
        // Read the current term after the complete patch and collective recheck.
        relay(el,attr,ws,data,true,onRelayed);
      }).catch(error=>blocked(controller.signal.aborted?controller.signal.reason:error))
        .finally(()=>{clearTimeout(timer);controller.abort();settlingActions.delete(scope);scope.removeAttribute('aria-busy');});
      return true;
    }
    var raw = el.getAttribute(attr);
    var term = null;
    try { term = raw ? JSON.parse(raw) : null; } catch (e) { term = null; }
    if (settled && term === null) throw Error('This action is no longer available. Your writing is retained.');
    // a navigate term also moves the URL bar (pushState), so the address
    // reflects the live route — a bookmarkable SPA over one socket. The
    // server still gets the SAME event and re-routes; this only syncs the URL.
    var nav = navTarget(term);
    if (nav) {
      try { history.pushState({ live: nav }, "", nav); } catch (_e) {}
      // The URL just moved. If the socket is down the term below is dropped, so
      // remember the route for the reopen flush — otherwise the address bar
      // would sit ahead of a stale page across the reconnect. When OPEN the
      // navigate rides in the term itself, so this only buffers on a dead
      // socket (no double send).
      if (!(ws && ws.readyState === WebSocket.OPEN) && ws && ws.__sendNav) {
        ws.__sendNav(nav);
      }
    }
    // A durable gesture (inside a [data-live-durable] node) is minted an
    // idempotency id, persisted to the outbox, and augmented into `data` as
    // "ev/id" BEFORE the send — so a drop-then-reconnect replays it exactly
    // once. A non-durable gesture (or an app without {outbox:true}) is a no-op
    // pass-through, unchanged.
    var d = (Live.__durable ? Live.__durable(el, term, data || {}) : (data || {}));
    // __send guards readyState (buffer while CONNECTING, drop when CLOSED) so a
    // fire before the handshake or after a drop never throws.
    (ws.__send || ws.send.bind(ws))(JSON.stringify(["event", term, d]));
    onRelayed?.();
    return true;
  }

  function fireFrom(target, evName, ws, data) {
    var el = closestAttrPrefix(target, "data-ev-" + evName);
    if (!el) return false;
    // the event TERM travels as a JSON attribute (data-ev-EVENT='<json>').
    // Send it back verbatim so the server performs exactly what the view
    // declared — the client never invents an intent, it only relays one.
    const clearComposer = () => {
      var box = target.closest("div,footer,form,section");
      var input = box && box.querySelector("input");
      if (input && input.__clear) { input.value = ""; input.__clear = false; }
    };
    // Clear only after relaying: a blocked publication retains attempted input.
    relay(el, el.__evAttr, ws, data, false, evName === "click" ? clearComposer : null);
    return true;
  }

  // the path of `el` under `root`, in the differ's coordinates (indices into
  // the text+element child list) — the inverse of `at`. Lets a tool point at
  // an element and ask the server about it.
  function pathOf(root, el) {
    var path = [];
    var top = rootEl(root);
    while (el && el !== top) {
      var parent = el.parentNode;
      if (!parent) return null;
      path.unshift(domChildren(parent).indexOf(el));
      el = parent;
    }
    return el === top ? path : null;
  }

  // Browser-only capability: never relay clipboard values into the event outbox.
  async function copy(button) {
    var value = button.getAttribute("data-copy") || "";
    var label = button.querySelector(".kn-lab, [data-copy-label]");
    var original = label ? label.textContent : "";
    var ticket = {}; button.__copyTicket = ticket;
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) throw Error("clipboard unavailable");
      await navigator.clipboard.writeText(value);
      if (!button.isConnected || button.__copyTicket !== ticket || button.getAttribute("data-copy") !== value) return;
      if (label) label.textContent = button.getAttribute("data-copy-success") || "Copied";
      button.setAttribute("aria-live", "polite");
      setTimeout(function () {
        if (button.isConnected && button.__copyTicket === ticket && label) label.textContent = original;
      }, 1800);
    } catch (_e) {
      if (!button.isConnected || button.__copyTicket !== ticket || button.getAttribute("data-copy") !== value) return;
      // Prefer the visible, server-rendered field. Never insert unmanaged
      // children into a live tree: they would shift subsequent patch paths.
      var scope = button.closest("[data-copy-scope]") || button.parentNode;
      var field = Array.prototype.find.call(scope.querySelectorAll("input[readonly], textarea[readonly]"),
        function (candidate) { return candidate.value === value; });
      if (!field) {
        var dialog = document.createElement("dialog");
        dialog.style.cssText = "max-width:90vw;width:38em;box-sizing:border-box";
        var heading = document.createElement("p");
        heading.textContent = button.getAttribute("data-copy-failure") || "Select and copy manually";
        field = document.createElement("textarea"); field.readOnly = true;
        field.setAttribute("data-copy-fallback", "");
        field.style.cssText = "display:block;width:100%;min-height:8em;box-sizing:border-box";
        var close = document.createElement("button"); close.type = "button";
        close.textContent = "×";
        close.setAttribute("aria-label", button.getAttribute("data-copy-close") || "Close");
        close.onclick = function () { dialog.close(); };
        dialog.append(heading, field, close);
        dialog.addEventListener("close", function () { dialog.remove(); });
        document.body.appendChild(dialog);
        dialog.showModal();
      }
      field.value = value;
      field.setAttribute("aria-label", button.getAttribute("data-copy-failure") || "Select and copy manually");
      field.focus(); field.select();
      if (label) label.textContent = field.getAttribute("aria-label");
      button.setAttribute("aria-live", "polite");
    }
  }

  window.Live = { copy: copy, connect: connect, applyOp: applyOp, render: render, hydrateText: hydrateText,
                  registerRegion, syncRegions,
                  disposeRegions(root) { for (const [el] of regionInstances) if (el === root || root.contains(el)) disposeRegion(el); },
                  at: at, pathOf: pathOf, ws: null, root: null };
  var Live = window.Live;
})();

// priv/lib/js/portable-leaves.mjs — host functions ordinary programs reach
// (renderers, formatters, parsers), with the BEAM's answers on the JS value
// model. Measured on the BEAM 2026-11-22; test/bl/js_portable_leaves_test.bl
// pins them. Arithmetic is one JS call; every algorithm lives in js.portable
// (Beam Lisp), reached through `lateModule` like js.binary.
import * as R from "./rt.mjs";
import { reOpts, badarg, badarith, exactInteger, beamOnly } from "./host-leaves.mjs";
const { Tup, Flt } = R;
const kw = (s) => R.kw(s);
const T = (...xs) => new Tup(xs);
const fnum = (x, what) => { if (x instanceof Flt) return x.v; if (exactInteger(x)) return Number(x); badarg(what); };
const toInt = (v) => (Number.isSafeInteger(v) ? v : R.add(BigInt(v), 0));
const halfAway = (v) => (v < 0 ? -Math.round(-v) : Math.round(v));
const mathFloat = (what, f) => (...xs) => { const v = f(...xs.map((x) => fnum(x, what))); if (!Number.isFinite(v)) badarith(); return R.flt(v); };

/** The leaves, given leaves.mjs's `lateModule` (no import cycle). */
export function portableLeaves(lateModule) {
  const P = (name) => (...args) => lateModule("js.portable")["d_" + name](...args);
  const B = () => lateModule("js.binary");
  const appEnv = new Map();
  const appKey = (app, k) => R.printStr(app) + "\u0000" + R.printStr(k);
  return {
  "erlang/round/1": (x) => (exactInteger(x) ? x : toInt(halfAway(fnum(x, "round")))),
  "erlang/ceil/1": (x) => (exactInteger(x) ? x : toInt(Math.ceil(fnum(x, "ceil")))),
  "erlang/floor/1": (x) => (exactInteger(x) ? x : toInt(Math.floor(fnum(x, "floor")))),
  "erlang/float/1": (x) => R.flt(fnum(x, "float")),
  "erlang/binary_to_integer/1": (s) => P("parse_integer")(s, 10),
  "erlang/binary_to_integer/2": (s, base) => P("parse_integer")(s, base),
  "erlang/binary_to_float/1": (s) => {
    if (typeof s !== "string" || !/^[+-]?[0-9]+\.[0-9]+([eE][+-]?[0-9]+)?$/.test(s)) badarg("binary_to_float");
    return R.flt(parseFloat(s));
  },
  "erlang/phash2/1": beamOnly("erlang/phash2/1"),
  "erlang/phash2/2": beamOnly("erlang/phash2/2"),
  "math/pow/2": mathFloat("pow", Math.pow),
  "math/sqrt/1": mathFloat("sqrt", Math.sqrt),
  "math/log/1": mathFloat("log", Math.log),
  "math/log2/1": mathFloat("log2", Math.log2),
  "math/log10/1": mathFloat("log10", Math.log10),
  "math/exp/1": mathFloat("exp", Math.exp),
  "math/sin/1": mathFloat("sin", Math.sin),
  "math/cos/1": mathFloat("cos", Math.cos),
  "math/tan/1": mathFloat("tan", Math.tan),
  "math/atan2/2": mathFloat("atan2", Math.atan2),
  "math/floor/1": mathFloat("floor", Math.floor),
  "math/ceil/1": mathFloat("ceil", Math.ceil),
  "math/pi/0": () => R.flt(Math.PI),
  "calendar/date_to_gregorian_days/3": (y, m, d) => P("gregorian_days")(y, m, d),
  "Elixir.URI/encode_www_form/1": (s) => P("www_form_encode")(s),
  "Elixir.URI/decode_www_form/1": (s) => P("www_form_decode")(s),
  "Elixir.String/trim_leading/2": (s, t) => P("trim_leading")(s, t),
  "Elixir.String/trim_trailing/2": (s, t) => P("trim_trailing")(s, t),
  "binary/encode_hex/1": (s) => P("hex")(s, false),
  "binary/encode_hex/2": (s, c) => P("hex")(s, c === kw("lowercase")),
  "binary/match/3": (s, pattern, opts) => {
    const scope = reOpts(opts).get("scope");
    if (!scope) return B().d_match(s, pattern);
    const [start, len] = scope.items;
    const found = B().d_match(B().d_part(s, start, len), pattern);
    return found instanceof Tup ? T(found.items[0] + start, found.items[1]) : found;
  },
  "Elixir.Regex/split/2": (r, s) => P("regex_split")(r.global(), s, false, false, 0),
  "Elixir.Regex/split/3": (r, s, opts) => {
    const o = reOpts(opts);
    return P("regex_split")(r.global(), s, o.get("include_captures") === true, o.get("trim") === true, o.get("parts") ?? 0);
  },
  // Paths are text: the pure ones answer; a page has no filesystem, so every
  // File call (and Path.expand, which reads the cwd) is a named refusal. Code
  // that reaches them compiles, and fails loudly only if a page runs it.
  "Elixir.Path/join/2": (a, b) => P("path_join")(a, b),
  "Elixir.Path/basename/1": (p) => P("path_basename")(p),
  "Elixir.Path/dirname/1": (p) => P("path_dirname")(p),
  "Elixir.Path/extname/1": (p) => P("path_extname")(p),
  "Elixir.Path/rootname/1": (p) => P("path_rootname")(p),
  ...Object.fromEntries(["Elixir.Path/expand/1", "Elixir.Path/expand/2", "Elixir.Path/wildcard/1",
    "Elixir.File/read!/1", "Elixir.File/read/1", "Elixir.File/write!/2", "Elixir.File/write/2",
    "Elixir.File/regular?/1", "Elixir.File/exists?/1", "Elixir.File/dir?/1", "Elixir.File/ls!/1", "Elixir.File/ls/1",
    "Elixir.File/mkdir_p!/1", "Elixir.File/rm/1", "Elixir.File/rm!/1", "Elixir.File/stat!/1", "Elixir.File/stat!/2",
    "Elixir.File/rename!/2", "Elixir.File/cwd!/0"].map((k) => [k, beamOnly(k)])),
  // A page loads namespaces from its module graph, never from source files.
  "Elixir.BeamLisp.Loader/source_path/1": () => null,
  // A page has no process environment: every variable is unset.
  "Elixir.System/get_env/1": () => null,
  "Elixir.System/get_env/2": (_k, d) => d,
  "Elixir.BeamLisp.Env/os_get_env/1": () => null,
  "Elixir.Application/get_env/2": (app, k) => (appEnv.has(appKey(app, k)) ? appEnv.get(appKey(app, k)) : null),
  "Elixir.Application/get_env/3": (app, k, d) => (appEnv.has(appKey(app, k)) ? appEnv.get(appKey(app, k)) : d),
  "Elixir.Application/put_env/3": (app, k, v) => { appEnv.set(appKey(app, k), v); return kw("ok"); },
  };
}

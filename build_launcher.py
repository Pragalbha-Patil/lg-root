"""Build Minimal Home: ATV-style sections + relay-service wiring.

Run `python build_launcher.py` to regenerate launcher-app/index.html and appinfo.json.
Use `--check` to verify tracked outputs are up to date (CI gate).
"""
import argparse
import json
import os
import re
import sys
import html as htmllib

BASE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE, "launcher-app")
SVC_DIR = os.path.join(BASE, "launcher-service")
SELF = "org.minimal.home"
SETTINGS_ID = "com.palm.app.settings"
SETTINGS_ICON = "icons/com.palm.app.settings.png"
LG_HOME_ID = "__LGHOME__"

DEFAULTS = {
    "version": "1.0.0",
    "header": {"text": "Welcome", "brand": "Minimal Home"},
    "ui": {
        "system": [
            "com.webos.app.discovery",
            "com.webos.app.mediadiscovery",
            SETTINGS_ID,
        ],
        "appsPriority": [
            "youtube.leanback.v4", "netflix", "amazon", "hotstar",
            "com.zee5.app", "com.apple.appletv", "io.strem.tv",
            "org.mariotaku.ihsplay", "org.litefin.app",
        ],
    },
}

# Input ports are NOT hardcoded per device: the TV publishes a launch point
# for every connected input (bookmarks like com.webos.app.hdmi2 carry the
# per-port PhysicalAddress/value params) plus the built-in com.webos.app.livetv.
# This regex only recognises the OS's fixed input-app id namespace; which ports
# actually exist comes from the system live (ps5 unplugged now, replug later)
# and the same classifier lives in launcher-service/service.js as INPUT_ID_RE.
MH_INPUT_RE = re.compile(r"^com\.webos\.app\.(livetv|hdmi\d+|av\d+|scart|dp\d+|usbc\d+)$")


def is_input_id(i):
    return bool(i and MH_INPUT_RE.match(i))


def load_config():
    cfg = dict(DEFAULTS)
    p = os.path.join(APP_DIR, "config.json")
    try:
        with open(p, encoding="utf-8") as f:
            user = json.load(f)
    except Exception:
        return cfg
    if isinstance(user, dict):
        for key in ("version", "ui"):
            if key in user and isinstance(user[key], type(DEFAULTS[key])):
                cfg[key] = user[key]
        if isinstance(user.get("header"), dict):
            cfg["header"] = dict(DEFAULTS["header"], **user["header"])
    return cfg


def load_tiles():
    with open(os.path.join(APP_DIR, "tiles.json"), encoding="utf-8") as f:
        data = json.load(f)
    return data.get("launchPoints", [])


def load_usage():
    for p in (os.path.join(SVC_DIR, "usage.json"), os.path.join(APP_DIR, "usage.json")):
        try:
            with open(p, encoding="utf-8") as f:
                u = json.load(f)
            if isinstance(u, dict):
                return u
        except Exception:
            continue
    return {}


def classify(tiles, cfg):
    sys_ids = {s for s in cfg["ui"]["system"] if s}
    apps, inputs, sysrow = [], [], []
    for lp in tiles:
        i = lp.get("id", "")
        if i == SELF or lp.get("hidden"):
            continue
        is_sys = bool(lp.get("systemApp"))
        if is_input_id(i) or lp.get("lptype") == "bookmark":
            inputs.append(tile_dict(lp))
            continue
        if i == SETTINGS_ID or (is_sys and i in sys_ids):
            sysrow.append(tile_dict(lp))
            continue
        if is_sys or i in sys_ids:
            continue
        apps.append(tile_dict(lp))
    if SETTINGS_ID in sys_ids and not any(t["id"] == SETTINGS_ID for t in sysrow):
        sysrow.append({"id": SETTINGS_ID, "title": "Settings",
                       "icon": SETTINGS_ICON, "params": None})
    sysrow.append({"id": LG_HOME_ID, "title": "LG Home", "icon": "", "params": None})
    return apps, inputs, sysrow


def tile_dict(lp):
    return {
        "id": lp.get("id", ""),
        "title": lp.get("title") or lp.get("id", ""),
        "icon": lp.get("largeIcon") or lp.get("icon") or "",
        "params": (lp.get("params")
                   if isinstance(lp.get("params"), dict) and lp.get("params") else None),
    }


def sort_key(t, usage, priority):
    if t["id"] in usage:
        return (-1, -usage[t["id"]])
    try:
        return (0, priority.index(t["id"]))
    except ValueError:
        return (1, t["title"].lower())


def tile_html(t):
    if t.get("icon"):
        art = '<img src="%s" alt="" data-title="%s">' % (t["icon"], htmllib.escape(t["title"], quote=True))
    else:
        art = '<div class="initial">%s</div>' % htmllib.escape((t["title"] or "?").strip()[:1].upper())
    return ('<div class="tile" tabindex="0" role="button" data-id="%s" data-params="%s">'
            '<div class="art">%s</div><div class="label">%s</div></div>'
            % (htmllib.escape(t["id"]), htmllib.escape(json.dumps(t["params"]) if t["params"] else ""),
               art, htmllib.escape(t["title"])))


def section_html(tiles, usage, priority, sort=False):
    ts = sorted(tiles, key=lambda t: sort_key(t, usage, priority)) if sort else tiles
    return "\n".join(tile_html(t) for t in ts)


TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__MH_TITLE__</title>
<style>
:root{--accent:#8fb6ff;--accent-soft:rgba(143,182,255,.35);--tile-art-h:126px;--tile-icon:104px;--tile-label:22px;--grid-min:310px}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:#0b0d11;color:#f2f4f8;font-family:"LG Smart UI","Segoe UI",Arial,sans-serif;padding:54px 76px 40px;overflow:hidden;transition:background .3s}
body::before{content:"";position:fixed;inset:0;pointer-events:none;
background:radial-gradient(1400px 600px at 50% -10%,var(--accent-soft),transparent 60%)}
body.density-compact{--tile-art-h:94px;--tile-icon:78px;--tile-label:17px;--grid-min:272px}
body.density-large{--tile-art-h:160px;--tile-icon:132px;--tile-label:26px;--grid-min:368px}
body.no-labels .label{display:none}
header{display:flex;align-items:center;justify-content:space-between;margin-bottom:30px;position:relative;z-index:2}
h1{font-size:34px;font-weight:200;letter-spacing:3px;color:#e8ecf1}
h1 b{font-weight:700}
.hright{display:flex;align-items:center;gap:28px}
#settingsBtn{display:flex;align-items:center;gap:11px;background:rgba(255,255,255,.08);border:3px solid transparent;border-radius:999px;color:#d8dee7;font-size:19px;padding:11px 26px 11px 20px;cursor:pointer;transition:transform .13s,background .13s,border-color .13s}
#settingsBtn .gear{font-size:22px}
#settingsBtn:focus{outline:none;background:rgba(255,255,255,.15);border-color:var(--accent);box-shadow:0 10px 30px rgba(0,0,0,.5);color:#fff}
#clock{font-size:42px;font-weight:200;color:#c3ccd8;text-align:right;line-height:1.1;min-width:210px}
#clock small{display:block;font-size:16px;color:#6b7686;margin-top:2px}
.section{font-size:18px;font-weight:500;letter-spacing:2px;color:#aeb8c6;margin:34px 0 18px;position:relative}
.row{display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--grid-min),1fr));gap:34px 36px;position:relative}
.tile{position:relative;background:#16181e;border:3px solid transparent;border-radius:22px;padding:0;cursor:pointer;overflow:hidden;transition:transform .13s ease,background .13s ease,border-color .13s ease,box-shadow .13s ease}
.tile .art{aspect-ratio:16/9;min-height:var(--tile-art-h);display:flex;align-items:center;justify-content:center;background:linear-gradient(150deg,#1e222b,#12141a)}
.tile .art img{width:var(--tile-icon);height:var(--tile-icon);object-fit:contain;filter:drop-shadow(0 8px 18px rgba(0,0,0,.55))}
.tile .initial{width:var(--tile-icon);height:var(--tile-icon);border-radius:24px;display:flex;align-items:center;justify-content:center;font-size:calc(var(--tile-icon)*.46);font-weight:700;background:#232936;color:#93a3ba}
.tile .label{font-size:var(--tile-label);font-weight:400;color:#d6dce5;text-align:center;padding:15px 12px 17px;background:rgba(255,255,255,.035);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tile .pin{position:absolute;top:12px;right:16px;font-size:24px;color:var(--accent);text-shadow:0 4px 12px rgba(0,0,0,.8);opacity:0;transition:opacity .2s}
.tile.pinned .pin{opacity:.95}
.tile:focus{outline:none;background:#1b1f27;border-color:var(--accent);transform:scale(1.06);box-shadow:0 18px 44px rgba(0,0,0,.6),0 0 0 6px var(--accent-soft)}
.tile:focus .label{color:#fff;font-weight:600}
#err{display:none;margin-top:40px;font-size:20px;color:#ff9a9a}
.dim{position:fixed;inset:0;background:rgba(8,10,14,.72);opacity:0;pointer-events:none;transition:opacity .18s;z-index:40}
.dim.show{opacity:1;pointer-events:auto}
.panel{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%) scale(.96);width:min(780px,92vw);max-height:82vh;overflow:auto;background:#12151b;border:1px solid #242a35;border-radius:26px;padding:26px 30px;opacity:0;pointer-events:none;transition:opacity .16s,transform .16s;z-index:50}
.panel.show{opacity:1;pointer-events:auto;transform:translate(-50%,-50%) scale(1)}
.panel-head{font-size:21px;font-weight:600;color:#e8ecf1;margin-bottom:20px;letter-spacing:1px;display:flex;justify-content:space-between;align-items:center}
.panel-head small{font-size:14px;font-weight:400;color:#5f6b7d}
.rowset{display:flex;flex-direction:column;gap:10px}
.srow{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:14px 18px;border-radius:16px;background:#171a21;border:2px solid transparent;cursor:pointer;color:#dfe6ef;font-size:20px}
.srow .val{color:#9fb0c6;font-size:19px}
.srow:focus{outline:none;background:#1d212b;border-color:var(--accent);transform:scale(1.02)}
.srow:focus .val{color:#e7edf6}
.dots{display:flex;gap:9px}
.dot{width:24px;height:24px;border-radius:50%;border:2px solid rgba(255,255,255,.25)}
.dot.sel{box-shadow:0 0 0 3px var(--accent-soft);border-color:#fff}
.opt{width:min(420px,86vw);padding:12px}
.optrow{padding:14px 22px;border-radius:14px;background:#171a21;color:#dfe6ef;cursor:pointer;margin:8px 0;border:2px solid transparent;font-size:19px}
.optrow:focus{outline:none;background:#1d212b;border-color:var(--accent)}
.search{position:fixed;left:50%;top:110px;transform:translateX(-50%);width:min(880px,94vw);background:#12151b;border:1px solid #242a35;border-radius:26px;padding:24px 28px;opacity:0;pointer-events:none;transition:opacity .16s;z-index:50}
.search.show{opacity:1;pointer-events:auto}
.search .q{font-size:32px;font-weight:200;color:#e8ecf1;letter-spacing:2px;border-bottom:2px solid var(--accent-soft);padding-bottom:16px;margin-bottom:18px}
.search .q b{color:var(--accent)}
.search .hint{font-size:14px;color:#5f6b7d;text-align:right;margin-bottom:12px}
.small{font-size:14px;color:#5f6b7d}
</style>
</head>
<body>
<header>
<h1>__WELCOME_TEXT__ <b>__WELCOME_BRAND__</b></h1>
<div class="hright">
<div id="settingsBtn" class="tile" tabindex="0" role="button" aria-label="Settings"><span class="gear">&#9881;</span><span>Settings</span></div>
<div id="clock">--:--<small></small></div>
</div>
</header>
<div class="section">Apps</div>
<div class="row" id="grid">
__APPS__
</div>
<div class="section">Inputs</div>
<div class="row" id="inputs">
__INPUTS__
</div>
<div class="section">System</div>
<div class="row" id="sysrow">
__SYS__
</div>
<div id="err"></div>
<div id="dim" class="dim"></div>
<div id="settingsPanel" class="panel">
  <div class="panel-head">Settings <small id="panelSub">Minimal Home</small></div>
  <div id="settingsRows" class="rowset"></div>
</div>
<div id="optionsPanel" class="panel opt">
  <div class="panel-head">Options</div>
  <div id="optionsRows" class="rowset"></div>
</div>
<div id="searchBox" class="search">
  <div id="searchQ" class="q"></div>
  <div id="searchRows" class="rowset"></div>
  <div class="hint">type to find an app &#183; &#8592; &#8594; to move &#183; OK to open &#183; BACK to close</div>
</div>
<script src="spatial-nav.js"></scr__TAG__pt>
<script>
(function(){
"use strict";
try { if (window.PalmSystem && PalmSystem.stageReady) PalmSystem.stageReady(); } catch (e) {}

var SVC = "luna://org.minimal.home.service";
var BUILD = "__MH_VERSION__"; window.__MHBUILD = BUILD;
var SVC_LIST_M = "getTiles";
var SVC_LAUNCH_M = "launchApp";
function svcCall(uri, method, params, onOk, onErr){
  window.__mhKeep = window.__mhKeep || [];
  function done(fn, arg){ try { fn(arg); } catch (e) {} }
  try {
    if (navigator.service && navigator.service.request) {
      var req = navigator.service.request(uri, { method: method, parameters: params || {}, subscribe: false,
        onSuccess: function(r){ done(onOk, r); }, onFailure: function(e){ done(onErr, e); } });
      window.__mhKeep.push(req);
      return;
    }
  } catch (e) {}
  try {
    var b = new PalmServiceBridge();
    window.__mhKeep.push(b);
    b.onservicecallback = function(msg){
      var d;
      try { d = JSON.parse(msg); } catch (e) { done(onErr, { errorText: "bad response" }); return; }
      if (d && d.returnValue === false) done(onErr, d); else done(onOk, d);
    };
    b.call(uri + "/" + method, JSON.stringify(params || {}));
  } catch (e) { done(onErr, { errorText: String((e && e.message) || e) }); }
}
function launch(id, params){
  var p = { id: id };
  if (params) {
    for (var k in params) {
      if (!Object.prototype.hasOwnProperty.call(params, k)) continue;
      if (k === "id") continue; // lp params carry id:"uniqueId" marker; never clobber p.id
      p[k] = params[k];
    }
  }
  svcCall(SVC, SVC_LAUNCH_M, p, function(){}, function(e){
    var el = document.getElementById("err");
    el.style.display = "block";
    el.textContent = "Could not open app: " + ((e && e.errorText) || "unknown error");
  });
}
function tileParams(el){
  try { return JSON.parse(el.getAttribute("data-params") || "null"); } catch (e) { return null; }
}
var SYS_IDS = __MH_SYS_IDS__;
var SETTINGS_TILE = __MH_SETTINGS_TILE__;
var SELF_ID = "org.minimal.home";
var SVC_PREFS_GET_M = "getPrefs";
var SVC_PREFS_SET_M = "setPrefs";
var SVC_LGHOME_M = "openLGHome";

var __mhTiles = []; window.__mhTiles = __mhTiles;
var PREFS = { accent: "steel", tileSize: "standard", labels: true, clock24: false, sort: "mru", pinned: [], hidden: [], focusId: "" };
var ACCENTS = {
  steel:   { name: "Steel",   main: "#8fb6ff", soft: "rgba(143,182,255,.35)" },
  emerald: { name: "Emerald", main: "#4ade9d", soft: "rgba(74,222,157,.35)" },
  violet:  { name: "Violet",  main: "#b79cff", soft: "rgba(183,156,255,.35)" },
  amber:   { name: "Amber",   main: "#ffc46b", soft: "rgba(255,196,107,.35)" },
  crimson: { name: "Crimson", main: "#ff7a8a", soft: "rgba(255,122,138,.35)" }
};
var BACK_KEYS = { 461: 1, 27: 1, 8: 1 };
var overlay = { mode: null };
var lastFocusEl = null;
var holdTimer = null, holdDir = null, holdN = 0;

function esc(s){
  return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function tile4(id){
  var els = document.querySelectorAll(".tile"), i;
  for (i = 0; i < els.length; i++) if (els[i].getAttribute("data-id") === id) return els[i];
  return null;
}
function dirOf(kc){ return kc === 37 ? "left" : kc === 39 ? "right" : kc === 38 ? "up" : kc === 40 ? "down" : null; }

function tick(){
  var n = new Date(), p = function(x){ return (x < 10 ? "0" : "") + x; };
  var days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  var h = n.getHours(), ap = "";
  if (!PREFS.clock24) { ap = h >= 12 ? "PM" : "AM"; h = h % 12; if (h === 0) h = 12; }
  document.getElementById("clock").innerHTML =
    (PREFS.clock24 ? p(h) : h) + ":" + p(n.getMinutes()) + " " + ap +
    "<small>" + days[n.getDay()] + " " + p(n.getDate()) + "." + p(n.getMonth() + 1) + "</small>";
}
function applyPrefs(){
  var b = document.body;
  b.classList.remove("density-compact", "density-standard", "density-large", "no-labels");
  b.classList.add(PREFS.tileSize === "compact" ? "density-compact" : PREFS.tileSize === "large" ? "density-large" : "density-standard");
  if (!PREFS.labels) b.classList.add("no-labels");
  var a = ACCENTS[PREFS.accent] || ACCENTS.steel;
  b.style.setProperty("--accent", a.main);
  b.style.setProperty("--accent-soft", a.soft);
  tick();
}
function persistFocus(){
  var el = document.activeElement;
  if (el && el.classList && el.classList.contains("tile")) {
    try { localStorage.setItem("mh.focus", el.getAttribute("data-id") || ""); } catch (e) {}
  }
}
function restoreFocus(){
  var wanted = null, el = null;
  try { wanted = localStorage.getItem("mh.focus"); } catch (e) {}
  el = wanted ? tile4(wanted) : null;
  el = el || document.querySelector("#grid .tile");
  try { if (el) el.focus(); } catch (e) {}
}

function rebuild(tiles, liveInputs){
  __mhTiles = tiles || [];
  window.__mhTiles = __mhTiles;
  var grid = document.getElementById("grid");
  var inputs = document.getElementById("inputs");
  var sysrow = document.getElementById("sysrow");
  var list = { grid: [], inputs: [], sys: [] };
  __mhTiles.forEach(function(t){
    if (!t || !t.id || t.id === SELF_ID) return;
    if (PREFS.hidden.indexOf(t.id) >= 0) return;
    if (SYS_IDS.indexOf(t.id) >= 0) { list.sys.push(t); }
    else { list.grid.push(t); }
  });
  (liveInputs || []).forEach(function(t){
    if (!t || !t.id || t.id === SELF_ID) return;
    if (PREFS.hidden.indexOf(t.id) >= 0) return;
    list.inputs.push(t);
  });
  var hasSettings = false;
  list.sys.forEach(function(t){ if (t.id === SETTINGS_TILE.id) hasSettings = true; });
  if (SETTINGS_TILE && PREFS.hidden.indexOf(SETTINGS_TILE.id) < 0 && !hasSettings) list.sys.push(SETTINGS_TILE);
  grid.innerHTML = ""; inputs.innerHTML = ""; sysrow.innerHTML = "";
  function reorder(arr){
    var pins = [], rest = [];
    arr.forEach(function(t){ (PREFS.pinned.indexOf(t.id) >= 0 ? pins : rest).push(t); });
    pins.sort(function(a, b){ return PREFS.pinned.indexOf(a.id) - PREFS.pinned.indexOf(b.id); });
    return pins.concat(rest);
  }
  reorder(list.grid).forEach(function(t){ grid.appendChild(tileEl(t)); });
  reorder(list.inputs).forEach(function(t){ inputs.appendChild(tileEl(t)); });
  reorder(list.sys).forEach(function(t){ sysrow.appendChild(tileEl(t)); });
  restoreFocus();
}
function tileEl(t){
  var d = document.createElement("div");
  d.className = t.pinned ? "tile pinned" : "tile"; d.tabIndex = 0;
  d.setAttribute("role", "button");
  d.setAttribute("data-id", t.id);
  try { d.setAttribute("data-params", t.params ? JSON.stringify(t.params) : ""); } catch (e) {}
  var art = document.createElement("div");
  art.className = "art";
  if (t.icon) {
    var img = document.createElement("img");
    img.src = t.icon; img.alt = "";
    img.setAttribute("data-title", t.title || t.id);
    img.addEventListener("error", function(){
      try { art.replaceChild(mkInitialEl(t.title), img); } catch (e) {}
    });
    art.appendChild(img);
  } else {
    art.appendChild(mkInitialEl(t.title));
  }
  d.appendChild(art);
  var s = document.createElement("span");
  s.className = "label"; s.textContent = t.title || t.id;
  d.appendChild(s);
  if (t.pinned) {
    var pin = document.createElement("span");
    pin.className = "pin"; pin.textContent = "\u2605";
    d.appendChild(pin);
  }
  d.addEventListener("click", function(){ doLaunch(d); });
  return d;
}
function doLaunch(el){
  var id = el.getAttribute("data-id");
  if (!id) return;
  if (id === "__LGHOME__") { svcCall(SVC, SVC_LGHOME_M, {}, function(){}, function(){}); return; }
  launch(id, tileParams(el));
}
function launchFromId(id){
  if (id === "__LGHOME__") { svcCall(SVC, SVC_LGHOME_M, {}, function(){}, function(){}); return; }
  var t = null;
  __mhTiles.forEach(function(x){ if (x.id === id) t = x; });
  launch(id, (t && t.params) || null);
}
function mkInitialEl(title){
  var d = document.createElement("div");
  d.className = "initial";
  d.textContent = ((title || "?").trim().charAt(0) || "?").toUpperCase();
  return d;
}

var SETTING_ROWS = [
  { key: "tvsettings", label: "TV settings", type: "action", fmt: function(){ return "open"; } },
  { key: "accent", label: "Accent color", type: "accent" },
  { key: "tileSize", label: "Tile size", type: "choice", opts: ["compact", "standard", "large"],
    fmt: function(v){ return v.charAt(0).toUpperCase() + v.slice(1); } },
  { key: "labels", label: "App labels", type: "toggle", fmt: function(v){ return v ? "On" : "Off"; } },
  { key: "clock24", label: "Clock", type: "toggle", fmt: function(v){ return v ? "24-hour" : "12-hour"; } },
  { key: "sort", label: "Sort order", type: "choice", opts: ["mru", "alpha", "pinned"],
    fmt: function(v){ return v === "mru" ? "Most used" : v === "alpha" ? "Alphabetical" : "Pinned first"; } },
  { key: "manage", label: "Hidden apps", type: "action", fmt: function(){ return "open"; } },
  { key: "reset", label: "Reset all", type: "action", fmt: function(){ return "reset"; } }
];
function findRow(key){ for (var i = 0; i < SETTING_ROWS.length; i++) if (SETTING_ROWS[i].key === key) return SETTING_ROWS[i]; return null; }
function commitPrefs(onDone){
  svcCall(SVC, SVC_PREFS_SET_M, {
    accent: PREFS.accent, tileSize: PREFS.tileSize, labels: PREFS.labels, clock24: PREFS.clock24,
    sort: PREFS.sort, pinned: PREFS.pinned.slice(), hidden: PREFS.hidden.slice(), focusId: PREFS.focusId
  }, function(){ if (onDone) onDone(); }, function(){ if (onDone) onDone(); });
}
function changeSetting(key, delta){
  var r = findRow(key);
  if (!r) return;
  if (r.type === "toggle") {
    PREFS[key] = !PREFS[key];
  } else if (r.type === "choice") {
    var i = r.opts.indexOf(PREFS[key]);
    PREFS[key] = r.opts[(i + delta + r.opts.length) % r.opts.length];
  } else if (r.type === "accent") {
    var ks = Object.keys(ACCENTS), j = ks.indexOf(PREFS[key]);
    PREFS[key] = ks[(j + delta + ks.length) % ks.length];
  }
  applyPrefs(); updateRow(key);
  commitPrefs(function(){ if (key === "sort") refresh(); });
}
function updateRow(key){
  var row = document.querySelector('#settingsRows .srow[data-key="' + key + '"]');
  if (!row) return;
  var r = findRow(key);
  if (!r) return;
  var val = row.querySelector(".val");
  if (!val) return;
  if (r.type === "accent") {
    val.innerHTML = ["steel", "emerald", "violet", "amber", "crimson"].map(function(name){
      return '<span class="dot' + (name === PREFS.accent ? " sel" : "") + '" data-name="' + name + '" style="background:' + ACCENTS[name].main + '"></span>';
    }).join("");
  } else {
    val.textContent = r.fmt(PREFS[key]);
  }
}
function focusRow(key){
  var r = document.querySelector('#settingsRows .srow[data-key="' + key + '"]');
  try { if (r) r.focus(); } catch (e) {}
}
function renderSettings(){
  var box = document.getElementById("settingsRows");
  var html = [], i, r, key;
  for (i = 0; i < SETTING_ROWS.length; i++) {
    r = SETTING_ROWS[i]; key = PREFS[r.key];
    if (r.type === "accent") {
      var dots = ["steel", "emerald", "violet", "amber", "crimson"].map(function(name){
        return '<span class="dot' + (name === PREFS.accent ? " sel" : "") + '" data-name="' + name + '" style="background:' + ACCENTS[name].main + '"></span>';
      }).join("");
      html.push('<div class="srow" tabindex="0" data-key="accent"><span class="sl">' + r.label + '</span><span class="val">' + dots + '</span></div>');
    } else if (r.type === "choice" || r.type === "toggle") {
      html.push('<div class="srow" tabindex="0" data-key="' + r.key + '"><span class="sl">' + r.label + '</span><span class="val">' + r.fmt(key) + '</span></div>');
    } else {
      html.push('<div class="srow" tabindex="0" data-key="' + r.key + '"><span class="sl">' + r.label + '</span><span class="val">' + r.fmt(key) + '</span></div>');
    }
  }
  box.innerHTML = html.join("");
}
function resetAll(){
  PREFS = { accent: "steel", tileSize: "standard", labels: true, clock24: false, sort: "mru", pinned: [], hidden: [], focusId: "" };
  applyPrefs(); renderSettings(); focusRow("reset");
  commitPrefs(function(){ refresh(); });
}
function loadPrefs(){
  svcCall(SVC, SVC_PREFS_GET_M, {}, function(d){
    if (d && d.prefs) {
      var p = d.prefs;
      PREFS.accent = p.accent || PREFS.accent;
      PREFS.tileSize = p.tileSize || PREFS.tileSize;
      if (typeof p.labels === "boolean") PREFS.labels = p.labels;
      if (typeof p.clock24 === "boolean") PREFS.clock24 = p.clock24;
      PREFS.sort = p.sort || PREFS.sort;
      if (Array.isArray(p.pinned)) PREFS.pinned = p.pinned.slice();
      if (Array.isArray(p.hidden)) PREFS.hidden = p.hidden.slice();
      applyPrefs();
      if (__mhTiles.length) rebuild(__mhTiles);
    }
  }, function(){});
}

function showOverlay(id){
  document.getElementById("dim").classList.add("show");
  document.getElementById(id).classList.add("show");
}
function hideOverlay(){
  document.getElementById("dim").classList.remove("show");
  document.getElementById("settingsPanel").classList.remove("show");
  document.getElementById("optionsPanel").classList.remove("show");
  document.getElementById("searchBox").classList.remove("show");
  overlay.mode = null;
  var el = lastFocusEl || document.querySelector("#grid .tile");
  try { if (el) el.focus(); } catch (e) {}
}
function focusFirst(sel){
  var f = document.querySelector(sel);
  try { if (f) f.focus(); } catch (e) {}
}
function openSettingsPanel(){
  lastFocusEl = document.activeElement;
  overlay.mode = "settings";
  renderSettings();
  showOverlay("settingsPanel");
  focusFirst("#settingsRows .srow");
}
function openOptions(el){
  lastFocusEl = el;
  overlay.mode = "options";
  var id = el.getAttribute("data-id");
  var label = (el.querySelector && el.querySelector(".label")) ? el.querySelector(".label").textContent : id;
  var pinned = PREFS.pinned.indexOf(id) >= 0;
  var rows = [ "Pin", "Hide app", "Launch" ];
  if (pinned) rows[0] = "Unpin";
  document.getElementById("optionsRows").innerHTML = rows.map(function(l){
    return '<div class="optrow" tabindex="0" data-id="' + esc(id) + '"><span class="sl">' + l + '</span></div>';
  }).join("");
  document.getElementById("optionsPanel").querySelector(".panel-head").innerHTML = "Options <small>" + label + "</small>";
  showOverlay("optionsPanel");
  focusFirst("#optionsRows .optrow");
}
function openManage(){
  overlay.mode = "manage";
  var hidden = [];
  __mhTiles.forEach(function(t){ if (PREFS.hidden.indexOf(t.id) >= 0) hidden.push(t); });
  var html = hidden.length ? hidden.map(function(t){
    var pin = PREFS.pinned.indexOf(t.id) >= 0 ? " \u2605" : "";
    return '<div class="optrow" tabindex="0" data-id="' + esc(t.id) + '"><span class="sl">' + (t.title || t.id) + pin + '</span><span class="small">' + t.id + '</span></div>';
  }).join("") : '<div class="srow" tabindex="0" data-key="none"><span class="sl">No hidden apps</span></div>';
  document.getElementById("optionsRows").innerHTML = html;
  document.getElementById("optionsPanel").querySelector(".panel-head").innerHTML = "Hidden apps <small>select to restore</small>";
  showOverlay("optionsPanel");
  focusFirst("#optionsRows .optrow, #optionsRows .srow");
}
function togglePin(id){
  var i = PREFS.pinned.indexOf(id);
  if (i >= 0) PREFS.pinned.splice(i, 1); else PREFS.pinned.push(id);
  commitPrefs(function(){ refresh(); });
}
function hideApp(id){
  if (PREFS.hidden.indexOf(id) < 0) PREFS.hidden.push(id);
  try { localStorage.removeItem("mh.focus"); } catch (e) {}
  commitPrefs(function(){ refresh(); });
}
function launchSearchRow(id){
  hideOverlay();
  launchFromId(id);
}
var searchQ = "";
function openSearch(ch){
  lastFocusEl = document.activeElement;
  overlay.mode = "search";
  searchQ = (ch || "");
  renderSearch();
  showOverlay("searchBox");
  focusFirst("#searchRows .srow");
}
function searchMatches(){
  var q = searchQ.toLowerCase();
  if (!q) return [];
  var starts = [], cont = [];
  __mhTiles.forEach(function(t){
    if (PREFS.hidden.indexOf(t.id) >= 0) return;
    var title = (t.title || "").toLowerCase(), id = (t.id || "").toLowerCase();
    if (title.indexOf(q) === 0 || id.indexOf(q) === 0) starts.push(t);
    else if (title.indexOf(q) >= 0 || id.indexOf(q) >= 0) cont.push(t);
  });
  return starts.concat(cont).slice(0, 8);
}
function renderSearch(){
  document.getElementById("searchQ").textContent = searchQ ? "\u201c" + searchQ + "\u201d" : "\u201c\u201d";
  var list = searchMatches();
  var html = list.length ? list.map(function(t){
    return '<div class="srow" tabindex="0" data-id="' + esc(t.id) + '"><span class="sl">' + (t.title || t.id) + '</span><span class="small">' + t.id + '</span></div>';
  }).join("") : '<div class="srow" tabindex="0" data-key="none"><span class="sl">No matches</span></div>';
  document.getElementById("searchRows").innerHTML = html;
  focusFirst("#searchRows .srow");
}
function activateRow(el){
  var mode = overlay.mode;
  if (!el) return;
  var key = el.getAttribute("data-key");
  var id = el.getAttribute("data-id");
  if (mode === "settings") {
    if (key === "tvsettings") { hideOverlay(); launch(SETTINGS_TILE.id, null); return; }
    if (key === "manage") { openManage(); return; }
    if (key === "reset") { resetAll(); return; }
    if (key && findRow(key)) changeSetting(key, 1);
    return;
  }
  if (mode === "manage") {
    if (id) {
      var i = PREFS.hidden.indexOf(id);
      if (i >= 0) PREFS.hidden.splice(i, 1);
      commitPrefs(function(){ hideOverlay(); refresh(); });
    }
    return;
  }
  if (mode === "options") {
    var old = lastFocusEl;
    var label = el.querySelector(".sl") ? el.querySelector(".sl").textContent : "";
    hideOverlay();
    if (id) {
      if (label === "Pin" || label === "Unpin") togglePin(id);
      else if (label === "Hide app") hideApp(id);
      else if (old) doLaunch(old);
    }
    return;
  }
  if (mode === "search") {
    if (id) launchSearchRow(id);
    return;
  }
}
function overlayKey(e){
  var kc = e.keyCode;
  if (BACK_KEYS[kc]) {
    if (overlay.mode === "search" && searchQ) { searchQ = searchQ.slice(0, -1); renderSearch(); return true; }
    hideOverlay();
    return true;
  }
  var dir = dirOf(kc);
  if (dir) {
    if (overlay.mode === "settings") {
      if (dir === "left" || dir === "right") {
        var row = document.activeElement;
        if (row && row.className && row.className.indexOf("srow") >= 0 && row.getAttribute("data-key")) {
          changeSetting(row.getAttribute("data-key"), dir === "left" ? -1 : 1);
        }
      } else {
        moveFocusIn("#settingsRows .srow", dir);
      }
      return true;
    }
    if (overlay.mode === "options") { moveFocusIn("#optionsRows .optrow", dir); return true; }
    if (overlay.mode === "manage") { moveFocusIn("#optionsRows .optrow, #optionsRows .srow", dir); return true; }
    if (overlay.mode === "search") { moveFocusIn("#searchRows .srow", dir); return true; }
    return true;
  }
  if (kc === 13) {
    e.preventDefault();
    var el = document.activeElement;
    activateRow(el);
    return true;
  }
  if (overlay.mode === "search") {
    if (kc === 8) { if (searchQ) { searchQ = searchQ.slice(0, -1); renderSearch(); } return true; }
    if (e.key && e.key.length === 1) { searchQ += e.key; renderSearch(); return true; }
  }
  return false;
}
function moveFocusIn(sel, dir){
  var els = Array.prototype.slice.call(document.querySelectorAll(sel));
  var cur = els.indexOf(document.activeElement);
  var next = (dir === "down" || dir === "right")
    ? (cur + 1 < els.length ? cur + 1 : 0)
    : (cur - 1 >= 0 ? cur - 1 : els.length - 1);
  if (els[next]) { els[next].focus(); try { els[next].scrollIntoView({ block: "nearest" }); } catch (e) {} }
}

function mainRowTiles(){
  return Array.prototype.slice.call(document.querySelectorAll("#grid .tile, #inputs .tile, #sysrow .tile"));
}
function buildRows(els){
  var rows = [], cur = -1;
  els.forEach(function(el){
    var top = Math.round(el.getBoundingClientRect().top);
    var row = rows[cur];
    if (!row || Math.abs(row.top - top) > 12) {
      rows.push({ top: top, items: [el] }); cur = rows.length - 1;
    } else {
      row.items.push(el);
    }
  });
  return rows;
}
function wrapTile(cur, dir){
  var main = mainRowTiles();
  var cEl = navTiles()[cur];
  var rows = buildRows(main);
  var ci = -1, col = 0, ri, ii;
  for (ri = 0; ri < rows.length; ri++) {
    for (ii = 0; ii < rows[ri].items.length; ii++) {
      if (rows[ri].items[ii] === cEl) { ci = ri; col = ii; break; }
    }
  }
  if (ci < 0) return null;
  var ni = (dir === "right" || dir === "down") ? (ci + 1) % rows.length : (ci - 1 + rows.length) % rows.length;
  var row = rows[ni];
  return row ? (row.items[col] || row.items[row.items.length - 1]) : null;
}
function navTiles(){ return Array.prototype.slice.call(document.querySelectorAll(".tile")); }
function moveTile(dir){
  var tiles = navTiles();
  var cur = tiles.indexOf(document.activeElement);
  if (cur < 0) { var g = document.querySelector("#grid .tile") || tiles[0]; if (g && g !== document.activeElement) g.focus(); persistFocus(); return; }
  var r0 = tiles[cur].getBoundingClientRect();
  var cx0 = r0.left + r0.width / 2, cy0 = r0.top + r0.height / 2, best = -1, bestScore = Infinity, i, r, cx, cy, dx, dy, primary, secondary, score;
  for (i = 0; i < tiles.length; i++) {
    if (i === cur) continue;
    r = tiles[i].getBoundingClientRect();
    cx = r.left + r.width / 2; cy = r.top + r.height / 2;
    dx = cx - cx0; dy = cy - cy0;
    if (dir === "left" && dx >= -4) continue;
    if (dir === "right" && dx <= 4) continue;
    if (dir === "up" && dy >= -4) continue;
    if (dir === "down" && dy <= 4) continue;
    if (dir === "left" || dir === "right") { primary = Math.abs(dx); secondary = Math.abs(dy); }
    else { primary = Math.abs(dy); secondary = Math.abs(dx); }
    score = primary + secondary * 2.2;
    if (score < bestScore) { bestScore = score; best = i; }
  }
  var target = best >= 0 ? tiles[best] : wrapTile(cur, dir);
  if (target && target !== document.activeElement) {
    target.focus();
    try { target.scrollIntoView({ block: "nearest" }); } catch (e) {}
  }
  persistFocus();
}
function startHold(dir){
  stopHold();
  holdDir = dir; holdN = 1;
  function step(){
    if (!holdDir) return;
    moveTile(holdDir);
    holdN++;
    var d = holdN < 4 ? 150 : holdN < 10 ? 90 : 55;
    holdTimer = setTimeout(step, d);
  }
  holdTimer = setTimeout(step, 450);
}
function stopHold(){
  if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
  holdDir = null; holdN = 0;
}
function enterKey(){
  var el0 = document.activeElement;
  if (!el0) return;
  if (el0.id === "settingsBtn") { openSettingsPanel(); return; }
  if (el0.className && (" " + el0.className + " ").indexOf(" tile ") >= 0) doLaunch(el0);
}
var enterHoldTimer = null;
function enterDown(){
  if (enterHoldTimer) return;
  enterHoldTimer = setTimeout(function(){
    enterHoldTimer = null;
    var el0 = document.activeElement;
    if (el0 && el0.className && (" " + el0.className + " ").indexOf(" tile ") >= 0) openOptions(el0);
  }, 700);
}
function openOptionsKey(){
  var el0 = document.activeElement;
  if (el0 && el0.className && (" " + el0.className + " ").indexOf(" tile ") >= 0) openOptions(el0);
}

document.addEventListener("keydown", function(e){
  if (overlay.mode) { if (overlayKey(e)) e.preventDefault(); return; }
  var kc = e.keyCode;
  if (kc === 13) { e.preventDefault(); enterDown(); return; }
  if (kc === 457 || kc === 412) { e.preventDefault(); openOptionsKey(); return; }
  var dir = dirOf(kc);
  if (dir) { e.preventDefault(); moveTile(dir); startHold(dir); return; }
  // Swallow Back everywhere on the grid: an unhandled back is what makes
  // WAM surface its "exit app?" dialog; this launcher is a home replacement
  // and never prompts to exit.
  if (BACK_KEYS[kc]) { e.preventDefault(); return; }
  if (e.key && e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
    e.preventDefault();
    openSearch(e.key.toLowerCase());
  }
});
document.addEventListener("keyup", function(e){
  if (e.keyCode === 13) {
    if (enterHoldTimer) { clearTimeout(enterHoldTimer); enterHoldTimer = null; enterKey(); }
    return;
  }
  if (dirOf(e.keyCode)) stopHold();
});
document.addEventListener("focusin", persistFocus);

var sb = document.getElementById("settingsBtn");
sb.addEventListener("click", function(){ openSettingsPanel(); });
Array.prototype.forEach.call(document.querySelectorAll("#grid .tile, #inputs .tile, #sysrow .tile"), function(el){
  el.addEventListener("click", function(){ doLaunch(el); });
});
document.addEventListener("click", function(e){
  if (!overlay.mode) return;
  var t = e.target;
  while (t && t !== document && !(t.classList && (t.classList.contains("srow") || t.classList.contains("optrow")))) t = t.parentNode;
  if (!t || t === document) return;
  try { t.focus(); } catch (e2) {}
  activateRow(t);
});

tick(); setInterval(tick, 15000);
var tries = 0;
function refresh(){
  tries++;
  svcCall(SVC, SVC_LIST_M, {},
    function(d){
      if (d && d.tiles && d.tiles.length) { rebuild(d.tiles, d.inputs); }
      else if (tries < 6) { setTimeout(refresh, 2500); }
    },
    function(e){
      if (tries < 6) { setTimeout(refresh, 2500); return; }
    });
}
refresh();
loadPrefs();
restoreFocus();
document.addEventListener("visibilitychange", function(){
  if (!document.hidden) { tries = 0; refresh(); }
});
window.addEventListener("focus", function(){ tries = 0; refresh(); });
})();
</script>
</body>
</html>
"""


def build(version=None):
    cfg = load_config()
    usage = load_usage()
    apps, inputs, sysrow = classify(load_tiles(), cfg)
    version = version or cfg.get("version") or "1.0.0"

    header_text = (cfg.get("header", {}).get("text") or "Welcome").upper()
    header_brand = cfg.get("header", {}).get("brand") or "Minimal Home"
    sys_ids = [s for s in cfg["ui"]["system"] if s]
    settings_tile = {"id": SETTINGS_ID, "title": "Settings",
                     "icon": SETTINGS_ICON, "params": None}

    inject = {
        "__MH_VERSION__": "v" + version,
        "__MH_SYS_IDS__": json.dumps(sys_ids),
        "__MH_SETTINGS_TILE__": json.dumps(settings_tile),
        "__MH_TITLE__": htmllib.escape(header_brand),
        "__WELCOME_TEXT__": htmllib.escape(header_text),
        "__WELCOME_BRAND__": htmllib.escape(header_brand),
    }

    priority = [p for p in cfg["ui"]["appsPriority"] if p]
    html = TEMPLATE
    html = (html.replace("__APPS__", section_html(apps, usage, priority, sort=True))
                .replace("__INPUTS__", section_html(inputs, usage, priority))
                .replace("__SYS__", section_html(sysrow, usage, priority))
                .replace("__TAG__", "i"))
    for key, value in inject.items():
        html = html.replace(key, value)
    if "__MH_" in html or "__WELCOME_" in html or "__APPS__" in html:
        raise RuntimeError("unresolved template placeholders in index.html")

    with open(os.path.join(APP_DIR, "appinfo.json"), encoding="utf-8") as f:
        appinfo = json.load(f)
    appinfo["version"] = version

    out = {
        "launcher-app/index.html": html,
        "launcher-app/appinfo.json": json.dumps(appinfo, indent=2) + "\n",
    }
    return out, (len(apps), len(inputs), len(sysrow)), usage


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build Minimal Home launcher")
    ap.add_argument("--check", action="store_true",
                    help="verify committed build output is up to date (no writes)")
    ap.add_argument("--version", default=None, help="override version")
    args = ap.parse_args(argv)

    out, (na, ni, ns), usage = build(args.version)

    diffs = []
    for rel, content in out.items():
        path = os.path.join(BASE, rel)
        try:
            with open(path, encoding="utf-8") as f:
                current = f.read()
        except OSError:
            current = None
        if current != content:
            diffs.append(rel)
            if not args.check:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

    print("baked apps=%d inputs=%d sys=%d" % (na, ni, ns))
    if usage:
        print("baking MRU order for %d apps" % len(usage))
    if args.check:
        if diffs:
            print("STALE OUTPUT: " + ", ".join(diffs) + " (run python build_launcher.py)")
            return 1
        print("up-to-date")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
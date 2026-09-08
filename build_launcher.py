"""Build Minimal Home: ATV-style sections + relay-service wiring.

Run `python build_launcher.py` to regenerate launcher-app/index.html and appinfo.json.
Use `--check` to verify tracked outputs are up to date (CI gate).
"""
import argparse
import json
import os
import sys
import html as htmllib

BASE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE, "launcher-app")
SVC_DIR = os.path.join(BASE, "launcher-service")
SELF = "org.minimal.home"
SETTINGS_ID = "com.palm.app.settings"
SETTINGS_ICON = "/usr/palm/applications/com.palm.app.settings/icon.png"
LG_HOME_ID = "__LGHOME__"

DEFAULTS = {
    "version": "1.0.0",
    "header": {"text": "Welcome", "brand": "Minimal Home"},
    "ui": {
        "inputs": [
            "com.webos.app.livetv",
            "com.webos.app.hdmi1",
            "com.webos.app.hdmi2",
            "com.webos.app.hdmi3",
            "com.webos.app.hdmi4",
        ],
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
    inputs_ids = {i for i in cfg["ui"]["inputs"] if i}
    sys_ids = {s for s in cfg["ui"]["system"] if s}
    apps, inputs, sysrow = [], [], []
    for lp in tiles:
        i = lp.get("id", "")
        if i == SELF or lp.get("hidden"):
            continue
        is_sys = bool(lp.get("systemApp"))
        if is_sys and i not in inputs_ids and i not in sys_ids:
            continue
        if not is_sys and i in sys_ids:
            continue
        t = {
            "id": i,
            "title": lp.get("title") or i,
            "icon": lp.get("largeIcon") or lp.get("icon") or "",
            "params": (lp.get("params")
                       if isinstance(lp.get("params"), dict) and lp.get("params") else None),
        }
        if i in inputs_ids and i not in sys_ids:
            inputs.append(t)
        elif i in sys_ids:
            sysrow.append(t)
        else:
            apps.append(t)
    if SETTINGS_ID in sys_ids and not any(t["id"] == SETTINGS_ID for t in sysrow):
        sysrow.append({"id": SETTINGS_ID, "title": "Settings",
                       "icon": SETTINGS_ICON, "params": None})
    sysrow.append({"id": LG_HOME_ID, "title": "LG Home", "icon": "", "params": None})
    return apps, inputs, sysrow


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
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:#0b0d11;color:#f2f4f8;font-family:"LG Smart UI","Segoe UI",Arial,sans-serif;padding:54px 76px 40px;overflow:hidden}
body::before{content:"";position:fixed;inset:0;pointer-events:none;
background:radial-gradient(1400px 600px at 50% -10%,rgba(255,255,255,.045),transparent 60%)}
header{display:flex;align-items:center;justify-content:space-between;margin-bottom:30px;position:relative}
h1{font-size:34px;font-weight:200;letter-spacing:3px;color:#e8ecf1}
h1 b{font-weight:700}
.hright{display:flex;align-items:center;gap:28px}
#settingsBtn{display:flex;align-items:center;gap:11px;background:rgba(255,255,255,.08);border:3px solid transparent;border-radius:999px;color:#d8dee7;font-size:19px;padding:11px 26px 11px 20px;cursor:pointer;transition:transform .13s,background .13s,border-color .13s}
#settingsBtn .gear{font-size:22px}
#settingsBtn:focus{outline:none;background:rgba(255,255,255,.15);border-color:#fff;box-shadow:0 10px 30px rgba(0,0,0,.5);color:#fff}
#clock{font-size:42px;font-weight:200;color:#c3ccd8;text-align:right;line-height:1.1;min-width:210px}
#clock small{display:block;font-size:16px;color:#6b7686;margin-top:2px}
.section{font-size:18px;font-weight:500;letter-spacing:2px;color:#aeb8c6;margin:34px 0 18px;position:relative}
.row{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:34px 36px;position:relative}
.tile{background:#16181e;border:3px solid transparent;border-radius:22px;padding:0;cursor:pointer;overflow:hidden;transition:transform .13s ease,background .13s ease,border-color .13s ease,box-shadow .13s ease}
.tile .art{aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;background:linear-gradient(150deg,#1e222b,#12141a)}
.tile .art img{width:104px;height:104px;object-fit:contain;filter:drop-shadow(0 8px 18px rgba(0,0,0,.55))}
.tile .initial{width:104px;height:104px;border-radius:24px;display:flex;align-items:center;justify-content:center;font-size:48px;font-weight:700;background:#232936;color:#93a3ba}
.tile .label{font-size:22px;font-weight:400;color:#d6dce5;text-align:center;padding:15px 12px 17px;background:rgba(255,255,255,.035);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tile:focus{outline:none;background:#1b1f27;border-color:#fff;transform:scale(1.06);box-shadow:0 18px 44px rgba(0,0,0,.6)}
.tile:focus .label{color:#fff;font-weight:600}
#err{display:none;margin-top:40px;font-size:20px;color:#ff9a9a}
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
  if (params) { for (var k in params) { if (Object.prototype.hasOwnProperty.call(params, k)) p[k] = params[k]; } }
  svcCall(SVC, SVC_LAUNCH_M, p, function(){}, function(e){
    var el = document.getElementById("err");
    el.style.display = "block";
    el.textContent = "Could not open app: " + ((e && e.errorText) || "unknown error");
  });
}
function tileParams(el){
  try { return JSON.parse(el.getAttribute("data-params") || "null"); } catch (e) { return null; }
}
function tileEl(t){
  var d = document.createElement("div");
  d.className = "tile"; d.tabIndex = 0;
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
  d.addEventListener("click", function(){ doLaunch(d); });
  return d;
}
var INPUT_IDS = __MH_INPUT_IDS__;
var SYS_IDS = __MH_SYS_IDS__;
var SETTINGS_TILE = __MH_SETTINGS_TILE__;
function rebuild(tiles){
  var grid = document.getElementById("grid");
  var inputs = document.getElementById("inputs");
  var sysrow = document.getElementById("sysrow");
  grid.innerHTML = ""; inputs.innerHTML = ""; sysrow.innerHTML = "";
  var added = { grid: 0, inputs: 0, sys: 0 };
  tiles.forEach(function(t){
    if (!t || !t.id || t.id === "org.minimal.home") return;
    var el = tileEl(t);
    if (INPUT_IDS.indexOf(t.id) >= 0) { inputs.appendChild(el); added.inputs++; }
    else if (SYS_IDS.indexOf(t.id) >= 0) { sysrow.appendChild(el); added.sys++; }
    else { grid.appendChild(el); added.grid++; }
  });
  if (SETTINGS_TILE && !sysrow.querySelector('[data-id="com.palm.app.settings"]')) sysrow.appendChild(tileEl(SETTINGS_TILE));
  var first = document.querySelector("#grid .tile");
  try { if (first && !document.activeElement) first.focus(); } catch (e) {}
  return added;
}
function doLaunch(el){
  var id = el.getAttribute("data-id");
  if (!id) return;
  if (id === "__LGHOME__") { svcCall(SVC, "openLGHome", {}, function(){}, function(){}); return; }
  launch(id, tileParams(el));
}
function openSettings(){ launch("com.palm.app.settings", null); }
function mkInitialEl(title){
  var d = document.createElement("div");
  d.className = "initial";
  d.textContent = ((title || "?").trim().charAt(0) || "?").toUpperCase();
  return d;
}
Array.prototype.forEach.call(document.querySelectorAll(".tile img[data-title]"), function(img){
  img.addEventListener("error", function(){
    try { img.parentNode.replaceChild(mkInitialEl(img.getAttribute("data-title")), img); } catch (e) {}
  });
});
document.addEventListener("keydown", function(e){
  if (e.keyCode === 13) {
    var el0 = document.activeElement;
    if (!el0) return;
    if (el0.id === "settingsBtn") { openSettings(); return; }
    if (el0.className && el0.className.indexOf("tile") >= 0) doLaunch(el0);
    return;
  }
  var dir = (e.keyCode === 37) ? "left" : (e.keyCode === 39) ? "right" : (e.keyCode === 38) ? "up" : (e.keyCode === 40) ? "down" : null;
  if (!dir) return;
  var tiles = Array.prototype.slice.call(document.querySelectorAll(".tile"));
  var cur = tiles.indexOf(document.activeElement);
  if (cur < 0) { var g0 = document.querySelector("#grid .tile"); (g0 || tiles[0]).focus(); e.preventDefault(); return; }
  var r0 = tiles[cur].getBoundingClientRect();
  var cx0 = r0.left + r0.width / 2, cy0 = r0.top + r0.height / 2;
  var best = -1, bestScore = Infinity, i, r, cx, cy, dx, dy, primary, secondary, score;
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
  e.preventDefault();
  if (best >= 0) {
    tiles[best].focus();
    try { tiles[best].scrollIntoView({ block: "nearest" }); } catch (e2) {}
  }
});
var sb = document.getElementById("settingsBtn");
sb.addEventListener("click", openSettings);
Array.prototype.forEach.call(document.querySelectorAll("#grid .tile, #inputs .tile, #sysrow .tile"), function(el){
  el.addEventListener("click", function(){ doLaunch(el); });
});
function tick(){
  var n = new Date(), p = function(x){ return (x < 10 ? "0" : "") + x; };
  var days = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
  var h = n.getHours(), ap = h >= 12 ? "PM" : "AM";
  h = h % 12; if (h === 0) h = 12;
  document.getElementById("clock").innerHTML =
    h + ":" + p(n.getMinutes()) + " " + ap +
    "<small>" + days[n.getDay()] + " " + p(n.getDate()) + "." + p(n.getMonth() + 1) + "</small>";
}
tick(); setInterval(tick, 15000);
var tries = 0;
function refresh(){
  tries++;
  svcCall(SVC, SVC_LIST_M, {},
    function(d){
      if (d && d.tiles && d.tiles.length) { rebuild(d.tiles); }
      else if (tries < 6) { setTimeout(refresh, 2500); }
    },
    function(e){
      if (tries < 6) { setTimeout(refresh, 2500); return; }
    });
}
refresh();

var first = document.querySelector("#grid .tile");
if (first) first.focus();
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
        "__MH_INPUT_IDS__": json.dumps([i for i in cfg["ui"]["inputs"] if i]),
        "__MH_SYS_IDS__": json.dumps(sys_ids),
        "__MH_SETTINGS_TILE__": json.dumps(settings_tile if SETTINGS_ID in sys_ids else None),
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

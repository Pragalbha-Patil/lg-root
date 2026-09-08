var Service = require('webos-service');
var fs = require('fs');
var C = require('./constants');
var LOG = C.SVC_LOG;
var USAGE_FILE = C.USAGE_FILE;
var CONFIG_FILE = C.CONFIG_FILE;
var PREFS_FILE = C.PREFS_FILE;
var SELF_ID = C.SELF_ID;

var logSize = 0;
function log(o) {
    o.ts = Date.now();
    try {
        var line = JSON.stringify(o) + '\n';
        logSize += line.length;
        fs.appendFileSync(LOG, line);
        if (logSize > 100000) {
            // rotate by rewriting the current line; track size in memory so a
            // hot path never pays a statSync per line
            logSize = line.length;
            fs.writeFileSync(LOG, line);
        }
    } catch (e) {}
}
function loadUsage() {
    try { return JSON.parse(fs.readFileSync(USAGE_FILE, 'utf8')); }
    catch (e) { return {}; }
}
var usageSeq = 0;
function loadUsageCounted() {
    var u = loadUsage();
    var keys = Object.keys(u);
    usageSeq = 0;
    keys.forEach(function (k) {
        if (typeof u[k] === 'number' && u[k] > usageSeq) usageSeq = u[k];
    });
    return u;
}
function saveUsage(u) {
    try {
        var keys = Object.keys(u);
        if (keys.length > 60) {
            keys.sort(function (a, b) { return u[a] - u[b]; });
            keys.slice(0, keys.length - 60).forEach(function (k) { delete u[k]; });
        }
        fs.writeFileSync(USAGE_FILE, JSON.stringify(u));
    } catch (e) {}
}

var PREFS_DEFAULTS = {
    accent: 'steel',
    tileSize: 'standard',
    labels: true,
    clock24: false,
    sort: 'mru',
    pinned: [],
    hidden: []
};
var PREFS_CHOICES = {
    accent: ['steel', 'emerald', 'violet', 'amber', 'crimson'],
    tileSize: ['compact', 'standard', 'large'],
    sort: ['mru', 'alpha', 'pinned']
};
function cleanPrefs(partial) {
    var out = {};
    if (!partial || typeof partial !== 'object' || Array.isArray(partial)) return out;
    Object.keys(partial).forEach(function (k) {
        var v = partial[k];
        if (PREFS_CHOICES[k] && PREFS_CHOICES[k].indexOf(v) >= 0) out[k] = v;
        else if (k === 'labels' || k === 'clock24') out[k] = !!v;
        else if (k === 'pinned' && Array.isArray(v)) {
            out[k] = v.filter(function (x) { return typeof x === 'string' && x; }).slice(0, 30);
        } else if (k === 'hidden' && Array.isArray(v)) {
            out[k] = v.filter(function (x) { return typeof x === 'string' && x; }).slice(0, 60);
        }
    });
    return out;
}
function loadPrefs() {
    var u = null;
    try { u = JSON.parse(fs.readFileSync(PREFS_FILE, 'utf8')); } catch (e) {}
    if (!u || typeof u !== 'object' || Array.isArray(u)) u = {};
    var out = {};
    Object.keys(PREFS_DEFAULTS).forEach(function (k) {
        var v = u[k];
        if (typeof PREFS_DEFAULTS[k] === 'boolean') out[k] = (typeof v === 'boolean') ? v : PREFS_DEFAULTS[k];
        else if (Array.isArray(PREFS_DEFAULTS[k])) {
            out[k] = (Array.isArray(v))
                ? v.filter(function (x) { return typeof x === 'string' && x; })
                : PREFS_DEFAULTS[k].slice();
        } else out[k] = (typeof v === 'string' && v) ? v : PREFS_DEFAULTS[k];
    });
    var acc = PREFS_CHOICES.accent, ts = PREFS_CHOICES.tileSize, so = PREFS_CHOICES.sort;
    if (acc.indexOf(out.accent) < 0) out.accent = PREFS_DEFAULTS.accent;
    if (ts.indexOf(out.tileSize) < 0) out.tileSize = PREFS_DEFAULTS.tileSize;
    if (so.indexOf(out.sort) < 0) out.sort = PREFS_DEFAULTS.sort;
    out.pinned = out.pinned.slice(0, 30);
    out.hidden = out.hidden.slice(0, 60);
    return out;
}

var service = new Service('org.minimal.home.service');

function loadConfig() {
    try {
        var cfg = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
        return (cfg && typeof cfg === 'object') ? cfg : {};
    } catch (e) { return {}; }
}
var ALLOW_SYSTEM = (function () {
    var u = loadConfig();
    var ui = (u && u.ui) || {};
    var list = (ui.system || []);
    return list.filter(function (x) { return typeof x === 'string' && x; });
})();

// Mirrors build_launcher.py MH_INPUT_RE: the OS's fixed input-port app id
// namespace. Inputs are never hardcoded per device -- which ports exist comes
// from the live launch points (a port appears when a device is connected,
// disappears when unplugged), plus lptype "bookmark" = input device.
var INPUT_ID_RE = /^com\.webos\.app\.(livetv|hdmi\d+|av\d+|scart|dp\d+|usbc\d+)$/;
function isInputLp(lp) {
    if (!lp || !lp.id) return false;
    if (lp.lptype === 'bookmark') return true;
    return INPUT_ID_RE.test(lp.id);
}

service.register('getTiles', function (msg) {
    try {
        service.call('luna://com.webos.applicationManager/listLaunchPoints', {}, function (res) {
            try {
                var p = (res && res.payload) || {};
                var usage = loadUsage();
                var prefs = loadPrefs();
                var hiddenSet = {}, pinIdx = {};
                prefs.hidden.forEach(function (id) { if (id) hiddenSet[id] = 1; });
                prefs.pinned.forEach(function (id, i) { if (id && !(id in pinIdx)) pinIdx[id] = i; });
                var cfg = loadConfig() || {};
                var cfgUI = cfg.ui || {};
                var cfgHeader = (cfg.header && typeof cfg.header === 'object')
                    ? { text: cfg.header.text, brand: cfg.header.brand } : null;
                var priority = (Object.prototype.toString.call(cfgUI.appsPriority) === '[object Array]')
                    ? cfgUI.appsPriority : [];
                var out = [], inputs = [];
                (p.launchPoints || []).forEach(function (lp) {
                    if (!lp || lp.hidden || lp.id === SELF_ID) return;
                    var isInp = isInputLp(lp);
                    if (lp.systemApp && !isInp) {
                        var sysOk = (ALLOW_SYSTEM.length === 0) || (ALLOW_SYSTEM.indexOf(lp.id) >= 0);
                        if (!sysOk) return;
                    }
                    var t = {
                        id: lp.id,
                        title: lp.title || lp.id,
                        icon: ICONS_PREFIX + lp.id.replace(/[\/\\]/g, '_') + '.png',
                        params: (lp.params && Object.keys(lp.params).length) ? lp.params : null,
                        pinned: (lp.id in pinIdx),
                        hidden: (lp.id in hiddenSet)
                    };
                    (isInp ? inputs : out).push(t);
                });
                function pinRank(t) { return (t.id in pinIdx) ? 0 : 1; }
                function keyOf(a, b) { // [usedIdx, usage, prioIdx, pinnedOrder?, title]
                    var pa = pinRank(a), pb = pinRank(b);
                    if (pa !== pb) return pa - pb;
                    if (pa === 0) return pinIdx[a.id] - pinIdx[b.id];
                    var ua = usage[a.id] || 0, ub = usage[b.id] || 0;
                    if (ua !== ub) return ub - ua;
                    var ia = priority.indexOf(a.id), ib = priority.indexOf(b.id);
                    if (ia !== ib) return (ia < 0 ? 1e9 : ia) - (ib < 0 ? 1e9 : ib);
                    var ta = (a.title || a.id || '').toLowerCase(), tb = (b.title || b.id || '').toLowerCase();
                    if (ta !== tb) return ta < tb ? -1 : 1;
                    return (a.id || '') < (b.id || '') ? -1 : 1;
                }
                out.sort(keyOf);
                if (prefs.sort === 'alpha') {
                    out.sort(function (a, b) {
                        var ta = (a.title || a.id || '').toLowerCase(), tb = (b.title || b.id || '').toLowerCase();
                        if (ta !== tb) return ta < tb ? -1 : 1;
                        return (a.id || '') < (b.id || '') ? -1 : 1;
                    });
                }
                log({ m: 'getTiles', n: out.length, inputs: inputs.length, sort: prefs.sort, pins: prefs.pinned.length,
                      hidden: prefs.hidden.length, err: '' });
                msg.respond({ returnValue: true, tiles: out, inputs: inputs, prefs: prefs, header: cfgHeader });
            } catch (e) {
                log({ m: 'getTiles', err: 'handler:' + (e && e.message) });
                msg.respond({ returnValue: false, errorText: String((e && e.message) || e) });
            }
        });
    } catch (e) {
        log({ m: 'getTiles', err: 'call:' + (e && e.message) });
        msg.respond({ returnValue: false, errorText: String((e && e.message) || e) });
    }
});

var ICONS_PREFIX = 'icons/';

var LAUNCH_PARAM_ALLOW = ['PhysicalAddress', 'uniqueId', 'value', 'displayId'];
var CALLER = 'org.minimal.home';

var HBOX_TITLE = /hdmi|livetv|av\d|scart|dp\d|usbc/i;

function inputLaunchParams(id, cb) {
    // Mirrors the default launcher: input/bookmark tiles are launched
    // through their launch point, which carries the per-port params
    // (e.g. PhysicalAddress + value) the input app needs to engage the
    // port. Without them this launcher left the screen black.
    if (id.indexOf('com.webos.app.') !== 0 || !HBOX_TITLE.test(id)) { cb(undefined); return; }
    service.call('luna://com.webos.applicationManager/listLaunchPoints', {}, function (res) {
        var rp = (res && res.payload) || {};
        var lps = rp.launchPoints || [];
        var lp = null;
        for (var i = 0; i < lps.length; i++) if (lps[i].id === id) { lp = lps[i]; break; }
        if (!lp || !lp.params || typeof lp.params !== 'object') { cb(undefined); return; }
        var ps = {};
        for (var k in lp.params) {
            if (!Object.prototype.hasOwnProperty.call(lp.params, k)) continue;
            if (k === 'id') continue;
            var v = lp.params[k];
            if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') ps[k] = v;
        }
        cb(Object.keys(ps).length ? ps : undefined);
    });
}

service.register('launchApp', function (msg) {
    try {
        var pl = msg.payload || {};
        var caller = (msg.callerId || '').toString();
        log({ m: 'launchApp-caller', caller: caller });
        inputLaunchParams(pl.id, function (lpParams) {
            var p = { id: pl.id, callerId: CALLER };
            var src = lpParams !== undefined ? lpParams : pl.params;
            if (src && typeof src === 'object') {
                for (var k in src) {
                    if (!Object.prototype.hasOwnProperty.call(src, k)) continue;
                    if (k === 'id') continue;
                    if (LAUNCH_PARAM_ALLOW.indexOf(k) < 0) continue;
                    p[k] = src[k];
                }
            }
            if (lpParams !== undefined) log({ m: 'launchApp-src', id: pl.id, lp: !!lpParams });
            p.id = pl.id;
            service.call('luna://com.webos.applicationManager/launch', p, function (res) {
                var rp = (res && res.payload) || {};
                if (rp.returnValue && pl.id) {
                    var u = loadUsageCounted();
                    usageSeq += 1;
                    u[pl.id] = usageSeq;
                    saveUsage(u);
                }
                log({ m: 'launchApp', id: pl.id, ok: !!rp.returnValue, err: rp.errorText || '' });
                msg.respond(rp.returnValue !== undefined ? rp : { returnValue: false });
            });
        });
    } catch (e) {
        log({ m: 'launchApp', err: 'call:' + (e && e.message) });
        msg.respond({ returnValue: false, errorText: String((e && e.message) || e) });
    }
});

service.register('openLGHome', function (msg) {
    try {
        fs.writeFileSync(C.BYPASS_FILE, String(Date.now() + 10*60*1000));
        service.call('luna://com.webos.applicationManager/launch', { id: C.HOME_ID }, function (res) {
            var rp = (res && res.payload) || {};
            log({ m: 'openLGHome', ok: !!rp.returnValue });
            msg.respond(rp.returnValue !== undefined ? rp : { returnValue: false });
        });
    } catch (e) {
        log({ m: 'openLGHome', err: String((e && e.message) || e) });
        msg.respond({ returnValue: false, errorText: String((e && e.message) || e) });
    }
});

service.register('getPrefs', function (msg) {
    try {
        var prefs = loadPrefs();
        log({ m: 'getPrefs', err: '' });
        msg.respond({ returnValue: true, prefs: prefs });
    } catch (e) {
        log({ m: 'getPrefs', err: 'call:' + (e && e.message) });
        msg.respond({ returnValue: false, errorText: String((e && e.message) || e) });
    }
});

service.register('setPrefs', function (msg) {
    try {
        var upd = cleanPrefs(msg.payload || {});
        var cur = loadPrefs();
        Object.keys(upd).forEach(function (k) { cur[k] = upd[k]; });
        fs.writeFileSync(PREFS_FILE, JSON.stringify(cur));
        log({ m: 'setPrefs', keys: Object.keys(upd).length, err: '' });
        msg.respond({ returnValue: true, prefs: cur });
    } catch (e) {
        log({ m: 'setPrefs', err: 'call:' + (e && e.message) });
        msg.respond({ returnValue: false, errorText: String((e && e.message) || e) });
    }
});

service.register('getSystemStats', function (msg) {
    try {
        var stats = { cpu: 0, ram: 0, temp: null };
        try {
            var raw = fs.readFileSync('/tmp/minhome-stats.json', 'utf8');
            stats = JSON.parse(raw);
        } catch (e) {}
        log({ m: 'getSystemStats', cpu: stats.cpu, ram: stats.ram, temp: stats.temp });
        msg.respond({ returnValue: true, cpu: stats.cpu, ram: stats.ram, temp: stats.temp });
    } catch (e) {
        log({ m: 'getSystemStats', err: String((e && e.message) || e) });
        msg.respond({ returnValue: false, errorText: String((e && e.message) || e) });
    }
});

log({ m: 'service-start', err: '' });

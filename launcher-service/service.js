var Service = require('webos-service');
var fs = require('fs');
var C = require('./constants');
var LOG = C.SVC_LOG;
var USAGE_FILE = C.USAGE_FILE;
var CONFIG_FILE = C.CONFIG_FILE;
var SELF_ID = C.SELF_ID;

function log(o) {
    o.ts = Date.now();
    try {
        var line = JSON.stringify(o) + '\n';
        fs.appendFileSync(LOG, line);
        try { if (fs.statSync(LOG).size > 100000) fs.writeFileSync(LOG, line); } catch (e) {}
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
    var list = (ui.system || []).concat(ui.inputs || []);
    return list.filter(function (x) { return typeof x === 'string' && x; });
})();

service.register('getTiles', function (msg) {
    try {
        service.call('luna://com.webos.applicationManager/listLaunchPoints', {}, function (res) {
            try {
                var p = (res && res.payload) || {};
                var usage = loadUsage();
                var out = [];
                (p.launchPoints || []).forEach(function (lp) {
                    if (!lp || lp.hidden || lp.id === SELF_ID) return;
                    if (lp.systemApp && ALLOW_SYSTEM.indexOf(lp.id) < 0) return;
                    out.push({
                        id: lp.id,
                        title: lp.title || lp.id,
                        icon: ICONS_PREFIX + lp.id + '.png',
                        params: (lp.params && Object.keys(lp.params).length) ? lp.params : null
                    });
                });
                out.sort(function (a, b) {
                    return (usage[b.id] || 0) - (usage[a.id] || 0);
                });
                log({ m: 'getTiles', n: out.length, err: '' });
                msg.respond({ returnValue: true, tiles: out });
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

service.register('launchApp', function (msg) {
    try {
        var pl = msg.payload || {};
        var caller = (msg.callerId || '').toString();
        log({ m: 'launchApp-caller', caller: caller });
        var p = { id: pl.id, callerId: CALLER };
        if (pl.params && typeof pl.params === 'object') {
            for (var k in pl.params) {
                if (!Object.prototype.hasOwnProperty.call(pl.params, k)) continue;
                if (k === 'id') continue;
                if (LAUNCH_PARAM_ALLOW.indexOf(k) < 0) continue;
                p[k] = pl.params[k];
            }
        }
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

log({ m: 'service-start', err: '' });

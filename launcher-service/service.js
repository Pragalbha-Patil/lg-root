var Service = require('webos-service');
var fs = require('fs');
var LOG = '/tmp/minhome-svc.log';

function log(o) {
    o.ts = Date.now();
    try { fs.appendFileSync(LOG, JSON.stringify(o) + '\n'); } catch (e) {}
}

var USAGE_FILE = require('path').join(__dirname, 'usage.json');
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

var ALLOW_SYSTEM = ['com.webos.app.livetv',
    'com.webos.app.hdmi1', 'com.webos.app.hdmi2', 'com.webos.app.hdmi3', 'com.webos.app.hdmi4',
    'com.webos.app.mediadiscovery', 'com.webos.app.discovery'];

function safeIcon(id) {
    return 'icons/' + String(id).replace(/[^a-zA-Z0-9._-]/g, '_') + '.png';
}

service.register('getTiles', function (msg) {
    try {
        service.call('luna://com.webos.applicationManager/listLaunchPoints', {}, function (res) {
            try {
                var p = (res && res.payload) || {};
                log({ m: 'getTiles-raw', keys: Object.keys(p), rv: p.returnValue, errText: (p.errorText || '').slice(0, 120) });
                var usage = loadUsage();
                var out = [];
                (p.launchPoints || []).forEach(function (lp) {
                    if (!lp || lp.hidden || lp.id === 'org.minimal.home') return;
                    if (lp.systemApp && ALLOW_SYSTEM.indexOf(lp.id) < 0) return;
                    out.push({
                        id: lp.id,
                        title: lp.title || lp.id,
                        icon: (lp.largeIcon || lp.icon) ? safeIcon(lp.id) : '',
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

service.register('launchApp', function (msg) {
    try {
        var pl = msg.payload || {};
        var p = { id: pl.id, callerId: 'org.minimal.home' };
        if (pl.params) {
            for (var k in pl.params) {
                if (Object.prototype.hasOwnProperty.call(pl.params, k) && k !== 'id') p[k] = pl.params[k];
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
        fs.writeFileSync(require('path').join(__dirname, '.noredirect'), String(Date.now() + 10*60*1000));
        service.call('luna://com.webos.applicationManager/launch', { id: 'com.webos.app.home' }, function (res) {
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

#!/usr/bin/env node
// Minimal Home redirect watcher (EVENT-DRIVEN v2).
// Subscribes to foreground-app changes; when LG Home comes up, opens
// Minimal Home instead (unless bypassed via the LG Home tile).
// No polling: zero CPU when idle, reacts instantly.
const { execFile, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const { BYPASS_FILE, WATCH_LOG: LOG, HOME_ID, SELF_ID, APP_DIR, SETTINGS_ID, SETTINGS_ICON } = require('./constants');

const ICON_DIR = path.join(APP_DIR, 'icons');
const ICON_MAX_BYTES = 300000;
const FIRSTUSE = '/var/luna/preferences/ran-firstuse';
const STATS_FILE = '/tmp/minhome-stats.json';

let fails = 0;
let lastRedirect = 0;
let foregroundApp = null;
let retryTimer = null;
let redirecting = false;

function log(o) {
    try {
        const line = new Date().toISOString() + ' ' + JSON.stringify(o) + '\n';
        fs.appendFileSync(LOG, line);
        try {
            if (fs.statSync(LOG).size > 100000) fs.writeFileSync(LOG, line);
        } catch (e) {}
    } catch (e) {}
}

function lunaLaunch(id) {
    return new Promise((resolve) => {
        execFile('luna-send', ['-n', '1', 'luna://com.webos.applicationManager/launch',
            JSON.stringify({ id })], { timeout: 15000 }, (err, stdout) => {
                if (err) return resolve(null);
                try { resolve(JSON.parse(stdout)); } catch (e) { resolve(null); }
            });
    });
}

function listLaunchPoints() {
    return new Promise((resolve) => {
        execFile('luna-send', ['-n', '1', 'luna://com.webos.applicationManager/listLaunchPoints', '{}'],
            { timeout: 20000 }, (err, stdout) => {
                if (err) return resolve([]);
                try {
                    const p = JSON.parse(stdout);
                    resolve((p && p.launchPoints) || []);
                } catch (e) { resolve([]); }
            });
    });
}

function provisionIcons(lps) {
    let ok = 0, total = 0;
    try { fs.mkdirSync(ICON_DIR, { recursive: true }); } catch (e) {}
    (lps || []).forEach((lp) => {
        if (!lp || !lp.id) return;
        const dst = path.join(ICON_DIR, lp.id.replace(/[\/\\]/g, '_') + '.png');
        const src = lp.largeIcon || lp.icon || '';
        total++;
        let good = false;
        if (src) {
            try {
                const b = fs.readFileSync(src);
                if (b.length && b.length <= ICON_MAX_BYTES) {
                    try {
                        if (fs.readFileSync(dst).equals(b)) {
                            good = true; // unchanged: skip the flash write
                        } else {
                            fs.writeFileSync(dst, b);
                            good = true;
                        }
                    } catch (e) {
                        fs.writeFileSync(dst, b);
                        good = true;
                    }
                }
            } catch (e) { good = false; }
        }
        if (good) ok++;
        else { try { fs.unlinkSync(dst); } catch (e) {} }
    });
    log({ m: 'icon-prov', total, ok });
}

function provisionSettingsIcon() {
    try {
        const dst = path.join(ICON_DIR, SETTINGS_ID + '.png');
        const b = fs.readFileSync(SETTINGS_ICON);
        if (b.length && b.length <= ICON_MAX_BYTES) {
            try { if (fs.readFileSync(dst).equals(b)) return; } catch (e) {}
            fs.writeFileSync(dst, b);
        }
    } catch (e) { log({ provErr: 'settings:' + String((e && e.code) || e) }); }
}

function collectSystemStats() {
    try {
        // Read prefs to respect showSystemStats toggle
        var showStats = true;
        try {
            var prefs = JSON.parse(fs.readFileSync('/media/developer/apps/usr/palm/services/org.minimal.home.service/prefs.json', 'utf8'));
            showStats = prefs.showSystemStats !== false;
        } catch (e) {}
        if (!showStats) { return; }

        // CPU
        var cpuUsage = 0;
        var stat = fs.readFileSync('/proc/stat', 'utf8');
        var m = stat.match(/^cpu\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)/);
        if (m) {
            var user = parseInt(m[1], 10), nice = parseInt(m[2], 10);
            var sys = parseInt(m[3], 10), idle = parseInt(m[4], 10);
            var total = user + nice + sys + idle;
            if (typeof lastCpuTotal === 'number' && total > lastCpuTotal) {
                var diffTotal = total - lastCpuTotal;
                var diffIdle = idle - (lastCpuIdle || 0);
                cpuUsage = Math.max(0, Math.min(100, Math.round(100 * (diffTotal - diffIdle) / diffTotal)));
            }
            lastCpuTotal = total;
            lastCpuIdle = idle;
        }
        // RAM
        var ramUsage = 0;
        var mem = fs.readFileSync('/proc/meminfo', 'utf8');
        var total = parseInt((mem.match(/MemTotal:\s+(\d+)/) || [])[1] || '0', 10);
        var avail = parseInt((mem.match(/MemAvailable:\s+(\d+)/) || [])[1] || '0', 10);
        if (total > 0) ramUsage = Math.round(100 * (total - avail) / total);
        // Temp
        var tempC = null;
        var zones = fs.readdirSync('/sys/class/thermal');
        for (var i = 0; i < zones.length; i++) {
            var tz = zones[i];
            if (/^thermal_zone\d+$/.test(tz)) {
                var t = fs.readFileSync('/sys/class/thermal/' + tz + '/temp', 'utf8').trim();
                var tc = parseInt(t, 10);
                if (!isNaN(tc)) { tempC = Math.round(tc / 1000); break; }
            }
        }
        fs.writeFileSync(STATS_FILE, JSON.stringify({ cpu: cpuUsage, ram: ramUsage, temp: tempC }));
    } catch (e) { log({ statsErr: String((e && e.message) || e) }); }
}

var lastCpuTotal = null;
var lastCpuIdle = null;

async function runProvision() {
    try {
        const lps = await listLaunchPoints();
        provisionIcons(lps);
        provisionSettingsIcon();
        collectSystemStats();
    } catch (e) { log({ provErr: String((e && e.message) || e) }); }
}

async function redirectLoop() {
    if (foregroundApp !== HOME_ID || redirecting) return;
    try {
        if (fs.existsSync(BYPASS_FILE) &&
            Date.now() < parseInt(fs.readFileSync(BYPASS_FILE, 'utf8'), 10)) return;
        if (Date.now() - lastRedirect < 8000) return;
        redirecting = true;
        const r = await lunaLaunch(SELF_ID);
        if (r && r.returnValue) {
            fails = 0; lastRedirect = Date.now();
            log({ redirect: true });
        } else {
            if (foregroundApp !== HOME_ID) return;
            fails++;
            const backoff = fails < 5 ? 2000 : Math.min(5 * 60 * 1000, 30000 * Math.pow(2, fails - 5));
            log({ redirectFail: true, fails, retryInMs: backoff });
            retryTimer = setTimeout(() => {
                retryTimer = null;
                redirectLoop();
            }, backoff);
        }
    } catch (e) { log({ tickErr: String((e && e.message) || e) }); }
    finally { redirecting = false; }
}

async function onForeground(appId) {
    foregroundApp = appId;
    if (appId !== HOME_ID && retryTimer !== null) {
        clearTimeout(retryTimer);
        retryTimer = null;
    }
    try {
        if (!appId || appId !== HOME_ID) { if (appId !== HOME_ID) fails = 0; return; }
        if (!fs.existsSync(FIRSTUSE)) return;
        try {
            if (fs.existsSync(BYPASS_FILE)) {
                const exp = parseInt(fs.readFileSync(BYPASS_FILE, 'utf8'), 10);
                if (Date.now() < exp) { fails = 0; return; }
                try { fs.unlinkSync(BYPASS_FILE); } catch (e) {}
            }
        } catch (e) {}
        if (retryTimer === null) redirectLoop();
    } catch (e) { log({ tickErr: String((e && e.message) || e) }); }
}

function watch() {
    log({ watcherStart: true });
    let child;
    try {
        child = spawn('luna-send', ['-n', '1000000', 'luna://com.webos.applicationManager/getForegroundAppInfo',
            '{"subscribe":true}']);
    } catch (e) {
        log({ spawnErr: String((e && e.message) || e) });
        setTimeout(watch, 5000);
        return;
    }
    let buf = '';
    function extractObjects() {
        // pull out balanced {...} blocks (handles pretty-printed multi-line JSON)
        let out = [];
        let depth = 0, inStr = false, esc = false, start = -1;
        for (let i = 0; i < buf.length; i++) {
            const c = buf[i];
            if (inStr) {
                if (esc) esc = false;
                else if (c === '\\') esc = true;
                else if (c === '"') inStr = false;
            } else {
                if (c === '"') inStr = true;
                else if (c === '{') { if (depth === 0) start = i; depth++; }
                else if (c === '}') {
                    depth--;
                    if (depth === 0 && start >= 0) {
                        out.push(buf.slice(start, i + 1));
                        start = -1;
                    }
                    if (depth < 0) depth = 0;
                }
            }
        }
        if (start >= 0) buf = buf.slice(start);
        else if (out.length) buf = '';
        else if (buf.length > 65536) buf = buf.slice(-4096);
        return out;
    }
    child.stdout.on('data', (chunk) => {
        buf += chunk.toString();
        const objs = extractObjects();
        for (const o of objs) {
            try {
                const msg = JSON.parse(o);
                if (msg && typeof msg.appId === 'string') onForeground(msg.appId);
            } catch (e) { /* ignore invalid */ }
        }
    });
    let reconnecting = false;
    const reconnect = (why) => {
        // spawn failure fires both 'error' and 'close'; one reconnect per child
        if (reconnecting) return;
        reconnecting = true;
        log({ resubscribe: why });
        try { child.kill(); } catch (e) {}
        setTimeout(watch, 3000);
    };
    child.on('error', () => reconnect('error'));
    child.on('close', (code) => reconnect('close:' + code));
    child.stderr.on('data', (d) => { log({ childStderr: ('' + d).slice(0, 200) }); });
}

setTimeout(runProvision, 15000);
setInterval(runProvision, 5 * 60 * 1000);

// System stats collection every 5s (watcher runs as root, can read /sys/class/thermal)
collectSystemStats();
setInterval(collectSystemStats, 5000);

watch();

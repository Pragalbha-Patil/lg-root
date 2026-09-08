#!/usr/bin/env node
// Minimal Home redirect watcher (EVENT-DRIVEN v2).
// Subscribes to foreground-app changes; when LG Home comes up, opens
// Minimal Home instead (unless bypassed via the LG Home tile).
// No polling: zero CPU when idle, reacts instantly.
const { execFile, spawn } = require('child_process');
const fs = require('fs');

const LOG = '/tmp/minhome-watch.log';
const BYPASS = '/media/developer/apps/usr/palm/services/org.minimal.home.service/.noredirect';
const HOME = 'com.webos.app.home';
const MINE = 'org.minimal.home';
const FIRSTUSE = '/var/luna/preferences/ran-firstuse';

let fails = 0;
let lastRedirect = 0;

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

async function onForeground(appId) {
    try {
        if (!appId || appId !== HOME) { if (appId !== HOME) fails = 0; return; }
        if (!fs.existsSync(FIRSTUSE)) return;
        try {
            if (fs.existsSync(BYPASS)) {
                const exp = parseInt(fs.readFileSync(BYPASS, 'utf8'), 10);
                if (Date.now() < exp) return;
                try { fs.unlinkSync(BYPASS); } catch (e) {}
            }
        } catch (e) {}
        if (Date.now() - lastRedirect < 8000) return;
        const r = await lunaLaunch(MINE);
        if (r && r.returnValue) {
            fails = 0; lastRedirect = Date.now();
            log({ redirect: true });
        } else {
            fails++;
            log({ redirectFail: true, fails });
            if (fails >= 5) { log({ givingUp: true }); process.exit(2); }
        }
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
    const reconnect = (why) => {
        log({ resubscribe: why });
        try { child.kill(); } catch (e) {}
        setTimeout(watch, 3000);
    };
    child.on('error', () => reconnect('error'));
    child.on('close', (code) => reconnect('close:' + code));
    child.stderr.on('data', (d) => { log({ childStderr: ('' + d).slice(0, 200) }); });
}

watch();

const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');
const { EventEmitter } = require('node:events');
const { JSDOM } = require('jsdom');
const constants = require('../../launcher-service/constants');
const ROOT = path.resolve(__dirname, '../..');

function timers() {
    let serial = 0;
    const pending = new Map();
    return {
        pending,
        setTimeout(fn, delay) { pending.set(++serial, { fn, delay }); return serial; },
        clearTimeout(id) { pending.delete(id); },
        setInterval(fn, delay) { pending.set(++serial, { fn, delay, interval: true }); return serial; },
        clearInterval(id) { pending.delete(id); },
        async run(delay, intervals = false) {
            const entries = [...pending].filter(([, timer]) => timer.delay === delay && (intervals || !timer.interval));
            for (const [id, timer] of entries) {
                if (!pending.has(id)) continue;
                if (!timer.interval) pending.delete(id);
                await timer.fn();
            }
        }
    };
}

function memoryFs(initial = {}) {
    const files = new Map(Object.entries(initial));
    const errors = new Map(), writes = [];
    function fail(operation, filename) {
        const error = errors.get(operation + ':' + filename) || errors.get(operation);
        if (error) throw error;
    }
    return {
        files, errors, writes,
        readFileSync(filename, encoding) {
            fail('read', filename);
            if (!files.has(filename)) throw new Error('ENOENT: ' + filename);
            const value = files.get(filename);
            return encoding ? String(value) : Buffer.from(value);
        },
        writeFileSync(filename, value) { fail('write', filename); files.set(filename, value); writes.push(filename); },
        appendFileSync(filename, value) {
            fail('append', filename); files.set(filename, String(files.get(filename) || '') + value);
        },
        renameSync(from, to) { fail('rename', to); files.set(to, files.get(from)); files.delete(from); },
        unlinkSync(filename) { fail('unlink', filename); files.delete(filename); },
        statSync(filename) {
            fail('stat', filename);
            if (!files.has(filename)) throw new Error('ENOENT');
            return { size: Buffer.byteLength(files.get(filename)) };
        },
        existsSync(filename) { fail('exists', filename); return files.has(filename); },
        mkdirSync(filename) { fail('mkdir', filename); },
        readdirSync(filename) { fail('readdir', filename); return [...files.keys()].filter(k => k.startsWith(filename + '/')).map(k => k.slice(filename.length + 1).split('/')[0]); }
    };
}

function runtime(filename, overrides = {}, extra = {}) {
    const full = path.join(ROOT, 'launcher-service', filename);
    const actualRequire = createRequire(full);
    const clock = timers();
    const context = {
        Buffer, console, Date, ...clock,
        require(name) { return Object.hasOwn(overrides, name) ? overrides[name] : actualRequire(name); },
        ...extra
    };
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(full, 'utf8'), context, { filename: full });
    return { context, clock };
}

function service(options = {}) {
    const disk = options.disk || memoryFs({ [constants.CONFIG_FILE]: JSON.stringify({ ui: { system: [constants.SETTINGS_ID], appsPriority: [] } }) });
    const handlers = {}, calls = [], pending = [];
    function Service() {}
    Service.prototype.register = (name, handler) => { handlers[name] = handler; };
    Service.prototype.call = (uri, payload, callback) => {
        calls.push({ uri, payload });
        if (options.throwCall) throw options.throwCall;
        pending.push(callback);
    };
    const { context, clock } = runtime('service.js', { fs: disk, 'webos-service': Service });
    function request(method, payload = {}) {
        const replies = [];
        handlers[method]({ payload, respond(value) { replies.push(JSON.parse(JSON.stringify(value))); } });
        return replies;
    }
    return { disk, handlers, calls, pending, context, clock, request,
        respond(value) { pending.shift()({ payload: value }); } };
}

function watcher(options = {}) {
    const disk = options.disk || memoryFs({ [constants.FIRSTUSE_FILE]: '', '/proc/stat': 'cpu  100 0 100 800 20 10 10 0', '/proc/meminfo': 'MemTotal: 1000\nMemAvailable: 400' });
    const children = [], calls = [], pending = [];
    const processMock = {
        spawn() {
            if (options.throwSpawn) throw new Error('spawn failed');
            const child = new EventEmitter();
            child.stdout = new EventEmitter(); child.stderr = new EventEmitter();
            child.kill = () => { if (options.throwKill) throw new Error('kill failed'); child.emit('close', 1); };
            children.push(child); return child;
        },
        execFile(binary, args, settings, callback) {
            calls.push({ binary, args, settings });
            if (options.throwExec) throw new Error('exec failed');
            pending.push(callback);
        }
    };
    let now = 1000000;
    class ClockDate extends Date { static now() { return now; } }
    const { context, clock } = runtime('watcher.js', { fs: disk, child_process: processMock, path: path.posix }, { Date: ClockDate });
    return { disk, context, clock, calls, children, pending,
        now: () => now, advance: ms => { now += ms; },
        respond(value, error = null) { pending.shift()(error, typeof value === 'string' ? value : JSON.stringify(value)); } };
}

function browser(options = {}) {
    const page = fs.readFileSync(path.join(ROOT, 'launcher-app/index.html'), 'utf8');
    const dom = new JSDOM(page, { runScripts: 'outside-only', url: 'https://minimal-home.test/', pretendToBeVisual: true });
    const window = dom.window, document = window.document, context = dom.getInternalVMContext();
    const clock = timers(), calls = [];
    Object.assign(window, clock);
    window.HTMLElement.prototype.scrollIntoView = function () {};
    let hidden = false;
    Object.defineProperty(document, 'hidden', { get: () => hidden });
    window.MH_CONFIG = { version: 'test', system: [constants.SETTINGS_ID], settingsTile: { id: constants.SETTINGS_ID, title: 'Settings' } };
    if (options.settings === false) window.MH_CONFIG.settingsTile = null;
    if (!options.bridgeOnly && !options.offline) {
        window.navigator.service = { request(uri, args) {
            if (options.throwRequest) throw new Error('request failed');
            const request = { cancel() { request.cancelled = true; } };
            calls.push({ uri, ...args, request });
            return request;
        } };
    }
    const bridges = [];
    if (!options.offline) window.PalmServiceBridge = function () {
        if (options.throwBridge) throw new Error('bridge failed');
        this.call = (uri, params) => { this.uri = uri; this.params = params; if (options.throwBridgeCall) throw new Error('bridge call failed'); };
        this.cancel = () => { if (options.throwCancel) throw new Error('cancel failed'); };
        bridges.push(this);
    };
    if (options.prepare) options.prepare(window, clock);
    for (const name of ['launcher-service/model.js', 'launcher-app/src/launcher.js']) {
        const full = path.join(ROOT, name);
        vm.runInContext(fs.readFileSync(full, 'utf8'), context, { filename: full });
    }
    function respond(method, value) {
        const call = calls.find(c => c.method === method && !c.answered);
        if (!call) throw new Error('No pending ' + method);
        call.answered = true;
        call.onSuccess(value);
        return call;
    }
    function key(code, type = 'keydown', extra = {}) {
        const event = new window.KeyboardEvent(type, { keyCode: code, bubbles: true, cancelable: true, ...extra });
        document.dispatchEvent(event); return event;
    }
    return { window, document, clock, calls, bridges, respond, key,
        visible(value) { hidden = !value; document.dispatchEvent(new window.Event('visibilitychange')); },
        click(selector) { const element = document.querySelector(selector); if (!element) throw new Error('Missing ' + selector); element.click(); return element; },
        tiles(data = {}) { return respond('getTiles', { returnValue: true, tiles: [], inputs: [], ...data }); },
        prefs(prefs = {}) { return respond('getPrefs', { returnValue: true, prefs }); },
        close() { window.close(); } };
}

module.exports = { ROOT, constants, timers, memoryFs, runtime, service, watcher, browser };

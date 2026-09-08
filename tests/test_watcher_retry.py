import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node.js is required for JavaScript regression tests")
class WatcherRetryTest(unittest.TestCase):
    def test_retries_stop_when_foreground_changes_or_bypass_is_enabled(self):
        subprocess.run(["node", "-e", """
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const EventEmitter = require('node:events');
const child = new EventEmitter();
child.stdout = new EventEmitter(); child.stderr = new EventEmitter();
const timers = new Map();
let serial = 0, launches = 0, bypass = false, finish;
const context = {
 require: name => name === 'child_process' ? {
  spawn: () => child, execFile: (bin, args, opts, cb) => { launches++; finish = cb; }
 } : name === 'fs' ? {
  appendFileSync() {}, statSync: () => ({size:0}),
  existsSync: path => path === 'bypass' ? bypass : true,
  readFileSync: () => String(Date.now() + 60000)
 } : name === 'path' ? { join: (...p) => '/' + p.join('/') } : {HOME_ID:'home', SELF_ID:'self', BYPASS_FILE:'bypass'},
 Date, setTimeout: (fn, ms) => { if (ms === 15000) return 'prov'; timers.set(++serial, fn); return serial; },
 clearTimeout: id => timers.delete(id), setInterval: () => 0
};
vm.runInNewContext(fs.readFileSync('launcher-service/watcher.js', 'utf8'), context);
(async () => {
 const first = context.onForeground('home');
 context.onForeground('home');
 assert.equal(launches, 1, 'only one launch in flight');
 finish(null, '{"returnValue":false}');
 await first;
 assert.equal(timers.size, 1);
 await context.onForeground('home');
 assert.equal(launches, 1, 'repeated Home events must preserve backoff');
 assert.equal(timers.size, 1);
 await context.onForeground('netflix');
 assert.equal(timers.size, 0);
 await context.redirectLoop();
 assert.equal(launches, 1);
 context.onForeground('home');
 await context.onForeground('netflix');
 finish(null, '{"returnValue":false}');
 await Promise.resolve();
 assert.equal(timers.size, 0, 'late failures must not restart retries');
 context.onForeground('home');
 finish(null, '{"returnValue":false}');
 await Promise.resolve();
 bypass = true;
 const retry = Array.from(timers.values())[0];
 timers.clear();
 await retry();
 assert.equal(launches, 3, 'bypass must prevent queued retry');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""], check=True)
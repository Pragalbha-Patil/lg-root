import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node.js is required for JavaScript regression tests")
class WatcherReconnectTest(unittest.TestCase):
    def test_error_then_close_schedules_one_subscription(self):
        subprocess.run(["node", "-e", """
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const EventEmitter = require('node:events');
const children = [], timers = [];
function spawn() {
  const child = new EventEmitter();
  child.stdout = new EventEmitter(); child.stderr = new EventEmitter();
  child.kill = () => child.emit('close', 1);
  children.push(child); return child;
}
vm.runInNewContext(fs.readFileSync('launcher-service/watcher.js', 'utf8'), {
  require: name => name === 'child_process' ? {spawn} : name === 'fs' ? {
    appendFileSync() {}, statSync: () => ({size:0})
  } : {}, setTimeout: fn => timers.push(fn), Date
});
children[0].emit('error', new Error('lost subscription'));
children[0].emit('close', 1);
assert.equal(timers.length, 1);
timers.shift()();
assert.equal(children.length, 2);
children[1].emit('close', 0);
assert.equal(timers.length, 1);
"""], check=True)

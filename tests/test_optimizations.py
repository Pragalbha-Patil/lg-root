import shutil
import subprocess
import unittest

# Node-vm runtime regressions for the optimization changes:
#  - watcher icon provisioning must not rewrite unchanged icon files (flash
#    write amplification) but must still write new/changed ones
#  - service log() must rotate from an in-memory size counter and no longer
#    pay a statSync per line


@unittest.skipUnless(shutil.which("node"), "Node.js is required for JavaScript regression tests")
class WatcherProvisionTest(unittest.TestCase):
    def test_provision_skips_identical_icons_and_writes_changes(self):
        subprocess.run(["node", "-e", """
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const files = {}; let writes = 0;
const fsMock = {
  mkdirSync() {},
  readFileSync: (p) => {
    if (p === '/s/n.png') return Buffer.from('ICON_V1');
    if (p === '/s/n2.png') return Buffer.from('ICON_V2');
    if (p.endsWith('/icons/netflix.png')) {
      if (!(p in files)) { const e = new Error('ENOENT'); e.code = 'ENOENT'; throw e; }
      return Buffer.from(files[p]);
    }
    return Buffer.from('');
  },
  writeFileSync: (dst, b) => { files[dst] = b.toString(); writes++; },
  unlinkSync() {}, appendFileSync() {}, statSync: () => ({ size: 0 })
};
const context = {
  require: name => name === 'fs' ? fsMock : name === 'path' ? { join: (...p) => '/' + p.join('/') }
    : name === 'child_process' ? { spawn: () => ({ stdout: { on() {} }, stderr: { on() {} }, on() {}, kill() {} }) }
    : { APP_DIR: '/app', SETTINGS_ID: 'com.palm.app.settings', SETTINGS_ICON: '/s/settings.png',
        LOG: '/log', HOME_ID: 'home', SELF_ID: 'self', BYPASS_FILE: '/bypass' },
  setTimeout: (fn, ms) => ms === 15000 ? 'prov' : 0,
  setInterval: () => 0, Date, Promise, console
};
vm.runInNewContext(fs.readFileSync('launcher-service/watcher.js', 'utf8'), context);
context.provisionIcons([{ id: 'netflix', largeIcon: '/s/n.png' }]);
assert.equal(writes, 1, 'first provision must write the icon');
context.provisionIcons([{ id: 'netflix', largeIcon: '/s/n.png' }]);
assert.equal(writes, 1, 'identical icon must NOT rewrite the file');
context.provisionIcons([{ id: 'netflix', largeIcon: '/s/n2.png' }]);
assert.equal(writes, 2, 'changed icon bytes must be rewritten');
"""], check=True)


@unittest.skipUnless(shutil.which("node"), "Node.js is required for JavaScript regression tests")
class ServiceLogTest(unittest.TestCase):
    def test_log_rotates_from_memory_counter_without_stat_sync(self):
        subprocess.run(["node", "-e", """
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
// NOTE: fs stub intentionally has NO statSync -- if log() still tried to
// stat the file, every call would throw (silently caught) and rotation,
// and therefore the write, would never happen.
let appends = 0, writes = 0;
const fsMock = {
  readFileSync: () => '{}',
  appendFileSync: () => { appends++; },
  writeFileSync: () => { writes++; }
};
const Service = function () {};
Service.prototype.register = function () {};
Service.prototype.call = function () {};
const context = {
  require: name => name === 'webos-service' ? Service : name === 'fs' ? fsMock : {},
  Date, console, JSON, Object
};
vm.runInNewContext(fs.readFileSync('launcher-service/service.js', 'utf8'), context);
const prior = appends;
for (let i = 0; i < 500; i++) context.log({ m: 'x', pad: 'a'.repeat(300) });
assert.equal(appends - prior, 500, 'every log line must be appended');
assert.equal(writes, 1, 'log must rotate once when the in-memory size passes 100KB');
"""], check=True)


if __name__ == "__main__":
    unittest.main()
import json
import shutil
import subprocess
import unittest

import build_launcher as bl

# The frontend sends nested params ({ id, params: {...} }); the service must
# pass them through the allowlist into applicationManager/launch, never letting
# the bookmark marker (id:"uniqueId") clobber the app id. The frontend also
# coalesces double-taps: a second OK pressed inside the in-flight window must
# not double-launch the app.


@unittest.skipUnless(shutil.which("node"), "Node.js is required for JavaScript regression tests")
class LaunchParamsTest(unittest.TestCase):
    def test_browser_payload_reaches_service_allowlist_and_double_tap_guard(self):
        html = bl.build()[0]["launcher-app/index.html"]
        launch = html[html.index("var launchBusy"):html.index("function tileParams(")]
        script = """
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let forwarded, requests = [];
const browser = { SVC: 'service', SVC_LAUNCH_M: 'launchApp',
  setTimeout, clearTimeout,
  svcCall: (uri, method, payload, ok, err) => {
    requests.push(payload);
    setTimeout(() => ok && ok({}), 5);
  } };
vm.runInNewContext(__LAUNCH_SOURCE__, browser);
(async () => {
  vm.runInNewContext('launch("com.webos.app.hdmi1", {PhysicalAddress:"1000", id:"wrong", unexpected:"drop"})', browser);
  vm.runInNewContext('launch("com.webos.app.hdmi1", {PhysicalAddress:"1000", id:"wrong", unexpected:"drop"})', browser);
  assert.equal(requests.length, 1, 'double-tap inside the busy window must be coalesced');
  await new Promise(r => setTimeout(r, 320));
  vm.runInNewContext('launch("netflix", null)', browser);
  await new Promise(r => setTimeout(r, 320));
  assert.equal(requests.length, 2, 'launch after the busy window clears must pass');
  const handlers = {};
  function Service() {}
  Service.prototype.register = (name, handler) => { handlers[name] = handler; };
  Service.prototype.call = (uri, payload, cb) => {
    if (uri.indexOf('listLaunchPoints') >= 0) { return cb && cb({ payload: { launchPoints: [] } }); }
    forwarded = payload;
    if (cb) cb({ payload: { returnValue: true } });
  };
  vm.runInNewContext(fs.readFileSync('launcher-service/service.js', 'utf8'), {
    require: name => name === 'webos-service' ? Service : name === 'fs' ? {
      readFileSync: () => '{}', appendFileSync() {}, statSync: () => ({size:0})
    } : {}, Date, console
  });
  handlers.launchApp({payload:requests[0], respond() {}});
  assert.equal(forwarded.id, 'com.webos.app.hdmi1');
  assert.equal(forwarded.PhysicalAddress, '1000');
  assert.equal(forwarded.unexpected, undefined);
  handlers.launchApp({payload:requests[1], respond() {}});
  assert.equal(forwarded.id, 'netflix');
  process.exit(0);
})().catch(error => { console.error(error); process.exitCode = 1; });
""".replace("__LAUNCH_SOURCE__", json.dumps(launch))
        subprocess.run(["node", "-e", script], check=True)


if __name__ == "__main__":
    unittest.main()
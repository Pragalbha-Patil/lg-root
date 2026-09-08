import json
import shutil
import subprocess
import unittest

import build_launcher as bl

# The frontend sends nested params ({ id, params: {...} }); the service must
# pass them through the allowlist into applicationManager/launch, never letting
# the bookmark marker (id:"uniqueId") clobber the app id.


@unittest.skipUnless(shutil.which("node"), "Node.js is required for JavaScript regression tests")
class LaunchParamsTest(unittest.TestCase):
    def test_browser_payload_reaches_service_allowlist(self):
        html = bl.build()[0]["launcher-app/index.html"]
        launch = html[html.index("function launch("):html.index("function tileParams(")]
        script = """
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let forwarded, requests = [];
const browser = { SVC: 'service', SVC_LAUNCH_M: 'launchApp',
  svcCall: (uri, method, payload) => { requests.push(payload); } };
vm.runInNewContext(__LAUNCH_SOURCE__, browser);
vm.runInNewContext('launch("com.webos.app.hdmi1", {PhysicalAddress:"1000", id:"wrong", unexpected:"drop"})', browser);
vm.runInNewContext('launch("netflix", null)', browser);
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
""".replace("__LAUNCH_SOURCE__", json.dumps(launch))
        subprocess.run(["node", "-e", script], check=True)
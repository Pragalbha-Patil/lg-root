import json
import shutil
import subprocess
import unittest
import build_launcher as bl


@unittest.skipUnless(shutil.which("node"), "Node.js is required for JavaScript regression tests")
class LaunchParamsTest(unittest.TestCase):
    def test_browser_payload_reaches_service_allowlist(self):
        html = bl.build()[0]["launcher-app/index.html"]
        launch = html[html.index("function launch("):html.index("function tileParams(")]
        script = """
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let request;
const browser = { SVC: 'service', SVC_LAUNCH_M: 'launchApp',
  svcCall: (uri, method, payload) => { request = payload; } };
vm.runInNewContext(__LAUNCH_SOURCE__, browser);
vm.runInNewContext('launch("com.webos.app.hdmi1", {PhysicalAddress:"1000", id:"wrong", unexpected:"drop"})', browser);
const handlers = {};
let forwarded;
function Service() {}
Service.prototype.register = (name, handler) => { handlers[name] = handler; };
Service.prototype.call = (uri, payload) => { forwarded = payload; };
vm.runInNewContext(fs.readFileSync('launcher-service/service.js', 'utf8'), {
  require: name => name === 'webos-service' ? Service : name === 'fs' ? {
    readFileSync: () => '{}', appendFileSync() {}, statSync: () => ({size:0})
  } : {}, Date
});
handlers.launchApp({payload:request, respond() {}});
assert.equal(forwarded.id, 'com.webos.app.hdmi1');
assert.equal(forwarded.PhysicalAddress, '1000');
assert.equal(forwarded.unexpected, undefined);
vm.runInNewContext('launch("netflix", null)', browser);
handlers.launchApp({payload:request, respond() {}});
assert.equal(forwarded.id, 'netflix');
""".replace("__LAUNCH_SOURCE__", json.dumps(launch))
        subprocess.run(["node", "-e", script], check=True)

"""Keep the Python fallback classifier aligned with the shared runtime model."""
import json
import subprocess
import unittest
import build_launcher as bl


class InputParityTests(unittest.TestCase):
    def test_input_classification_matches_javascript(self):
        fixtures = [
            {'id': 'com.webos.app.'+suffix, 'title': suffix, 'systemApp': True}
            for suffix in ['livetv','hdmi1','hdmi2','hdmi3','hdmi4','av1','scart','dp1','usbc1']
        ] + [
            {'id':'custom.device','title':'Custom','lptype':'bookmark','params':{'PhysicalAddress':'4000','value':'4'}},
            {'id':'video','title':'Video'},
            {'id':'com.webos.app.camera','title':'Camera','systemApp':True},
            {'id':'com.webos.app.hdmi5','title':'Hidden port','hidden':True},
        ]
        expected = [t['id'] for t in bl.classify(fixtures, bl.load_config())[1]]
        script = """
const assert = require('node:assert/strict');
const model = require('./launcher-service/model');
const fixtures = %s, expected = %s;
assert.deepEqual(fixtures.filter(model.input).filter(t => !t.hidden).map(t => t.id), expected);
""" % (json.dumps(fixtures), json.dumps(expected))
        subprocess.run(["node", "-e", script], check=True, timeout=30)

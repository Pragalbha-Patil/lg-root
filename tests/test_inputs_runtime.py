import json
import shutil
import subprocess
import unittest
import build_launcher as bl


@unittest.skipUnless(shutil.which('node'), 'Node.js required')
class InputRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        page = bl.build()[0]['launcher-app/index.html']
        sections = [
            ('function rebuild(', 'function tileEl('),
            ('function loadPrefs(', 'function showOverlay('),
            ('function refresh(', 'var refreshTimer'),
            ('function searchMatches(', 'function renderSearch('),
            ('function launchFromId(', 'function mkInitialEl('),
            ('function openManage(', 'function togglePin('),
        ]
        cls.source = '\n'.join(page[page.index(a):page.index(b)] for a, b in sections)
        cls.harness = r'''
const assert = require('assert');
const vm = require('vm');
function browser() {
  const rows = {};
  ['grid','inputs','sysrow','optionsRows','optionsPanel'].forEach(id=>{
    rows[id]={children:[],appendChild(t){this.children.push(t)},querySelector(){return {innerHTML:''}},
      set innerHTML(v){this.html=v;this.children=[]},get innerHTML(){return this.html}};
  });
  const pending={}, launches=[];
  const c={__mhTiles:[],__mhInputs:[],tilesLoaded:false,window:{},
    document:{getElementById:id=>rows[id]},
    SELF_ID:'self',SYS_IDS:['settings'],SETTINGS_TILE:{id:'settings',title:'Settings'},
    PREFS:{hidden:[],pinned:[]},tries:0,SVC:'svc',SVC_LIST_M:'tiles',SVC_PREFS_GET_M:'prefs',
    svcCall(s,m,p,ok,fail){pending[m]={ok,fail}},setTimeout(){},
    tileEl:t=>t,restoreFocus(){},applyPrefs(){},applyHeader(){},
    overlay:{},esc:s=>s,showOverlay(){},focusFirst(){},searchQ:'',
    launch(id,params){launches.push({id,params})}};
  vm.createContext(c);vm.runInContext(SOURCE,c);
  return {c,rows,pending,launches,ids:id=>rows[id].children.map(t=>t.id)};
}
const app={id:'video',title:'Video'};
const ps={id:'com.webos.app.hdmi2',title:'PlayStation 5',params:{id:'uniqueId',PhysicalAddress:'2000',value:'4'}};
const fire={id:'com.webos.app.hdmi3',title:'Fire TV Stick'};
const tv={id:'com.webos.app.livetv',title:'Live TV'};
const inputs=[tv,fire,ps];
const data={returnValue:true,tiles:[app],inputs};
'''.replace('SOURCE', json.dumps(cls.source))

    def run_js(self, body):
        subprocess.run(['node', '-e', self.harness + body], check=True)

    def test_startup_response_orders_and_all_preferences(self):
        for order in ('tiles-first', 'prefs-first'):
            for size in ('compact', 'standard', 'large'):
                for sort in ('mru', 'alpha', 'pinned'):
                    with self.subTest(order=order, size=size, sort=sort):
                        self.run_js('const order='+json.dumps(order)+';const size='+json.dumps(size)+';const sort='+json.dumps(sort)+r''';
const {c,pending,ids}=browser();c.refresh();c.loadPrefs();
const prefs={prefs:{pinned:[ps.id],hidden:[],tileSize:size,sort,labels:false,showSystemStats:false,dateFormat:'HH:mm:ss'}};
if(order==='tiles-first'){pending.tiles.ok(data);pending.prefs.ok(prefs)}
else {pending.prefs.ok(prefs);pending.tiles.ok(data)}
assert.deepEqual(ids('inputs'),[ps.id,tv.id,fire.id]);
assert.deepEqual(ids('grid'),['video']);
for(let i=0;i<5;i++){c.loadPrefs();pending.prefs.ok(prefs);assert.equal(ids('inputs').length,3)}
''')

    def test_refresh_disconnect_reconnect_empty_and_invalid_responses(self):
        self.run_js(r'''
const {c,pending,ids}=browser();
function receive(d){c.refresh();pending.tiles.ok(d)}
receive(data);
for(const bad of [null,{}, {returnValue:false,tiles:[],inputs:[]}, {returnValue:true,tiles:[app]},
 {returnValue:true,tiles:[app],inputs:null},{returnValue:true,tiles:{},inputs:[]}]){
 receive(bad);assert.equal(ids('inputs').length,3);
}
c.refresh();pending.tiles.fail({});assert.equal(ids('inputs').length,3);
receive({returnValue:true,tiles:[],inputs:[ps]});assert.deepEqual(ids('inputs'),[ps.id]);
c.loadPrefs();pending.prefs.ok({prefs:{}});assert.deepEqual(ids('inputs'),[ps.id]);
receive({returnValue:true,tiles:[app],inputs:[]});assert.deepEqual(ids('inputs'),[]);
receive(data);assert.equal(ids('inputs').length,3);
receive({returnValue:true,tiles:[],inputs:[]});assert.deepEqual(ids('grid'),[]);assert.deepEqual(ids('inputs'),[]);
''')

    def test_hide_restore_search_pin_and_launch_params(self):
        self.run_js(r'''
const {c,rows,ids,launches}=browser();c.rebuild([app],inputs);
c.searchQ='play';assert.equal(c.searchMatches()[0].id,ps.id);
c.launchFromId(ps.id);assert.deepEqual(launches[0],{id:ps.id,params:ps.params});
c.PREFS.hidden=[ps.id];c.rebuild();assert.equal(ids('inputs').length,2);
assert.equal(c.searchMatches().length,0);c.openManage();assert(rows.optionsRows.innerHTML.includes('PlayStation 5'));
c.PREFS.hidden=[];c.PREFS.pinned=[ps.id];c.rebuild();assert.deepEqual(ids('inputs'),[ps.id,tv.id,fire.id]);
c.rebuild([app],[]);assert.equal(c.searchMatches().length,0);
c.rebuild([app],[null,{}, {id:'self'},ps]);assert.deepEqual(ids('inputs'),[ps.id]);
''')

    def test_service_discovery_validation_and_build_parity(self):
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
        self.run_js('const fixtures='+json.dumps(fixtures)+';const expected='+json.dumps(expected)+r''';
const fs=require('fs');const handlers={};let payload,answer;
function Service(){};
Service.prototype.register=function(n,fn){handlers[n]=fn};
Service.prototype.call=function(uri,p,fn){fn({payload})};
const c={require(n){if(n==='webos-service')return Service;if(n==='fs')return {
 readFileSync(p){return JSON.stringify(p==='config'?{ui:{system:['settings']}}:{})},appendFileSync(){}};
 return {CONFIG_FILE:'config',PREFS_FILE:'prefs',SELF_ID:'self'}},Date,console};
vm.runInNewContext(fs.readFileSync('launcher-service/service.js','utf8'),c);
function get(p){payload=p;handlers.getTiles({respond(r){answer=r}});return answer}
let r=get({returnValue:true,launchPoints:fixtures.concat([null,{}, {id:42}])});
assert.equal(r.returnValue,true);assert.deepEqual(Array.from(r.inputs,t=>t.id),expected);
assert.equal(r.inputs.find(t=>t.id==='custom.device').params.PhysicalAddress,'4000');
for(const p of [undefined,{}, {returnValue:false,errorText:'offline'}, {returnValue:true,launchPoints:{}}])assert.equal(get(p).returnValue,false);
r=get({returnValue:true,launchPoints:[]});assert.equal(r.returnValue,true);assert.equal(r.inputs.length,0);
''')

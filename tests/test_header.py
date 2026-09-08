import json
import shutil
import subprocess
import unittest
from pathlib import Path
import build_launcher as bl

@unittest.skipUnless(shutil.which('node'), 'Node.js required')
class HeaderRegressionTest(unittest.TestCase):
    def run_js(self, script):
        subprocess.run(['node', '-e', script], check=True)

    def test_date_names_and_single_clock_timer(self):
        page = bl.build()[0]['launcher-app/index.html']
        formatter = page[page.index('function formatDate('):page.index('function applyPrefs(')]
        timer = page[page.index('function tickInterval('):page.index('var tries = 0;')]
        self.run_js('const assert=require("assert");' + formatter + '''
const months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
months.forEach((m,i)=>assert.equal(formatDate(new Date(2026,i,9,15,4,5),'MMM D, h:mm:ss A'),m+' 9, 3:04:05 PM'));
assert.equal(formatDate(new Date(2026,8,9),'ddd D MMM'),'Wed 9 Sep');
assert.equal(formatDate(new Date(2026,8,9),'dddd D MMMM'),'Wednesday 9 September');
assert.equal(formatDate(new Date(2026,8,9),'ddd ddd'),'Wed Wed');
let timers=[], ticks=0;
tick=function(){ticks++};
function setInterval(fn){timers.push(fn);}
''' + timer + '''
for(let i=0;i<100;i++) timers[0]();
assert.equal(timers.length,1);
assert.equal(ticks,101);
''')

    def test_cpu_deltas_and_stale_service_samples(self):
        watcher = Path('launcher-service/watcher.js').read_text(encoding='utf-8')
        collector = watcher[watcher.index('var lastCpuTotal'):watcher.index('async function runProvision')]
        self.run_js('const assert=require("assert");' + '''
let stat='cpu  100 0 100 800 20 10 10 0 0 0', written;
const STATS_FILE='/stats'; function log(){}
const fs={readFileSync(p){if(p==='/proc/stat') return stat;if(p==='/proc/meminfo')return 'MemTotal: 1000\\nMemAvailable: 400';return '{}'},readdirSync(){return []},writeFileSync(p,s){written=JSON.parse(s)},renameSync(){}};
''' + collector + '''
collectSystemStats(); assert.equal(written.cpu,null);
stat='cpu  120 0 110 850 30 15 15 0 0 0';
collectSystemStats(); assert.equal(written.cpu,40); assert.equal(written.ram,60);
stat='cpu  120 0 110 950 30 15 15 0 0 0';
collectSystemStats(); assert.equal(written.cpu,0);
const vm=require('vm'), realFs=require('fs'); let handlers={}, response;
function Service(){} Service.prototype.register=function(n,f){handlers[n]=f}; Service.prototype.call=function(){};
let sample={cpu:42,ram:60,temp:70,timestamp:Date.now()};
vm.runInNewContext(realFs.readFileSync('launcher-service/service.js','utf8'),{require(n){if(n==='webos-service')return Service;if(n==='fs')return {readFileSync(){return JSON.stringify(sample)},appendFileSync(){}};return {}},Date,console});
function read(){handlers.getSystemStats({respond(r){response=r}})}
read();assert.equal(response.cpu,42);
sample.timestamp-=30000;read();assert.equal(response.cpu,null);
sample={cpu:0};read();assert.equal(response.cpu,null);
''')

    def test_all_clock_formats_across_calendar_and_time_boundaries(self):
        page = bl.build()[0]['launcher-app/index.html']
        formatter = page[page.index('function formatDate('):page.index('function tick(')]
        self.run_js('const assert=require("assert");' + formatter + r'''
const shortMonths=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const days=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const pad=n=>String(n).padStart(2,'0');
for(let month=0;month<12;month++) for(let day=1;day<=7;day++)
for(const hour of [0,1,11,12,13,23]) for(const minute of [0,9,59]) for(const second of [0,9,59]) {
 const n=new Date(2026,month,day,hour,minute,second),h12=hour%12||12,ap=hour<12?'AM':'PM';
 const hm=pad(hour)+':'+pad(minute),ha=h12+':'+pad(minute),mon=shortMonths[month];
 const expected={'HH:mm':hm,'h:mm A':ha+' '+ap,'HH:mm:ss':hm+':'+pad(second),
 'h:mm:ss A':ha+':'+pad(second)+' '+ap,'MMM D, HH:mm':mon+' '+day+', '+hm,
 'MMM D, h:mm A':mon+' '+day+', '+ha+' '+ap,
 'YYYY-MM-DD HH:mm':'2026-'+pad(month+1)+'-'+pad(day)+' '+hm,
 'DD/MM/YYYY HH:mm':pad(day)+'/'+pad(month+1)+'/2026 '+hm};
 for(const fmt of Object.keys(expected))assert.equal(formatDate(n,fmt),expected[fmt]);
 assert.equal(formatDate(n,'ddd D MMM'),days[n.getDay()]+' '+day+' '+mon);
}
assert.equal(formatDate(new Date(2028,1,29,0,0,0),'YYYY-MM-DD HH:mm:ss'),'2028-02-29 00:00:00');
assert.equal(formatDate(new Date(2026,11,31,23,59,59),'YYYY-MM-DD HH:mm:ss'),'2026-12-31 23:59:59');
''')

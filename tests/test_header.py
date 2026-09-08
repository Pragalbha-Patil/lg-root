import shutil
import subprocess
import unittest
import build_launcher as bl

@unittest.skipUnless(shutil.which('node'), 'Node.js required')
class HeaderRegressionTest(unittest.TestCase):
    def run_js(self, script):
        subprocess.run(['node', '-e', script], check=True, timeout=30)

    def test_date_names(self):
        page = bl.build()[0]['launcher-app/index.html']
        formatter = page[page.index('function formatDate('):page.index('function tick(')]
        self.run_js('const assert=require("assert");' + formatter + '''
const months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
months.forEach((m,i)=>assert.equal(formatDate(new Date(2026,i,9,15,4,5),'MMM D, h:mm:ss A'),m+' 9, 3:04:05 PM'));
assert.equal(formatDate(new Date(2026,8,9),'ddd D MMM'),'Wed 9 Sep');
assert.equal(formatDate(new Date(2026,8,9),'dddd D MMMM'),'Wednesday 9 September');
assert.equal(formatDate(new Date(2026,8,9),'ddd ddd'),'Wed Wed');
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

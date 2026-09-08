const assert = require('node:assert/strict');
const { test } = require('node:test');
const { browser, constants: C } = require('./helpers.cjs');

const video = { id: 'video', title: 'Video', icon: 'icons/video.png' };
const port = { id: 'com.webos.app.hdmi2', title: 'PlayStation', params: { id: 'wrong', value: 4, PhysicalAddress: '2000' } };
function appFor(t, options = {}) {
    const app = browser(options); t.after(() => app.close()); return app;
}
function ready(app, data = {}) { app.tiles({ tiles: [video], inputs: [port], ...data }); app.prefs(); }
function save(app) {
    const call = app.calls.find(c => c.method === 'setPrefs' && !c.answered);
    return app.respond('setPrefs', { returnValue: true, prefs: call.parameters });
}
function ids(app, section) { return [...app.document.querySelectorAll('#' + section + ' .tile')].map(el => el.dataset.id); }
function row(app, key) { return app.document.querySelector('#settingsRows [data-key="' + key + '"]'); }

test('all startup response orders and preferences preserve inputs and sorting', t => {
    for (const order of ['tiles-first', 'prefs-first']) for (const size of ['compact', 'standard', 'large']) {
        for (const sort of ['mru', 'alpha', 'pinned']) {
            const app = appFor(t); const data = { tiles: [video], inputs: [port, { id: 'av', title: 'AV' }] };
            const prefs = { tileSize: size, sort, pinned: [port.id], hidden: [], labels: false, showSystemStats: false, dateFormat: 'HH:mm:ss' };
            if (order === 'tiles-first') { app.tiles(data); app.prefs(prefs); } else { app.prefs(prefs); app.tiles(data); }
            assert.deepEqual(ids(app, 'inputs'), sort === 'alpha' ? ['av', port.id] : [port.id, 'av']);
            assert.ok(app.document.body.classList.contains('density-' + size));
            assert.ok(app.document.body.classList.contains('no-labels'));
            assert.equal(app.document.querySelector('#sysStats').style.display, 'none');
            assert.ok(app.document.querySelector('[data-id="__LGHOME__"]'));
        }
    }
});

test('completed service requests are released, duplicate replies ignored, and expiry is bounded', async t => {
    const app = appFor(t); const first = app.tiles(); app.prefs();
    assert.equal(app.window.__mhKeep.length, 0);
    first.onSuccess({ returnValue: true, tiles: [video], inputs: [] });
    assert.deepEqual(ids(app, 'grid'), []);
    await app.clock.run(1000); assert.equal(app.window.__mhKeep.length, 1);
    await app.clock.run(15000); assert.equal(app.window.__mhKeep.length, 0);
    assert.equal(app.calls.find(c => c.method === 'getSystemStats').request.cancelled, true);
    app.window.__mhKeep = Array(32).fill({});
    await app.clock.run(5000); assert.equal(app.window.__mhKeep.length, 32);
});

test('Palm bridge fallback handles valid, failed, malformed, thrown and missing platform APIs', async t => {
    for (const options of [{ bridgeOnly: true }, { throwRequest: true }]) {
        const app = appFor(t, options);
        assert.equal(app.bridges.length, 2);
        app.bridges[0].onservicecallback(JSON.stringify({ returnValue: true, tiles: [video], inputs: [] }));
        app.bridges[1].onservicecallback('{bad');
        assert.deepEqual(ids(app, 'grid'), ['video']); assert.equal(app.window.__mhKeep.length, 0);
    }
    const failed = appFor(t, { bridgeOnly: true });
    failed.bridges[0].onservicecallback('{"returnValue":false}'); failed.bridges[1].onservicecallback('null');
    assert.equal(failed.window.__mhKeep.length, 0);
    for (const options of [{ offline: true }, { bridgeOnly: true, throwBridge: true }, { bridgeOnly: true, throwBridgeCall: true }]) {
        const app = appFor(t, options); assert.equal(app.window.__mhKeep.length, 0);
    }
    const expired = appFor(t, { bridgeOnly: true, throwCancel: true });
    await expired.clock.run(15000); assert.equal(expired.window.__mhKeep.length, 0);
});

test('bad tile replies preserve the last grid and retries recover without overlapping requests', async t => {
    const app = appFor(t); ready(app); await app.clock.run(400);
    for (const response of [null, {}, { returnValue: false }, { returnValue: true, tiles: {}, inputs: [] }, { returnValue: true, tiles: [] }]) {
        app.window.dispatchEvent(new app.window.Event('focus')); app.respond('getTiles', response);
        assert.deepEqual(ids(app, 'grid'), ['video']); await app.clock.run(400);
    }
    await app.clock.run(2500); const count = app.calls.length;
    app.window.dispatchEvent(new app.window.Event('focus')); assert.equal(app.calls.length, count);
    app.tiles({ tiles: [], inputs: [] }); assert.deepEqual(ids(app, 'grid'), []);
    assert.ok(app.document.querySelector('[data-id="__LGHOME__"]'));
});

test('invalid live records are removed and optional Settings remains absent', t => {
    const app = appFor(t, { settings: false });
    app.tiles({ tiles: [null, {}, { id: 1 }, { id: '../bad' }, { id: C.SELF_ID }, { id: '__LGHOME__' }, video, video,
        { id: 'no-title', title: 3 }], inputs: [null, port] }); app.prefs();
    assert.deepEqual(ids(app, 'grid'), ['video', 'no-title']);
    assert.deepEqual(ids(app, 'sysrow'), ['__LGHOME__']);
    app.click('#settingsBtn'); app.click('[data-key="tvsettings"]');
    assert.equal(app.calls.filter(c => c.method === 'launchApp').length, 0);
});

test('tile icons fall back to initials and all app-provided menu/search text is escaped', t => {
    const app = appFor(t); const title = '<img src=x onerror="bad()"> & "Video"';
    ready(app, { tiles: [{ ...video, title }, { id: 'blank', title: '  ' }] });
    const tile = app.document.querySelector('#grid .tile');
    tile.querySelector('img').dispatchEvent(new app.window.Event('error'));
    assert.equal(tile.querySelector('.initial').textContent, '<');
    assert.equal(app.document.querySelector('[data-id="blank"] .initial').textContent, '?');
    tile.focus(); app.key(457);
    assert.equal(app.document.querySelector('#optionsPanel .panel-head small').textContent, title);
    assert.equal(app.document.querySelector('#optionsPanel .panel-head img'), null);
    app.key(461); app.key(86, 'keydown', { key: 'v' });
    assert.equal(app.document.querySelector('#searchRows .sl').textContent, title);
    assert.equal(app.document.querySelector('#searchRows img'), null);
});

test('settings cycle choices, toggles and accents; save errors are visible; action rows ignore arrows', t => {
    const app = appFor(t); ready(app); app.click('#settingsBtn');
    assert.equal(app.window.getComputedStyle(app.document.querySelector('#grid .label')).display, 'block');
    assert.equal(app.window.getComputedStyle(row(app, 'accent').querySelector('.val')).display, 'flex');
    for (const key of ['accent', 'tileSize', 'labels', 'showSystemStats', 'dateFormat', 'sort']) {
        row(app, key).focus(); app.key(39); save(app); app.key(37); save(app);
    }
    row(app, 'close').focus(); const count = app.calls.length; app.key(39); assert.equal(app.calls.length, count);
    app.click('[data-key="labels"]');
    const call = app.calls.find(c => c.method === 'setPrefs' && !c.answered); call.answered = true; call.onFailure({ errorText: 'disk full' });
    assert.match(app.document.querySelector('#err').textContent, /disk full/);
    app.click('[data-key="reset"]'); save(app);
    assert.equal(app.document.body.classList.contains('no-labels'), false);
    app.click('[data-key="close"]'); assert.equal(app.document.querySelector('#settingsPanel').classList.contains('show'), false);
});

test('late preference replies cannot overwrite a newer local edit', t => {
    const app = appFor(t); app.tiles({ tiles: [video], inputs: [] });
    app.click('#settingsBtn'); app.click('[data-key="labels"]');
    app.visible(false); app.visible(true);
    assert.equal(app.calls.filter(c => c.method === 'getPrefs').length, 1,
        'foreground reload must not fetch stale preferences while saving');
    app.prefs({ labels: true }); assert.equal(app.document.body.classList.contains('no-labels'), true);
    app.click('[data-key="labels"]');
    assert.equal(app.calls.filter(c => c.method === 'setPrefs').length, 1, 'writes must be serialized');
    save(app); save(app); assert.equal(app.document.body.classList.contains('no-labels'), false);
});

test('options Launch and Close rows work and unrelated overlay keys are ignored', t => {
    const app = appFor(t); ready(app); app.document.querySelector('#grid .tile').focus();
    app.key(457); assert.equal(app.key(112, 'keydown', { key: 'F1' }).defaultPrevented, false);
    app.click('#optionsRows .optrow:nth-child(4)'); assert.equal(app.document.querySelector('#optionsPanel.show'), null);
    app.key(457); app.click('#optionsRows .optrow:nth-child(3)'); assert.equal(app.calls.at(-1).parameters.id, 'video');
    app.respond('launchApp', { returnValue: true });
});

test('Settings tile opens launcher preferences and TV settings action launches the platform settings', async t => {
    const app = appFor(t); ready(app);
    app.click('[data-id="' + C.SETTINGS_ID + '"]'); assert.ok(app.document.querySelector('#settingsPanel.show'));
    app.click('[data-key="tvsettings"]'); assert.equal(app.calls.at(-1).parameters.id, C.SETTINGS_ID);
    app.respond('launchApp', { returnValue: true }); await app.clock.run(250);
    app.click('[data-id="__LGHOME__"]'); app.respond('openLGHome', { returnValue: false, errorText: 'denied' });
    assert.match(app.document.querySelector('#err').textContent, /denied/);
});

test('long OK opens options without launching; pin, hide, restore, and close work', async t => {
    const app = appFor(t); ready(app); const tile = app.document.querySelector('#grid .tile'); tile.focus();
    app.key(13); app.key(13); await app.clock.run(700); app.key(13);
    assert.equal(app.calls.filter(c => c.method === 'setPrefs').length, 0);
    app.key(13, 'keyup');
    assert.equal(app.calls.filter(c => c.method === 'launchApp').length, 0);
    app.click('#optionsRows .optrow'); save(app); app.tiles({ tiles: [video], inputs: [port] });
    assert.ok(app.document.querySelector('#grid .pin'));
    app.document.querySelector('#grid .tile').focus(); app.key(412); app.click('#optionsRows .optrow'); save(app);
    app.tiles({ tiles: [video], inputs: [port] }); assert.equal(app.document.querySelector('#grid .pin'), null);
    app.document.querySelector('#grid .tile').focus(); app.key(457); app.click('#optionsRows .optrow:nth-child(2)'); save(app);
    app.tiles({ tiles: [video], inputs: [port] }); assert.deepEqual(ids(app, 'grid'), []);
    app.click('#settingsBtn'); app.click('[data-key="manage"]'); assert.match(app.document.querySelector('#optionsRows').textContent, /Video/);
    app.click('#optionsRows [data-id="video"]'); save(app); app.tiles({ tiles: [video], inputs: [port] }); assert.deepEqual(ids(app, 'grid'), ['video']);
    app.click('#settingsBtn'); app.click('[data-key="manage"]'); assert.match(app.document.querySelector('#optionsRows').textContent, /No hidden/);
    app.click('#optionsRows [data-key="close"]');
});

test('search ranks prefixes before substrings, caps results, edits only with Backspace and closes with Back', t => {
    const app = appFor(t); ready(app, { tiles: [{ id: 'prefix', title: 'App' }, { id: 'contains', title: 'My App' },
        ...Array.from({ length: 10 }, (_, i) => ({ id: 'app' + i, title: 'App ' + i }))] });
    app.key(65, 'keydown', { key: 'a' });
    assert.equal(app.document.querySelectorAll('#searchRows .srow').length, 8);
    assert.equal(app.document.querySelector('#searchRows .srow').dataset.id, 'prefix');
    app.key(80, 'keydown', { key: 'p' }); app.key(8); assert.match(app.document.querySelector('#searchQ').textContent, /a/);
    app.key(461); assert.equal(app.document.querySelector('#searchBox.show'), null);
    app.key(81, 'keydown', { key: 'q' }); assert.match(app.document.querySelector('#searchRows').textContent, /No matches/);
    app.key(8); app.key(8); assert.equal(app.document.querySelector('#searchBox.show'), null);
    assert.equal(app.key(461).defaultPrevented, true);
});

test('search launches input parameters; double taps and stale launch completions cannot unlock a newer launch', async t => {
    const app = appFor(t); ready(app); app.key(80, 'keydown', { key: 'p' }); app.key(13);
    const first = app.calls.find(c => c.method === 'launchApp');
    assert.equal(first.parameters.id, port.id); assert.equal(first.parameters.params.value, 4);
    assert.equal(first.parameters.params.id, undefined);
    app.click('#grid .tile'); assert.equal(app.calls.filter(c => c.method === 'launchApp').length, 1);
    await app.clock.run(4000); app.click('#grid .tile');
    first.onSuccess({ returnValue: true }); await app.clock.run(250);
    app.click('#grid .tile'); assert.equal(app.calls.filter(c => c.method === 'launchApp').length, 2);
    first.onFailure({ errorText: 'late' });
    const second = app.calls.filter(c => c.method === 'launchApp')[1]; second.onFailure({ errorText: 'offline' });
    await app.clock.run(0); assert.match(app.document.querySelector('#err').textContent, /offline/);
});

test('remote navigation, repeating arrows, focus restoration and overlays stay usable', async t => {
    const app = appFor(t); ready(app, { tiles: [video, { id: 'two', title: 'Two' }, { id: 'three', title: 'Three' }] });
    const tiles = [...app.document.querySelectorAll('.tile')];
    tiles.forEach((tile, i) => { tile.getBoundingClientRect = () => ({ left: i % 3 * 150, top: Math.floor(i / 3) * 150, width: 100, height: 100 }); });
    tiles[0].focus(); app.key(39); const focused = app.document.activeElement; app.key(39); assert.equal(app.document.activeElement, focused);
    await app.clock.run(450); await app.clock.run(150); await app.clock.run(150);
    for (let i = 0; i < 8; i++) await app.clock.run(90);
    await app.clock.run(55); app.key(39, 'keyup');
    for (const key of [37, 38, 40]) { app.key(key); app.key(key, 'keyup'); }
    app.click('#settingsBtn'); app.key(40); app.key(38); row(app, 'labels').focus(); app.key(13); app.key(13, 'keyup'); save(app);
    app.key(27); app.document.querySelector('#grid .tile').focus(); app.key(457); app.key(40); app.key(37); app.key(461);
    app.click('#settingsBtn'); app.click('[data-key="manage"]'); app.key(40); app.key(38); app.key(461);
    app.key(86, 'keydown', { key: 'v' }); app.key(40); app.key(38); app.key(461);
    app.document.querySelector('#grid .tile').focus(); app.key(13); app.key(13, 'keyup');
    assert.equal(app.calls.at(-1).method, 'launchApp');
});

test('blur/background cancels held keys and skips stats polling; foreground reloads preferences', async t => {
    const app = appFor(t); ready(app); app.document.querySelector('#grid .tile').focus();
    app.key(39); app.key(13); app.window.dispatchEvent(new app.window.Event('blur'));
    await app.clock.run(450); await app.clock.run(700); assert.equal(app.document.querySelector('#optionsPanel.show'), null);
    app.visible(false); await app.clock.run(1000);
    assert.equal(app.calls.filter(c => c.method === 'getSystemStats').length, 0);
    app.visible(true); app.prefs({ showSystemStats: false }); app.tiles();
    await app.clock.run(5000); assert.equal(app.calls.filter(c => c.method === 'getSystemStats').length, 0);
});

test('webOS foreground focus overrides a stale hidden state for tiles and stats', async t => {
    const app = appFor(t, { hidden: true, focused: true });
    ready(app);
    assert.deepEqual(ids(app, 'grid'), ['video']);
    await app.clock.run(1000);
    assert.equal(app.calls.filter(c => c.method === 'getSystemStats').length, 1);
    app.visible(false);
    assert.equal(app.calls.filter(c => c.method === 'getPrefs').length, 2);
});

test('stats render numbers and unknowns, and header updates use text rather than HTML', async t => {
    const app = appFor(t); app.tiles({ header: { text: '<hello>', brand: '<Brand>' } }); app.prefs();
    assert.equal(app.document.querySelector('#headText').textContent, '<HELLO>'); assert.equal(app.document.title, '<Brand>');
    await app.clock.run(1000); app.respond('getSystemStats', { returnValue: true, cpu: 0, ram: 60, temp: 65 });
    assert.equal(app.document.querySelector('#statCpu').textContent, '0%');
    await app.clock.run(5000); app.respond('getSystemStats', { returnValue: true });
    assert.equal(app.document.querySelector('#statTemp').textContent, '--°C');
    assert.ok(app.document.querySelector('#clock small').textContent.length);
});

test('fallback tiles and keyboard Settings work before the relay answers, including malformed parameters', async t => {
    const app = appFor(t);
    app.document.querySelector('#grid .tile').dataset.params = '{broken';
    app.click('#grid .tile'); assert.deepEqual(Object.keys(app.calls.at(-1).parameters.params), []);
    app.respond('launchApp', { returnValue: true }); await app.clock.run(250);
    app.document.querySelector('#settingsBtn').focus(); app.key(13); app.key(13, 'keyup');
    assert.ok(app.document.querySelector('#settingsPanel.show'));
    app.key(461);
    app.document.activeElement.blur(); app.key(39); app.key(39, 'keyup');
    assert.ok(app.document.activeElement.classList.contains('tile'));
});

test('live system tiles remain unique, multiple pins keep their order, and unknown settings rows are inert', t => {
    const app = appFor(t);
    app.tiles({ tiles: [video, { id: 'two', title: 'Two' }, { id: C.SETTINGS_ID, title: 'Settings' }], inputs: [] });
    app.prefs({ pinned: ['two', 'video'] }); assert.deepEqual(ids(app, 'grid'), ['two', 'video']);
    assert.equal(ids(app, 'sysrow').filter(id => id === C.SETTINGS_ID).length, 1);
    app.click('#settingsBtn');
    const unknown = app.document.createElement('div'); unknown.className = 'srow'; unknown.dataset.key = 'removed-setting';
    app.document.querySelector('#settingsRows').appendChild(unknown);
    const count = app.calls.length; unknown.click(); assert.equal(app.calls.length, count);
});

const assert = require('node:assert/strict');
const { test } = require('node:test');
const { browser, service, watcher } = require('./helpers.cjs');

test('launcher starts with a fallback and replaces it with live tiles', t => {
    const app = browser(); t.after(() => app.close());
    assert.ok(app.document.querySelector('#grid .tile'));
    app.tiles({ tiles: [{ id: 'video', title: 'Video' }] }); app.prefs();
    assert.equal(app.document.querySelector('#grid .tile').dataset.id, 'video');
    assert.ok(app.document.querySelector('[data-id="__LGHOME__"]'));
});

test('relay returns defaults and watcher opens its subscription', () => {
    const relay = service();
    assert.equal(relay.request('getPrefs')[0].prefs.accent, 'steel');
    assert.equal(watcher().children.length, 1);
});

const assert = require('node:assert/strict');
const { test } = require('node:test');
const { browser } = require('./helpers.cjs');

test('App labels only hides tile captions and preserves accessible tile names', t => {
    for (const labels of [true, false]) {
        const app = browser(); t.after(() => app.close());
        app.tiles({ tiles: [{ id: 'video', title: 'Video' }], inputs: [], prefs: { labels, showSystemStats: true } });
        const tile = app.document.querySelector('#grid .tile');
        assert.equal(tile.getAttribute('aria-label'), 'Video');
        assert.equal(app.window.getComputedStyle(tile.querySelector('.label')).display === 'none', !labels);
        for (const caption of app.document.querySelectorAll('#sysStats .label')) {
            assert.notEqual(app.window.getComputedStyle(caption).display, 'none');
        }
        app.document.dispatchEvent(new app.window.Event('webOSRelaunch'));
        app.tiles({ tiles: [], inputs: [], prefs: { labels, showSystemStats: false } });
        assert.equal(app.window.getComputedStyle(app.document.querySelector('#sysStats')).display, 'none');
    }
});

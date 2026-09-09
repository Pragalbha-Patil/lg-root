const assert = require('node:assert/strict');
const { test } = require('node:test');
const { browser } = require('./helpers.cjs');

test('permanently missing icons retry once per refresh without rebuilding tiles', async t => {
    const app = browser(); t.after(() => app.close());
    const response = { tiles: [{ id: 'video', title: 'Video', icon: 'icons/video.png' }], inputs: [], prefs: {} };
    app.tiles(response);
    const tile = app.document.querySelector('#grid .tile'); tile.focus();
    for (let i = 0; i < 3; i++) {
        const previous = tile.querySelector('img');
        previous.dispatchEvent(new app.window.Event('error'));
        assert.equal(tile.querySelector('img'), null);
        await app.clock.run(400);
        app.document.dispatchEvent(new app.window.Event('webOSRelaunch')); app.tiles(response);
        assert.equal(app.document.querySelector('#grid .tile'), tile);
        assert.equal(tile.querySelectorAll('img').length, 1);
        assert.notEqual(tile.querySelector('img'), previous);
        assert.equal(app.document.activeElement, tile);
    }
});

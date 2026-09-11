const assert = require('node:assert/strict');
const { test } = require('node:test');
const { browser } = require('./helpers.cjs');

test('changed discovery during a move restores its marker and focus; Back restores the snapshot', async t => {
    const app = browser(); t.after(() => app.close());
    const tiles = [{ id: 'video', title: 'Video' }, { id: 'alpha', title: 'Alpha' }];
    app.tiles({ tiles, prefs: { pinned: ['video', 'alpha'], brandSetupDone: true } });
    app.document.querySelector('[data-id="video"]').focus();
    app.key(457);
    app.click('#optionsRows .optrow:nth-child(3)');
    app.key(39); app.key(39, 'keyup');
    const before = app.document.querySelector('[data-id="video"]');
    app.window.dispatchEvent(new app.window.Event('focus'));
    app.tiles({ tiles: [...tiles, { id: 'new', title: 'New' }], prefs: {} });
    const moved = app.document.querySelector('[data-id="video"]');
    assert.notEqual(moved, before);
    assert.equal(app.document.activeElement, moved);
    assert.equal(moved.classList.contains('moving'), true);
    await app.clock.run(400);
    app.window.dispatchEvent(new app.window.Event('focus'));
    app.tiles({ tiles: [...tiles, { id: 'new', title: 'New' }], prefs: {} });
    assert.equal(app.document.querySelector('[data-id="video"]'), moved);
    assert.equal(app.document.activeElement, moved);
    app.key(461);
    assert.deepEqual([...app.document.querySelectorAll('#grid .tile')].map(el => el.dataset.id),
        ['video', 'alpha', 'new']);
    assert.equal(app.document.querySelector('.moving'), null);
    assert.equal(app.calls.filter(call => call.method === 'setPrefs').length, 0);
});

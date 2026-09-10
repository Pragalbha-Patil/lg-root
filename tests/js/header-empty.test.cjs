const assert = require('node:assert/strict');
const { test } = require('node:test');
const { browser } = require('./helpers.cjs');

test('empty header strings clear text and title while absent or invalid values preserve them', async t => {
    const app = browser(); t.after(() => app.close());
    app.tiles({ prefs: {}, header: { text: 'Hello', brand: 'Home' } });
    async function refresh(header) {
        await app.clock.run(400);
        app.window.dispatchEvent(new app.window.Event('focus'));
        app.tiles({ prefs: {}, header });
    }
    await refresh({ text: '', brand: '' });
    assert.equal(app.document.getElementById('headText').textContent, '');
    assert.equal(app.document.getElementById('headBrand').textContent, '');
    assert.equal(app.document.title, '');
    await refresh({ text: 'Welcome', brand: 'Living room' });
    await refresh({ text: null, brand: 42 });
    await refresh({});
    assert.equal(app.document.getElementById('headText').textContent, 'WELCOME');
    assert.equal(app.document.getElementById('headBrand').textContent, 'Living room');
    assert.equal(app.document.title, 'Living room');
});

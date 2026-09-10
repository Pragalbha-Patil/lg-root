const assert = require('node:assert/strict');
const { test } = require('node:test');
const { browser } = require('./helpers.cjs');

test('stats polling is single-flight and resumes after success, failure and timeout', async t => {
    const app = browser(); t.after(() => app.close());
    app.tiles({ prefs: { showSystemStats: true } });
    const requests = () => app.calls.filter(c => c.method === 'getSystemStats');
    await app.clock.run(1000);
    await app.clock.run(5000);
    await app.clock.run(5000);
    assert.equal(requests().length, 1);
    app.respond('getSystemStats', { returnValue: true, cpu: 12, ram: 34, temp: 50 });
    await app.clock.run(5000);
    assert.equal(requests().length, 2);
    app.respond('getSystemStats', { returnValue: false, errorText: 'unavailable' });
    await app.clock.run(5000);
    assert.equal(requests().length, 3);
    await app.clock.run(15000);
    assert.equal(requests()[2].request.cancelled, true);
    await app.clock.run(5000);
    assert.equal(requests().length, 4);
});

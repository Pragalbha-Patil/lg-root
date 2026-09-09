const assert = require('node:assert/strict');
const { test } = require('node:test');
const { watcher, constants: C } = require('./helpers.cjs');

test('icons use small alternatives, retain good bytes on failure and prune only confirmed removals', async () => {
    const w = watcher(), dir = C.APP_DIR + '/icons/';
    w.disk.files.set('/small', 'small');
    for (const source of ['/missing', '/empty', '/large', '/unreadable']) {
        w.disk.files.set('/empty', ''); w.disk.files.set('/large', Buffer.alloc(300001));
        w.disk.files.set('/unreadable', 'x'); w.disk.errors.set('read:/unreadable', new Error('denied'));
        w.context.provisionIcons([{ id: 'video', largeIcon: source, icon: '/small' }]);
        assert.equal(w.disk.files.get(dir + 'video.png').toString(), 'small');
    }
    w.disk.files.set(dir + 'old.png', 'old');
    w.disk.files.set(dir + 'notes.txt', 'keep');
    w.disk.files.set(dir + '@invalid.png', 'keep');
    w.disk.files.set(dir + C.SETTINGS_ID + '.png', 'settings');
    const fail = w.context.runProvision(); w.respond({ returnValue: false }); await fail;
    assert.equal(w.disk.files.has(dir + 'old.png'), true);
    w.disk.errors.set('unlink:' + dir + 'old.png', new Error('denied'));
    w.context.provisionIcons([{ id: 'video', icon: '/missing' }]);
    assert.equal(w.disk.files.has(dir + 'old.png'), true);
    w.disk.errors.delete('unlink:' + dir + 'old.png');
    const empty = w.context.runProvision(); w.respond({ returnValue: true, launchPoints: [] }); await empty;
    assert.equal(w.disk.files.has(dir + 'old.png'), false);
    assert.equal(w.disk.files.has(dir + 'video.png'), false);
    assert.equal(w.disk.files.has(dir + C.SETTINGS_ID + '.png'), true);
    assert.equal(w.disk.files.has(dir + 'notes.txt'), true);
    w.disk.errors.set('readdir', new Error('denied')); w.context.provisionIcons([]);
});

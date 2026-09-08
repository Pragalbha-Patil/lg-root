// Shared runtime constants for the launcher-service (webOS/Node).
// Keep ids and mount paths in ONE place: the app and service dirs must agree.

var SELF_ID = 'org.minimal.home';
var HOME_ID = 'com.webos.app.home';
var SETTINGS_ID = 'com.palm.app.settings';
var SETTINGS_ICON = '/usr/palm/applications/com.palm.app.settings/icon.png';
var LG_HOME_TILE_ID = '__LGHOME__';

// appinfo.json lives next to the app assets.
var APP_DIR = '/media/developer/apps/usr/palm/applications/' + SELF_ID;
// this service always lives under the same org.minimal.home.service dir.
var SVC_DIR = '/media/developer/apps/usr/palm/services/' + SELF_ID + '.service';
// Runtime config starts as a build-generated COPY kept in THIS dir: the dev-mode
// service jailer cannot open files under .../applications/<id> (ENOENT),
// so the service rereads its own copy on each getTiles request. Root can edit it.
var CONFIG_FILE = SVC_DIR + '/config.json';
var BYPASS_FILE = SVC_DIR + '/.noredirect';
var USAGE_FILE = SVC_DIR + '/usage.json';
var PREFS_FILE = SVC_DIR + '/prefs.json';
var WATCH_LOG = '/tmp/minhome-watch.log';
var SVC_LOG = '/tmp/minhome-svc.log';

module.exports = {
    SELF_ID: SELF_ID,
    HOME_ID: HOME_ID,
    SETTINGS_ID: SETTINGS_ID,
    SETTINGS_ICON: SETTINGS_ICON,
    LG_HOME_TILE_ID: LG_HOME_TILE_ID,
    APP_DIR: APP_DIR,
    SVC_DIR: SVC_DIR,
    CONFIG_FILE: CONFIG_FILE,
    BYPASS_FILE: BYPASS_FILE,
    USAGE_FILE: USAGE_FILE,
    PREFS_FILE: PREFS_FILE,
    WATCH_LOG: WATCH_LOG,
    SVC_LOG: SVC_LOG,
    STATS_FILE: '/tmp/minhome-stats.json',
    FIRSTUSE_FILE: '/var/luna/preferences/ran-firstuse',
    BYPASS_MS: 10 * 60 * 1000,
    LUNA_TIMEOUT_MS: 15000,
    LOG_MAX_BYTES: 100000
};

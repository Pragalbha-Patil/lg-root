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
var CONFIG_FILE = APP_DIR + '/config.json';
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
  SVC_LOG: SVC_LOG
};
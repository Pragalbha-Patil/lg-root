'use strict';

// Inject fs so device I/O can be tested without loading the platform service.
module.exports = function (fs) {
    function readJson(path) {
        try {
            return JSON.parse(fs.readFileSync(path, 'utf8'));
        } catch (error) {
            return null;
        }
    }
    function writeJson(path, value) {
        // A crash before rename leaves the last complete preferences intact.
        var temporary = path + '.tmp';
        try {
            fs.writeFileSync(temporary, JSON.stringify(value));
            fs.renameSync(temporary, path);
        } catch (error) {
            try {
                fs.unlinkSync(temporary);
            } catch (ignored) {
                /* Best-effort cleanup. */
            }
            throw error;
        }
    }
    function logger(path, limit) {
        var size = 0;
        try {
            size = fs.statSync(path).size;
        } catch (ignored) {
            /* First log on this boot. */
        }
        return function (event) {
            try {
                var line =
                    JSON.stringify({ ts: Date.now(), event: event }) + '\n';
                var bytes = Buffer.byteLength(line, 'utf8');
                if (bytes > limit) return;
                if (size + bytes > limit) {
                    fs.writeFileSync(path, line);
                    size = bytes;
                } else {
                    fs.appendFileSync(path, line);
                    size += bytes;
                }
            } catch (ignored) {
                /* Logging must not prevent launches. */
            }
        };
    }
    return { readJson: readJson, writeJson: writeJson, logger: logger };
};

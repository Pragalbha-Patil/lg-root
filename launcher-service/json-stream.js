'use strict';

// luna-send may split or combine pretty-printed JSON objects across chunks.
module.exports = function (limit) {
    var buffer = '',
        depth = 0,
        quoted = false,
        escaped = false;
    return function (chunk) {
        var objects = [];
        for (var i = 0; i < chunk.length; i++) {
            var character = chunk[i];
            if (depth === 0 && character !== '{') continue;
            buffer += character;
            if (buffer.length > limit) {
                buffer = '';
                depth = 0;
                quoted = false;
                escaped = false;
                break;
            }
            if (quoted) {
                if (escaped) escaped = false;
                else if (character === '\\') escaped = true;
                else if (character === '"') quoted = false;
            } else if (character === '"') quoted = true;
            else if (character === '{') depth++;
            else if (character === '}') depth--;
            if (depth === 0) {
                try {
                    objects.push(JSON.parse(buffer));
                } catch (ignored) {
                    /* Skip malformed frames. */
                }
                buffer = '';
            }
        }
        return objects;
    };
};

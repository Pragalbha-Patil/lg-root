import js from '@eslint/js';
import globals from 'globals';

export default [
    { ignores: ['dist/**', 'node_modules/**', 'launcher-app/index.html'] },
    js.configs.recommended,
    {
        files: ['launcher-service/*.js', 'launcher-app/src/*.js'],
        languageOptions: { ecmaVersion: 5, sourceType: 'script' },
        rules: {
            eqeqeq: ['error', 'always'],
            'no-unused-vars': ['error', { args: 'none', caughtErrors: 'none' }],
            'no-empty': ['error', { allowEmptyCatch: true }],
            'no-trailing-spaces': 'error',
            'eol-last': ['error', 'always']
        }
    },
    { files: ['launcher-service/*.js'], languageOptions: { globals: globals.node } },
    {
        files: ['launcher-app/src/*.js', 'launcher-service/model.js'],
        languageOptions: { globals: { ...globals.browser, PalmServiceBridge: 'readonly' } }
    },
    { files: ['launcher-service/watcher.js'], languageOptions: { ecmaVersion: 2018 } },
    {
        files: ['tests/js/*.cjs'],
        languageOptions: { ecmaVersion: 'latest', sourceType: 'commonjs', globals: globals.node }
    }
];

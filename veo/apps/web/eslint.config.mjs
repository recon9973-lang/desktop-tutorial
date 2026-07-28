import nextCoreWebVitals from 'eslint-config-next/core-web-vitals';
import nextTypeScript from 'eslint-config-next/typescript';

/** @type {import('eslint').Linter.Config[]} */
const config = [
  {
    ignores: ['.next/**', 'next-env.d.ts', 'node_modules/**'],
  },
  ...nextCoreWebVitals,
  ...nextTypeScript,
  {
    rules: {
      'no-warning-comments': [
        'error',
        { terms: ['todo', 'fixme', 'xxx', 'hack'], location: 'anywhere' },
      ],
    },
  },
];

export default config;

import path from 'node:path';
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

const src = path.join(import.meta.dirname, 'src');

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': src,
      // `server-only` throws on import outside a React Server Component. The
      // guard is what we want in production; under test it would stop us from
      // ever exercising the server modules, so it resolves to a no-op here.
      'server-only': path.join(import.meta.dirname, 'test', 'server-only-stub.ts'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    // An opaque origin has no Web Storage, and the token tests must be able to
    // prove that storage is empty rather than absent.
    environmentOptions: { jsdom: { url: 'https://console.veo.test/' } },
    setupFiles: ['./vitest.setup.ts'],
    include: ['src/**/*.test.{ts,tsx}', 'test/**/*.test.{ts,tsx}'],
  },
});

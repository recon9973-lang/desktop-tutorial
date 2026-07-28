/**
 * Stand-in for the `server-only` package under test.
 *
 * The real package throws when a module is pulled into a client bundle. That
 * boundary is enforced by `next build`, not by Vitest, so here the import is a
 * no-op. `src/lib/no-client-token.test.ts` asserts the boundary separately.
 */
export {};

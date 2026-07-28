// Fails when src/schema.d.ts no longer matches apps/api/openapi.json.
// The generated client is part of the contract: an API change that does not
// regenerate it must not merge.
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const generated = join(mkdtempSync(join(tmpdir(), "veo-client-")), "schema.d.ts");

execFileSync(
  "node",
  ["node_modules/openapi-typescript/bin/cli.js", "../../apps/api/openapi.json", "-o", generated],
  { stdio: "inherit" },
);

const fresh = readFileSync(generated, "utf8");
const committed = readFileSync("src/schema.d.ts", "utf8");

if (fresh !== committed) {
  console.error(
    "packages/api-client/src/schema.d.ts is stale.\n" +
      "Run: pnpm --filter @veo/api-client generate",
  );
  process.exit(1);
}

console.log("api-client schema is in sync with apps/api/openapi.json");

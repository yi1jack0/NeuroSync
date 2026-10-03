// Fails the build if first-load JS+CSS exceeds the budget in docs/WEB_PLAN.md (70 KB gzipped).
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { gzipSync } from 'node:zlib';

const BUDGET = 70 * 1024;
const dir = join(import.meta.dirname, '..', 'dist', 'assets');
let total = 0;
for (const f of readdirSync(dir)) {
  if (!/\.(js|css)$/.test(f) || f.startsWith('workbox')) continue;
  const gz = gzipSync(readFileSync(join(dir, f))).length;
  total += gz;
  console.log(`${(gz / 1024).toFixed(1).padStart(6)} KB  ${f}`);
}
console.log(`${(total / 1024).toFixed(1).padStart(6)} KB  total (budget ${BUDGET / 1024} KB)`);
if (total > BUDGET) { console.error('bundle over budget'); process.exit(1); }

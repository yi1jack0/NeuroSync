// Copies data shared with the desktop app into the web build (single source of truth):
//   ../src/neurosync/app/builtin/*.json      -> src/generated/presets.json   (merged, ordered like desktop)
//   ../src/neurosync/assets/ambience/*.ogg    -> public/ambience/
//   ../src/neurosync/assets/ambience/catalog.json -> src/generated/catalog.json
// AAC fallbacks (*.m4a) are committed in public/ambience (see transcode-aac.mjs).
import { copyFileSync, mkdirSync, readFileSync, readdirSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = join(dirname(fileURLToPath(import.meta.url)), '..');
const pkg = join(web, '..', 'src', 'neurosync');
const gen = join(web, 'src', 'generated');
const amb = join(web, 'public', 'ambience');
mkdirSync(gen, { recursive: true });
mkdirSync(amb, { recursive: true });

const builtinDir = join(pkg, 'app', 'builtin');
const presets = readdirSync(builtinDir).filter((f) => f.endsWith('.json')).sort()
  .flatMap((f) => JSON.parse(readFileSync(join(builtinDir, f), 'utf8')));
writeFileSync(join(gen, 'presets.json'), JSON.stringify(presets, null, 1) + '\n');

const catalog = JSON.parse(readFileSync(join(pkg, 'assets', 'ambience', 'catalog.json'), 'utf8'));
writeFileSync(join(gen, 'catalog.json'), JSON.stringify(catalog, null, 1) + '\n');
for (const s of catalog) {
  copyFileSync(join(pkg, 'assets', 'ambience', s.file), join(amb, s.file));
  const m4a = s.file.replace(/\.ogg$/, '.m4a');
  if (!existsSync(join(amb, m4a))) console.warn(`warning: no AAC fallback ${m4a} (run: npm run transcode)`);
}
console.log(`synced ${presets.length} presets, ${catalog.length} ambience sounds`);

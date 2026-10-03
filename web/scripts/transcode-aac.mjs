// Safari's Ogg support varies, so every ambience sound also ships as AAC (.m4a).
// Run after the desktop assets change:  npm run transcode   (needs ffmpeg on PATH)
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(web, '..', 'src', 'neurosync', 'assets', 'ambience');
const catalog = JSON.parse(readFileSync(join(src, 'catalog.json'), 'utf8'));
for (const s of catalog) {
  const out = join(web, 'public', 'ambience', s.file.replace(/\.ogg$/, '.m4a'));
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', join(src, s.file), '-c:a', 'aac', '-b:a', '128k',
    '-ar', '48000', '-movflags', '+faststart', '-map_metadata', '-1', out]);
  console.log('wrote', out);
}

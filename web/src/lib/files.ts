// Import/export of presets as .json files (same format as the desktop app).
import { type Preset, parsePreset } from '../domain/preset';
import { shareable } from './share';

export function downloadPreset(p: Preset): number {
  const { preset, dropped } = shareable(p);
  const blob = new Blob([JSON.stringify(preset, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${p.name.replace(/[^\w\- ]+/g, '').trim() || 'preset'}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  return dropped;
}

export async function readPresetFile(file: File): Promise<Preset> {
  if (file.size > 256 * 1024) throw new Error('file too large');
  return parsePreset(JSON.parse(await file.text()));
}

export function pickFile(accept: string): Promise<File | null> {
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = accept;
    input.onchange = () => resolve(input.files?.[0] ?? null);
    input.oncancel = () => resolve(null);
    input.click();
  });
}

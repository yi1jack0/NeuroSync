// Preset schema identical to the desktop JSON (src/neurosync/domain/models.py).
import { type BandName, BANDS, band } from './bands';
import { BASE_FREQ_MAX_HZ, BASE_FREQ_MIN_HZ, BEAT_FREQ_MAX_HZ, BEAT_FREQ_MIN_HZ, clamp } from './limits';

export type ChannelKind = 'binaural' | 'noise' | 'sample';
export type NoiseVariant = 'white' | 'pink' | 'brown';
export const NOISE_VARIANTS: readonly NoiseVariant[] = ['white', 'pink', 'brown'];
export const ASSET_PREFIX = 'asset:';
export const LOCAL_PREFIX = 'local:';   // web-only: user sound stored in IndexedDB

export interface ChannelConfig {
  kind: ChannelKind; name: string; volume: number; pan: number; muted: boolean;
  base_hz: number; beat_hz: number; variant: NoiseVariant; path: string;
}

export interface Preset {
  name: string; band: BandName; icon: string; description: string; category: string;
  channels: ChannelConfig[];
}

export class PresetError extends Error {}

const num = (v: unknown, d: number) => (typeof v === 'number' && Number.isFinite(v) ? v : d);
const str = (v: unknown, d = '') => (typeof v === 'string' ? v : d);

/** Validate + clamp one channel exactly like ChannelConfig.__post_init__. */
export function parseChannel(raw: unknown): ChannelConfig {
  if (!raw || typeof raw !== 'object') throw new PresetError('channel must be an object');
  const r = raw as Record<string, unknown>;
  const kind = r.kind;
  if (kind !== 'binaural' && kind !== 'noise' && kind !== 'sample') throw new PresetError(`unknown channel kind: ${String(kind)}`);
  const variant = str(r.variant, 'pink') as NoiseVariant;
  if (kind === 'noise' && !NOISE_VARIANTS.includes(variant)) throw new PresetError(`unknown noise variant: ${variant}`);
  return {
    kind,
    name: str(r.name, kind).slice(0, 48),
    volume: clamp(num(r.volume, 0.5), 0, 1),
    pan: clamp(num(r.pan, 0), -1, 1),
    muted: r.muted === true,
    base_hz: clamp(num(r.base_hz, 200), BASE_FREQ_MIN_HZ, BASE_FREQ_MAX_HZ),
    beat_hz: clamp(num(r.beat_hz, 10), BEAT_FREQ_MIN_HZ, BEAT_FREQ_MAX_HZ),
    variant: NOISE_VARIANTS.includes(variant) ? variant : 'pink',
    path: str(r.path),
  };
}

export function parsePreset(raw: unknown): Preset {
  if (!raw || typeof raw !== 'object') throw new PresetError('preset must be an object');
  const r = raw as Record<string, unknown>;
  const name = str(r.name).trim();
  if (!name) throw new PresetError('preset needs a name');
  const bandName = str(r.band) as BandName;
  if (!BANDS.some((b) => b.name === bandName)) throw new PresetError(`unknown band: ${bandName}`);
  if (!Array.isArray(r.channels)) throw new PresetError('preset needs channels');
  if (r.channels.length > 16) throw new PresetError('too many channels');
  return {
    name: name.slice(0, 48), band: bandName, icon: str(r.icon, 'waves'), description: str(r.description).slice(0, 200),
    category: str(r.category), channels: r.channels.map(parseChannel),
  };
}

export const presetCategory = (p: Preset, user: boolean) => (user ? 'My Presets' : p.category || band(p.band).category);
export const binauralOf = (p: Preset) => p.channels.find((c) => c.kind === 'binaural');

export function describe(p: Preset): string {
  const b = binauralOf(p);
  return b ? `${band(p.band).label} · ${+b.beat_hz.toFixed(2)} Hz` : band(p.band).label;
}

export const clonePreset = (p: Preset): Preset => ({ ...p, channels: p.channels.map((c) => ({ ...c })) });

export function binauralChannel(over: Partial<ChannelConfig> = {}): ChannelConfig {
  return parseChannel({ kind: 'binaural', name: 'Binaural', volume: 0.45, base_hz: 200, beat_hz: 10, ...over });
}

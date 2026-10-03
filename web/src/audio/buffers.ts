// Decoded, loop-ready AudioBuffers, cached per (context sample rate, source) and shared.
import catalogJson from '../generated/catalog.json';
import { ASSET_PREFIX, type ChannelConfig, LOCAL_PREFIX } from '../domain/preset';
import { makeLoopable, makeNoise } from './dsp';
import { preferredAmbienceExt } from './platform';

export interface AmbienceSound {
  id: string; name: string; file: string; category: string; description: string;
  loop_xfade_s: number; default_volume: number; duration_s: number;
}
export const CATALOG: readonly AmbienceSound[] = catalogJson as AmbienceSound[];
export const findSound = (id: string) => CATALOG.find((s) => s.id === id);

/** Hook for user-uploaded sounds (IndexedDB), injected by the app layer. */
export type LocalSoundLoader = (id: string) => Promise<Blob | undefined>;
let localLoader: LocalSoundLoader = async () => undefined;
export const setLocalSoundLoader = (fn: LocalSoundLoader) => { localLoader = fn; };

const NOISE_SECONDS = 20;
const cache = new Map<string, Promise<AudioBuffer>>();
const base = () => (import.meta.env?.BASE_URL ?? '/');

function toBuffer(ctx: BaseAudioContext, chans: Float32Array[]): AudioBuffer {
  const len = chans[0]!.length;
  const buf = ctx.createBuffer(2, len, ctx.sampleRate);
  buf.copyToChannel(chans[0]! as Float32Array<ArrayBuffer>, 0);
  buf.copyToChannel((chans[1] ?? chans[0]!) as Float32Array<ArrayBuffer>, 1);
  return buf;
}

async function decode(ctx: BaseAudioContext, data: ArrayBuffer, xfadeS: number): Promise<AudioBuffer> {
  const decoded = await ctx.decodeAudioData(data);
  const chans = [decoded.getChannelData(0), decoded.getChannelData(decoded.numberOfChannels > 1 ? 1 : 0)];
  return toBuffer(ctx, makeLoopable(chans, Math.round(xfadeS * decoded.sampleRate)));
}

async function fetchAsset(ctx: BaseAudioContext, s: AmbienceSound): Promise<AudioBuffer> {
  const exts = preferredAmbienceExt() === 'ogg' ? ['ogg', 'm4a'] : ['m4a', 'ogg'];
  let lastErr: unknown;
  for (const ext of exts) {          // canPlayType can lie about decodeAudioData: fall back
    try {
      const res = await fetch(`${base()}ambience/${s.file.replace(/\.ogg$/, '.' + ext)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await decode(ctx, await res.arrayBuffer(), s.loop_xfade_s);
    } catch (e) { lastErr = e; }
  }
  throw new Error(`could not load ${s.name}: ${String(lastErr)}`);
}

export function bufferFor(ctx: BaseAudioContext, cfg: ChannelConfig): Promise<AudioBuffer> {
  const key = cfg.kind === 'noise' ? `noise:${cfg.variant}` : cfg.path;
  const ck = `${ctx.sampleRate}|${key}`;
  let p = cache.get(ck);
  if (!p) {
    if (cfg.kind === 'noise') {
      const sr = ctx.sampleRate;
      p = Promise.resolve(toBuffer(ctx, makeNoise(cfg.variant, NOISE_SECONDS * sr, sr, 7 + cfg.variant.length)));
    } else if (cfg.path.startsWith(ASSET_PREFIX)) {
      const s = findSound(cfg.path.slice(ASSET_PREFIX.length));
      p = s ? fetchAsset(ctx, s) : Promise.reject(new Error(`unknown sound ${cfg.path}`));
    } else if (cfg.path.startsWith(LOCAL_PREFIX)) {
      p = localLoader(cfg.path.slice(LOCAL_PREFIX.length)).then(async (blob) => {
        if (!blob) throw new Error('this sound is no longer stored on this device');
        return decode(ctx, await blob.arrayBuffer(), 1.0);
      });
    } else {
      p = Promise.reject(new Error(`unsupported sound source: ${cfg.path || cfg.kind}`));
    }
    p.catch(() => cache.delete(ck));   // allow retry after a failure
    cache.set(ck, p);
  }
  return p;
}

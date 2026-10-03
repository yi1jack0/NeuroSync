// Pure DSP helpers (no Web Audio): tested against the Python engine via golden.json.
import { FADE_FLOOR_DB, MIN_FADE_OUT_S } from '../domain/limits';

/** Equal-power crossfade of the tail into the head (== engine.sources.make_loopable). */
export function makeLoopable(channels: Float32Array[], xfade: number): Float32Array[] {
  const n = channels[0]?.length ?? 0;
  const xf = Math.min(Math.floor(xfade), Math.floor(n / 2));
  if (xf <= 0) return channels;
  return channels.map((ch) => {
    const out = ch.slice(0, n - xf);
    for (let i = 0; i < xf; i++) {
      const t = (i + 0.5) / xf;
      out[i] = ch[i]! * Math.sqrt(t) + ch[n - xf + i]! * Math.sqrt(1 - t);
    }
    return out;
  });
}

/** Gain of the logarithmic fade at fraction t (0..1) (== engine.fade.LogFade). */
export function logFadeGain(t: number): number {
  const u = Math.min(Math.max(t, 0), 1);
  return 10 ** ((FADE_FLOOR_DB * u) / 20) * Math.min(Math.max((1 - u) / 0.01, 0), 1);
}

export const effectiveFadeS = (requested: number) => Math.max(requested, MIN_FADE_OUT_S);

/** Spectrally tilted noise via cheap filters, then made loopable (wrap is click-free).
 *  pink: Paul Kellet's refined filter; brown: leaky integrator. Peak-normalised to 0.7. */
export function makeNoise(variant: 'white' | 'pink' | 'brown', frames: number, xfade: number, seed = 1): Float32Array[] {
  let s = seed >>> 0 || 1;
  const rand = () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296 * 2 - 1; };
  const chans: Float32Array[] = [];
  for (let c = 0; c < 2; c++) {
    const out = new Float32Array(frames + xfade);
    let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, last = 0;
    for (let i = 0; i < out.length; i++) {
      const w = rand();
      let v: number;
      if (variant === 'white') v = w;
      else if (variant === 'pink') {
        b0 = 0.99886 * b0 + w * 0.0555179; b1 = 0.99332 * b1 + w * 0.0750759; b2 = 0.969 * b2 + w * 0.153852;
        b3 = 0.8665 * b3 + w * 0.3104856; b4 = 0.55 * b4 + w * 0.5329522; b5 = -0.7616 * b5 - w * 0.016898;
        v = b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362; b6 = w * 0.115926;
      } else { last = (last + 0.02 * w) / 1.02; v = last * 3.5; }
      out[i] = v;
    }
    chans.push(out);
  }
  const looped = makeLoopable(chans, xfade);   // normalise *after* the crossfade (it can add up to +3 dB)
  let peak = 1e-9;
  for (const ch of looped) for (const v of ch) peak = Math.max(peak, Math.abs(v));
  for (const ch of looped) for (let i = 0; i < ch.length; i++) ch[i] = (ch[i]! / peak) * 0.7;
  return looped;
}

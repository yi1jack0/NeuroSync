// Test-only page (not in the production build): renders the real graph offline so
// Playwright can measure what users would hear.
import { Bus, outputChain, scheduleFadeOut } from '../src/audio/graph';
import { parsePreset } from '../src/domain/preset';

const SR = 48000;

function fftMag(x: Float32Array): Float64Array {
  const n = 1 << Math.floor(Math.log2(x.length));
  const re = new Float64Array(n), im = new Float64Array(n);
  for (let i = 0; i < n; i++) re[i] = x[i]! * (0.5 - 0.5 * Math.cos((2 * Math.PI * i) / n));
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j]!, re[i]!]; [im[i], im[j]] = [im[j]!, im[i]!]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const a = (-2 * Math.PI) / len;
    for (let i = 0; i < n; i += len)
      for (let k = 0; k < len / 2; k++) {
        const wr = Math.cos(a * k), wi = Math.sin(a * k);
        const ur = re[i + k]!, ui = im[i + k]!;
        const vr = re[i + k + len / 2]! * wr - im[i + k + len / 2]! * wi;
        const vi = re[i + k + len / 2]! * wi + im[i + k + len / 2]! * wr;
        re[i + k] = ur + vr; im[i + k] = ui + vi; re[i + k + len / 2] = ur - vr; im[i + k + len / 2] = ui - vi;
      }
  }
  const mag = new Float64Array(n / 2);
  for (let i = 0; i < n / 2; i++) mag[i] = Math.hypot(re[i]!, im[i]!);
  return mag;
}
const dominantHz = (x: Float32Array) => {
  const m = fftMag(x); let best = 1;
  for (let i = 2; i < m.length; i++) if (m[i]! > m[best]!) best = i;
  return (best * SR) / (2 * m.length);
};
const peak = (x: Float32Array) => x.reduce((a, v) => Math.max(a, Math.abs(v)), 0);
const rms = (x: Float32Array) => Math.sqrt(x.reduce((a, v) => a + v * v, 0) / x.length);

async function renderPreset(raw: unknown, seconds: number, master: number) {
  const ctx = new OfflineAudioContext(2, Math.round(seconds * SR), SR);
  const chain = outputChain(ctx, master);
  chain.limiter.connect(ctx.destination);
  const bus = await Bus.build(ctx, parsePreset(raw));
  bus.gain.connect(chain.master);
  bus.start(0);
  const out = await ctx.startRendering();
  const L = out.getChannelData(0).slice(SR / 2), R = out.getChannelData(1).slice(SR / 2);
  return { peak: Math.max(peak(L), peak(R)), rmsL: rms(L), rmsR: rms(R), domL: dominantHz(L), domR: dominantHz(R) };
}

/** Constant tone through the chain, fade scheduled at `at`; returns 10 ms RMS envelope. */
async function renderFade(requestedS: number, at: number, seconds: number) {
  const ctx = new OfflineAudioContext(1, Math.round(seconds * SR), SR);
  const chain = outputChain(ctx, 0.85);
  chain.limiter.connect(ctx.destination);
  const osc = ctx.createOscillator(); osc.frequency.value = 200;   // 2 whole cycles per 10 ms window
  const g = ctx.createGain(); g.gain.value = 0.5;
  osc.connect(g).connect(chain.master); osc.start(0);
  const end = scheduleFadeOut(chain.fade.gain, at, requestedS);
  const out = (await ctx.startRendering()).getChannelData(0);
  const step = SR / 100, env: number[] = [];
  for (let i = 0; i + step <= out.length; i += step) env.push(rms(out.subarray(i, i + step)));
  return { end, env };
}

Object.assign(window, { harness: { renderPreset, renderFade } });
document.title = 'harness ready';

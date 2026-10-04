// Test-only page (not in the production build): renders the real graph offline so
// Playwright can measure what users would hear.
import { Bus, outputChain, rampDuck, scheduleFadeOut } from '../src/audio/graph';
import { parsePreset } from '../src/domain/preset';
import { Engine } from '../src/audio/engine';

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

/** Real-time engine: a short sleep timer must end playback by itself (audio-clock scheduled). */
async function runTimer(minutes: number, fadeMinutes: number) {
  const engine = new Engine('direct');
  await engine.load(parsePreset({ name: 't', band: 'DELTA', channels: [{ kind: 'binaural', name: 'b', base_hz: 150, beat_hz: 2, volume: 0.3 }] }));
  engine.setTimer(minutes, fadeMinutes);
  const t0 = performance.now();
  await engine.play();
  const states: string[] = [engine.state];
  engine.subscribe(() => states.push(engine.state));
  while (engine.state !== 'stopped' && performance.now() - t0 < 30000) {
    engine.tick();
    await new Promise((r) => setTimeout(r, 50));
  }
  return { elapsed: (performance.now() - t0) / 1000, states, ctxState: engine.context?.state };
}

/** Pause freezes the countdown (the context clock is suspended). */
async function pauseFreezesTimer() {
  const engine = new Engine('direct');
  await engine.load(parsePreset({ name: 't', band: 'ALPHA', channels: [{ kind: 'binaural', name: 'b', base_hz: 200, beat_hz: 10, volume: 0.3 }] }));
  engine.setTimer(1, 0);
  await engine.play();
  await new Promise((r) => setTimeout(r, 600));
  await engine.pause();
  const a = engine.remaining!;
  await new Promise((r) => setTimeout(r, 1200));
  const b = engine.remaining!;
  await engine.play();
  await new Promise((r) => setTimeout(r, 600));
  const c = engine.remaining!;
  await engine.stop();
  return { a, b, c, state: engine.state };
}

/** Smoothness report: 20 ms RMS envelopes of each ear and of the mono sum (what a phone
 *  speaker plays), plus the largest sample-to-sample jump (clicks). */
async function analyze(raw: unknown, seconds: number, master: number, speaker = false) {
  const ctx = new OfflineAudioContext(2, Math.round(seconds * SR), SR);
  const chain = outputChain(ctx, master);
  chain.limiter.connect(ctx.destination);
  const bus = await Bus.build(ctx, parsePreset(raw), speaker);
  bus.gain.connect(chain.master);
  bus.start(0);
  const out = await ctx.startRendering();
  const L = out.getChannelData(0), R = out.getChannelData(1);
  const M = L.map((v, i) => (v + R[i]!) / 2);
  const step = SR / 50;
  const env = (x: Float32Array) => { const e: number[] = []; for (let i = SR; i + step <= x.length; i += step) e.push(rms(x.subarray(i, i + step))); return e; };
  let jump = 0;
  for (let i = SR + 1; i < L.length; i++) jump = Math.max(jump, Math.abs(L[i]! - L[i - 1]!), Math.abs(R[i]! - R[i - 1]!));
  return { envL: env(L), envR: env(R), envM: env(M), jump };
}

/** Start fade-in (0 -> 1 over `inS`), then a pause fade begun mid-way through a resume:
 *  returns the 10 ms RMS envelope and the largest sample-to-sample jump. */
async function renderDuck(inS: number, pauseAt: number, pauseS: number, seconds: number) {
  const ctx = new OfflineAudioContext(1, Math.round(seconds * SR), SR);
  const chain = outputChain(ctx, 0.85);
  chain.limiter.connect(ctx.destination);
  const osc = ctx.createOscillator(); osc.frequency.value = 200;
  const g = ctx.createGain(); g.gain.value = 0.5;
  osc.connect(g).connect(chain.master); osc.start(0);
  rampDuck(chain, 1, 0, inS, 0);
  // the turnaround must start from the level the ramp has reached at pauseAt
  const reached = Math.min(pauseAt / inS, 1);
  rampDuck(chain, 0, pauseAt, pauseS, reached);
  const out = (await ctx.startRendering()).getChannelData(0);
  const step = SR / 100, env: number[] = [];
  for (let i = 0; i + step <= out.length; i += step) env.push(rms(out.subarray(i, i + step)));
  let jump = 0;
  for (let i = 1; i < out.length; i++) jump = Math.max(jump, Math.abs(out[i]! - out[i - 1]!));
  return { env, jump };
}

Object.assign(window, { harness: { analyze, renderDuck, renderPreset, renderFade, runTimer, pauseFreezesTimer } });
document.title = 'harness ready';

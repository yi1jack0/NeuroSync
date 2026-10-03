// Web Audio graph construction. Works on AudioContext and OfflineAudioContext (tests).
//
//   channel nodes -> bus gain -> master (<= 0.85) -> duck (pause) -> fade (stop/timer) -> limiter -> out
import { type ChannelConfig, type Preset } from '../domain/preset';
import { MASTER_GAIN_MAX, clamp } from '../domain/limits';
import { bufferFor } from './buffers';
import { effectiveFadeS } from './dsp';

const SMOOTH = 0.02;          // s, time-constant for live parameter changes (click-free)
const FADE_FLOOR = 0.001;     // -60 dB, matches the desktop LogFade floor

export interface ChannelNode {
  output: AudioNode;
  start(when: number): void;
  stop(when: number): void;
  apply(cfg: ChannelConfig, when: number): void;
}

function binauralNode(ctx: BaseAudioContext, cfg: ChannelConfig): ChannelNode {
  const left = ctx.createOscillator();
  const right = ctx.createOscillator();
  const merger = ctx.createChannelMerger(2);
  const gain = ctx.createGain();
  left.connect(merger, 0, 0);            // each ear gets exactly one pure tone
  right.connect(merger, 0, 1);
  merger.connect(gain);
  left.frequency.value = cfg.base_hz;
  right.frequency.value = cfg.base_hz + cfg.beat_hz;
  gain.gain.value = cfg.muted ? 0 : cfg.volume;
  return {
    output: gain,
    start: (t) => { left.start(t); right.start(t); },
    stop: (t) => { try { left.stop(t); right.stop(t); } catch { /* not started */ } },
    apply: (c, t) => {
      left.frequency.setTargetAtTime(c.base_hz, t, SMOOTH);
      right.frequency.setTargetAtTime(c.base_hz + c.beat_hz, t, SMOOTH);
      gain.gain.setTargetAtTime(c.muted ? 0 : c.volume, t, SMOOTH);
    },
  };
}

function bufferNode(ctx: BaseAudioContext, cfg: ChannelConfig, buffer: AudioBuffer): ChannelNode {
  const src = ctx.createBufferSource();
  src.buffer = buffer;
  src.loop = true;                       // sample-accurate; buffer already loop-crossfaded
  const gain = ctx.createGain();
  const pan = ctx.createStereoPanner();
  src.connect(gain).connect(pan);
  gain.gain.value = cfg.muted ? 0 : cfg.volume;
  pan.pan.value = cfg.pan;
  return {
    output: pan,
    start: (t) => src.start(t, Math.random() * buffer.duration * 0.5),   // varied loop start point
    stop: (t) => { try { src.stop(t); } catch { /* not started */ } },
    apply: (c, t) => {
      gain.gain.setTargetAtTime(c.muted ? 0 : c.volume, t, SMOOTH);
      pan.pan.setTargetAtTime(c.pan, t, SMOOTH);
    },
  };
}

export async function channelNode(ctx: BaseAudioContext, cfg: ChannelConfig): Promise<ChannelNode> {
  return cfg.kind === 'binaural' ? binauralNode(ctx, cfg) : bufferNode(ctx, cfg, await bufferFor(ctx, cfg));
}

/** All channels of one preset, summed into one gain (so presets can be crossfaded). */
export class Bus {
  readonly gain: GainNode;
  private nodes: ChannelNode[] = [];
  private started = false;
  private constructor(private ctx: BaseAudioContext) { this.gain = ctx.createGain(); }

  static async build(ctx: BaseAudioContext, preset: Preset): Promise<Bus> {
    const bus = new Bus(ctx);
    const nodes = await Promise.all(preset.channels.map((c) => channelNode(ctx, c)));
    nodes.forEach((n) => n.output.connect(bus.gain));
    bus.nodes = nodes;
    return bus;
  }

  start(when: number) { if (!this.started) { this.nodes.forEach((n) => n.start(when)); this.started = true; } }
  stop(when: number) { this.nodes.forEach((n) => n.stop(when)); }
  apply(index: number, cfg: ChannelConfig) { this.nodes[index]?.apply(cfg, this.ctx.currentTime); }

  async add(cfg: ChannelConfig) {
    const n = await channelNode(this.ctx, cfg);
    n.output.connect(this.gain);
    if (this.started) n.start(this.ctx.currentTime);
    this.nodes.push(n);
  }

  remove(index: number) {
    const n = this.nodes[index];
    if (!n) return;
    const t = this.ctx.currentTime;
    n.apply({ ...dummyMute }, t);
    n.stop(t + 0.15);
    setTimeout(() => n.output.disconnect(), 300);
    this.nodes.splice(index, 1);
  }

  disconnect() { this.gain.disconnect(); }
}
const dummyMute = { kind: 'noise', name: '', volume: 0, pan: 0, muted: true, base_hz: 200, beat_hz: 10, variant: 'pink', path: '' } as ChannelConfig;

export interface OutputChain { master: GainNode; duck: GainNode; fade: GainNode; limiter: AudioNode }

/** Transparent below 0.7, then a smooth knee that can never exceed 0.85 (inputs beyond the
 *  curve's range are clamped to its end points by the WaveShaper itself). */
export function ceilingCurve(points = 4097, ceiling = MASTER_GAIN_MAX, knee = 0.7): Float32Array<ArrayBuffer> {
  const curve = new Float32Array(points);
  const room = ceiling - knee;
  for (let i = 0; i < points; i++) {
    const x = (i / (points - 1)) * 2 - 1;
    const a = Math.abs(x);
    curve[i] = Math.sign(x) * (a <= knee ? a : knee + room * Math.tanh((a - knee) / room));
  }
  return curve;
}

export function outputChain(ctx: BaseAudioContext, masterGain: number): OutputChain {
  const master = ctx.createGain();
  const duck = ctx.createGain();
  const fade = ctx.createGain();
  // Safety net when many tracks sum: a compressor tames sustained overs, then a
  // WaveShaper ceiling guarantees no sample ever exceeds 0.85 (compressors overshoot).
  const comp = ctx.createDynamicsCompressor();
  comp.threshold.value = -4; comp.knee.value = 3; comp.ratio.value = 12;
  comp.attack.value = 0.003; comp.release.value = 0.15;
  const ceiling = ctx.createWaveShaper();
  ceiling.curve = ceilingCurve();
  ceiling.oversample = 'none';   // oversampling filters ring past the curve: keep the bound exact
  master.gain.value = clamp(masterGain, 0, MASTER_GAIN_MAX);
  master.connect(duck).connect(fade).connect(comp).connect(ceiling);
  return { master, duck, fade, limiter: ceiling };
}

export function setMaster(chain: OutputChain, value: number, when: number) {
  chain.master.gain.setTargetAtTime(clamp(value, 0, MASTER_GAIN_MAX), when, SMOOTH);   // never above 0.85
}

/** Logarithmic (linear-in-dB) fade to silence, never shorter than 3 s. Returns the end time. */
export function scheduleFadeOut(param: AudioParam, start: number, requestedS: number): number {
  const end = start + effectiveFadeS(requestedS);
  param.cancelScheduledValues(start);
  param.setValueAtTime(Math.max(param.value, FADE_FLOOR), start);
  param.exponentialRampToValueAtTime(FADE_FLOOR, end);
  param.setValueAtTime(0, end);
  return end;
}

/** Cancel any scheduled fade and restore full level smoothly. */
export function cancelFade(param: AudioParam, now: number) {
  param.cancelScheduledValues(now);
  param.setValueAtTime(param.value, now);
  param.setTargetAtTime(1, now, 0.05);
}

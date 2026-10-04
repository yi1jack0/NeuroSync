// Web Audio graph construction. Works on AudioContext and OfflineAudioContext (tests).
//
//   channel nodes -> bus gain -> master (<= 0.85) -> duck (start/pause/resume) -> fade (stop/timer) -> limiter -> out
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
  /** Speaker-safe rendering (binaural only): see binauralNode. */
  setSpeaker?(on: boolean, when: number): void;
}

const SPEAKER_DEPTH = 0.3;     // gentle sine pulse (about 3 dB) instead of a hard on/off beat
const MODE_SWITCH_TC = 0.15;   // s, time-constant of the headphones <-> speaker crossfade

/**
 * Headphones: each ear gets exactly one pure tone (left = base, right = base + beat); the
 * brain hears the beat. Through speakers the two tones meet in the air (or in a phone's mono
 * speaker) and cancel each other at the beat rate: the sound drops out 2-10 times a second.
 * Speaker mode therefore plays one centred tone with a soft, shallow pulse at the beat rate.
 * Both paths run all the time and are crossfaded, so switching is click-free.
 */
function binauralNode(ctx: BaseAudioContext, cfg: ChannelConfig, speaker: boolean): ChannelNode {
  const left = ctx.createOscillator();
  const right = ctx.createOscillator();
  const merger = ctx.createChannelMerger(2);
  const phones = ctx.createGain();
  left.connect(merger, 0, 0);
  right.connect(merger, 0, 1);
  merger.connect(phones);
  left.frequency.value = cfg.base_hz;
  right.frequency.value = cfg.base_hz + cfg.beat_hz;

  const tone = ctx.createOscillator();     // centre pitch, same in both ears
  const lfo = ctx.createOscillator();      // beat-rate pulse
  const pulse = ctx.createGain();          // gain = 1 - d/2 + d/2 * sin(2 pi beat t)
  const depth = ctx.createGain();
  const spk = ctx.createGain();
  tone.frequency.value = cfg.base_hz + cfg.beat_hz / 2;
  lfo.frequency.value = cfg.beat_hz;
  pulse.gain.value = 1 - SPEAKER_DEPTH / 2;
  depth.gain.value = SPEAKER_DEPTH / 2;
  lfo.connect(depth).connect(pulse.gain);
  tone.connect(pulse).connect(spk);        // mono: up-mixed to both channels

  const gain = ctx.createGain();
  phones.connect(gain);
  spk.connect(gain);
  phones.gain.value = speaker ? 0 : 1;
  spk.gain.value = speaker ? 1 : 0;
  gain.gain.value = cfg.muted ? 0 : cfg.volume;
  const oscs = [left, right, tone, lfo];
  return {
    output: gain,
    start: (t) => oscs.forEach((o) => o.start(t)),
    stop: (t) => { try { oscs.forEach((o) => o.stop(t)); } catch { /* not started */ } },
    apply: (c, t) => {
      left.frequency.setTargetAtTime(c.base_hz, t, SMOOTH);
      right.frequency.setTargetAtTime(c.base_hz + c.beat_hz, t, SMOOTH);
      tone.frequency.setTargetAtTime(c.base_hz + c.beat_hz / 2, t, SMOOTH);
      lfo.frequency.setTargetAtTime(c.beat_hz, t, SMOOTH);
      gain.gain.setTargetAtTime(c.muted ? 0 : c.volume, t, SMOOTH);
    },
    setSpeaker: (on, t) => {
      phones.gain.setTargetAtTime(on ? 0 : 1, t, MODE_SWITCH_TC);
      spk.gain.setTargetAtTime(on ? 1 : 0, t, MODE_SWITCH_TC);
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

export async function channelNode(ctx: BaseAudioContext, cfg: ChannelConfig, speaker = false): Promise<ChannelNode> {
  return cfg.kind === 'binaural' ? binauralNode(ctx, cfg, speaker) : bufferNode(ctx, cfg, await bufferFor(ctx, cfg));
}

/** All channels of one preset, summed into one gain (so presets can be crossfaded). */
export class Bus {
  readonly gain: GainNode;
  private nodes: ChannelNode[] = [];
  private started = false;
  private constructor(private ctx: BaseAudioContext, private speaker: boolean) { this.gain = ctx.createGain(); }

  static async build(ctx: BaseAudioContext, preset: Preset, speaker = false): Promise<Bus> {
    const bus = new Bus(ctx, speaker);
    const nodes = await Promise.all(preset.channels.map((c) => channelNode(ctx, c, speaker)));
    nodes.forEach((n) => n.output.connect(bus.gain));
    bus.nodes = nodes;
    return bus;
  }

  start(when: number) { if (!this.started) { this.nodes.forEach((n) => n.start(when)); this.started = true; } }
  stop(when: number) { this.nodes.forEach((n) => n.stop(when)); }
  apply(index: number, cfg: ChannelConfig) { this.nodes[index]?.apply(cfg, this.ctx.currentTime); }

  setSpeaker(on: boolean) {
    this.speaker = on;
    this.nodes.forEach((n) => n.setSpeaker?.(on, this.ctx.currentTime));
  }

  async add(cfg: ChannelConfig) {
    const n = await channelNode(this.ctx, cfg, this.speaker);
    n.output.connect(this.gain);
    if (this.started) n.start(this.ctx.currentTime);
    this.nodes.push(n);
  }

  remove(index: number) {
    const n = this.nodes[index];
    if (!n) return;
    const t = this.ctx.currentTime;
    n.apply({ ...dummyMute }, t);          // SMOOTH time-constant: silent well before the stop
    n.stop(t + 0.3);
    setTimeout(() => n.output.disconnect(), 450);
    this.nodes.splice(index, 1);
  }

  disconnect() { this.gain.disconnect(); }
}
const dummyMute = { kind: 'noise', name: '', volume: 0, pan: 0, muted: true, base_hz: 200, beat_hz: 10, variant: 'pink', path: '' } as ChannelConfig;

/** duck is two gain stages driven by the same linear ramp, so the level follows x^2: a soft
 *  start for fade-ins, a soft landing for fade-outs, and still interruptible at any moment. */
export interface OutputChain { master: GainNode; duck: [GainNode, GainNode]; fade: GainNode; limiter: AudioNode }

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
  const duck: [GainNode, GainNode] = [ctx.createGain(), ctx.createGain()];
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
  master.connect(duck[0]).connect(duck[1]).connect(fade).connect(comp).connect(ceiling);
  return { master, duck, fade, limiter: ceiling };
}

/** Smoothly move the duck to `target` (0 or 1) over `seconds`, starting from wherever it is now
 *  (a pause during a fade-in turns around without a jump). */
export function rampDuck(chain: OutputChain, target: number, when: number, seconds: number, from?: number) {
  for (const g of chain.duck) {
    const p = g.gain;
    p.cancelScheduledValues(when);
    p.setValueAtTime(from ?? p.value, when);
    p.linearRampToValueAtTime(target, when + seconds);
  }
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

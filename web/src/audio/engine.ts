// Realtime controller: owns the AudioContext, the current Bus and the session lifecycle.
// Timer + fades are scheduled on the *audio clock*, so they complete even when the
// browser throttles timers in a background tab. Pause suspends the context, which also
// freezes the clock: the remaining time pauses with it for free.
import { type ChannelConfig, type Preset } from '../domain/preset';
import { Bus, cancelFade, outputChain, type OutputChain, scheduleFadeOut, setMaster } from './graph';
import { declarePlaybackSession, type OutputMode, preferredOutputMode } from './platform';

export type EngineState = 'idle' | 'loading' | 'playing' | 'paused' | 'fading' | 'stopped';

const CROSSFADE_S = 0.35;
const PAUSE_RAMP_S = 0.12;

type Listener = () => void;
type SinkCapable = { setSinkId?: (id: string) => Promise<void> };

export class Engine {
  state: EngineState = 'idle';
  error = '';
  interrupted = false;            // the browser/OS paused us (phone call, lock screen ...)
  readonly mode: OutputMode;

  private ctx: AudioContext | null = null;
  private chain: OutputChain | null = null;
  private bus: Bus | null = null;
  private preset: Preset | null = null;
  private master = 0.5;
  private timer: { seconds: number; fadeS: number } | null = null;
  private endAt: number | null = null;           // ctx time when audio reaches silence
  private remainingAtPause: number | null = null;
  private element: HTMLAudioElement | null = null;
  private sinkId = '';
  private listeners = new Set<Listener>();
  private loadToken = 0;

  constructor(mode: OutputMode = preferredOutputMode()) { this.mode = mode; }

  subscribe(fn: Listener) { this.listeners.add(fn); return () => this.listeners.delete(fn); }
  private emit() { this.listeners.forEach((fn) => fn()); }
  private set(state: EngineState) { this.state = state; this.emit(); }

  get isPlaying() { return this.state === 'playing' || this.state === 'fading'; }
  get context() { return this.ctx; }

  /** Seconds until silence, or null when no timer is armed. Reads the audio clock. */
  get remaining(): number | null {
    if (!this.timer) return null;
    if (this.endAt === null || !this.ctx) return this.remainingAtPause ?? this.timer.seconds;
    return Math.max(0, this.endAt - this.ctx.currentTime);
  }

  // ------------------------------------------------------------------ context
  /** Must run inside a user gesture (autoplay policy). */
  private ensureContext(): AudioContext {
    if (this.ctx) return this.ctx;
    declarePlaybackSession();
    const ctx = new AudioContext({ latencyHint: 'playback', sampleRate: 48000 });
    const chain = outputChain(ctx, this.master);
    if (this.mode === 'element') {
      const dest = ctx.createMediaStreamDestination();
      chain.limiter.connect(dest);
      const el = new Audio();
      el.srcObject = dest.stream;
      el.setAttribute('playsinline', '');
      this.element = el;
    } else {
      chain.limiter.connect(ctx.destination);
    }
    ctx.addEventListener('statechange', () => {
      const s = ctx.state as string;
      if ((s === 'suspended' || s === 'interrupted') && this.isPlaying && !this.pausing) {
        this.interrupted = true;
        this.emit();
      }
    });
    this.ctx = ctx;
    this.chain = chain;
    if (this.sinkId) void this.setSink(this.sinkId);
    return ctx;
  }
  private pausing = false;

  // ------------------------------------------------------------------ preset
  /** Load (or switch to) a preset. While playing, the old one crossfades out. */
  async load(preset: Preset): Promise<void> {
    this.preset = preset;
    if (!this.ctx || !this.chain) return;           // built lazily on first play
    const token = ++this.loadToken;
    const ctx = this.ctx;
    let next: Bus;
    try {
      next = await Bus.build(ctx, preset);
    } catch (e) {
      this.error = String(e instanceof Error ? e.message : e);
      this.emit();
      return;
    }
    if (token !== this.loadToken) { next.disconnect(); return; }   // superseded by a newer load
    const old = this.bus;
    const t = ctx.currentTime;
    next.gain.connect(this.chain.master);
    if (old && this.isPlaying) {
      next.gain.gain.setValueAtTime(0, t);
      next.gain.gain.linearRampToValueAtTime(1, t + CROSSFADE_S);
      old.gain.gain.setValueAtTime(old.gain.gain.value, t);
      old.gain.gain.linearRampToValueAtTime(0, t + CROSSFADE_S);
      old.stop(t + CROSSFADE_S + 0.05);
      setTimeout(() => old.disconnect(), (CROSSFADE_S + 0.2) * 1000);
      next.start(t);
    } else {
      old?.stop(t);
      old?.disconnect();
      if (this.isPlaying) next.start(t);
    }
    this.bus = next;
  }

  apply(index: number, cfg: ChannelConfig) { this.bus?.apply(index, cfg); }
  async addChannel(cfg: ChannelConfig) { await this.bus?.add(cfg); }
  removeChannel(index: number) { this.bus?.remove(index); }

  setMaster(value: number) {
    this.master = value;
    if (this.ctx && this.chain) setMaster(this.chain, value, this.ctx.currentTime);
  }

  async setSink(id: string): Promise<boolean> {
    this.sinkId = id;
    try {
      const target = (this.mode === 'element' ? this.element : this.ctx) as SinkCapable | null;
      if (target?.setSinkId) { await target.setSinkId(id); return true; }
    } catch { /* device gone or not allowed */ }
    return false;
  }

  // ------------------------------------------------------------------ transport
  async play(): Promise<void> {
    if (!this.preset) return;
    const ctx = this.ensureContext();
    this.interrupted = false;
    this.error = '';
    if (this.state === 'stopped' || !this.bus) {
      this.set('loading');
      this.endAt = null;
      this.remainingAtPause = null;
      this.chain!.fade.gain.cancelScheduledValues(0);
      this.chain!.fade.gain.value = 1;
      await ctx.resume();
      this.bus?.disconnect();
      this.bus = null;
      await this.load(this.preset);
      const bus = this.bus as Bus | null;          // set by load()
      if (!bus) { this.set('idle'); return; }
      bus.start(ctx.currentTime);
    } else {
      await ctx.resume();
    }
    if (this.element) await this.element.play().catch(() => undefined);
    const t = ctx.currentTime;
    this.chain!.duck.gain.cancelScheduledValues(t);
    this.chain!.duck.gain.setValueAtTime(this.chain!.duck.gain.value, t);
    this.chain!.duck.gain.linearRampToValueAtTime(1, t + PAUSE_RAMP_S);
    this.set('playing');
    this.armTimer();
  }

  async pause(): Promise<void> {
    if (!this.ctx || !this.chain || this.state !== 'playing') return;
    const t = this.ctx.currentTime;
    this.pausing = true;
    this.remainingAtPause = this.remaining;
    this.chain.duck.gain.setValueAtTime(this.chain.duck.gain.value, t);
    this.chain.duck.gain.linearRampToValueAtTime(0, t + PAUSE_RAMP_S);
    this.set('paused');
    await new Promise((r) => setTimeout(r, PAUSE_RAMP_S * 1000 + 30));
    if ((this.state as EngineState) === 'paused') await this.ctx.suspend();   // freezes the clock and saves CPU
    this.pausing = false;
  }

  toggle() { return this.isPlaying ? this.pause() : this.play(); }

  /** Stop with a logarithmic fade of at least 3 s. Never cuts abruptly. */
  async stop(fadeS = 3): Promise<void> {
    if (!this.ctx || !this.chain) return;
    if (this.state === 'paused') { this.finish(); return; }     // already silent
    if (this.state !== 'playing') return;
    this.endAt = scheduleFadeOut(this.chain.fade.gain, this.ctx.currentTime, fadeS);
    this.timer = this.timer ? { ...this.timer } : null;
    this.set('fading');
  }

  /** minutes = 0 disables. The timer's fade ends exactly when the countdown reaches 0. */
  setTimer(minutes: number, fadeMinutes: number) {
    this.timer = minutes > 0 ? { seconds: minutes * 60, fadeS: fadeMinutes * 60 } : null;
    this.remainingAtPause = null;
    if (this.state === 'playing') this.armTimer();
    else if (!this.timer) this.endAt = null;
    this.emit();
  }

  private armTimer() {
    if (!this.ctx || !this.chain || this.state !== 'playing') return;
    const now = this.ctx.currentTime;
    if (!this.timer) {
      if (this.endAt !== null) cancelFade(this.chain.fade.gain, now);
      this.endAt = null;
      return;
    }
    const remaining = this.remainingAtPause ?? (this.endAt !== null ? this.endAt - now : this.timer.seconds);
    this.remainingAtPause = null;
    const fade = Math.max(this.timer.fadeS, 3);
    const end = now + Math.max(remaining, 3);
    cancelFade(this.chain.fade.gain, now);
    this.endAt = scheduleFadeOut(this.chain.fade.gain, Math.max(now, end - fade), Math.min(fade, end - now));
  }

  /** Call regularly (each animation frame / timer tick): finishes a faded-out session. */
  tick(): void {
    if (!this.ctx || this.endAt === null) return;
    if ((this.state === 'playing' || this.state === 'fading') && this.ctx.currentTime >= this.endAt) this.finish();
  }

  private finish() {
    if (!this.ctx) return;
    this.bus?.stop(this.ctx.currentTime);
    this.bus?.disconnect();
    this.bus = null;
    this.endAt = null;
    this.remainingAtPause = null;
    this.element?.pause();
    void this.ctx.suspend();                  // release the audio device / CPU
    this.set('stopped');
  }
}

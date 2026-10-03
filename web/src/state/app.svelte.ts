// Application state + actions. UI components read this and call its methods; the audio
// engine is driven only from here.
import presetsJson from '../generated/presets.json';
import { Engine, type EngineState } from '../audio/engine';
import { CATALOG, findSound, setLocalSoundLoader } from '../audio/buffers';
import { canChooseOutput, listOutputDevices, type OutputDevice } from '../audio/platform';
import { type Band, band, bandForFrequency } from '../domain/bands';
import { gainToSlider, sliderToGain } from '../domain/limits';
import {
  ASSET_PREFIX, binauralChannel, binauralOf, type ChannelConfig, clonePreset, LOCAL_PREFIX, parseChannel,
  parsePreset, type Preset,
} from '../domain/preset';
import { downloadPreset, pickFile, readPresetFile } from '../lib/files';
import { idbDelete, idbGet, idbGetAll, idbPut } from '../lib/idb';
import { loadSettings, saveSettings, type Settings } from '../lib/settings';
import { decodePreset, presetTokenFromHash, shareable, shareUrl } from '../lib/share';

export const BUILTIN: readonly Preset[] = (presetsJson as unknown[]).map(parsePreset);
export type Tab = 'library' | 'now' | 'mixer';
export interface Toast { id: number; text: string; action?: { label: string; run: () => void } }

const NOISE_NAMES = { pink: 'Pink Noise', brown: 'Brown Noise', white: 'White Noise' } as const;
const MAX_UPLOAD = 25 * 1024 * 1024;

class AppState {
  readonly engine = new Engine();
  readonly canChooseOutput = canChooseOutput(this.engine.mode);

  status = $state<EngineState>('idle');
  remaining = $state<number | null>(null);
  interrupted = $state(false);
  settings = $state<Settings>(loadSettings());
  user = $state<Preset[]>([]);
  draft = $state<Preset>(clonePreset(BUILTIN[0]!));
  loadedName = $state('');
  dirty = $state(false);
  timerMinutes = $state(0);
  toasts = $state<Toast[]>([]);
  tab = $state<Tab>('now');
  libraryOpen = $state(false);
  mixerOpen = $state(false);
  dialog = $state<'none' | 'disclaimer' | 'shortcuts'>('none');
  pendingShare = $state<Preset | null>(null);
  offlineReady = $state(false);
  installPrompt = $state<(Event & { prompt: () => Promise<void> }) | null>(null);
  devices = $state<OutputDevice[]>([]);
  muted = $state(false);
  saving = $state(false);

  /** Accent follows the *current* beat, so dragging across bands recolours the app. */
  band: Band = $derived.by(() => {
    const b = binauralOf(this.draft);
    return b ? bandForFrequency(b.beat_hz) : band(this.draft.band);
  });
  isPlaying = $derived(this.status === 'playing' || this.status === 'fading');
  masterPct = $derived(this.muted ? 0 : gainToSlider(this.settings.masterVolume));

  private toastId = 0;

  // ------------------------------------------------------------------ boot
  async init() {
    this.engine.subscribe(() => this.syncEngine());
    this.engine.setMaster(this.settings.masterVolume);
    if (this.settings.sinkId) void this.engine.setSink(this.settings.sinkId);
    setLocalSoundLoader((id) => idbGet<Blob>('sounds', id));
    try { this.user = (await idbGetAll<unknown>('presets')).map(parsePreset).sort((a, b) => a.name.localeCompare(b.name)); }
    catch { /* IndexedDB unavailable (private mode): user presets disabled */ }
    const start = this.find(this.settings.lastPreset) ?? BUILTIN.find((p) => p.name === 'Alpha Focus') ?? BUILTIN[0]!;
    this.loadPreset(start);
    await this.checkShareLink();
    addEventListener('hashchange', () => void this.checkShareLink());
    if (!this.settings.disclaimerAccepted) this.dialog = 'disclaimer';
    setInterval(() => { this.engine.tick(); this.remaining = this.engine.remaining; }, 250);
    this.setupMediaSession();
    addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); this.installPrompt = e as never; });
  }

  private syncEngine() {
    const prev = this.status;
    this.status = this.engine.state;
    this.interrupted = this.engine.interrupted;
    this.remaining = this.engine.remaining;
    if (this.engine.error) { this.toast(this.engine.error); this.engine.error = ''; }
    if (prev === 'fading' && this.status === 'stopped' && this.timerMinutes > 0) this.toast('Session complete — audio stopped');
    if ('mediaSession' in navigator) {
      navigator.mediaSession.playbackState = this.isPlaying ? 'playing' : this.status === 'paused' ? 'paused' : 'none';
    }
  }

  private save() { saveSettings($state.snapshot(this.settings) as Settings); }
  find(name: string) { return [...BUILTIN, ...this.user].find((p) => p.name === name); }
  isBuiltin(name: string) { return BUILTIN.some((p) => p.name.toLowerCase() === name.toLowerCase()); }

  // ------------------------------------------------------------------ presets
  loadPreset(p: Preset) {
    this.draft = clonePreset(p);
    this.loadedName = p.name;
    this.dirty = false;
    this.saving = false;
    this.settings.lastPreset = p.name;
    this.save();
    void this.engine.load($state.snapshot(this.draft) as Preset);
    this.updateMediaMetadata();
    this.libraryOpen = false;
    if (this.tab === 'library') this.tab = 'now';
  }

  newSession() {
    this.loadPreset({ name: 'Untitled session', band: 'ALPHA', icon: 'waves', description: 'Custom session', category: '', channels: [binauralChannel()] });
    this.dirty = true;
    this.tab = 'mixer';
  }

  private pushDraft() {
    this.dirty = true;
    this.engine.setPreset($state.snapshot(this.draft) as Preset);
  }

  updateChannel(index: number, changes: Partial<ChannelConfig>) {
    const cur = this.draft.channels[index];
    if (!cur) return;
    const next = parseChannel({ ...$state.snapshot(cur), ...changes });   // re-applies safety clamps
    this.draft.channels[index] = next;
    this.engine.apply(index, next);
    this.pushDraft();
  }

  async addChannel(key: string) {
    let cfg: ChannelConfig;
    if (key === 'pink' || key === 'brown' || key === 'white') {
      cfg = parseChannel({ kind: 'noise', name: NOISE_NAMES[key], variant: key, volume: 0.3 });
    } else if (key === 'binaural') {
      cfg = binauralChannel();
    } else if (key.startsWith(ASSET_PREFIX)) {
      const s = findSound(key.slice(ASSET_PREFIX.length));
      if (!s) return;
      cfg = parseChannel({ kind: 'sample', name: s.name, path: key, volume: s.default_volume });
    } else {
      const file = await pickFile('audio/*');
      if (!file) return;
      if (file.size > MAX_UPLOAD) { this.toast('That file is larger than 25 MB'); return; }
      const id = crypto.randomUUID();
      try { await idbPut('sounds', id, file); } catch { this.toast('This browser cannot store sounds (private mode?)'); return; }
      cfg = parseChannel({ kind: 'sample', name: file.name.replace(/\.[^.]+$/, '').slice(0, 18), path: LOCAL_PREFIX + id, volume: 0.4 });
    }
    try { await this.engine.addChannel(cfg); }
    catch (e) { this.toast(`Couldn't open that sound: ${e instanceof Error ? e.message : e}`); return; }
    this.draft.channels.push(cfg);
    this.pushDraft();
    this.toast(`Added ${cfg.name}`);
  }

  removeChannel(index: number) {
    const ch = this.draft.channels[index];
    if (!ch) return;
    this.engine.removeChannel(index);
    this.draft.channels.splice(index, 1);
    this.pushDraft();
    this.toast(`Removed ${ch.name}`);
  }

  async savePreset(name: string) {
    name = name.trim().slice(0, 48);
    if (!name) return;
    if (this.isBuiltin(name)) { this.toast("Built-in presets can't be overwritten — choose another name"); return; }
    const b = binauralOf(this.draft);
    const preset = parsePreset({ ...$state.snapshot(this.draft), name, band: b ? bandForFrequency(b.beat_hz).name : this.draft.band, category: '' });
    const existed = this.user.some((p) => p.name.toLowerCase() === name.toLowerCase());
    try { await idbPut('presets', name.toLowerCase(), preset); } catch { this.toast('Saving needs browser storage (unavailable here)'); return; }
    this.user = [...this.user.filter((p) => p.name.toLowerCase() !== name.toLowerCase()), preset].sort((a, b2) => a.name.localeCompare(b2.name));
    this.draft.name = name;
    this.draft.band = preset.band;
    this.loadedName = name;
    this.dirty = false;
    this.saving = false;
    this.settings.lastPreset = name;
    this.save();
    this.toast(existed ? `Updated “${name}”` : `Saved “${name}” to My Presets`);
  }

  async deletePreset(p: Preset) {
    await idbDelete('presets', p.name.toLowerCase()).catch(() => undefined);
    this.user = this.user.filter((u) => u.name !== p.name);
    this.toast(`Deleted “${p.name}”`, { label: 'Undo', run: () => void this.restore(p) });
  }

  private async restore(p: Preset) {
    await idbPut('presets', p.name.toLowerCase(), p).catch(() => undefined);
    this.user = [...this.user, p].sort((a, b) => a.name.localeCompare(b.name));
    this.toast(`Restored “${p.name}”`);
  }

  exportPreset(p: Preset = this.draft) {
    const dropped = downloadPreset($state.snapshot(p) as Preset);
    this.toast(dropped ? `Exported (${dropped} device-only sound${dropped > 1 ? 's' : ''} left out)` : `Exported “${p.name}”`);
  }

  async importPreset() {
    const file = await pickFile('application/json,.json');
    if (!file) return;
    try {
      const p = await readPresetFile(file);
      if (this.isBuiltin(p.name)) p.name = `${p.name} (imported)`;
      await idbPut('presets', p.name.toLowerCase(), p);
      this.user = [...this.user.filter((u) => u.name !== p.name), p].sort((a, b) => a.name.localeCompare(b.name));
      this.toast(`Imported “${p.name}”`);
    } catch { this.toast("That file isn't a valid NeuroSync preset"); }
  }

  async sharePreset(p: Preset = this.draft) {
    const snap = $state.snapshot(p) as Preset;
    const { dropped } = shareable(snap);
    const url = await shareUrl(snap);
    try {
      if (navigator.share && matchMedia('(pointer: coarse)').matches) await navigator.share({ title: `NeuroSync — ${p.name}`, url });
      else { await navigator.clipboard.writeText(url); this.toast(dropped ? 'Link copied (device-only sounds left out)' : 'Link copied to clipboard'); }
    } catch { /* user cancelled share sheet */ }
  }

  private async checkShareLink() {
    const token = presetTokenFromHash();
    if (!token) return;
    try { this.pendingShare = await decodePreset(token); }
    catch { this.toast('That share link is damaged or incomplete'); }
    history.replaceState(null, '', location.pathname + location.search);
  }

  async acceptShare(add: boolean) {
    const p = this.pendingShare;
    this.pendingShare = null;
    if (!p) return;
    if (add) {
      if (this.isBuiltin(p.name)) p.name = `${p.name} (shared)`;
      await idbPut('presets', p.name.toLowerCase(), p).catch(() => undefined);
      this.user = [...this.user.filter((u) => u.name !== p.name), p].sort((a, b) => a.name.localeCompare(b.name));
      this.toast(`Added “${p.name}” to My Presets`);
    }
    this.loadPreset(p);
  }

  // ------------------------------------------------------------------ transport
  async toggle() {
    if (this.dialog === 'disclaimer') return;           // no sound before the safety notice
    await this.engine.toggle();
  }
  stop() { void this.engine.stop(); }
  resumeAfterInterruption() { void this.engine.play(); }

  setMasterPct(pct: number) {
    const g = sliderToGain(pct);
    if (pct > 0) { this.settings.masterVolume = g; this.muted = false; this.save(); }
    this.engine.setMaster(g);
  }
  nudgeMaster(delta: number) { this.setMasterPct(Math.max(0, Math.min(100, this.masterPct + delta))); }
  toggleMute() {
    this.muted = !this.muted;
    this.engine.setMaster(this.muted ? 0 : this.settings.masterVolume);
  }

  setTimer(minutes: number, fadeMinutes: number) {
    this.timerMinutes = minutes;
    if (fadeMinutes > 0) { this.settings.fadeMinutes = fadeMinutes; this.save(); }
    this.engine.setTimer(minutes, minutes ? Math.min(fadeMinutes, minutes) : 0);
  }

  // ------------------------------------------------------------------ devices / prefs
  async refreshDevices(askPermission: boolean) { this.devices = await listOutputDevices(askPermission); }
  async chooseDevice(id: string) {
    this.settings.sinkId = id;
    this.save();
    const ok = await this.engine.setSink(id);
    const name = this.devices.find((d) => d.id === id)?.label ?? 'System default';
    this.toast(ok || !id ? `Output: ${name}` : "Couldn't switch output device");
  }
  setPref<K extends 'highContrast' | 'reduceMotion'>(key: K, value: boolean) { this.settings[key] = value; this.save(); }
  acceptDisclaimer() { this.settings.disclaimerAccepted = true; this.save(); this.dialog = 'none'; }
  async install() { await this.installPrompt?.prompt(); this.installPrompt = null; }

  toast(text: string, action?: Toast['action']) {
    const id = ++this.toastId;
    this.toasts = [...this.toasts.slice(-2), { id, text, action }];
    setTimeout(() => { this.toasts = this.toasts.filter((t) => t.id !== id); }, action ? 6000 : 3200);
  }

  // ------------------------------------------------------------------ phone lock screen
  private setupMediaSession() {
    if (!('mediaSession' in navigator)) return;
    const ms = navigator.mediaSession;
    ms.setActionHandler('play', () => void this.engine.play());
    ms.setActionHandler('pause', () => void this.engine.pause());
    ms.setActionHandler('stop', () => this.stop());
  }

  private updateMediaMetadata() {
    if (!('mediaSession' in navigator) || typeof MediaMetadata === 'undefined') return;
    const b = binauralOf(this.draft);
    navigator.mediaSession.metadata = new MediaMetadata({
      title: this.draft.name, artist: 'NeuroSync',
      album: b ? `${band(this.draft.band).label} · ${b.beat_hz} Hz` : 'Ambience',
      artwork: [{ src: `${import.meta.env.BASE_URL}icons/icon-512.png`, sizes: '512x512', type: 'image/png' }],
    });
  }
}

export const app = new AppState();
export { CATALOG };

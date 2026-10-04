// Application state + actions. UI components read this and call its methods; the audio
// engine is driven only from here.
import presetsJson from '../generated/presets.json';
import { Engine, type EngineState } from '../audio/engine';
import { CATALOG, findSound, setLocalSoundLoader } from '../audio/buffers';
import { canChooseOutput, listOutputDevices, type OutputDevice } from '../audio/platform';
import { type Band, band, bandColorFor, bandForFrequency, ORB_SPEEDS } from '../domain/bands';
import { gainToSlider, sliderToGain } from '../domain/limits';
import {
  ASSET_PREFIX, binauralChannel, binauralOf, type ChannelConfig, clonePreset, LOCAL_PREFIX, parseChannel,
  parsePreset, type Preset,
} from '../domain/preset';
import { downloadPreset, pickFile, readPresetFile } from '../lib/files';
import { idbDelete, idbGet, idbGetAll, idbPut } from '../lib/idb';
import { loadSettings, saveSettings, type Settings } from '../lib/settings';
import { decodePreset, presetTokenFromHash, shareable, shareUrl } from '../lib/share';
import { i18n, type Lang, LANGS, t } from '../lib/i18n.svelte';
import { haptic } from '../lib/haptics';

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
  /** Band colour in the active design (Liquid uses a palette harmonised with Prussian blue). */
  bandColor = $derived(bandColorFor(this.band, this.settings.theme));
  colorOf = (b: Band) => bandColorFor(b, this.settings.theme);
  masterPct = $derived(this.muted ? 0 : gainToSlider(this.settings.masterVolume));

  private toastId = 0;

  // ------------------------------------------------------------------ boot
  /** Switch UI language (persisted). Stored preset names stay canonical. */
  setLang(lang: Lang, { announce = true, chosen = true } = {}) {
    i18n.lang = lang;
    this.settings.lang = lang;
    if (chosen) this.settings.langChosen = true;
    this.save();
    document.documentElement.lang = LANGS.find((l) => l.id === lang)!.html;
    this.updateMediaMetadata();
    if (announce) this.toast(t('ts.language'));
  }

  /** Speaker mode avoids the beat-rate dropouts you get when both ears' tones mix in the air. */
  speakerMode = $derived(this.settings.listening ? this.settings.listening === 'speaker'
    : typeof matchMedia !== 'undefined' && matchMedia('(pointer: coarse)').matches);
  setListening(mode: 'headphones' | 'speaker') {
    this.settings.listening = mode;
    this.save();
    this.engine.setSpeaker(mode === 'speaker');
    haptic(8);                                       // no toast: the switch and reminder line show the state
  }

  setTheme(theme: 'classic' | 'pour') { this.settings.theme = theme; this.settings.themeChosen = true; this.save(); }

  async init() {
    this.setLang(this.settings.lang || 'zh', { announce: false, chosen: false });
    // Preview link: ?theme=pour or ?theme=classic (saved, then removed from the address bar)
    const qs = new URLSearchParams(location.search).get('theme');
    if (qs === 'pour' || qs === 'classic') { this.setTheme(qs); history.replaceState(null, '', location.pathname + location.hash); }
    this.engine.subscribe(() => this.syncEngine());
    this.engine.setMaster(this.settings.masterVolume);
    this.engine.setSpeaker(this.speakerMode);
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
    if (this.engine.error) { this.toast(t('ts.audioError', { msg: this.engine.error })); this.engine.error = ''; }
    if (prev === 'fading' && this.status === 'stopped' && this.timerMinutes > 0) this.toast(t('ts.complete'));
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
    if (cur.kind === 'binaural' && bandForFrequency(cur.beat_hz) !== bandForFrequency(next.beat_hz)) haptic(12);   // crossed a band
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
      if (file.size > MAX_UPLOAD) { this.toast(t('ts.tooBig')); return; }
      const id = crypto.randomUUID();
      try { await idbPut('sounds', id, file); } catch { this.toast(t('ts.noSoundStorage')); return; }
      cfg = parseChannel({ kind: 'sample', name: file.name.replace(/\.[^.]+$/, '').slice(0, 18), path: LOCAL_PREFIX + id, volume: 0.4 });
    }
    try { await this.engine.addChannel(cfg); }
    catch (e) { this.toast(t('ts.soundFailed', { e: e instanceof Error ? e.message : String(e) })); return; }
    this.draft.channels.push(cfg);
    this.pushDraft();
    this.toast(t('ts.added', { name: i18n.name(cfg.name) }));
  }

  removeChannel(index: number) {
    const ch = this.draft.channels[index];
    if (!ch) return;
    this.engine.removeChannel(index);
    this.draft.channels.splice(index, 1);
    this.pushDraft();
    this.toast(t('ts.removed', { name: i18n.name(ch.name) }));
  }

  async savePreset(name: string) {
    name = name.trim().slice(0, 48);
    if (!name) return;
    if (this.isBuiltin(name)) { this.toast(t('ts.builtin')); return; }
    const b = binauralOf(this.draft);
    const preset = parsePreset({ ...$state.snapshot(this.draft), name, band: b ? bandForFrequency(b.beat_hz).name : this.draft.band, category: '' });
    const existed = this.user.some((p) => p.name.toLowerCase() === name.toLowerCase());
    try { await idbPut('presets', name.toLowerCase(), preset); } catch { this.toast(t('ts.noStorage')); return; }
    this.user = [...this.user.filter((p) => p.name.toLowerCase() !== name.toLowerCase()), preset].sort((a, b2) => a.name.localeCompare(b2.name));
    this.draft.name = name;
    this.draft.band = preset.band;
    this.loadedName = name;
    this.dirty = false;
    this.saving = false;
    this.settings.lastPreset = name;
    this.save();
    this.toast(existed ? t('ts.updated', { name }) : t('ts.saved', { name }));
  }

  async deletePreset(p: Preset) {
    await idbDelete('presets', p.name.toLowerCase()).catch(() => undefined);
    this.user = this.user.filter((u) => u.name !== p.name);
    this.toast(t('ts.deleted', { name: p.name }), { label: t('ts.undo'), run: () => void this.restore(p) });
  }

  private async restore(p: Preset) {
    await idbPut('presets', p.name.toLowerCase(), p).catch(() => undefined);
    this.user = [...this.user, p].sort((a, b) => a.name.localeCompare(b.name));
    this.toast(t('ts.restored', { name: p.name }));
  }

  exportPreset(p: Preset = this.draft) {
    const dropped = downloadPreset($state.snapshot(p) as Preset);
    this.toast(dropped ? t('ts.exportedDropped', { n: dropped }) : t('ts.exported', { name: i18n.name(p.name) }));
  }

  async importPreset() {
    const file = await pickFile('application/json,.json');
    if (!file) return;
    try {
      const p = await readPresetFile(file);
      if (this.isBuiltin(p.name)) p.name = `${p.name} (imported)`;
      await idbPut('presets', p.name.toLowerCase(), p);
      this.user = [...this.user.filter((u) => u.name !== p.name), p].sort((a, b) => a.name.localeCompare(b.name));
      this.toast(t('ts.imported', { name: p.name }));
    } catch { this.toast(t('ts.badFile')); }
  }

  async sharePreset(p: Preset = this.draft) {
    const snap = $state.snapshot(p) as Preset;
    const { dropped } = shareable(snap);
    const url = await shareUrl(snap);
    try {
      if (navigator.share && matchMedia('(pointer: coarse)').matches) await navigator.share({ title: `NeuroSync — ${i18n.name(p.name)}`, url });
      else { await navigator.clipboard.writeText(url); this.toast(dropped ? t('ts.linkCopiedDropped') : t('ts.linkCopied')); }
    } catch { /* user cancelled share sheet */ }
  }

  private async checkShareLink() {
    const token = presetTokenFromHash();
    if (!token) return;
    try { this.pendingShare = await decodePreset(token); }
    catch { this.toast(t('ts.badLink')); }
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
      this.toast(t('ts.addedShared', { name: p.name }));
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
    const name = this.devices.find((d) => d.id === id)?.label ?? t('dev.default');
    this.toast(ok || !id ? t('ts.output', { name }) : t('ts.outputFail'));
  }
  setPref<K extends 'highContrast' | 'reduceMotion'>(key: K, value: boolean) { this.settings[key] = value; this.save(); }
  cycleOrbSpeed() {
    this.settings.orbSpeed = (this.settings.orbSpeed + 1) % ORB_SPEEDS.length;
    haptic(8);                                       // the orb itself shows the new speed
    this.save();
  }
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
      title: i18n.name(this.draft.name), artist: 'NeuroSync',
      album: b ? `${i18n.band(this.draft.band)} · ${b.beat_hz} Hz` : t('st.ambienceOnly'),
      artwork: [{ src: `${import.meta.env.BASE_URL}icons/icon-512.png`, sizes: '512x512', type: 'image/png' }],
    });
  }
}

export const app = new AppState();
export { CATALOG };

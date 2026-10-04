// Per-device preferences in localStorage (guarded: private mode / blocked storage => defaults).
import { MASTER_GAIN_MAX, clamp } from '../domain/limits';

export interface Settings {
  masterVolume: number; lastPreset: string; disclaimerAccepted: boolean; fadeMinutes: number;
  highContrast: boolean; reduceMotion: boolean; sinkId: string; orbSpeed: number; lang: 'en' | 'zh' | ''; theme: 'classic' | 'pour';
  /** true once the person picked it themselves; otherwise the current product default applies */
  langChosen: boolean; themeChosen: boolean;
  /** '' = automatic: speaker-safe on phones and tablets, headphones on computers */
  listening: '' | 'headphones' | 'speaker';
}

export const DEFAULTS: Settings = {
  masterVolume: 0.5, lastPreset: 'Alpha Focus', disclaimerAccepted: false, fadeMinutes: 5,
  highContrast: false, reduceMotion: false, sinkId: '', orbSpeed: 1, lang: 'zh', theme: 'pour', langChosen: false, themeChosen: false, listening: '',
};
const KEY = 'neurosync.settings.v1';

export function loadSettings(): Settings {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? '{}') as Partial<Settings>;
    const s = { ...DEFAULTS, ...raw };
    s.masterVolume = clamp(Number(s.masterVolume), 0, MASTER_GAIN_MAX);
    s.orbSpeed = Math.round(clamp(Number(s.orbSpeed), 0, 2));
    // Product defaults: Simplified Chinese + Liquid design. Earlier visitors who never picked
    // (their saved values were just the old defaults) move to the new defaults; explicit choices stay.
    if (!s.langChosen || (s.lang !== 'en' && s.lang !== 'zh')) s.lang = 'zh';
    if (!s.themeChosen || (s.theme !== 'pour' && s.theme !== 'classic')) s.theme = 'pour';
    if (s.listening !== 'headphones' && s.listening !== 'speaker') s.listening = '';
    return s;
  } catch { return { ...DEFAULTS }; }
}

export function saveSettings(s: Settings): void {
  try { localStorage.setItem(KEY, JSON.stringify(s)); } catch { /* storage unavailable */ }
}

// Per-device preferences in localStorage (guarded: private mode / blocked storage => defaults).
import { MASTER_GAIN_MAX, clamp } from '../domain/limits';

export interface Settings {
  masterVolume: number; lastPreset: string; disclaimerAccepted: boolean; fadeMinutes: number;
  highContrast: boolean; reduceMotion: boolean; sinkId: string;
}

export const DEFAULTS: Settings = {
  masterVolume: 0.5, lastPreset: 'Alpha Focus', disclaimerAccepted: false, fadeMinutes: 5,
  highContrast: false, reduceMotion: false, sinkId: '',
};
const KEY = 'neurosync.settings.v1';

export function loadSettings(): Settings {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? '{}') as Partial<Settings>;
    const s = { ...DEFAULTS, ...raw };
    s.masterVolume = clamp(Number(s.masterVolume), 0, MASTER_GAIN_MAX);
    return s;
  } catch { return { ...DEFAULTS }; }
}

export function saveSettings(s: Settings): void {
  try { localStorage.setItem(KEY, JSON.stringify(s)); } catch { /* storage unavailable */ }
}

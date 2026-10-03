// Browser capability detection + the phone-specific workarounds (Phase 1 spikes).
export type OutputMode = 'direct' | 'element';

interface AudioSessionLike { type: string }
type SinkCapable = { setSinkId?: (id: string) => Promise<void> };

/** Phones/tablets: route audio through an <audio> element so it survives screen lock and
 *  gets lock-screen controls. Desktop: connect straight to the destination (lowest latency). */
export function preferredOutputMode(): OutputMode {
  if (typeof matchMedia === 'undefined') return 'direct';
  return matchMedia('(pointer: coarse)').matches ? 'element' : 'direct';
}

/** iOS 16.4+: declare a "playback" session so audio ignores the silent switch and keeps
 *  playing in the background. No-op elsewhere. */
export function declarePlaybackSession(): void {
  const nav = navigator as Navigator & { audioSession?: AudioSessionLike };
  try { if (nav.audioSession) nav.audioSession.type = 'playback'; } catch { /* unsupported */ }
}

/** Which compressed format to fetch for ambience. Ogg is smaller; AAC is the Safari fallback. */
export function preferredAmbienceExt(): 'ogg' | 'm4a' {
  if (typeof Audio === 'undefined') return 'ogg';
  return new Audio().canPlayType('audio/ogg; codecs="vorbis"') ? 'ogg' : 'm4a';
}

/** Output-device selection support (Chrome/Edge: AudioContext.setSinkId; media elements in
 *  Chrome/Edge/Firefox). Returns false when the selector should be hidden. */
export function canChooseOutput(mode: OutputMode): boolean {
  if (mode === 'direct') return typeof (AudioContext.prototype as SinkCapable).setSinkId === 'function';
  return typeof (HTMLMediaElement.prototype as SinkCapable).setSinkId === 'function';
}

export interface OutputDevice { id: string; label: string }

/** Device names require a media permission in Chromium; we only ask when the user opens the
 *  selector, and fall back to unnamed entries if they decline. */
export async function listOutputDevices(askPermission: boolean): Promise<OutputDevice[]> {
  if (!navigator.mediaDevices?.enumerateDevices) return [];
  let devices = await navigator.mediaDevices.enumerateDevices();
  const unnamed = devices.some((d) => d.kind === 'audiooutput' && !d.label);
  if (unnamed && askPermission) {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      s.getTracks().forEach((t) => t.stop());
      devices = await navigator.mediaDevices.enumerateDevices();
    } catch { /* declined: keep generic labels */ }
  }
  return devices.filter((d) => d.kind === 'audiooutput' && d.deviceId !== 'default' && d.deviceId !== 'communications')
    .map((d, i) => ({ id: d.deviceId, label: d.label || `Output ${i + 1}` }));
}

// Subtle vibration feedback on Android (Galaxy, Pixel …). iOS/desktop: silently unsupported.
export function haptic(ms = 10): void {
  try { (navigator as Navigator & { vibrate?: (p: number) => boolean }).vibrate?.(ms); } catch { /* no-op */ }
}

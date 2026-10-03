// Service worker registration + "Offline ready" detection (all bundled sounds cached in
// this browser's format). Production builds only.
import { registerSW } from 'virtual:pwa-register';
import { CATALOG } from '../audio/buffers';
import { preferredAmbienceExt } from '../audio/platform';

export const offlineSupported = import.meta.env.PROD && 'serviceWorker' in navigator && 'caches' in globalThis;

async function controlled(): Promise<void> {
  if (navigator.serviceWorker.controller) return;
  await new Promise<void>((r) => navigator.serviceWorker.addEventListener('controllerchange', () => r(), { once: true }));
}

const soundUrls = () => {
  const ext = preferredAmbienceExt();
  return CATALOG.map((s) => `${location.origin}/ambience/${s.file.replace(/\.ogg$/, '.' + ext)}`);
};

export async function allSoundsCached(): Promise<boolean> {
  const cache = await caches.open('ambience');      // same cache the service worker serves from
  return (await Promise.all(soundUrls().map((u) => cache.match(u)))).every(Boolean);
}

/** Store every bundled sound (this browser's format) so the whole app works offline. */
async function cacheAllSounds(): Promise<void> {
  const cache = await caches.open('ambience');
  const missing = (await Promise.all(soundUrls().map(async (u) => ((await cache.match(u)) ? null : u)))).filter((u): u is string => !!u);
  await Promise.all(missing.map((u) => cache.add(u).catch(() => undefined)));
}

export function setupOffline(onReady: (ready: boolean) => void): void {
  if (!offlineSupported) return;
  registerSW({ immediate: true });
  void (async () => {
    await navigator.serviceWorker.ready;
    await controlled();
    await cacheAllSounds();
    onReady(await allSoundsCached());
  })();
}

export const isIos = () => /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
export const isStandalone = () => matchMedia('(display-mode: standalone)').matches || (navigator as Navigator & { standalone?: boolean }).standalone === true;

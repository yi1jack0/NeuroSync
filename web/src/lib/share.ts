// Preset <-> URL fragment. The fragment never reaches the server, so sharing stays private.
import { LOCAL_PREFIX, type Preset, parsePreset } from '../domain/preset';

const b64url = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const fromB64url = (s: string) => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/')), (c) => c.charCodeAt(0));

async function pipe(data: Uint8Array, stream: CompressionStream | DecompressionStream): Promise<Uint8Array> {
  const out = new Blob([data as Uint8Array<ArrayBuffer>]).stream().pipeThrough(stream);
  return new Uint8Array(await new Response(out).arrayBuffer());
}

/** Local (device-only) sounds cannot travel in a link: they are dropped and counted. */
export function shareable(p: Preset): { preset: Preset; dropped: number } {
  const channels = p.channels.filter((c) => !c.path.startsWith(LOCAL_PREFIX));
  return { preset: { ...p, channels }, dropped: p.channels.length - channels.length };
}

export async function encodePreset(p: Preset): Promise<string> {
  const json = new TextEncoder().encode(JSON.stringify(shareable(p).preset));
  return b64url(await pipe(json, new CompressionStream('deflate-raw')));
}

export async function decodePreset(token: string): Promise<Preset> {
  if (token.length > 8000) throw new Error('link too long');
  const json = await pipe(fromB64url(token), new DecompressionStream('deflate-raw'));
  return parsePreset(JSON.parse(new TextDecoder().decode(json)));   // validated + clamped
}

export async function shareUrl(p: Preset): Promise<string> {
  return `${location.origin}${location.pathname}#p=${await encodePreset(p)}`;
}

export function presetTokenFromHash(hash = location.hash): string | null {
  const m = /^#p=([A-Za-z0-9_-]+)$/.exec(hash);
  return m ? m[1]! : null;
}

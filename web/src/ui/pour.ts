// "Liquid" theme: procedural acrylic-pour painting (Prussian Blue Hue, Turquoise Deep,
// a trace of Iridescent Bright Gold) with wet light-and-shadow shading.
// Pure functions on ImageData: rendered once per size, never per frame.

type RGB = [number, number, number];

export const POUR = {
  prussian: ['#050b14', '#08131f', '#0d2136', '#16375a'] as const,
  turquoise: '#1FB5AD',
  turquoiseDeep: '#0B7F86',
  gold: '#D9B45A',
};

const hex = (h: string): RGB => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const P0 = hex('#050b14'), P1 = hex('#0a1a2c'), P2 = hex('#123252'), P3 = hex('#1b4a70');
const T0 = hex('#0b7f86'), T1 = hex('#2bb7ad'), G0 = hex('#e8c66d'), G1 = hex('#9fd8c9');

const smooth = (e0: number, e1: number, x: number) => { const t = Math.min(Math.max((x - e0) / (e1 - e0), 0), 1); return t * t * (3 - 2 * t); };
const mix = (a: RGB, b: RGB, t: number): RGB => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

/** Seeded value noise + fBm + domain warping (Inigo Quilez style): marbled, flowing fields. */
export function makeNoise(seed: number, octaves = 4, warp = 4, warp2 = 3.5) {
  const perm = new Uint16Array(512);
  let s = seed >>> 0 || 1;
  const rnd = () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
  const p = Array.from({ length: 256 }, (_, i) => i);
  for (let i = 255; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [p[i], p[j]] = [p[j]!, p[i]!]; }
  for (let i = 0; i < 512; i++) perm[i] = p[i & 255]!;
  const vals = new Float32Array(256).map(() => rnd());
  const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
  const fade = (t: number) => t * t * (3 - 2 * t);
  const value = (x: number, y: number) => {
    const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
    const h = (a: number, b: number) => vals[perm[(perm[a & 255]! + b) & 511]! & 255]!;
    const u = fade(xf), v = fade(yf);
    return lerp(lerp(h(xi, yi), h(xi + 1, yi), u), lerp(h(xi, yi + 1), h(xi + 1, yi + 1), u), v);
  };
  const fbm = (x: number, y: number) => {
    let a = 0.5, f = 1, sum = 0;
    let norm = 0;
    for (let o = 0; o < octaves; o++) { sum += a * value(x * f, y * f); norm += a; f *= 2.03; a *= 0.5; }
    return sum / norm;
  };
  /** Height of the "paint" at (x, y): two levels of domain warping give pour-like flows. */
  return (x: number, y: number) => {
    const qx = fbm(x, y), qy = fbm(x + 5.2, y + 1.3);
    const rx = fbm(x + warp * qx + 1.7, y + warp * qy + 9.2), ry = fbm(x + warp * qx + 8.3, y + warp * qy + 2.8);
    return fbm(x + warp2 * rx, y + warp2 * ry);
  };
}

/** Colour of the paint for height h (0..1): mostly Prussian, turquoise ribbons, a gold lace line. */
function paint(h: number, detail: number, soft = 1): RGB {
  let c = mix(P0, P1, smooth(0.18, 0.42, h));
  c = mix(c, P2, smooth(0.42, 0.6, h));
  c = mix(c, P3, smooth(0.6, 0.66, h) * (1 - smooth(0.7, 0.78, h)));
  const ribbon = smooth(0.6, 0.665, h) * (1 - smooth(0.69, 0.74, h));      // turquoise band
  c = mix(c, mix(T0, T1, detail), ribbon * 0.85);
  const lace = Math.exp(-(((h - 0.7) / (0.0045 * soft)) ** 2));                    // a thin iridescent gold line
  c = mix(c, mix(G0, G1, detail * 0.35), lace * 0.55);
  const lace2 = Math.exp(-(((h - 0.58) / (0.003 * soft)) ** 2));                   // fainter secondary lacing
  c = mix(c, T1, lace2 * 0.25);
  return c;
}

/**
 * Paints the pour into an ImageData of w x h (low resolution: the browser upscales it smoothly,
 * which suits the soft, wet look). Light comes from the upper left; specular highlights give
 * the glossy sheen; a vignette keeps the edges dark for night use.
 */
/** zoom > 1 magnifies the painting around its centre (same composition, larger and calmer flows). */
export interface PourOptions { seed?: number; scale?: number; brightness?: number; octaves?: number; warp?: number; warp2?: number; zoom?: number; soft?: number }
export function renderPour(w: number, h: number, o: PourOptions = {}): ImageData {
  // Defaults chosen from side-by-side variants: calm, dark centre (orb + text sit on deep Prussian),
  // turquoise rivers and gold lacing toward the edges.
  const { seed = 42, scale = 1.7, brightness = 0.78, octaves = 3, warp = 3.6, warp2 = 2.4, zoom = 2.56, soft = 1 } = o;   // background: 160% x 160%
  const field = makeNoise(seed, octaves, warp, warp2);
  const img = new ImageData(w, h);
  const hts = new Float32Array((w + 2) * (h + 2));
  const aspect = h / w;
  for (let y = -1; y <= h; y++)
    for (let x = -1; x <= w; x++)
      hts[(y + 1) * (w + 2) + (x + 1)] = field(((x / w - 0.5) / zoom + 0.5) * scale, ((y / h - 0.5) / zoom + 0.5) * scale * aspect);
  const L = [-0.45, -0.62, 0.64];
  const Ln = Math.hypot(L[0]!, L[1]!, L[2]!);
  const lx = L[0]! / Ln, ly = L[1]! / Ln, lz = L[2]! / Ln;
  const bump = Math.max(w, h) * 1.1 * zoom;   // keep the same wet sheen when magnified
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = (y + 1) * (w + 2) + (x + 1);
      const v = hts[i]!;
      const dx = (hts[i + 1]! - hts[i - 1]!) * bump, dy = (hts[i + w + 2]! - hts[i - w - 2]!) * bump;
      const nl = Math.hypot(dx, dy, 1);
      const nx = -dx / nl, ny = -dy / nl, nz = 1 / nl;
      const diff = Math.max(0, nx * lx + ny * ly + nz * lz);
      // Blinn-Phong half vector with the viewer straight above: wet, glossy paint
      const hx = lx, hy = ly, hz = lz + 1, hl = Math.hypot(hx, hy, hz);
      const spec = Math.max(0, (nx * hx + ny * hy + nz * hz) / hl) ** 60;
      let c = paint(v, (x + y) / (w + h), soft);
      const shade = 0.62 + 0.5 * diff;
      const u = x / w - 0.5, t = y / h - 0.5;
      const vig = 1 - Math.min(1, (u * u + t * t) * 1.5);
      const k = brightness * shade * (0.55 + 0.45 * vig);
      c = [c[0] * k + 210 * spec * 0.28 * vig, c[1] * k + 230 * spec * 0.28 * vig, c[2] * k + 240 * spec * 0.28 * vig];
      const o = (y * w + x) * 4;
      img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = 255;
    }
  }
  return img;
}

/** Square marble texture for the liquid orb (rotated slowly inside its glass shell). */
export function marbleTexture(size: number, seed = 777): HTMLCanvasElement {
  // Smooth, silky lines: fewer fine octaves, gentler warping, wider (soft) lacing, then a
  // one-off blur so curves never look jagged when the texture is scaled up and rotated.
  const raw = document.createElement('canvas');
  raw.width = raw.height = size;
  raw.getContext('2d')!.putImageData(renderPour(size, size, { seed, scale: 1.6, brightness: 1.15, octaves: 3, warp: 3.4, warp2: 2.8, zoom: 1.6, soft: 2.6 }), 0, 0);
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const ctx = c.getContext('2d')!;
  ctx.filter = `blur(${Math.max(1, size / 360)}px)`;
  ctx.drawImage(raw, 0, 0);
  return c;
}

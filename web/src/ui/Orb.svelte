<script lang="ts">
  // Breathing orb locked to the beat, folded down by octaves to a slow <= 0.6 Hz breath (never a
  // flicker), floating on a slow, non-repeating drift with a wandering highlight.
  // ~30 fps while playing; zero work when paused, hidden, off-screen or reduced-motion.
  import { ORB_SPEEDS, visualPulseHz } from '../domain/bands';
  import { t } from '../lib/i18n.svelte';
  let { color, beat, playing, reduceMotion = false, flat = false, speed = 1 }:
    { color: string; beat: number; playing: boolean; reduceMotion?: boolean; flat?: boolean; speed?: number } = $props();

  let canvas: HTMLCanvasElement;
  let energy = 0, target = 0, raf = 0, last = 0, visible = true;
  // Integrated clocks (not now * rate): changing speed keeps phase continuous, no jump.
  let phaseAcc = 0.25, driftClock = 0, prevNow = 0;
  const mode = $derived(ORB_SPEEDS[speed] ?? ORB_SPEEDS[1]);
  const pulse = $derived(visualPulseHz(beat, mode.ceiling));   // Calm: 10 Hz beat -> one breath every 3.2 s
  const TAU = Math.PI * 2;
  const motion = $derived(!reduceMotion && !(typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches));

  function rgb(hex: string): [number, number, number] {
    const m = /^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(hex.trim());
    return m ? [parseInt(m[1]!, 16), parseInt(m[2]!, 16), parseInt(m[3]!, 16)] : [45, 212, 232];
  }
  const rgba = (c: [number, number, number], a: number) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
  const mix = (c: [number, number, number], k: number): [number, number, number] =>
    k >= 0 ? [c[0] + (255 - c[0]) * k, c[1] + (255 - c[1]) * k, c[2] + (255 - c[2]) * k] : [c[0] * (1 + k), c[1] * (1 + k), c[2] * (1 + k)];

  function draw(now: number) {
    const ctx = canvas?.getContext('2d');
    if (!ctx) return;
    const dpr = Math.min(devicePixelRatio || 1, 2);
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) { canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr); }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    energy = motion ? energy + (target - energy) * (target > energy ? 0.05 : 0.025) : target;   // no easing under reduced motion
    const dt = prevNow ? Math.min((now - prevNow) / 1000, 0.1) : 0;
    prevNow = now;
    if (playing && motion) { phaseAcc = (phaseAcc + dt * pulse) % 1; driftClock += dt * mode.drift; }
    const phase = playing && motion ? phaseAcc : 0.25;
    const breath = 0.5 - 0.5 * Math.cos(2 * Math.PI * phase);
    const base = Math.min(w, h) * 0.2;
    const r = base * (1 + 0.07 * breath * energy);
    // Slow floating drift: two incommensurate periods (31 s / 23 s) so the path never visibly repeats.
    const t = driftClock;
    const drift = playing && motion ? Math.min(w, h) * 0.035 * energy : 0;
    const cx = w / 2 + Math.sin((t * TAU) / 31) * drift;
    const cy = h / 2 + Math.sin((t * TAU) / 23 + 1.3) * drift * 0.8;
    const ox = w / 2, oy = h / 2;   // the faint orbit ring stays put: a calm frame of reference
    const c = rgb(color);
    if (flat) {   // high contrast: outlines only
      ctx.lineWidth = 3; ctx.strokeStyle = '#fff'; ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.stroke();
      ctx.lineWidth = 2; ctx.strokeStyle = '#ff0'; ctx.beginPath(); ctx.arc(cx, cy, r * (1 + 0.5 * breath * energy), 0, 7); ctx.stroke();
      return;
    }
    const reach = Math.min(w, h) * 0.46;   // leaves room for the drift: the glow never hits the canvas edge
    const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, reach);
    glow.addColorStop(0, rgba(c, 0.1 + 0.22 * energy + 0.08 * breath * energy));
    glow.addColorStop(0.45, rgba(c, 0.03 + 0.1 * energy));
    glow.addColorStop(1, rgba(c, 0));
    ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(cx, cy, reach, 0, 7); ctx.fill();
    if (energy > 0.01 && motion) {
      for (let k = 0; k < 3; k++) {
        const q = (phase + k / 3) % 1;
        ctx.strokeStyle = rgba(c, 0.32 * energy * (1 - q) ** 2); ctx.lineWidth = 1.4;
        ctx.beginPath(); ctx.arc(cx, cy, r * (1.05 + 1.25 * q), 0, 7); ctx.stroke();
      }
    }
    ctx.strokeStyle = 'rgba(255,255,255,.07)'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(ox, oy, base * 1.9, 0, 7); ctx.stroke();
    ctx.globalAlpha = 0.55 + 0.45 * energy;
    const core = ctx.createRadialGradient(cx - r * 0.35, cy - r * 0.4, 0, cx - r * 0.35, cy - r * 0.4, r * 1.5);
    core.addColorStop(0, rgba(mix(c, 0.75), 1)); core.addColorStop(0.45, rgba(c, 1)); core.addColorStop(1, rgba(mix(c, -0.7), 1));
    ctx.fillStyle = core; ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.fill();
    // Highlight wanders slowly across the glass (~40 s loop).
    const sw = playing && motion ? energy : 0;
    const hx = cx - r * (0.3 + 0.08 * Math.sin((t * TAU) / 40) * sw);
    const hy = cy - r * (0.4 + 0.06 * Math.cos((t * TAU) / 40) * sw);
    const spec = ctx.createRadialGradient(hx, hy, 0, hx, hy, r * 0.55);
    spec.addColorStop(0, 'rgba(255,255,255,.35)'); spec.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = spec; ctx.beginPath(); ctx.arc(hx, hy + r * 0.02, r * 0.55, 0, 7); ctx.fill();
    ctx.globalAlpha = 1;
  }

  function loop(now: number) {
    raf = 0;
    if (!visible || document.hidden) return;
    if (now - last >= 33) { last = now; draw(now); }
    const settling = Math.abs(target - energy) > 0.005;
    if ((playing && motion) || settling) raf = requestAnimationFrame(loop);
  }
  const kick = () => { if (!raf) raf = requestAnimationFrame(loop); };

  $effect(() => { target = playing ? 1 : 0; void color; void flat; void motion; kick(); });
  $effect(() => {
    const ro = new ResizeObserver(() => draw(performance.now()));
    const io = new IntersectionObserver(([e]) => { visible = !!e?.isIntersecting; kick(); });
    ro.observe(canvas); io.observe(canvas);
    const vis = () => kick();
    document.addEventListener('visibilitychange', vis);
    return () => { ro.disconnect(); io.disconnect(); document.removeEventListener('visibilitychange', vis); cancelAnimationFrame(raf); };
  });
</script>

<div class="wrap" role="img" aria-label={t('orb.img', { p: pulse.toFixed(2), b: beat.toFixed(1) })}>
  <canvas bind:this={canvas} aria-hidden="true"></canvas>
</div>

<style>.wrap, canvas { width: 100%; height: 100%; display: block; }</style>

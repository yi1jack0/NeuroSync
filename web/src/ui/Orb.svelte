<script lang="ts">
  // Breathing orb locked to the beat, folded down by octaves to <= 1.25 Hz (never a flicker).
  // ~30 fps while playing; zero work when paused, hidden, off-screen or reduced-motion.
  import { visualPulseHz } from '../domain/bands';
  let { color, beat, playing, reduceMotion = false, flat = false }:
    { color: string; beat: number; playing: boolean; reduceMotion?: boolean; flat?: boolean } = $props();

  let canvas: HTMLCanvasElement;
  let energy = 0, target = 0, raf = 0, last = 0, visible = true;
  const t0 = performance.now();
  const pulse = $derived(visualPulseHz(beat));
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
    const phase = playing && motion ? (((now - t0) / 1000) * pulse) % 1 : 0.25;
    const breath = 0.5 - 0.5 * Math.cos(2 * Math.PI * phase);
    const base = Math.min(w, h) * 0.2;
    const r = base * (1 + 0.07 * breath * energy);
    const cx = w / 2, cy = h / 2;
    const c = rgb(color);
    if (flat) {   // high contrast: outlines only
      ctx.lineWidth = 3; ctx.strokeStyle = '#fff'; ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.stroke();
      ctx.lineWidth = 2; ctx.strokeStyle = '#ff0'; ctx.beginPath(); ctx.arc(cx, cy, r * (1 + 0.5 * breath * energy), 0, 7); ctx.stroke();
      return;
    }
    const reach = Math.min(w, h) * 0.5;
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
    ctx.beginPath(); ctx.arc(cx, cy, base * 1.9, 0, 7); ctx.stroke();
    ctx.globalAlpha = 0.55 + 0.45 * energy;
    const core = ctx.createRadialGradient(cx - r * 0.35, cy - r * 0.4, 0, cx - r * 0.35, cy - r * 0.4, r * 1.5);
    core.addColorStop(0, rgba(mix(c, 0.75), 1)); core.addColorStop(0.45, rgba(c, 1)); core.addColorStop(1, rgba(mix(c, -0.7), 1));
    ctx.fillStyle = core; ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.fill();
    const spec = ctx.createRadialGradient(cx - r * 0.3, cy - r * 0.4, 0, cx - r * 0.3, cy - r * 0.4, r * 0.55);
    spec.addColorStop(0, 'rgba(255,255,255,.35)'); spec.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = spec; ctx.beginPath(); ctx.arc(cx - r * 0.3, cy - r * 0.38, r * 0.55, 0, 7); ctx.fill();
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

<div class="wrap" role="img" aria-label="Visualizer pulsing at {pulse.toFixed(2)} per second, synced to a {beat.toFixed(1)} hertz beat">
  <canvas bind:this={canvas} aria-hidden="true"></canvas>
</div>

<style>.wrap, canvas { width: 100%; height: 100%; display: block; }</style>

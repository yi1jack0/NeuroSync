<script lang="ts">
  // Full-screen acrylic-pour painting for the Liquid theme. Rendered once per screen size
  // (off the critical path, at ~1/2 resolution: the browser's smooth upscale suits the wet look).
  import { renderPour } from './pour';
  let canvas: HTMLCanvasElement;
  let lastKey = '';

  function draw() {
    const w = Math.min(720, Math.max(160, Math.round(innerWidth / 2)));
    const h = Math.min(1000, Math.max(160, Math.round(innerHeight / 2)));
    const key = `${Math.round(w / 20)}x${Math.round(h / 20)}`;          // ignore tiny resizes (mobile toolbars)
    if (key === lastKey) return;
    lastKey = key;
    canvas.width = w; canvas.height = h;
    canvas.getContext('2d')!.putImageData(renderPour(w, h), 0, 0);
    canvas.dataset.painted = '1';
  }
  $effect(() => {
    const run = () => ('requestIdleCallback' in window ? requestIdleCallback(draw, { timeout: 300 }) : setTimeout(draw, 0));
    run();
    let t: ReturnType<typeof setTimeout>;
    const onResize = () => { clearTimeout(t); t = setTimeout(run, 250); };
    addEventListener('resize', onResize);
    return () => removeEventListener('resize', onResize);
  });
</script>

<canvas class="pour" bind:this={canvas} aria-hidden="true"></canvas>

<style>
  /* soft blur = wet paint; slight over-scale hides the blurred edge */
  .pour { position: fixed; inset: 0; width: 100vw; height: 100dvh; z-index: -2; display: block; pointer-events: none;
    filter: blur(1.2px); transform: scale(1.03); }
  :global(.hc) .pour { display: none; }
</style>
